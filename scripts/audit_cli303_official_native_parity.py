#!/usr/bin/env python3
"""Recheck official Claude Code CLI 2.1.303 core types and safe native mocks.

Use only the byte-pinned first-party ARM64 tarball and installed binary.
The original 2.1.302 model snippets run exclusively inside Bubblewrap
with unshared networking and a disposable home, never an actual account.
This establishes a narrow backward-compatible subset, NOT permission,
full generated tool types, approved 303 Claims, or a new 303 Skill.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import mmap
import tarfile
import tempfile
from pathlib import Path

from audit_p5_original_model_code import FIXTURES, stage
from extract_reviewed_cli302_core_types import (
    DECLARATION_BYTES,
    DECLARATION_SHA256,
    ZSTD_MAGIC,
    _zstd_lib,
    verify_core,
)
from run_p5_model_code_native_host_sandbox import (
    MOCK_TEST,
    _create_mod_folder,
    _run,
    _sandbox_argv,
)

ROOT = Path(__file__).resolve().parents[1]
CLI_VERSION = "2.1.303 (Claude Code)"
OFFICIAL_ASSET_SHA256 = "0c219f6d5fadf1ce5771f7976fe18d6a57a9b8267def5198b58d3e121eeb98c1"
OFFICIAL_BINARY_SHA256 = "f384f49826336d4ac0484ac6ac9d8d16f64d244d186ce227cbd7cc088c03315d"
REPORT_RELATIVE = "docs/reports/2026-10-20-cli303-official-core-and-native-mock-parity.json"
EXPECTED_CANDIDATES = frozenset({"codex-01", "codex-02", "sonnet-01", "sonnet-02", "sonnet-03"})


class Native303Blocked(ValueError):
    """An untrusted native binary or incomplete parity check cannot be published."""


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def attest_official_archive(asset: Path, binary: Path) -> None:
    """Stream official release content without extracting paths or executing it."""
    expected_install = Path.home() / ".local/share/claude/versions/2.1.303"
    if binary != expected_install:
        raise Native303Blocked("Requested binary is not the installed 2.1.303 executable")
    if (
        not asset.is_file()
        or asset.is_symlink()
        or not binary.is_file()
        or binary.is_symlink()
        or not 100_000_000 < asset.stat().st_size < 160_000_000
        or not 250_000_000 < binary.stat().st_size < 330_000_000
        or file_sha256(asset) != OFFICIAL_ASSET_SHA256
        or file_sha256(binary) != OFFICIAL_BINARY_SHA256
    ):
        raise Native303Blocked("Official 2.1.303 release asset or installed binary SHA mismatch")
    try:
        with tarfile.open(asset, "r:gz") as archive:
            entries = archive.getmembers()
            if len(entries) != 1 or entries[0].name != "claude" or not entries[0].isfile():
                raise Native303Blocked("Unexpected 2.1.303 release archive contents")
            if entries[0].size != binary.stat().st_size:
                raise Native303Blocked("Official binary size disagrees with installed version")
            with archive.extractfile(entries[0]) as source:  # type: ignore[arg-type]
                if source is None or hashlib.file_digest(source, "sha256").hexdigest() != (
                    OFFICIAL_BINARY_SHA256
                ):
                    raise Native303Blocked("Installed binary is not official release binary")
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise Native303Blocked("Unverifiable official 2.1.303 tar archive") from exc


def extract_matching_core_digest(binary: Path) -> dict:
    """Scan bounded Zstd frames; never write upstream declaration contents."""
    lib = _zstd_lib()
    matches: list[tuple[int, int]] = []
    count = 0
    with binary.open("rb") as source:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_COPY) as view:
            index = 0
            while True:
                index = view.find(ZSTD_MAGIC, index)
                if index < 0:
                    break
                offset = index
                index += len(ZSTD_MAGIC)
                count += 1
                if count > 12_000:
                    raise Native303Blocked("Too many compressed source candidates")
                ptr = ctypes.addressof(ctypes.c_char.from_buffer(view, offset))
                frame_len = lib.ZSTD_findFrameCompressedSize(ptr, len(view) - offset)
                if lib.ZSTD_isError(frame_len) or not 0 < frame_len < 16_000_000:
                    continue
                size = lib.ZSTD_getFrameContentSize(ptr, frame_len)
                if size != DECLARATION_BYTES:
                    continue
                buf = ctypes.create_string_buffer(size)
                decompressed = lib.ZSTD_decompress(ctypes.addressof(buf), size, ptr, frame_len)
                if lib.ZSTD_isError(decompressed) or decompressed != size:
                    continue
                if hashlib.sha256(buf.raw).hexdigest() == DECLARATION_SHA256:
                    verify_core(buf.raw)
                    matches.append((offset, frame_len))
    if len(matches) != 1:
        raise Native303Blocked("Official 303 embedded core type declarations differ from 302")
    return {
        "sha256": DECLARATION_SHA256,
        "bytes": DECLARATION_BYTES,
        "compressed_zstd_frame_offset": matches[0][0],
        "compressed_zstd_frame_bytes": matches[0][1],
        "frames_scanned": count,
        "one_exact_matching_frame": True,
    }


def _version_in_sandbox(binary: Path, work: Path) -> str:
    argv = _sandbox_argv(binary, work, "validate", "codex-01")
    # Keep exactly the same mandatory namespace and mount restrictions.
    argv = argv[: argv.index("--") + 1] + ["/runtime/claude", "--version"]
    code, output = _run(argv, cwd=work, timeout=30)
    if code != 0 or output.strip() != CLI_VERSION:
        raise Native303Blocked("Official CLI 303 version check failed in networkless sandbox")
    return output.strip()


def fail_closed_validation_gate(code: int, output: str) -> None:
    """A zero native validator exit code may still contain critical warnings."""
    if (
        code != 0
        or "Validation passed" not in output
        or "gating hook without .catch" in output.lower()
        or "warning" in output.lower()
    ):
        raise Native303Blocked("Native CLI validation is not warning-free and fail-closed")


def audit(asset: Path, binary: Path) -> dict:
    attest_official_archive(asset, binary)
    core = extract_matching_core_digest(binary)
    if not MOCK_TEST.is_file() or MOCK_TEST.is_symlink():
        raise Native303Blocked("Native mocked test source is not present")
    with tempfile.TemporaryDirectory(prefix="mods-cli303-native-parity-") as temporary:
        work = Path(temporary) / "work"
        prepared = stage(FIXTURES, work)
        if prepared["original_reviewed_source_files"] != 5:
            raise Native303Blocked("Not all genuine original model code fixtures are preserved")
        version = _version_in_sandbox(binary, work)
        cases = []
        gating_warnings = 0
        fail_closed_rejections = 0
        for entry in prepared["per_case"]:
            name = entry["sandbox_module_name"].removesuffix(".mjs")
            if name not in EXPECTED_CANDIDATES:
                raise Native303Blocked("Unknown original model code candidate")
            _create_mod_folder(work, name, work / "candidates" / entry["sandbox_module_name"])
            for mode in ("validate", "test"):
                code, output = _run(_sandbox_argv(binary, work, mode, name), cwd=work, timeout=35)
                if code != 0:
                    raise Native303Blocked("Official 303 native mock or validation failed")
                if mode == "validate":
                    if "Validation passed" not in output:
                        raise Native303Blocked("Missing native strict validation success")
                    uncaught = "gating hook without .catch: tool.call" in output.lower()
                    if "without .catch" in output.lower() and not uncaught:
                        raise Native303Blocked("Unexpected native gating hook warning")
                    gating_warnings += int(uncaught)
                    try:
                        fail_closed_validation_gate(code, output)
                    except Native303Blocked:
                        if not uncaught:
                            raise Native303Blocked("Unreviewed native validation warning") from None
                        fail_closed_rejections += 1
                if mode == "test" and not all(
                    s in output for s in ("2 pass", "0 fail", "Ran 2 tests across 1 file.")
                ):
                    raise Native303Blocked("Native read/denial mock did not pass both cases")
            cases.append(
                {
                    "case_id": name,
                    "original_model_code_sha256": entry["source_code_sha256"],
                    "native_strict_validation": "pass_with_gating_warning",
                    "uncaught_tool_call_hook_warning": True,
                    "fail_closed_safety_gate": "blocked",
                    "synthetic_read_denial_tests_passed": 2,
                    "original_code_type_correctness_certified": False,
                }
            )
        if {c["case_id"] for c in cases} != EXPECTED_CANDIDATES:
            raise Native303Blocked("Original source candidates missing or repeated")
        if gating_warnings != 5 or fail_closed_rejections != 5:
            raise Native303Blocked("Frozen native CLI303 warning evidence differs")
        negative = work / "mods/codex-01/hooks/register.js"
        negative.write_text(
            "export function register(on) {"
            " on('tool.call', async ($, e, next) => ({result: 'WRONG'}));"
            "}"
        )
        status, output = _run(_sandbox_argv(binary, work, "test", "codex-01"), cwd=work, timeout=35)
        if status == 0 or "fail" not in output:
            raise Native303Blocked("Native mock failed to catch incorrect tool result")
    return {
        "schema_version": 1,
        "first_party_release": "https://github.com/anthropics/claude-code/releases/tag/v2.1.303",
        "official_arm64_archive_sha256": OFFICIAL_ASSET_SHA256,
        "official_arm64_executable_sha256": OFFICIAL_BINARY_SHA256,
        "installed_native_binary_matches_official_executable": True,
        "sandboxed_executable_version": version,
        "embedded_core_type_evidence": core,
        "core_types_byte_identical_to_reviewed_302": True,
        "reviewed_reference_302_core_sha256": DECLARATION_SHA256,
        "original_model_fixture_manifest_sha256": file_sha256(FIXTURES / "manifest.json"),
        "safe_native_mock_fixture_sha256": file_sha256(MOCK_TEST),
        "original_302_model_code_candidates_reviewed": 5,
        "official_303_strict_native_validations_passed": 5,
        "official_303_native_mock_read_denial_tests_passed": 10,
        "official_303_native_mock_tests_failed": 0,
        "original_hook_without_catch_warnings": gating_warnings,
        "additional_fail_closed_safety_gate_rejections": fail_closed_rejections,
        "native_validation_exit_zero_does_not_certify_safe_hooks": True,
        "uncaught_gating_hooks_accepted_for_deployment": False,
        "incorrect_result_counterexample_rejected": True,
        "cases": cases,
        "actual_model_inference_calls": 0,
        "actual_user_tool_calls": 0,
        "host_home_credentials_or_network_mounted": False,
        "full_runtime_generated_builtin_tool_types_certified": False,
        "original_model_generated_code_completely_type_correct": False,
        "real_human_permission_host_verified": False,
        "all_31_cli303_claims_reviewed": False,
        "cli303_skill_or_chatgpt_plugin_promotion_authorized": False,
        "full_native_model_skill_acceptance": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-archive", required=True, type=Path)
    parser.add_argument(
        "--installed-binary",
        type=Path,
        default=Path.home() / ".local/share/claude/versions/2.1.303",
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: native evidence record must not be overwritten")
    try:
        result = audit(args.official_archive, args.installed_binary)
    except (Native303Blocked, ValueError, OSError, ctypes.ArgumentError):
        raise SystemExit("BLOCKED: official native 303 compatibility not verified") from None
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "core_matches_cli302": True,
                "native_mock_passed": result["official_303_native_mock_read_denial_tests_passed"],
                "strict_validation_exit_zero": result[
                    "official_303_strict_native_validations_passed"
                ],
                "fail_closed_gating_warnings_blocked": result[
                    "additional_fail_closed_safety_gate_rejections"
                ],
                "real_permission_host_approved": False,
                "new_claims_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
