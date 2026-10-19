#!/usr/bin/env python3
"""Reproduce first-party CLI 2.1.304 tool.check no-network native MOCK QA.

Only the official SHA256-pinned v2.1.304 Linux ARM64 executable and tiny
reviewed synthetic source fixtures may run, inside mandatory Bubblewrap
with an unshared NETWORK and filesystem namespace. Never install the
binary, run a model, accept real user input, execute actual Read/Write,
read host Home/SSH, or change existing Claude/Pi configurations.

A native strict validator only WARNED about a gating hook without .catch.
Our QA gate MUST treat that warning as an error and confirm a deliberately
uncaught version fails this *stronger* gate.
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

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals/fixtures/cli304-official-toolcheck-review"
SOURCE = ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
OFFICIAL_BINARY_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
OFFICIAL_TARBALL_SHA = "17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5"
MAX_OUTPUT = 160_000
REQUIRED_VERSION = "2.1.304 (Claude Code)"


class Native304Blocked(ValueError):
    """Reviewed target binary, fixture, sandbox or native mock was invalid."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attest_fixture_and_binary(binary: Path, asset: Path) -> dict:
    if any(
        not path.is_file() or path.is_symlink()
        for path in (binary, asset, SOURCE, FIXTURES / "source-hashes.json")
    ):
        raise Native304Blocked("Missing reviewed official release asset and source")
    if _sha(binary) != OFFICIAL_BINARY_SHA or _sha(asset) != OFFICIAL_TARBALL_SHA:
        raise Native304Blocked("Official 304 native tar or executable SHA mismatch")
    source = json.loads(SOURCE.read_text())
    release = source["releases"][1]
    info = release["native_sandbox_target_review"]
    if (
        source["source_review_status"]
        != "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI304_API_CLAIMS"
        or source["compiler_version_304_publish_authorized"] is not False
        or info["official_linux_arm64_binary_sha256"] != OFFICIAL_BINARY_SHA
        or release["asset_linux_arm64"]["release_asset_sha256"] != "sha256:" + OFFICIAL_TARBALL_SHA
        or info["native_core_types_sha256"]
        != "6694767741c445872577d96a55fb08816d0f4b5783bc49e1eacd55f27b383308"
    ):
        raise Native304Blocked("Unreviewed target facts have changed")
    manifest = json.loads((FIXTURES / "source-hashes.json").read_text())
    files = manifest["fixtures"]
    if len(files) != 5 or manifest["target_cli"] != "2.1.304":
        raise Native304Blocked("Unexpected native Mod fixture set")
    expected = {str(p.relative_to(FIXTURES)) for p in FIXTURES.rglob("*") if p.is_file()}
    expected.remove("source-hashes.json")
    if set(files) != expected:
        raise Native304Blocked("Missing or unexpected native 304 source file")
    for name, hash_value in files.items():
        path = FIXTURES / name
        if path.is_symlink() or not re.fullmatch(r"[a-f0-9]{64}", hash_value):
            raise Native304Blocked("Invalid pinned native mock source file")
        if _sha(path) != hash_value:
            raise Native304Blocked("Native 304 test fixture was modified")
    return manifest


def sandbox_argv(
    bwrap: Path,
    binary: Path,
    work: Path,
    subcommand: str,
) -> list[str]:
    if (
        not bwrap.is_absolute()
        or not binary.is_absolute()
        or not binary.is_file()
        or not work.is_dir()
        or subcommand not in ("version", "validate", "test")
    ):
        raise Native304Blocked("Unsupported CLI304 sandbox operation")
    argv = ["/runtime/claude"]
    if subcommand == "version":
        argv += ["--version"]
    elif subcommand == "validate":
        argv += ["plugin", "validate", "--strict", "/work/qa-toolcheck304"]
    else:
        argv += ["plugin", "test", "/work/qa-toolcheck304"]
    return [
        str(bwrap),
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
        str(binary),
        "/runtime/claude",
        "--bind",
        str(work),
        "/work",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",  # noqa: S108 - isolated namespace, not host /tmp
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
        *argv,
    ]


