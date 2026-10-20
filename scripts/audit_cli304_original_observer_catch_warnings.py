#!/usr/bin/env python3
"""Record CLI304 native validator's unsafe original-model hook warnings.

Five original Codex/Sonnet source-pinned observer modules are only parsed
in isolated native `plugin validate --strict` invocations. No model calls,
user tools, real permission prompts, network or host Home are available.
Do not confuse a zero validator exit code with deployable hook safety.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from audit_cli303_official_native_parity import Native303Blocked, fail_closed_validation_gate
from audit_p5_original_model_code import FIXTURES, stage
from run_cli304_firstparty_mock_sandbox import (
    OFFICIAL_BINARY_SHA,
    OFFICIAL_TARBALL_SHA,
    attest_fixture_and_binary,
    execute,
    sandbox_argv,
)
from run_p5_model_code_native_host_sandbox import _create_mod_folder, _run, _sandbox_argv

ROOT = Path(__file__).resolve().parents[1]
OLD_REPORT = ROOT / "docs/reports/2026-10-20-cli304-native-prior-observer-compat-mock.json"
EXPECTED_CANDIDATES = frozenset({"codex-01", "codex-02", "sonnet-01", "sonnet-02", "sonnet-03"})


class Original304CatchBlocked(ValueError):
    """Refuse unsafe source inputs or an unreviewed validator result."""


def _sha(file: Path) -> str:
    with file.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def audit(binary: Path, asset: Path) -> dict:
    attest_fixture_and_binary(binary, asset)
    prior = json.loads(OLD_REPORT.read_text())
    if (
        prior.get("target_cli") != "2.1.304"
        or prior.get("official_native_bin_sha256") != OFFICIAL_BINARY_SHA
        or prior.get("original_302_model_snippet_sha256_verified") != 5
        or prior.get("backward_compatible_strict_mod_validations_passed") != 5
        or prior.get("backward_compatible_mocked_read_denial_tests_passed") != 10
        or prior.get("complete_304_api_contract_verified") is not False
    ):
        raise Original304CatchBlocked("Historical native 304 compatibility evidence changed")
    with tempfile.TemporaryDirectory(prefix="mods304-original-catch-audit-") as temporary:
        work = Path(temporary) / "work"
        prepared = stage(FIXTURES, work)
        if prepared["original_reviewed_source_files"] != 5:
            raise Original304CatchBlocked("Missing source-hashed original model fixtures")
        bwrap_path = shutil.which("bwrap")
        if not bwrap_path or not Path(bwrap_path).is_absolute():
            raise Original304CatchBlocked("Mandatory Linux Bubblewrap not installed")
        version_code, version_output = execute(
            sandbox_argv(Path(bwrap_path).resolve(strict=True), binary, work, "version"), work
        )
        if version_code != 0 or version_output.strip() != "2.1.304 (Claude Code)":
            raise Original304CatchBlocked("Native target version mismatch in sandbox")
        cases = []
        warnings = 0
        gate_blocks = 0
        for entry in prepared["per_case"]:
            name = entry["sandbox_module_name"].removesuffix(".mjs")
            if name not in EXPECTED_CANDIDATES:
                raise Original304CatchBlocked("Unreviewed original model fixture")
            _create_mod_folder(work, name, work / "candidates" / entry["sandbox_module_name"])
            code, output = _run(_sandbox_argv(binary, work, "validate", name), cwd=work, timeout=35)
            warning = "gating hook without .catch: tool.call" in output.lower()
            if code != 0 or "Validation passed" not in output or not warning:
                raise Original304CatchBlocked("Target 304 native validation outcome differs")
            warnings += 1
            try:
                fail_closed_validation_gate(code, output)
            except Native303Blocked:
                gate_blocks += 1
            else:
                raise Original304CatchBlocked("Unsafe warning was wrongly accepted")
            cases.append(
                {
                    "candidate": name,
                    "original_model_source_sha256": entry["source_code_sha256"],
                    "native_strict_validation_exit_code": 0,
                    "native_validator_reported_pass": True,
                    "native_uncaught_tool_call_warning": True,
                    "additional_fail_closed_gate": "BLOCKED",
                    "source_code_type_correctness_certified": False,
                }
            )
    if {case["candidate"] for case in cases} != EXPECTED_CANDIDATES:
        raise Original304CatchBlocked("Unexpected number or identity of original model cases")
    if warnings != 5 or gate_blocks != 5:
        raise Original304CatchBlocked("Native warning totals changed")
    return {
        "schema_version": 1,
        "reviewed_target_cli": "2.1.304",
        "official_release_url": "https://github.com/anthropics/claude-code/releases/tag/v2.1.304",
        "official_native_executable_sha256": OFFICIAL_BINARY_SHA,
        "official_native_archive_sha256": OFFICIAL_TARBALL_SHA,
        "prior_mock_evidence_sha256": _sha(OLD_REPORT),
        "original_source_manifest_sha256": _sha(FIXTURES / "manifest.json"),
        "native_original_302_model_candidates": 5,
        "native_strict_validator_exit_zero": 5,
        "native_uncaught_tool_call_warnings": warnings,
        "additional_fail_closed_safety_gate_blocks": gate_blocks,
        "historical_mocked_read_denial_tests_passed_not_rerun": 10,
        "all_execution_in_linux_bubblewrap_without_network": True,
        "host_home_or_credentials_mounted": False,
        "real_model_calls_or_user_tools_performed": 0,
        "real_permission_host_or_dynamically_generated_types_verified": False,
        "no_catch_original_model_hooks_approved_for_deployment": False,
        "all_31_cli304_claims_approved": False,
        "full_native_model_skill_acceptance": False,
        "chatgpt_plugin_release_authorized": False,
        "stable_release_authorized": False,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-archive", required=True, type=Path)
    parser.add_argument("--official-binary", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable native CLI304 warning report already exists")
    try:
        result = audit(args.official_binary, args.official_archive)
    except (Original304CatchBlocked, OSError, ValueError):
        raise SystemExit("BLOCKED: native 304 warning audit source/host mismatch") from None
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "native_strict_exit_zero": result["native_strict_validator_exit_zero"],
                "uncaught_hook_warnings": result["native_uncaught_tool_call_warnings"],
                "fail_closed_safety_blocks": result["additional_fail_closed_safety_gate_blocks"],
                "production_approval": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
