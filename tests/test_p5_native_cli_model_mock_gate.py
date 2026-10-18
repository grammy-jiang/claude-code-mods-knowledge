"""Native Claude 2.1.302 actual-mock gate must isolate original model snippets.

Pytest only audits the runner's argument construction and trusted
synthetic test fixture, never executes model-origin JS. The actual CLI
plugin validate/test run is a separate Linux Bubblewrap-only experiment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p5_model_code_native_host_sandbox import (  # noqa: E402
    MOCK_TEST,
    NativeModMockBlocked,
    _sandbox_argv,
)


def test_genuine_reviewed_cli_mock_test_cannot_call_real_user_tools() -> None:
    code = MOCK_TEST.read_text()
    assert MOCK_TEST.name == "mod-host-mock.test.ts"
    assert "claude-code/testing" in code
    assert code.count("test(") == 2
    assert code.count("on('tool.call', () =>") == 2
    assert "result: 'QA_ORIGINAL_RESULT'" in code
    assert "result: 'QA_ORIGINAL_DENIAL', isError: true" in code
    assert "MOCK_NOT_REAL_FILE" in code
    assert "expect(actual.result).toBe" in code
    assert "expect(actual.isError).toBe(true)" in code
    for unsafe in (
        "spawn(",
        "process.",
        "exec(",
        "writeFile",
        "fs.",
        "fetch(",
        "http://",
        "https://",
        "tool: 'Bash'",
        "command: 'echo",
        ".ssh",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
    ):
        assert unsafe not in code


@pytest.mark.parametrize("mode", ["validate", "test"])
def test_model_code_native_cli_is_restricted_to_networkless_os_sandbox(
    tmp_path: Path,
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import run_p5_model_code_native_host_sandbox as native

    monkeypatch.setattr(native.shutil, "which", lambda name: "/usr/bin/bwrap")
    work = tmp_path / "work"
    work.mkdir()
    binary = tmp_path / "claude302"
    binary.write_text("nonexecuted test stub")
    cmd = _sandbox_argv(binary, work, mode, "codex-01")
    assert cmd[0].endswith("bwrap")
    assert "--unshare-all" in cmd
    assert "--share-net" not in cmd
    assert "--clearenv" in cmd
    assert "--die-with-parent" in cmd
    assert "--proc" in cmd and "--dev" in cmd
    assert "--tmpfs" in cmd
    assert cmd[cmd.index("--chdir") + 1] == "/work"
    mounts = [
        (cmd[i + 1], cmd[i + 2])
        for i, token in enumerate(cmd[:-2])
        if token in ("--ro-bind", "--bind")
    ]
    assert ("/usr", "/usr") in mounts
    assert (str(binary), "/runtime/claude") in mounts
    assert (str(work), "/work") in mounts
    assert not any(source in ("/", "/home", "/root", "/etc", "/mnt") for source, _ in mounts)
    assert cmd[cmd.index("--") + 1] == "/runtime/claude"
    assert "plugin" in cmd
    if mode == "validate":
        assert cmd[-4:] == [
            "plugin",
            "validate",
            "--strict",
            "/work/mods/codex-01",
        ]
    else:
        assert cmd[-3:] == ["plugin", "test", "/work/mods/codex-01"]


@pytest.mark.parametrize("bad", ["file_not_pinned", "folder", "mode"])
def test_nonreviewed_native_binary_or_command_refused(
    tmp_path: Path,
    bad: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import run_p5_model_code_native_host_sandbox as native

    monkeypatch.setattr(native.shutil, "which", lambda name: "/usr/bin/bwrap")
    work = tmp_path / "work"
    work.mkdir()
    binary = tmp_path / "claude302"
    binary.write_text("stub")
    if bad == "file_not_pinned":
        binary.unlink()
    if bad == "folder":
        with pytest.raises(NativeModMockBlocked):
            _sandbox_argv(binary, work, "test", "unknown")
    elif bad == "file_not_pinned":
        with pytest.raises(NativeModMockBlocked):
            _sandbox_argv(binary, work, "test", "codex-01")
    else:
        with pytest.raises(NativeModMockBlocked):
            _sandbox_argv(binary, work, "install", "codex-01")


def test_source_writes_only_safe_artifact_metadata_not_live_model_response() -> None:
    import inspect

    import run_p5_model_code_native_host_sandbox as native

    implementation = inspect.getsource(native.audit)
    assert "plugin" in implementation
    assert "validate" in implementation
    assert "test" in implementation
    assert "native_wrong_result_semantic_counterexample_rejected" in implementation
    assert "stable_release_authorized" in implementation
    assert "actual_interactive_user_session_approved" in implementation
    assert "False" in implementation
    assert "No model" not in implementation  # no bogus claim in output
    assert "subprocess" not in MOCK_TEST.read_text()


def test_native_contract_harness_is_not_an_official_type_definition() -> None:
    """Native mock API is real, but approved generated TypeScript types absent."""
    source = (ROOT / "scripts/run_p5_model_code_native_host_sandbox.py").read_text()
    assert "typechecked_against_actual_2_1_302_generated_declarations" in source
    assert "full_model_generated_mod_runtime_semantics_certified" in source
    assert "actual_claude_mod_host_plugin_test_executed" not in source
    assert (
        json.loads((ROOT / "evals/fixtures/p5-native-model-code-302/manifest.json").read_text())[
            "tests_do_not_grant_actual_claude_mods_host_acceptance"
        ]
        is True
    )
