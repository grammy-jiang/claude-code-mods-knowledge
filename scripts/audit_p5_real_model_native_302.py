#!/usr/bin/env python3
"""Check saved real model code using genuine no-network CLI302 mock/TypeScript.

Use source-hashed PRIVATE model code excerpts only (not private transcripts).
All untrusted JS executes only inside mandatory networkless Linux Bubblewrap,
with disposable HOME, no live tools and no user account mounted. Strict tsc
uses first-party core types without dynamically merged built-in tool schemas.
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

from audit_p5_real_model_skill_ab import EXPECTED_SOURCES
from run_p5_model_code_native_host_sandbox import _create_mod_folder, _run, _sandbox_argv

ROOT = Path(__file__).resolve().parents[1]
CLI_SHA = "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10"
CORE_SHA = "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
SOURCE_CODE_TEST = ROOT / "evals/fixtures/p5-cli302-hook-catch/observer.test.ts"


class NativeModel302Blocked(ValueError):
    """Do not bless unknown model source, target or broken native mocks."""


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(codes: Path, binary: Path, core: Path) -> dict:
    if (
        not codes.is_dir()
        or codes.is_symlink()
        or not binary.is_file()
        or binary.is_symlink()
        or checksum(binary) != CLI_SHA
        or not core.is_file()
        or core.is_symlink()
        or not SOURCE_CODE_TEST.is_file()
        or SOURCE_CODE_TEST.is_symlink()
    ):
        raise NativeModel302Blocked("Pinned native CLI/Core/test fixture missing")
    core_bytes = core.read_bytes()
    header = b"// Written by Claude Code 2.1.302.\n"
    if hashlib.sha256(core_bytes.removeprefix(header)).hexdigest() != CORE_SHA:
        raise NativeModel302Blocked("Native CLI302 core TypeScript declarations mismatch")
    tsc = shutil.which("tsc")
    if not tsc:
        raise NativeModel302Blocked("TypeScript compiler unavailable")
    version = subprocess.run(  # noqa: S603 - local pinned TypeScript version inquiry
        [tsc, "--version"], capture_output=True, text=True, timeout=8, check=True
    ).stdout.strip()
    if version != "Version 6.0.3":
        raise NativeModel302Blocked("Unreviewed TypeScript compiler version")
    rows = []
    with tempfile.TemporaryDirectory(prefix="mods-p5-real-model-bwrap-302-") as temporary:
        work = Path(temporary) / "work"
        work.mkdir()
        for agent in ("sonnet", "codex"):
            for index, arm in enumerate(("baseline", "candidate"), 1):
                src = codes / f"{agent}-{arm}.js"
                if (
                    not src.is_file()
                    or src.is_symlink()
                    or not 100 < src.stat().st_size < 10_000
                    or checksum(src) != EXPECTED_SOURCES[(agent, arm)]
                ):
                    raise NativeModel302Blocked(
                        "Original real-model JavaScript source hash mismatch"
                    )
                source = src.read_text()
                if re.search(
                    r"\b(?:import|require|process|fetch|child_process|eval|Function|Deno|Bun|execSync)\b",
                    source,
                ):
                    raise NativeModel302Blocked("Unreviewed external action in model code")
                name = f"{agent}-0{index}"
                dest = _create_mod_folder(work, name, src)
                shutil.copyfile(SOURCE_CODE_TEST, dest / "tests/observer.test.ts")
                validated = {}
                for operation in ("validate", "test"):
                    status, output = _run(
                        _sandbox_argv(binary, work, operation, name), cwd=work, timeout=30
                    )
                    if status != 0:
                        raise NativeModel302Blocked("Original model source failed native Claude QA")
                    if operation == "validate":
                        expected_warning = arm == "baseline"
                        warning = "gating hook without .catch: tool.call" in output
                        caught = "gating hook with .catch: tool.call" in output
                        if (
                            "Validation passed" not in output
                            or warning != expected_warning
                            or caught == expected_warning
                        ):
                            raise NativeModel302Blocked("Native validator warning differs from A/B")
                        validated["strict_exit_zero"] = True
                        validated["missing_registration_catch_warning"] = warning
                    else:
                        if not (
                            "2 pass" in output
                            and "0 fail" in output
                            and "Ran 2 tests across 1 file." in output
                            and output.count("(pass)") == 2
                        ):
                            raise NativeModel302Blocked(
                                "Downstream result/denial count mock failed"
                            )
                        validated["read_denial_and_single_call_tests_passed"] = 2
                ts = re.sub(
                    r"export\s+function\s+register\s*\(\s*on\s*\)",
                    "export function register(on: On)",
                    source,
                    count=1,
                )
                if ts == source:
                    raise NativeModel302Blocked("Model source register cannot be core typechecked")
                twork = work / f"typed-{name}"
                twork.mkdir()
                (twork / "claude-core.d.ts").write_bytes(core_bytes)
                (twork / "reviewed-original.ts").write_text(
                    "import type { On } from 'claude-code';\n" + ts
                )
                (twork / "tsconfig.json").write_text(
                    json.dumps(
                        {
                            "compilerOptions": {
                                "target": "ES2023",
                                "module": "ESNext",
                                "moduleResolution": "Bundler",
                                "strict": True,
                                "noEmit": True,
                                "skipLibCheck": True,
                                "types": [],
                                "lib": ["ES2023"],
                            },
                            "include": ["claude-core.d.ts", "reviewed-original.ts"],
                        }
                    )
                )
                tsc_result = subprocess.run(  # noqa: S603 - pinned noEmit compiler only
                    [tsc, "--project", str(twork / "tsconfig.json"), "--pretty", "false"],
                    cwd=twork,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                if tsc_result.returncode != 0:
                    raise NativeModel302Blocked(
                        "Original model snippet failed reviewed core typing"
                    )
                rows.append(
                    {
                        "agent": agent,
                        "arm": arm,
                        "original_model_code_sha256": checksum(src),
                        "target_cli": "2.1.302",
                        "native_strict_exit_zero": validated["strict_exit_zero"],
                        "native_missing_catch_warning": validated[
                            "missing_registration_catch_warning"
                        ],
                        "mock_read_and_denial_single_call_tests_passed": validated[
                            "read_denial_and_single_call_tests_passed"
                        ],
                        "firstparty_core_typescript_noemit_pass": True,
                        "typecheck_adaptation": "add On annotation to register parameter only",
                    }
                )
    if len(rows) != 4:
        raise NativeModel302Blocked("Incomplete native comparison")
    return {
        "schema_version": 1,
        "native_target_cli": "2.1.302",
        "native_executable_sha256": CLI_SHA,
        "firstparty_core_types_sha256": CORE_SHA,
        "typescript_version": version,
        "trusted_mock_source_sha256": checksum(SOURCE_CODE_TEST),
        "original_model_snippets": 4,
        "native_strict_validations_exit_zero": 4,
        "old_model_code_catch_warnings": 2,
        "new_model_code_catch_warnings": 0,
        "mock_result_denial_and_single_call_tests_passed": 8,
        "native_core_typechecks_passed": 4,
        "all_mod_code_execution_only_inside_networkless_bubblewrap": True,
        "model_requests_performed_in_native_validation": 0,
        "real_user_tool_calls_or_account_mounted": False,
        "real_host_permission_callbacks_verified": False,
        "dynamically_merged_builtin_tool_types_verified": False,
        "full_model_quality_approved": False,
        "stable_release_authorized": False,
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-source-dir", required=True, type=Path)
    parser.add_argument("--native302-binary", required=True, type=Path)
    parser.add_argument("--private-core-types", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    opts = parser.parse_args()
    if opts.out.exists() or opts.out.is_symlink():
        raise SystemExit("REFUSED: immutable native proof already recorded")
    try:
        report = audit(opts.private_source_dir, opts.native302_binary, opts.private_core_types)
    except (NativeModel302Blocked, OSError, ValueError, subprocess.SubprocessError):
        raise SystemExit("BLOCKED: original model code native safety not proven") from None
    opts.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "native_original_model_snippets": report["original_model_snippets"],
                "baseline_missing_registration_catch": report["old_model_code_catch_warnings"],
                "candidate_warning_free": report["new_model_code_catch_warnings"] == 0,
                "native_mock_passed": report["mock_result_denial_and_single_call_tests_passed"],
                "target_typechecks_passed": report["native_core_typechecks_passed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
