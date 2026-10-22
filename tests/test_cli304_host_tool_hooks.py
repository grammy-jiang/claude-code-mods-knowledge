"""Host-level native tool interception is separate from reloadable Mods hooks."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from mods_knowledge.guarded_rollout import (
    GuardedRollout,
    UpdateBlocked,
    fixture_verifier_for_tests_only,
)

ROOT = Path(__file__).resolve().parents[1]


def load_script(filename: str):
    src = ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location("qa_" + filename.replace(".", "_"), src)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = load_script("cli304_host_tool_gate.py")
SETTINGS = load_script("cli304_host_tool_settings.py")


@pytest.fixture
def healthy(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    input_file = workspace / "readme.txt"
    input_file.write_text("QA benign content\n")
    sid = "11111111-2222-4333-8444-555555555555"
    state = GuardedRollout(tmp_path / "cohort")
    state.create([sid], good_version="0.0.1", good_tree="a" * 64)
    secret = state.enroll(sid)
    challenge = state.challenge(sid, secret)
    proof = tmp_path / "bootstrap.test.json"
    proof.write_text(
        json.dumps(
            {
                "TEST_ONLY": True,
                "session": sid,
                "challenge": challenge["challenge"],
                "tree": challenge["tree_sha"],
                "epoch": challenge["epoch"],
            }
        )
    )
    state.attest(sid, secret, proof, verifier=fixture_verifier_for_tests_only)
    state.ready()
    private_secret = tmp_path / "secret"
    private_secret.write_text(secret + "\n")
    private_secret.chmod(0o600)
    return state, sid, secret, workspace, input_file, private_secret


def event(kind: str, session: str, path: Path, *, tool: str = "Read", tool_id="toolu_QA_00001"):
    return {
        "hook_event_name": kind,
        "session_id": session,
        "tool_use_id": tool_id,
        "tool_name": tool,
        "tool_input": {"file_path": str(path)},
        "cwd": str(path.parent),
    }


def test_real_lifetime_tracked_from_pre_to_post_not_just_single_check(healthy):
    gate, sid, secret, workspace, file, _ = healthy
    before = event("PreToolUse", sid, file)
    GATE.handle(gate, secret, before, phase="pre", workspace=workspace)
    assert gate.status()["outstanding_permits"] == 1
    gate.begin(transaction_id="testing", new_version="0.0.2", new_tree="b" * 64)
    with pytest.raises(UpdateBlocked, match="INFLIGHT_PROTECTED_OP"):
        gate.acknowledge(sid, secret)
    after = event("PostToolUse", sid, file)
    GATE.handle(gate, secret, after, phase="post", workspace=workspace)
    assert gate.status()["outstanding_permits"] == 0
    gate.acknowledge(sid, secret)
    assert gate.status()["acknowledged"] == 1


def test_pretool_gate_denies_every_mutating_or_unknown_tool_even_when_ready(healthy):
    gate, sid, secret, workspace, file, _ = healthy
    for tool in ("Write", "Edit", "Bash", "mcp__files__write", "WebFetch", "Unknown"):
        with pytest.raises(UpdateBlocked, match="DENIES_UNREVIEWED_TOOL"):
            GATE.handle(
                gate,
                secret,
                event("PreToolUse", sid, file, tool=tool),
                phase="pre",
                workspace=workspace,
            )
    assert gate.status()["outstanding_permits"] == 0


def test_session_identity_and_both_native_events_are_mandatory(healthy):
    gate, sid, secret, workspace, file, _ = healthy
    cases = [
        (event("PreToolUse", "unknown", file), "UNREGISTERED_OR_UNAUTHORIZED"),
        (event("PostToolUse", sid, file), "MISSING_NATIVE_TOOL_START"),
        (event("PreToolUse", sid, file, tool_id="not!valid"), "INVALID_NATIVE_TOOL_ID"),
        (event("UserPromptSubmit", sid, file), "HOST_GATE_WRONG_EVENT"),
    ]
    for ev, message in cases:
        with pytest.raises(UpdateBlocked, match=message):
            GATE.handle(
                gate,
                secret,
                ev,
                phase="post" if ev["hook_event_name"] == "PostToolUse" else "pre",
                workspace=workspace,
            )


def test_unfinished_tool_and_replayed_pretool_refuse_quiescence(healthy):
    gate, sid, secret, workspace, file, _ = healthy
    ev = event("PreToolUse", sid, file)
    GATE.handle(gate, secret, ev, phase="pre", workspace=workspace)
    with pytest.raises(UpdateBlocked, match="DUPLICATE_NATIVE_TOOL_ID"):
        GATE.handle(gate, secret, ev, phase="pre", workspace=workspace)
    reopened = GuardedRollout(gate.directory)
    assert reopened.status()["outstanding_permits"] == 1
    reopened.begin(transaction_id="waiting", new_version="0.0.2", new_tree="b" * 64)
    with pytest.raises(UpdateBlocked, match="INFLIGHT_PROTECTED_OP"):
        reopened.acknowledge(sid, secret)


def test_path_confined_read_and_symlink_escape_denied(healthy, tmp_path: Path):
    gate, sid, secret, workspace, file, _ = healthy
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    bad_link = workspace / "escape.txt"
    bad_link.symlink_to(outside)
    for path in (outside, bad_link, workspace / "not-a-file"):
        with pytest.raises(UpdateBlocked, match="READ_OUTSIDE|PATH_NOT_EXISTING"):
            GATE.handle(
                gate,
                secret,
                event("PreToolUse", sid, path),
                phase="pre",
                workspace=workspace,
            )
    assert gate.status()["outstanding_permits"] == 0


def test_paused_host_cannot_request_native_tools(healthy):
    gate, sid, secret, workspace, file, _ = healthy
    gate.begin(transaction_id="frozen", new_version="0.0.2", new_tree="b" * 64)
    with pytest.raises(UpdateBlocked, match="NATIVE_TOOL_FROZEN"):
        GATE.handle(gate, secret, event("PreToolUse", sid, file), phase="pre", workspace=workspace)


def test_settings_generator_pins_block_on_hook_failures(healthy):
    state, _, _, workspace, _, private_secret = healthy
    output = SETTINGS.build_settings(
        python=Path(sys.executable).resolve(),
        script=ROOT / "scripts/cli304_host_tool_gate.py",
        state_root=state.directory,
        secret_file=private_secret,
        workspace=workspace,
    )
    assert set(output["hooks"]) == {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
    for name, handlers in output["hooks"].items():
        assert handlers[0]["matcher"] == ""
        command = handlers[0]["hooks"][0]
        assert command["onFailure"] == "block"
        assert command["timeout"] == 12
        assert command["command"] == str(Path(sys.executable).resolve())
        assert command["args"][0] == str(ROOT / "scripts/cli304_host_tool_gate.py")
        assert (
            command["args"][2]
            == {"PreToolUse": "pre", "PostToolUse": "post", "PostToolUseFailure": "failure"}[name]
        )
    assert private_secret.read_text().strip() not in json.dumps(output)


def test_settings_generator_rejects_insecure_secret(healthy):
    state, _, _, workspace, _, private_secret = healthy
    private_secret.chmod(0o644)
    with pytest.raises(ValueError, match="UNSAFE_PRIVATE_SECRET"):
        SETTINGS.build_settings(
            python=Path(sys.executable).resolve(),
            script=ROOT / "scripts/cli304_host_tool_gate.py",
            state_root=state.directory,
            secret_file=private_secret,
            workspace=workspace,
        )


def test_native_hook_entrypoint_exit_two_on_corrupt_input(healthy, monkeypatch, capsys):
    state, sid, secret, workspace, file, private_secret = healthy
    from io import BytesIO

    class FakeStdin:
        buffer = BytesIO(b'{"hook_event_name":"PreToolUse","tool_name":"Write"}')

    monkeypatch.setattr(GATE.sys, "stdin", FakeStdin())
    monkeypatch.setattr(
        GATE.sys,
        "argv",
        [
            "cli304_host_tool_gate.py",
            "--phase",
            "pre",
            "--state-root",
            str(state.directory),
            "--secret-file",
            str(private_secret),
            "--workspace",
            str(workspace),
        ],
    )
    assert GATE.main() == 2
    assert "HOST_GATE_REFUSED" in capsys.readouterr().err
    assert state.status()["outstanding_permits"] == 0


def test_tool_post_failure_event_releases_precisely_one_permit(healthy):
    gate, sid, secret, workspace, file, _ = healthy
    ev = event("PreToolUse", sid, file)
    GATE.handle(gate, secret, ev, phase="pre", workspace=workspace)
    ev["hook_event_name"] = "PostToolUseFailure"
    GATE.handle(gate, secret, ev, phase="failure", workspace=workspace)
    with pytest.raises(UpdateBlocked, match="MISSING_NATIVE_TOOL_START"):
        GATE.handle(gate, secret, ev, phase="failure", workspace=workspace)
    assert gate.status()["outstanding_permits"] == 0
