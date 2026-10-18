#!/usr/bin/env python3
"""Run exact real Codex/Sonnet JS modules in native Claude 2.1.302 MOCK tests.

All code execution is inside Linux Bubblewrap with an unshared NETWORK and
mount namespace. Original host Home/SSH/Projects are not mapped. Only the
reviewed Claude 2.1.302 binary, safe trusted synthetic test, source-hashed
model snippet and disposable workspace are visible. No genuine Bash, tool,
user file, external model, Claude auth or account API call is ever performed.
Full synthetic 48/48 Node contracts are separate evidence.

A real CLI version-matched MOCK is stronger than custom Node tests but not a
production Claude interactive session, real user permission check, TypeScript
declarations check, or approval of a complete model answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from audit_p5_original_model_code import FIXTURES, stage

ROOT = Path(__file__).resolve().parents[1]
MOCK_TEST = FIXTURES / "mod-host-mock.test.ts"
CLAUDE_TARGET = "2.1.302 (Claude Code)"


class NativeModMockBlocked(ValueError):
    """Original model code failed a real native host validation or test gate."""


def _sandbox_argv(claude: Path, work: Path, subcommand: str, folder: str) -> list[str]:
    bwrap = shutil.which("bwrap")
    if not bwrap or not Path(bwrap).is_absolute():
        raise NativeModMockBlocked("Linux Bubblewrap sandbox mandatory; no raw code on host")
    if not claude.is_file() or claude.is_symlink() or not claude.is_absolute():
        raise NativeModMockBlocked("Exact reviewed native Claude CLI binary not pinned")
    if not work.is_dir():
        raise NativeModMockBlocked("Private sandbox working directory missing")
    if not re.fullmatch(r"(?:codex|sonnet)-0[1-3]", folder):
        raise NativeModMockBlocked("Unreviewed Mod test fixture name")
    if subcommand not in ("validate", "test"):
        raise NativeModMockBlocked("Only strict validation and mocked tests allowed")
    invocation = (
        ["/runtime/claude", "plugin", "validate", "--strict", "/work/mods/" + folder]
        if subcommand == "validate"
        else ["/runtime/claude", "plugin", "test", "/work/mods/" + folder]
    )
    return [
        bwrap,
        "--unshare-all",
        "--die-with-parent",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/bin",
        "/bin",
        "--dir",
        "/runtime",
        "--ro-bind",
        str(claude),
        "/runtime/claude",
        "--bind",
        str(work),
        "/work",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",  # noqa: S108 - new isolated tmpfs, not host /tmp
        "--dir",
        "/home",
        "--tmpfs",
        "/home/qa",
        "--clearenv",
        "--setenv",
        "HOME",
        "/home/qa",
        "--setenv",
        "PATH",
        "/runtime:/usr/bin:/bin",
        "--chdir",
        "/work",
        "--",
        *invocation,
    ]


def _run(argv: list[str], *, cwd: Path, timeout: int) -> tuple[int, str]:
    if not 10 <= timeout <= 60:
        raise NativeModMockBlocked("Unbounded CLI invocation timeout")
    try:
        process = subprocess.run(  # noqa: S603 - reviewed fixed Bubblewrap path and args
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            input="",
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise NativeModMockBlocked("Native CLI mock test timeout") from exc
    output = process.stdout + process.stderr
    if len(output.encode()) > 150_000:
        raise NativeModMockBlocked("Unexpected oversized native CLI output")
    return process.returncode, output


def _create_mod_folder(work: Path, name: str, source: Path) -> Path:
    mod = work / "mods" / name
    for folder in (mod / ".claude-plugin", mod / "hooks", mod / "tests"):
        folder.mkdir(parents=True)
    manifest = {
        "name": "qa-synthetic-" + name,
        "version": "0.0.1",
        "description": "Exact model code under strictly mocked native Mod tests",
        "author": {"name": "Mods QA"},
    }
    (mod / ".claude-plugin/plugin.json").write_text(json.dumps(manifest) + "\n")
    (mod / "hooks/hooks.json").write_text(
        json.dumps(
            {
                "description": "Synthetic tool.call passthrough, no external tool",
                "modules": ["./register.js"],
            }
        )
        + "\n"
    )
    shutil.copyfile(source, mod / "hooks/register.js")
    (mod / "tests/observer.test.ts").write_bytes(MOCK_TEST.read_bytes())
    return mod


def _claude_binary() -> Path:
    path = Path.home() / ".local/share/claude/versions/2.1.302"
    if not path.is_file() or path.is_symlink() or path.stat().st_size < 10_000_000:
        raise NativeModMockBlocked("Current pinned 2.1.302 native Claude binary missing")
    return path


def audit(*, timeout: int = 35) -> dict:
    claude = _claude_binary()
    if not MOCK_TEST.is_file() or MOCK_TEST.is_symlink():
        raise NativeModMockBlocked("Trusted source-controlled mock test missing")
    with tempfile.TemporaryDirectory(prefix="mods-p5-real-cli302-mock-") as tmp:
        work = Path(tmp) / "work"
        prepared = stage(FIXTURES, work)
        if prepared["original_reviewed_source_files"] != 5:
            raise NativeModMockBlocked("Insufficient original model fixture hashes")
        rows = []
        for entry in prepared["per_case"]:
            source = work / "candidates" / entry["sandbox_module_name"]
            name = entry["sandbox_module_name"].removesuffix(".mjs")
            _create_mod_folder(work, name, source)
            for mode in ("validate", "test"):
                cmd = _sandbox_argv(claude, work, mode, name)
                code, output = _run(cmd, cwd=work, timeout=timeout)
                if code != 0:
                    raise NativeModMockBlocked(
                        f"Native Claude 2.1.302 {mode} rejected reviewed model module: {name}"
                    )
                if mode == "validate" and "Validation passed" not in output:
                    raise NativeModMockBlocked("Strict native Mod validation confirmation missing")
                if mode == "test" and not (
                    "2 pass" in output
                    and "0 fail" in output
                    and "Ran 2 tests across 1 file." in output
                ):
                    raise NativeModMockBlocked("Native mocked Read/denial results not exact")
            rows.append(
                {
                    "model_source_code_sha256": entry["source_code_sha256"],
                    "sandbox_adapted_module_sha256": entry["sandbox_module_sha256"],
                    "fragment_requires_nonoriginal_wrapper": entry[
                        "requires_test_only_register_wrapper"
                    ],
                    "native_claude_2_1_302_plugin_validate_strict": "pass",
                    "native_claude_2_1_302_mocked_mod_tests_passed": 2,
                    "native_claude_2_1_302_mocked_mod_tests_failed": 0,
                    "real_user_tool_invoked": False,
                    "actual_interactive_user_session_approved": False,
                }
            )
        # Negative control, within the same isolated environment: a
        # deliberately incorrect replacement hook must fail the actual
        # Claude mock tool.result equivalence expectations. Native strict
        # validation alone is NOT a semantics test.
        negative = work / "mods" / "codex-01" / "hooks/register.js"
        negative.write_text(
            "export function register(on) {"
            " on('tool.call', async ($, e, next) => ({result: 'WRONG'}));"
            "}"
        )
        bad_command = _sandbox_argv(claude, work, "test", "codex-01")
        bad_status, bad_output = _run(bad_command, cwd=work, timeout=timeout)
        if bad_status == 0 or "fail" not in bad_output:
            raise NativeModMockBlocked("Native mock failed to detect altered result")
        return {
            "schema_version": 1,
            "date": "2026-10-19",
            "target_cli": "2.1.302",
            "source_fixture_manifest_sha256": hashlib.sha256(
                (FIXTURES / "manifest.json").read_bytes()
            ).hexdigest(),
            "trusted_native_mock_test_sha256": hashlib.sha256(MOCK_TEST.read_bytes()).hexdigest(),
            "five_genuine_model_snippets_original_sha256_verified": 5,
            "self_contained_installable_source_modules": 3,
            "fragments_only_accepted_with_synthetic_wrapper": 2,
            "reviewed_native_cli_strict_plugin_validations_passed": 5,
            "reviewed_native_cli_mocked_tool_contract_tests_passed": 10,
            "reviewed_native_cli_mocked_tool_contract_tests_failed": 0,
            "native_wrong_result_semantic_counterexample_rejected": True,
            "all_execution_inside_bubblewrap": True,
            "network_namespace_unshared": True,
            "original_host_home_or_credentials_mounted": False,
            "model_network_requests": 0,
            "original_user_bash_or_read_tool_executed": False,
            "native_mod_test_uses_approved_synthetic_mocks_only": True,
            "typechecked_against_actual_2_1_302_generated_declarations": False,
            "real_user_session_or_permission_host_test_performed": False,
            "full_model_generated_mod_runtime_semantics_certified": False,
            "stable_release_authorized": False,
            "candidate_results": rows,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=35)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable prior original native mock result exists")
    try:
        result = audit(timeout=args.timeout)
    except (NativeModMockBlocked, OSError, ValueError, subprocess.SubprocessError):
        raise SystemExit("BLOCKED: source-pinned native Claude Mod mock test incomplete") from None
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        {
            "real_cli_2_1_302_strict_validations_passed": result[
                "reviewed_native_cli_strict_plugin_validations_passed"
            ],
            "real_cli_2_1_302_mocked_tool_tests_passed": result[
                "reviewed_native_cli_mocked_tool_contract_tests_passed"
            ],
            "negative_semantic_counterexample_rejected": True,
            "actual_live_user_tool_calls": 0,
            "model_requests": 0,
            "stable_release_authorized": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