def execute(argv: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - reviewed Bubblewrap absolute path
            argv,
            cwd=cwd,
            input="",
            capture_output=True,
            text=True,
            check=False,
            timeout=25,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        raise Native304Blocked("Native no-network 304 mock timed out") from exc
    result = proc.stdout + proc.stderr
    if len(result.encode()) > MAX_OUTPUT:
        raise Native304Blocked("Unbounded native mock output")
    return proc.returncode, result


def check_gating_validation(code: int, output: str) -> None:
    # Native --strict validation reported success WITH a missing catch.
    # This additional deterministic safety gate fails closed on warnings.
    if (
        code != 0
        or "Validation passed" not in output
        or "gating hook with .catch: tool.check" not in output
        or "gating hook without .catch" in output
    ):
        raise Native304Blocked("Current tool.check gating hook is not fail-closed")


def check_native_mock(code: int, output: str) -> None:
    if (
        code != 0
        or "4 pass" not in output
        or "0 fail" not in output
        or "Ran 4 tests across 1 file." not in output
    ):
        raise Native304Blocked("Native 304 permission and error mock incomplete")
    # Each of the four original QA test cases must have run exactly once.
    if output.count("(pass)") != 4:
        raise Native304Blocked("Native 304 mock pass count is not complete")


def audit(binary: Path, asset: Path) -> dict:
    manifest = attest_fixture_and_binary(binary, asset)
    bwrap_exe = shutil.which("bwrap")
    if not bwrap_exe or not Path(bwrap_exe).is_absolute():
        raise Native304Blocked("Cannot execute target code outside Linux Bubblewrap")
    bwrap = Path(bwrap_exe).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="mods304-bwrap-gating-") as temp:
        work = Path(temp) / "work"
        destination = work / "qa-toolcheck304"
        shutil.copytree(FIXTURES, destination)
        for kind in ("version", "validate", "test"):
            rc, out = execute(sandbox_argv(bwrap, binary, work, kind), work)
            if kind == "version" and (rc != 0 or out.strip() != REQUIRED_VERSION):
                raise Native304Blocked("Off-pinned native Claude CLI version")
            if kind == "validate":
                check_gating_validation(rc, out)
            if kind == "test":
                check_native_mock(rc, out)
        hook = destination / "hooks/register.js"
        original = hook.read_text()
        suffix = (
            "  }).catch(($ , e, next) => ({\n"
            "    decision: 'deny',\n"
            "    reason: 'QA_SYNTHETIC_HOOK_ERROR_BLOCKED'\n"
            "  }));\n"
        )
        if original.count(suffix) != 1:
            raise Native304Blocked("Reviewed gating .catch cannot be removed deterministically")
        # Construct a KNOWN BAD counterexample without modifying the
        # checked-in source: Native CLI warns but exits zero on this.
        hook.write_text(original.replace(suffix, "  });\n"))
        fail_rc, fail_out = execute(sandbox_argv(bwrap, binary, work, "validate"), work)
        if fail_rc != 0 or "gating hook without .catch" not in fail_out:
            raise Native304Blocked("Negative control no longer detects missing .catch")
        try:
            check_gating_validation(fail_rc, fail_out)
        except Native304Blocked:
            warning_rejected = True
        else:
            warning_rejected = False
        if not warning_rejected:
            raise Native304Blocked("Native strict warning was falsely scored as a pass")
    return {
        "schema_version": 1,
        "reviewed_target_cli": "2.1.304",
        "official_release_asset_sha256": OFFICIAL_TARBALL_SHA,
        "official_binary_sha256": OFFICIAL_BINARY_SHA,
        "fixture_manifest_sha256": hashlib.sha256(
            (FIXTURES / "source-hashes.json").read_bytes()
        ).hexdigest(),
        "source_fixture_count": len(manifest["fixtures"]),
        "native_304_strict_mod_validation": "pass",
        "native_304_validation_reported_gating_with_catch": True,
        "native_304_permission_mock_tests_passed": 4,
        "native_304_permission_mock_tests_failed": 0,
        "native_304_forced_gating_exception_denied": True,
        "native_304_uncaught_gating_warning_seen_in_counterexample": True,
        "additional_review_gate_rejected_native_missing_catch_warning": True,
        "execution_isolated_without_network_namespace": True,
        "host_home_or_secrets_mounted": False,
        "real_user_file_read_or_write_performed": False,
        "native_model_or_account_calls_performed": 0,
        "real_user_approval_dialog_tested": False,
        "fully_reviewed_cli304_skill_approved": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--official-asset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable CLI304 QA report already exists")
    try:
        report = audit(args.binary, args.official_asset)
    except (Native304Blocked, ValueError, OSError, subprocess.SubprocessError):
        raise SystemExit("BLOCKED: reviewed native 304 permission QA failed") from None
    args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(
        {
            "reviewed_native_304_mock_pass": 4,
            "strict_gating_catch_safety": True,
            "missing_catch_warning_rejected": True,
            "model_calls": 0,
            "real_user_permissions_approved": False,
            "stable_release_authorized": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
