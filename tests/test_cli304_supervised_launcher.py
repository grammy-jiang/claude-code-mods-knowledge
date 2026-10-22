"""The CLI304 QA launcher must stage exact private managed policy, never /etc."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest

from mods_knowledge.cli304_supervised_lease import SupervisorBlocked

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/cli304_supervised_qa.py"

_spec = importlib.util.spec_from_file_location("qa_supervisor_cli304", SOURCE)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


@pytest.fixture
def setup(tmp_path: Path, monkeypatch):
    binary = tmp_path / "fake-native-for-deterministic-QA"
    binary.write_bytes(b"not a real Claude executable; digest test only")
    monkeypatch.setattr(m, "NATIVE_CLI304_SHA", hashlib.sha256(binary.read_bytes()).hexdigest())
    python = Path(sys.executable).resolve()
    hook = ROOT / "scripts/cli304_supervised_pretool.py"
    newroot = tmp_path / "reviewed-private"
    return binary, python, hook, newroot


def test_native_preflight_builds_isolated_managed_pretool_fail_closed(setup):
    binary, python, hook, root = setup
    result = m.prepare(root=root, cli=binary, python=python, hook=hook)
    assert result["timeout"] == 2.0
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    policy = root / "managed/managed-settings.json"
    assert stat.S_IMODE(policy.stat().st_mode) == 0o600
    settings = json.loads(policy.read_text())
    assert settings["allowManagedHooksOnly"] is True
    assert settings["allowManagedPermissionRulesOnly"] is True
    assert set(settings["permissions"]["deny"]) == {"Write", "Edit", "Bash"}
    assert set(settings["hooks"]) == {"PreToolUse"}
    hook_command = settings["hooks"]["PreToolUse"][0]["hooks"][0]
    assert hook_command["onFailure"] == "block"
    assert hook_command["command"] == str(python)
    assert hook_command["args"] == [
        str(hook),
        "--lease",
        str(root / "private/supervisor-lease.json"),
        "--workspace",
        str(root / "work"),
    ]
    assert result["managed_policy_sha256"] == hashlib.sha256(policy.read_bytes()).hexdigest()
    assert not Path("/etc/claude-code/managed-settings.json").is_relative_to(root)


def test_reject_missing_binary_identity_before_writing_private_profile(setup):
    binary, python, hook, root = setup
    binary.write_bytes(b"tampered")
    with pytest.raises(SupervisorBlocked, match="WRONG_CLAUDE_304_BINARY"):
        m.prepare(root=root, cli=binary, python=python, hook=hook)
    assert not root.exists()


def test_existing_directory_and_invalid_timeout_cannot_overwrite_qa(setup):
    binary, python, hook, root = setup
    root.mkdir()
    with pytest.raises(SupervisorBlocked, match="NEW_QA_ROOT_REQUIRED"):
        m.prepare(root=root, cli=binary, python=python, hook=hook)
    root.rmdir()
    with pytest.raises(SupervisorBlocked, match="INVALID_LEASE_TIMEOUT"):
        m.prepare(root=root, cli=binary, python=python, hook=hook, timeout=123)


def test_no_shell_or_user_cli_extra_flags_in_fixed_sandbox_argv(setup):
    binary, python, hook, root = setup
    # Check our fixed command-vector construction without starting any sandbox.
    # The actual bwrap executable must be available on the Linux test host.
    if not Path("/usr/bin/bwrap").is_file():
        pytest.skip("Bubblewrap unavailable on this unit-test platform")
    m.prepare(root=root, cli=binary, python=python, hook=hook)
    command = m._bwrap_argv(root, binary, ["--version"])
    assert command[0] == "/usr/bin/bwrap"
    assert command[-2:] == [str(binary), "--version"]
    pairs = list(zip(command, command[1:], strict=False))
    assert (str(root / "managed"), "/etc/claude-code") in pairs
    assert ("--ro-bind", str(root / "managed")) in pairs
    assert ("--ro-bind", "/") in pairs
    assert ("--bind", str(root / "work")) in pairs
    assert command.count("--") == 1
    assert "--settings" not in command
