"""P5 current-target Pi native: preflight->model->BUFFERED postflight, no bypass.

All fake model tools are synthetic and no real network, provider or model is
called by these tests. Boundary tests assert the model backend is not probed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mods_knowledge.compiler import build_artifacts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_p5_pi_native_302_gated.py"


def module():
    spec = importlib.util.spec_from_file_location("p5_pi302_native", SCRIPT)
    assert spec is not None and spec.loader is not None
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


@pytest.fixture()
def reviewed_dist(tmp_path: Path):
    dist = tmp_path / "dist"
    exe = shutil.which("git")
    assert exe
    sha = subprocess.check_output(  # noqa: S603 - read-only native Git revision
        [exe, "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    build_artifacts(
        ROOT,
        dist,
        api_version="2.1.302",
        surface="cli",
        knowledge_version="0.4.12",
        package_version="0.4.12-test.1",
        source_revision=sha,
    )
    installed = tmp_path / "installed"
    installed.mkdir()
    from shutil import copytree

    copytree(
        dist / "common/claude-code-mods-development", installed / "claude-code-mods-development"
    )
    return dist, installed / "claude-code-mods-development"


def synthetic_native_events(case: dict, *, answer: str, skill_root: Path, skill: bool):
    events = [
        {
            "type": "message_end",
            "message": {"role": "user", "content": [{"type": "text", "text": case["prompt"]}]},
        },
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "provider": "mac-qwen",
                "model": "qwen36-35b-a3b-mtp",
                "stopReason": "stop",
                "content": [{"type": "text", "text": answer}],
            },
        },
    ]
    if skill:
        events.extend(
            [
                {
                    "type": "tool_execution_start",
                    "toolName": "read",
                    "toolCallId": "skill1",
                    "args": {"path": str(skill_root / "SKILL.md")},
                },
                {
                    "type": "tool_execution_end",
                    "toolName": "read",
                    "toolCallId": "skill1",
                    "isError": False,
                },
                {
                    "type": "tool_execution_start",
                    "toolName": "read",
                    "toolCallId": "ref1",
                    "args": {"path": str(skill_root / "references/events.md")},
                },
                {
                    "type": "tool_execution_end",
                    "toolName": "read",
                    "toolCallId": "ref1",
                    "isError": False,
                },
            ]
        )
    events.append({"type": "agent_end"})
    return events


def invoke(
    mod,
    *,
    case_id: str,
    dist: Path,
    installed: Path,
    dest: Path,
    with_model: bool = True,
    answer: str = "",
    expected_skill: bool = True,
):
    counters = {"health": 0, "model": 0}

    def healthy():
        counters["health"] += 1

    def fake_model(case, skill_root, private_root):
        counters["model"] += 1
        events = synthetic_native_events(
            case, answer=answer, skill_root=skill_root, skill=expected_skill
        )
        # The native wire is ALWAYS private, even for a successful model final.
        wire = private_root / "native-events.private.jsonl"
        wire.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        wire.chmod(0o600)
        return events, 0, False, False, hashlib.sha256(wire.read_bytes()).hexdigest()

    result = mod.run_case(
        case_id,
        root=ROOT,
        dist=dist,
        skill_root=installed,
        evidence_dir=dest,
        run_model=with_model,
        observed_claude_version="2.1.302 (Claude Code)",
        observed_pi_version="1.3.0",
        health_check=healthy,
        model_runner=fake_model,
    )
    return result, counters


def test_future_version_is_refused_before_any_model_network_or_codegen(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    result, calls = invoke(
        mod,
        case_id="BOUND-VERSION-NEW",
        dist=dist,
        installed=installed,
        dest=tmp_path / "b",
    )
    assert result["action"] == "abstain_before_model"
    assert result["model_requests_performed"] == 0
    assert result["raw_model_output_delivered"] is False
    assert result["stable_release_authorized"] is False
    assert calls == {"health": 0, "model": 0}
    assert not (tmp_path / "b/native-events.private.jsonl").exists()


def test_positive_requires_real_buffered_exact_source_and_forbids_raw_release(
    reviewed_dist, tmp_path
):
    mod = module()
    dist, installed = reviewed_dist
    answer = (
        "K-0040 https://code.claude.com/docs/en/plugins/mods/events#observe-an-event\n"
        "K-0064 https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function"
    )
    result, calls = invoke(
        mod,
        case_id="POS-E-01",
        dist=dist,
        installed=installed,
        dest=tmp_path / "p",
        answer=answer,
    )
    assert calls == {"health": 1, "model": 1}
    assert result["gate_action"] == "allow_structural_only"
    assert result["raw_model_output_delivered"] is False
    assert result["semantic_correctness_verified"] is False
    assert result["actual_skill_read_observed"] is True
    assert result["stable_release_authorized"] is False
    saved = json.dumps(result)
    assert "K-0040 https" not in saved
    assert "native-events.private.jsonl" not in saved


def test_cited_claim_without_own_link_blocked_even_when_others_are_correct(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    answer = (
        "K-0040 https://code.claude.com/docs/en/plugins/mods/events#observe-an-event\n"
        "K-0064 https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function\n"
        "K-0041 K-0042"
    )
    result, calls = invoke(
        mod,
        case_id="POS-E-01",
        dist=dist,
        installed=installed,
        dest=tmp_path / "missing",
        answer=answer,
    )
    assert calls == {"health": 1, "model": 1}
    assert result["gate_action"] == "block_candidate"
    assert "missing_exact_approved_claim_sources" in result["gate_reason_codes"]
    assert result["raw_model_output_delivered"] is False


def test_negative_stays_outside_skill_and_no_source_laundering(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    result, calls = invoke(
        mod,
        case_id="NEG-TYPESCRIPT",
        dist=dist,
        installed=installed,
        dest=tmp_path / "negative",
        answer="Ordinary TypeScript overloads.",
        expected_skill=False,
    )
    assert calls == {"health": 1, "model": 1}
    assert result["gate_action"] == "allow_structural_only"
    assert result["actual_skill_read_observed"] is False
    assert result["raw_model_output_delivered"] is False


def test_no_backend_is_only_pending_not_model_pass(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    result, calls = invoke(
        mod,
        case_id="POS-E-01",
        dist=dist,
        installed=installed,
        dest=tmp_path / "pending",
        with_model=False,
    )
    assert result["action"] == "model_backend_required_after_preflight"
    assert calls == {"health": 0, "model": 0}
    assert result["native_model_inference_completed"] is False


def test_existing_test_evidence_refuses_duplicate_inference(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    dest = tmp_path / "once"
    invoke(mod, case_id="BOUND-VERSION-NEW", dist=dist, installed=installed, dest=dest)
    with pytest.raises((ValueError, FileExistsError)):
        invoke(mod, case_id="BOUND-VERSION-NEW", dist=dist, installed=installed, dest=dest)


def test_unreviewed_installed_skill_and_cli_version_cannot_skip_preflight(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    (installed / "SKILL.md").write_text("tampered")
    with pytest.raises(ValueError):
        invoke(
            mod,
            case_id="BOUND-VERSION-NEW",
            dist=dist,
            installed=installed,
            dest=tmp_path / "tampered",
        )
    assert not (tmp_path / "tampered/native-events.private.jsonl").exists()


def test_native_pi_command_has_no_exec_write_extension_mcp_or_remote_client():
    mod = module()
    command = mod._pi_argv(
        "/absolute/p5/pi",
        {"prompt": "Original reviewed request"},
        Path("/isolated/skill/claude-code-mods-development"),
    )
    assert command[0] == "/absolute/p5/pi"
    assert command[-1] == "Original reviewed request"
    assert command[command.index("--tools") + 1] == "read"
    assert command[command.index("--thinking") + 1] == "off"
    assert command[command.index("--provider") + 1] == "mac-qwen"
    assert command[command.index("--model") + 1] == "qwen36-35b-a3b-mtp"
    assert "--no-mcp" in command
    assert "--no-extensions" in command
    assert "--no-context-files" in command
    assert "--no-approve" in command
    assert "--offline" in command
    assert "--no-session" in command
    assert "--skill" in command
    assert "--extension" not in command
    assert "--api-key" not in command
    assert "--no-skills" not in command
    assert "bash" not in command
    assert "write" not in command
    assert "edit" not in command


def test_unavailable_backend_fails_closed_with_no_model_request(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    calls = {"health": 0, "model": 0}

    def unavailable():
        calls["health"] += 1
        raise ConnectionError("private backend unavailable")

    def unexpected(*args, **kwargs):
        calls["model"] += 1
        raise AssertionError("Offline backend must NOT launch the model")

    report = mod.run_case(
        "POS-E-01",
        root=ROOT,
        dist=dist,
        skill_root=installed,
        evidence_dir=tmp_path / "offline",
        run_model=True,
        observed_claude_version="2.1.302 (Claude Code)",
        observed_pi_version="1.3.0",
        health_check=unavailable,
        model_runner=unexpected,
    )
    assert calls == {"health": 1, "model": 0}
    assert report["action"] == "blocked_model_backend_unavailable"
    assert report["model_requests_performed"] == 0
    assert report["raw_model_output_delivered"] is False
    assert report["stable_release_authorized"] is False
    assert "private backend unavailable" not in json.dumps(report)


def test_model_read_outside_reviewed_skill_is_never_accepted(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist
    answer = (
        "K-0040 https://code.claude.com/docs/en/plugins/mods/events#observe-an-event\n"
        "K-0064 https://code.claude.com/docs/en/plugins/mods/reference#the-hook-function"
    )

    def healthy():
        return None

    def outside_model(case, skill_root, private_root):
        wire = private_root / "native-events.private.jsonl"
        events = synthetic_native_events(case, answer=answer, skill_root=skill_root, skill=True)
        events.insert(
            2,
            {
                "type": "tool_execution_start",
                "toolName": "read",
                "toolCallId": "untrusted",
                "args": {"path": "/home/private/secrets.txt"},
            },
        )
        events.insert(
            3,
            {
                "type": "tool_execution_end",
                "toolName": "read",
                "toolCallId": "untrusted",
                "isError": False,
            },
        )
        wire.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        return events, 0, False, False, hashlib.sha256(wire.read_bytes()).hexdigest()

    report = mod.run_case(
        "POS-E-01",
        root=ROOT,
        dist=dist,
        skill_root=installed,
        evidence_dir=tmp_path / "out-of-scope",
        run_model=True,
        observed_claude_version="2.1.302 (Claude Code)",
        observed_pi_version="1.3.0",
        health_check=healthy,
        model_runner=outside_model,
    )
    assert report["gate_action"] == "block_candidate"
    assert "tool_read_outside_isolated_skill_or_workspace" in report["gate_reason_codes"]
    assert report["raw_model_output_delivered"] is False
    assert report["semantic_correctness_verified"] is False


def test_native_completion_error_never_promotes_synthetic_response(reviewed_dist, tmp_path):
    mod = module()
    dist, installed = reviewed_dist

    def healthy():
        pass

    def failed_model(case, skill_root, private_root):
        events = synthetic_native_events(
            case,
            answer="K-0040 https://code.claude.com/docs/en/plugins/mods/events#observe-an-event",
            skill_root=skill_root,
            skill=True,
        )
        wire = private_root / "native-events.private.jsonl"
        wire.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        return events, 1, False, False, hashlib.sha256(wire.read_bytes()).hexdigest()

    report = mod.run_case(
        "POS-E-01",
        root=ROOT,
        dist=dist,
        skill_root=installed,
        evidence_dir=tmp_path / "failed",
        run_model=True,
        observed_claude_version="2.1.302 (Claude Code)",
        observed_pi_version="1.3.0",
        health_check=healthy,
        model_runner=failed_model,
    )
    assert report["gate_action"] == "block_candidate"
    assert "native_run_incomplete" in report["gate_reason_codes"]
    assert report["native_model_inference_completed"] is False
    assert report["raw_model_output_delivered"] is False
