"""Frozen independent CLI303 binary/core and sandboxed native evidence.

Never replay an online Claude session in deterministic offline CI. Only
first-party SHA-pinned evidence and exact original fixture identities are used.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-20-cli303-official-core-and-native-mock-parity.json"
MODEL_FIXTURE = ROOT / "evals/fixtures/p5-native-model-code-302/manifest.json"
MOCK_TEST = ROOT / "evals/fixtures/p5-native-model-code-302/mod-host-mock.test.ts"
CORE302 = "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
CORE304 = "6694767741c445872577d96a55fb08816d0f4b5783bc49e1eacd55f27b383308"
ASSET303 = "0c219f6d5fadf1ce5771f7976fe18d6a57a9b8267def5198b58d3e121eeb98c1"
BINARY303 = "f384f49826336d4ac0484ac6ac9d8d16f64d244d186ce227cbd7cc088c03315d"


def _audit_module(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("audit_cli303_official_native_parity")


def _original_fixtures() -> dict[str, str]:
    data = json.loads(MODEL_FIXTURE.read_text())
    found = {}
    for item in data["model_candidate_sources"]:
        for index, fixture in enumerate(item.get("fixtures", []), 1):
            name = f"{Path(fixture['path']).parts[0]}-{index:02d}"
            found[name] = fixture["code_sha256"]
        for block in item.get("source", {}).get("blocks", []):
            path = block.get("fixture_path")
            if path and not block["is_shell_command_not_mod_code"]:
                name = f"{Path(path).parts[0]}-{block['ordinal']:02d}"
                found[name] = block["code_sha256"]
    return found


def test_native_303_is_exact_first_party_binary_and_core_parity():
    report = json.loads(REPORT.read_text())
    assert report["schema_version"] == 1
    assert report["first_party_release"] == (
        "https://github.com/anthropics/claude-code/releases/tag/v2.1.303"
    )
    assert report["official_arm64_archive_sha256"] == ASSET303
    assert report["official_arm64_executable_sha256"] == BINARY303
    assert report["installed_native_binary_matches_official_executable"] is True
    assert report["sandboxed_executable_version"] == "2.1.303 (Claude Code)"
    core = report["embedded_core_type_evidence"]
    assert report["reviewed_reference_302_core_sha256"] == CORE302
    assert core["sha256"] == CORE302
    assert core["sha256"] != CORE304
    assert core["bytes"] == 651852
    assert core["one_exact_matching_frame"] is True
    assert core["frames_scanned"] >= 1
    assert report["core_types_byte_identical_to_reviewed_302"] is True
    upstream = json.loads(
        (
            ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
        ).read_text()
    )
    assert upstream["releases"][0]["version"] == "2.1.303"
    assert upstream["version_303_api_compatibility_proven"] is False


def test_native_303_mock_real_source_identity_is_complete():
    report = json.loads(REPORT.read_text())
    assert (
        report["original_model_fixture_manifest_sha256"]
        == hashlib.sha256(MODEL_FIXTURE.read_bytes()).hexdigest()
    )
    assert (
        report["safe_native_mock_fixture_sha256"]
        == hashlib.sha256(MOCK_TEST.read_bytes()).hexdigest()
    )
    assert report["original_302_model_code_candidates_reviewed"] == 5
    assert report["official_303_strict_native_validations_passed"] == 5
    assert report["official_303_native_mock_read_denial_tests_passed"] == 10
    assert report["official_303_native_mock_tests_failed"] == 0
    assert report["original_hook_without_catch_warnings"] == 5
    assert report["additional_fail_closed_safety_gate_rejections"] == 5
    assert report["native_validation_exit_zero_does_not_certify_safe_hooks"] is True
    assert report["uncaught_gating_hooks_accepted_for_deployment"] is False
    assert report["incorrect_result_counterexample_rejected"] is True
    cases = report["cases"]
    assert len(cases) == 5
    expected = _original_fixtures()
    assert set(expected) == {"codex-01", "codex-02", "sonnet-01", "sonnet-02", "sonnet-03"}
    assert {x["case_id"]: x["original_model_code_sha256"] for x in cases} == expected
    assert all(x["native_strict_validation"] == "pass_with_gating_warning" for x in cases)
    assert all(x["uncaught_tool_call_hook_warning"] is True for x in cases)
    assert all(x["fail_closed_safety_gate"] == "blocked" for x in cases)
    assert all(x["synthetic_read_denial_tests_passed"] == 2 for x in cases)
    assert all(x["original_code_type_correctness_certified"] is False for x in cases)


def test_native_303_subset_cannot_be_misreported_as_full_compatibility():
    record = json.loads(REPORT.read_text())
    for key in (
        "full_runtime_generated_builtin_tool_types_certified",
        "original_model_generated_code_completely_type_correct",
        "real_human_permission_host_verified",
        "all_31_cli303_claims_reviewed",
        "cli303_skill_or_chatgpt_plugin_promotion_authorized",
        "full_native_model_skill_acceptance",
        "stable_release_authorized",
        "host_home_credentials_or_network_mounted",
    ):
        assert record[key] is False
    assert record["actual_model_inference_calls"] == 0
    assert record["actual_user_tool_calls"] == 0
    sources = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    for target in ("2.1.303", "2.1.304"):
        assert approved_claims(claims, target, "cli") == []
        with pytest.raises(CompilerError, match="No approved Claims"):
            compile_knowledge(ROOT, api_version=target, surface="cli", source_revision="303-only")


def test_official_asset_mismatch_and_symlink_fail_before_any_binary_execution(
    tmp_path, monkeypatch
):
    mod = _audit_module(monkeypatch)
    assert mod.OFFICIAL_ASSET_SHA256 == ASSET303
    assert mod.OFFICIAL_BINARY_SHA256 == BINARY303
    fake_archive = tmp_path / "fake.tar.gz"
    fake_archive.write_bytes(b"incorrect")
    fake_binary = tmp_path / "claude"
    fake_binary.write_bytes(b"not an upstream binary")
    with pytest.raises(mod.Native303Blocked):
        mod.attest_official_archive(fake_archive, fake_binary)
    symlink = tmp_path / "alias"
    symlink.symlink_to(fake_binary)
    with pytest.raises(mod.Native303Blocked):
        mod.attest_official_archive(fake_archive, symlink)


def test_native_validation_exit_zero_with_missing_catch_still_fails_safety_gate(monkeypatch):
    mod = _audit_module(monkeypatch)
    good = "gating hook with .catch: tool.call\nValidation passed"
    mod.fail_closed_validation_gate(0, good)
    for unsafe in (
        "gating hook without .catch: tool.call\nValidation passed",
        "Warning: permission shortcut\nValidation passed",
    ):
        with pytest.raises(mod.Native303Blocked):
            mod.fail_closed_validation_gate(0, unsafe)
    with pytest.raises(mod.Native303Blocked):
        mod.fail_closed_validation_gate(1, good)


def test_public_303_record_contains_no_private_source_or_credentials():
    text = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Cookie:",
        "Authorization:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "declare module 'claude-code'",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in text
    assert "2.1.302" not in str(json.loads(REPORT.read_text())["sandboxed_executable_version"])
