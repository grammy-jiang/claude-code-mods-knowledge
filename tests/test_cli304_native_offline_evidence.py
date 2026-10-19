"""First-party CLI304 no-network permission and version-type checks are narrow.

Real native ARM64 CLI304 behavior ran on Raspberry Pi under Bubblewrap,
with no user Home, model, network or actual Read/Write permissions.
The official copyrighted core declarations remain private, never in Git.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "evals/fixtures/cli304-official-toolcheck-review"
TYPE_REPORT = ROOT / "docs/reports/2026-10-20-cli304-official-core-type-compatibility.json"
PERMISSION = ROOT / "docs/reports/2026-10-20-cli304-official-permission-native-sandbox.json"
BACKCOMPAT = ROOT / "docs/reports/2026-10-20-cli304-native-prior-observer-compat-mock.json"
OFFICIAL = ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
NATIVE_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
CORE_SHA = "6694767741c445872577d96a55fb08816d0f4b5783bc49e1eacd55f27b383308"


def _script(filename: str):
    spec = importlib.util.spec_from_file_location(
        "cli304_offline_source_test_" + filename,
        ROOT / "scripts" / filename,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_five_native_fixture_files_are_exact_sha_pinned() -> None:
    digest_map = json.loads((SRC / "source-hashes.json").read_text())
    assert digest_map["target_cli"] == "2.1.304"
    assert digest_map["official_binary_sha256"] == NATIVE_SHA
    assert digest_map["official_core_types_sha256"] == CORE_SHA
    assert len(digest_map["fixtures"]) == 5
    assert set(digest_map["fixtures"]) == {
        ".claude-plugin/plugin.json",
        "hooks/hooks.json",
        "hooks/register.js",
        "tests/check.test.ts",
        "toolcheck-delta.ts",
    }
    for filename, fingerprint in digest_map["fixtures"].items():
        file = SRC / filename
        assert file.is_file() and not file.is_symlink()
        assert hashlib.sha256(file.read_bytes()).hexdigest() == fingerprint
    source = (SRC / "hooks/register.js").read_text()
    assert source.count("on('tool.check'") == 1
    assert ").catch(" in source
    assert "return { ...originalVerdict, decider: 'person' }" in source
    assert "decision: 'deny'" in source
    assert "QA_SYNTHETIC_HOOK_ERROR_BLOCKED" in source


def test_actual_two_native_core_typechecks_prove_a_real_version_change() -> None:
    doc = json.loads(TYPE_REPORT.read_text())
    assert doc["typescript_version"] == "Version 6.0.3"
    assert doc["same_source_302_rejected_and_304_accepted"] is True
    assert doc["new_304_core_types_sha256"] == CORE_SHA
    assert doc["source_reviewed_prototype_sha256"] == (
        "d103f782bea523878d6978354498c25111c1384df60a9d37cb9be83e32c80884"
    )
    assert [(x["target_cli"], x["typescript_exit_code"]) for x in doc["two_typecheck_runs"]] == [
        ("2.1.302", 2),
        ("2.1.304", 0),
    ]
    assert doc["two_typecheck_runs"][0]["diagnostic_codes"] == ["TS2339", "TS2345"]
    assert doc["two_typecheck_runs"][1]["diagnostic_codes"] == []
    assert doc["native_type_source_content_exported_to_git"] is False
    assert doc["model_generated_code_executed"] is False
    assert doc["model_or_account_network_requests"] == 0
    assert doc["stable_release_authorized"] is False


def test_actual_native_304_permission_mock_covers_failure_and_warning() -> None:
    data = json.loads(PERMISSION.read_text())
    assert data["official_binary_sha256"] == NATIVE_SHA
    assert data["reviewed_target_cli"] == "2.1.304"
    assert data["source_fixture_count"] == 5
    assert (
        data["fixture_manifest_sha256"]
        == hashlib.sha256((SRC / "source-hashes.json").read_bytes()).hexdigest()
    )
    assert data["native_304_strict_mod_validation"] == "pass"
    assert data["native_304_permission_mock_tests_passed"] == 4
    assert data["native_304_permission_mock_tests_failed"] == 0
    assert data["native_304_forced_gating_exception_denied"] is True
    assert data["native_304_validation_reported_gating_with_catch"] is True
    assert data["native_304_uncaught_gating_warning_seen_in_counterexample"] is True
    assert data["additional_review_gate_rejected_native_missing_catch_warning"] is True
    assert data["execution_isolated_without_network_namespace"] is True
    assert data["native_model_or_account_calls_performed"] == 0
    assert data["real_user_approval_dialog_tested"] is False
    assert data["stable_release_authorized"] is False


def test_existing_302_observer_candidates_hold_a_small_backward_compat_subset():
    data = json.loads(BACKCOMPAT.read_text())
    assert data["target_cli"] == "2.1.304"
    assert data["official_native_bin_sha256"] == NATIVE_SHA
    assert data["original_302_model_snippet_sha256_verified"] == 5
    assert data["backward_compatible_strict_mod_validations_passed"] == 5
    assert data["backward_compatible_mocked_read_denial_tests_passed"] == 10
    assert data["backward_compatible_mocked_tests_failed"] == 0
    assert data["synthetic_wrong_result_detected"] is True
    assert len(data["cases"]) == 5
    assert data["complete_304_api_contract_verified"] is False
    assert data["current_304_plugin_release_authorized"] is False


def test_native_strict_warning_is_rejected_as_incomplete_gate_even_with_exit_zero():
    mod = _script("run_cli304_firstparty_mock_sandbox.py")
    original_success = "hooks: tool.check\ngating hook with .catch: tool.check\nValidation passed"
    mod.check_gating_validation(0, original_success)
    warning = "hooks: tool.check\ngating hook without .catch: tool.check\nValidation passed"
    with pytest.raises(mod.Native304Blocked):
        mod.check_gating_validation(0, warning)
    with pytest.raises(mod.Native304Blocked):
        mod.check_gating_validation(1, original_success)


@pytest.mark.parametrize(
    "tampered",
    (
        "3 pass\n0 fail\nRan 3 tests across 1 file.",
        "4 pass\n1 fail\nRan 4 tests across 1 file.",
        "4 pass\n0 fail\nRan 4 tests across 1 file.",
    ),
)
def test_native_mock_tap_cannot_be_laundered_by_totals_alone(tampered: str) -> None:
    mod = _script("run_cli304_firstparty_mock_sandbox.py")
    with pytest.raises(mod.Native304Blocked):
        mod.check_native_mock(0, tampered)


def test_release_remains_unapproved_and_user_material_is_private():
    upstream = json.loads(OFFICIAL.read_text())
    assert upstream["compiler_version_304_publish_authorized"] is False
    assert upstream["current_skill_promotion_authorized"] is False
    assert upstream["chatgpt_plugin_stable_release_authorized"] is False
    for file in (TYPE_REPORT, PERMISSION, BACKCOMPAT):
        data = file.read_text()
        for marker in (
            "/home/",
            "/Users/",
            "Authorization:",
            "Cookie:",
            "Plugin_",
            "TASK_ID:",
            "chatgpt.com/c/",
            "raw_reply",
            "sandbox:/mnt/data",
            "declare module 'claude-code'",
        ):
            assert marker not in data
        assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", data)
    assert not list((ROOT / "evals/fixtures/cli304-official-toolcheck-review").rglob("*.d.ts"))
