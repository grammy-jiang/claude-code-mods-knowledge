#!/usr/bin/env python3
"""Prove the hook REGISTRATION .catch contract on exact native 302/303/304.

The tests are synthetic, source-pinned, offline, and run only within mandatory
Linux Bubblewrap with separate network/user namespaces and disposable Home.
Do not mistake this for actual model or production-user approval. Official
Claude executable and archived source identities are checked before execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from audit_p5_original_model_code import FIXTURES, stage
from run_cli304_firstparty_mock_sandbox import sandbox_argv
from run_p5_model_code_native_host_sandbox import _create_mod_folder, _run, _sandbox_argv

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "evals/fixtures/p5-cli302-hook-catch"
ORIGINALS = FIXTURES
BIN_SHA = {
    "2.1.302": "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10",
    "2.1.303": "f384f49826336d4ac0484ac6ac9d8d16f64d244d186ce227cbd7cc088c03315d",
    "2.1.304": "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3",
}
ASSET304 = "17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5"
VALID = ("normal", "prethrow", "postthrow")


class CatchNativeBlocked(ValueError):
    """Input, native warning or original-result behavior has changed."""


def digest(p: Path) -> str:
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def pin(bin_map: dict[str, Path], asset: Path) -> dict:
    manifest_path = SOURCES / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise CatchNativeBlocked("Missing reviewed fixture identity")
    manifest = json.loads(manifest_path.read_text())
    expect_files = {f"{name}.js" for name in (*VALID, "wrong-deny")} | {"observer.test.ts"}
    found_files = {p.name for p in SOURCES.iterdir() if p.is_file() and p.name != "manifest.json"}
    if (
        manifest.get("schema_version") != 1
        or manifest.get("reviewed_core_version") != "2.1.302"
        or manifest.get("all_synthetic_no_model_generated_code") is not True
        or set(manifest.get("sources", {})) != expect_files
        or found_files != expect_files
        or any(digest(SOURCES / name) != manifest["sources"][name] for name in expect_files)
    ):
        raise CatchNativeBlocked("Fixture mismatch or unreviewed synthetic source")
    for version, expected in BIN_SHA.items():
        path = bin_map.get(version)
        if not path or not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise CatchNativeBlocked("First-party target native binary mismatch")
    if not asset.is_file() or asset.is_symlink() or digest(asset) != ASSET304:
        raise CatchNativeBlocked("First-party 304 release archive mismatch")
    bwrap = shutil.which("bwrap")
    if not bwrap or not Path(bwrap).is_absolute():
        raise CatchNativeBlocked("Linux unprivileged Bubblewrap namespace is mandatory")
    return {"fixture_manifest_sha256": digest(manifest_path), "bwrap": str(Path(bwrap).resolve())}


def stage_mod(work: Path, variant: str) -> None:
    target = work / "qa-toolcheck304"
    for sub in (".claude-plugin", "hooks", "tests"):
        (target / sub).mkdir(parents=True, exist_ok=True)
    (target / ".claude-plugin/plugin.json").write_text(
        json.dumps(
            {
                "name": "qa-only-p5-catch",
                "version": "0.0.1",
                "description": "Safe native no-network hook catch mock",
                "author": {"name": "QA"},
            }
        )
        + "\n"
    )
    (target / "hooks/hooks.json").write_text(
        json.dumps(
            {
                "description": "Synthetic transparent observer only",
                "modules": ["./register.js"],
            }
        )
        + "\n"
    )
    shutil.copyfile(SOURCES / f"{variant}.js", target / "hooks/register.js")
    shutil.copyfile(SOURCES / "observer.test.ts", target / "tests/observer.test.ts")


def validate_native(output: str, code: int, *, catch: bool) -> None:
    expected = f"gating hook {'with' if catch else 'without'} .catch: tool.call"
    if (
        code != 0
        or "Validation passed" not in output
        or expected not in output
        or (catch and "gating hook without .catch" in output)
        or "warning:" in output.lower()
    ):
        raise CatchNativeBlocked("Native hook validation or warning did not match")


def audit(binaries: dict[str, Path], asset: Path) -> dict:
    attested = pin(binaries, asset)
    rows: list[dict] = []
    old_warnings = 0
    with tempfile.TemporaryDirectory(prefix="mods-p5-hookcatch-bwrap-") as temp:
        work = Path(temp) / "work"
        originals = stage(ORIGINALS, work)
        if originals["original_reviewed_source_files"] != 5:
            raise CatchNativeBlocked("Original model modules not exactly SHA-bound")
        version302 = binaries["2.1.302"]
        for row in originals["per_case"]:
            name = row["sandbox_module_name"].removesuffix(".mjs")
            _create_mod_folder(work, name, work / "candidates" / row["sandbox_module_name"])
            code, output = _run(
                _sandbox_argv(version302, work, "validate", name), cwd=work, timeout=35
            )
            validate_native(output, code, catch=False)
            old_warnings += 1
        if old_warnings != 5:
            raise CatchNativeBlocked("Unfixed original code warning count is not five")
        for version, binary in binaries.items():
            argv = sandbox_argv(Path(attested["bwrap"]), binary, work, "version")
            code, output = _run(argv, cwd=work, timeout=30)
            if code != 0 or output.strip() != f"{version} (Claude Code)":
                raise CatchNativeBlocked("Isolated binary version mismatch")
            for variant in VALID:
                stage_mod(work, variant)
                codes: dict[str, int] = {}
                for mode in ("validate", "test"):
                    argv = sandbox_argv(Path(attested["bwrap"]), binary, work, mode)
                    status, out = _run(argv, cwd=work, timeout=35)
                    if mode == "validate":
                        validate_native(out, status, catch=True)
                    else:
                        if (
                            status != 0
                            or "2 pass" not in out
                            or "0 fail" not in out
                            or "Ran 2 tests across 1 file." not in out
                            or out.count("(pass)") != 2
                        ):
                            raise CatchNativeBlocked("Native stub result/denial not preserved")
                    codes[mode] = status
                rows.append(
                    {
                        "native_cli": version,
                        "variant": variant,
                        "source_sha256": digest(SOURCES / f"{variant}.js"),
                        "native_strict_catch_warning_free": True,
                        "native_mock_read_and_denial_passed": 2,
                        "native_mock_downstream_invocations_per_case": 1,
                    }
                )
            stage_mod(work, "wrong-deny")
            argv = sandbox_argv(Path(attested["bwrap"]), binary, work, "test")
            status, output = _run(argv, cwd=work, timeout=35)
            if status == 0 or "fail" not in output or "QA_EXACT_DOWNSTREAM_RESULT" not in output:
                raise CatchNativeBlocked(
                    "Unsafe response-replacing .catch escaped negative control"
                )
    if len(rows) != 9:
        raise CatchNativeBlocked("Expected three native versions and three variants")
    return {
        "schema_version": 1,
        "scope": "safe-synthetic-native-cli-mock-not-production",
        "versions": sorted(BIN_SHA),
        "reviewed_302_core_sha256": "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e",
        "native_binary_sha256": BIN_SHA,
        "official_304_archive_sha256": ASSET304,
        "fixture_manifest_sha256": attested["fixture_manifest_sha256"],
        "original_model_302_missing_catch_warnings": old_warnings,
        "fixed_native_validate_with_catch_count": 9,
        "fixed_native_mock_pass_count": 18,
        "wrong_result_or_deny_catch_native_rejected_per_version": 3,
        "original_model_code_modified": False,
        "real_model_inference_requests": 0,
        "real_user_permission_calls": 0,
        "native_thrown_error_object_identity_proven": False,
        "full_runtime_generated_tool_types_proven": False,
        "latest_cli_api_claims_approved": False,
        "stable_release_authorized": False,
        "original_model_code_candidate_type_errors_still_open": True,
        "real_user_tool_calls_or_host_home_mounted": False,
        "cases": rows,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for ver in ("302", "303", "304"):
        p.add_argument(f"--binary{ver}", type=Path, required=True)
    p.add_argument("--asset304", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or a.out.is_symlink():
        raise SystemExit("REFUSED: native source evidence is immutable")
    try:
        report = audit(
            {"2.1.302": a.binary302, "2.1.303": a.binary303, "2.1.304": a.binary304}, a.asset304
        )
    except (CatchNativeBlocked, OSError, ValueError, KeyError):
        raise SystemExit("BLOCKED: original hooks and fail-closed catch were not proven") from None
    a.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "native_validations_warning_free": report["fixed_native_validate_with_catch_count"],
                "native_read_denial_mock_passed": report["fixed_native_mock_pass_count"],
                "original_302_missing_catch_warnings": report[
                    "original_model_302_missing_catch_warnings"
                ],
                "unsafe_replacing_catch_rejected": report[
                    "wrong_result_or_deny_catch_native_rejected_per_version"
                ],
                "approved_for_release": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
