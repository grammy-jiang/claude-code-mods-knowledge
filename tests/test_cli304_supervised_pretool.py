"""Managed pre-tool hook enforces short supervisor lease and scoped QA reads."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from mods_knowledge.cli304_supervised_lease import SupervisorBlocked

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/cli304_supervised_pretool.py"
_spec = importlib.util.spec_from_file_location("cli304_managed_host_qa_gate", SCRIPT)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def actual_event(file: Path, *, tool="Read", session="session-0123456789"):
    return {
        "hook_event_name": "PreToolUse",
        "session_id": session,
        "tool_name": tool,
        "tool_input": {"file_path": str(file)},
        "cwd": str(file.parent),
    }


@pytest.fixture
def setting(tmp_path: Path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    file = work / "qa-read.txt"
    file.write_text("QA_TEST\n")
    fake = {"session": "session-0123456789"}
    monkeypatch.setattr(m, "read_lease", lambda _: fake)
    return work, file


def test_ready_managed_session_read_is_allowed(setting):
    work, file = setting
    assert m.check(actual_event(file), lease=work / "lease", workspace=work) is None


def test_mutating_and_unknown_tools_denied_under_qa_policy(setting):
    work, file = setting
    for tool in ("Write", "Edit", "Bash", "WebFetch", "mcp__x__delete"):
        with pytest.raises(SupervisorBlocked, match="QA_READ_ONLY"):
            m.check(actual_event(file, tool=tool), lease=work, workspace=work)


def test_session_mismatch_and_missing_supervisor_are_denied(setting, monkeypatch):
    work, file = setting
    with pytest.raises(SupervisorBlocked, match="UNREGISTERED_NATIVE_SESSION"):
        m.check(actual_event(file, session="other-session"), lease=work, workspace=work)

    def failed(_):
        raise SupervisorBlocked("SUPERVISOR_LEASE_EXPIRED_OR_FUTURE")

    monkeypatch.setattr(m, "read_lease", failed)
    with pytest.raises(SupervisorBlocked, match="SUPERVISOR_LEASE_EXPIRED"):
        m.check(actual_event(file), lease=work, workspace=work)


def test_symlink_escape_outside_private_sandbox_rejected(setting, tmp_path):
    work, file = setting
    outside = tmp_path / "outside.txt"
    outside.write_text("outside")
    link = work / "link.txt"
    link.symlink_to(outside)
    for path in (outside, link):
        with pytest.raises(SupervisorBlocked, match="READ_TARGET_OUTSIDE"):
            m.check(actual_event(path), lease=work, workspace=work)


def test_different_event_and_bad_json_rejected(setting, monkeypatch, capsys):
    work, file = setting
    malformed = actual_event(file)
    malformed["hook_event_name"] = "UserPromptSubmit"
    with pytest.raises(SupervisorBlocked, match="UNKNOWN_HOOK_EVENT"):
        m.check(malformed, lease=work, workspace=work)
    from io import BytesIO

    class Input:
        buffer = BytesIO(b"not json")

    monkeypatch.setattr(m.sys, "stdin", Input())
    monkeypatch.setattr(
        m.sys,
        "argv",
        [
            "cli304_supervised_pretool.py",
            "--lease",
            str(work / "lease"),
            "--workspace",
            str(work),
        ],
    )
    assert m.main() == 2
    assert "SUPERVISOR_QA_DENIED" in capsys.readouterr().err


def test_untrusted_work_path_without_read_file_is_rejected(setting):
    work, _ = setting
    event = actual_event(work / "absent.txt")
    with pytest.raises(FileNotFoundError):
        m.check(event, lease=work, workspace=work)
