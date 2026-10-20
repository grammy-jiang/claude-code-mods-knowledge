#!/usr/bin/env python3
"""First-party Claude CLI304 tool.check *mock-only* high-risk boundary audit.

The SHA-pinned official ARM64 executable and reviewed synthetic fixture run
exclusively in mandatory networkless Linux Bubblewrap. No real user account,
Home, Read/Write tools or permission dialogues are available. In particular,
an explicitly supplied isReadOnly:true is NOT proof that an actual host marks
all real Read tool calls as read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from run_cli304_firstparty_mock_sandbox import (
    OFFICIAL_BINARY_SHA,
    OFFICIAL_TARBALL_SHA,
    Native304Blocked,
    execute,
    sandbox_argv,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals/fixtures/cli304-toolcheck-p1-boundaries"
TAP_CASES = (
    "Read surfaces expected metadata",
    "Write ask is delegated to person",
    "Write deny must remain deny",
    "Write allow remains allow",
    "Thrown hook denied by registration catch",
    "A deliberately injected synthetic read-only flag can be read",
)


class P1Native304Blocked(ValueError):
    """Current pinned native ABI/fixture/permission mock is not verified."""


def sha(file: Path) -> str:
    with file.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def attestation(binary: Path, asset: Path) -> dict:
    if (
        any(
            not file.is_file() or file.is_symlink()
            for file in (binary, asset, FIXTURES / "source-hashes.json")
        )
        or sha(binary) != OFFICIAL_BINARY_SHA
        or sha(asset) != OFFICIAL_TARBALL_SHA
    ):
        raise P1Native304Blocked("Missing first-party official CLI304 release bytes")
    manifest = json.loads((FIXTURES / "source-hashes.json").read_text())
    sources = manifest.get("fixtures")
    expected_files = {
        ".claude-plugin/plugin.json",
        "hooks/hooks.json",
        "hooks/register.js",
        "tests/check.test.ts",
    }
    actual_files = {str(p.relative_to(FIXTURES)) for p in FIXTURES.rglob("*") if p.is_file()}
    if (
        manifest.get("schema_version") != 1
        or manifest.get("target_cli") != "2.1.304"
        or manifest.get("official_native_bin_sha256") != OFFICIAL_BINARY_SHA
        or manifest.get("official_tar_sha256") != OFFICIAL_TARBALL_SHA
        or manifest.get("actual_human_permission_verified") is not False
        or manifest.get("real_readonly_host_metadata_verified") is not False
        or not isinstance(sources, dict)
        or set(sources) != expected_files
        or actual_files != expected_files | {"source-hashes.json"}
        or manifest.get("expected_test_cases") != list(TAP_CASES)
    ):
        raise P1Native304Blocked("Unreviewed native tool.check fixture manifest")
    for name, fingerprint in sources.items():
        path = FIXTURES / name
        if path.is_symlink() or sha(path) != fingerprint:
            raise P1Native304Blocked("Unpinned synthetic tool.check source bytes")
    executable = shutil.which("bwrap")
    if not executable or not Path(executable).is_absolute():
        raise P1Native304Blocked("Linux Bubblewrap with unshared network is mandatory")
    return {
        "fixture_manifest_sha256": sha(FIXTURES / "source-hashes.json"),
        "bwrap": Path(executable).resolve(strict=True),
    }


def _run(bwrap: Path, binary: Path, work: Path, mode: str) -> tuple[int, str]:
    return execute(sandbox_argv(bwrap, binary, work, mode), work)


def assert_strict_with_catch(rc: int, output: str) -> None:
    if (
        rc != 0
        or "Validation passed" not in output
        or "gating hook with .catch: tool.check" not in output
        or "gating hook without .catch" in output
        or "warning" in output.lower()
    ):
        raise P1Native304Blocked("Native strict validator not warning-free")


def assert_mock_six(rc: int, output: str) -> None:
    if (
        rc != 0
        or "6 pass" not in output
        or "0 fail" not in output
        or "Ran 6 tests across 1 file." not in output
        or output.count("(pass)") != 6
        or any(output.count("(pass) " + name) != 1 for name in TAP_CASES)
    ):
        raise P1Native304Blocked("Native permission mock evidence incomplete")


def audit(binary: Path, asset: Path) -> dict:
    attested = attestation(binary, asset)
    with tempfile.TemporaryDirectory(prefix="mods-cli304-p1-native-") as tmp:
        work = Path(tmp) / "work"
        fixture = work / "qa-toolcheck304"
        shutil.copytree(FIXTURES, fixture)
        bwrap = attested["bwrap"]
        rc, out = _run(bwrap, binary, work, "version")
        if rc != 0 or out.strip() != "2.1.304 (Claude Code)":
            raise P1Native304Blocked("Wrong native Claude Code target")
        rc, out = _run(bwrap, binary, work, "validate")
        assert_strict_with_catch(rc, out)
        rc, out = _run(bwrap, binary, work, "test")
        assert_mock_six(rc, out)
        handler = fixture / "hooks/register.js"
        original = handler.read_text()
        if original.count("}).catch(") != 1:
            raise P1Native304Blocked("Native test has unexpected hook catch form")
        handler.write_text(original.replace("}).catch(", "}); /* no outer catch */ (", 1))
        rc, out = _run(bwrap, binary, work, "validate")
        if not (
            rc == 0
            and "Validation passed" in out
            and "gating hook without .catch: tool.check" in out
        ):
            raise P1Native304Blocked("Native unguarded hook counterexample not detected")
        try:
            assert_strict_with_catch(rc, out)
        except P1Native304Blocked:
            warned = True
        else:
            raise P1Native304Blocked("Fail-closed safety gate accepted native catch warning")
        handler.write_text(original)
        signature = "if (origin.decision === 'ask') return {...origin,decider:'person'};"
        if original.count(signature) != 1:
            raise P1Native304Blocked("Reviewed denial-preserving source pattern changed")
        handler.write_text(
            original.replace(signature, "return {decision:'allow',reason:'QA_BAD_OVERRIDE'};")
        )
        rc, out = _run(bwrap, binary, work, "test")
        if rc == 0 or "(fail) Write deny must remain deny" not in out:
            raise P1Native304Blocked("Mock suite did not reject permissive denial override")
    return {
        "schema_version": 1,
        "reviewed_target_cli": "2.1.304",
        "official_native_binary_sha256": OFFICIAL_BINARY_SHA,
        "official_release_tar_sha256": OFFICIAL_TARBALL_SHA,
        "trusted_fixture_manifest_sha256": attested["fixture_manifest_sha256"],
        "strict_plugin_validation_with_catch_passed": True,
        "native_synthetic_permission_cases_passed": 6,
        "native_synthetic_permission_cases_failed": 0,
        "simulated_read_without_explicit_metadata_isReadOnly": "undefined",
        "synthetic_explicit_isReadOnly_true_handled": True,
        "native_mock_event_and_input_deep_frozen": True,
        "synthetic_write_ask_preserved_and_person_decider": True,
        "synthetic_write_deny_preserved": True,
        "synthetic_write_allow_preserved": True,
        "synthetic_hook_exception_denied": True,
        "unsafe_missing_catch_warning_exit_zero_rejected": warned,
        "unsafe_permission_deny_override_mock_rejected": True,
        "actual_host_readonly_classification_verified": False,
        "actual_host_person_dialog_approved": False,
        "actual_managed_rule_precedence_verified": False,
        "actual_cross_plugin_skip_transcript_verified": False,
        "actual_failed_reload_lifecycle_verified": False,
        "real_user_tools_or_credentials_exposed": False,
        "real_model_requests": 0,
        "sandbox_unshares_network": True,
        "all_31_claims_approved_for_304": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-binary", type=Path, required=True)
    parser.add_argument("--official-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    if opts.out.exists() or opts.out.is_symlink():
        raise SystemExit("REFUSED: immutable P1 native permission evidence exists")
    try:
        data = audit(opts.official_binary, opts.official_archive)
    except (P1Native304Blocked, Native304Blocked, ValueError, OSError, subprocess.SubprocessError):
        raise SystemExit("BLOCKED: native 304 tool.check boundary evidence incomplete") from None
    opts.out.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "native_tests_passed": data["native_synthetic_permission_cases_passed"],
                "readOnly_not_auto_set_in_mock": True,
                "unsafe_missing_catch_rejected": data[
                    "unsafe_missing_catch_warning_exit_zero_rejected"
                ],
                "unsafe_deny_override_rejected": data[
                    "unsafe_permission_deny_override_mock_rejected"
                ],
                "host_permission_callback_verified": False,
                "stable_release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
