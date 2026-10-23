"""Pinned native 309 /verify & /code-review: nested Skill is not always invoked."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts/audit_cli309_bundled_nested_evidence.py"
REPORT = ROOT / "docs/reports/2026-10-23-cli309-bundled-nested-native-evidence.json"
FIXTURE = ROOT / "evals/fixtures/cli309-bundled-nested-20261023"

_spec = importlib.util.spec_from_file_location("cli309_bundled_replay", AUDITOR)
assert _spec and _spec.loader
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report() -> dict:
    return json.loads(REPORT.read_text())


def test_genuine_native_versions_and_all_reviewed_fixture_sources_are_pinned():
    record = report()
    assert record["schema_version"] == 1
    assert record["target_version"] == "2.1.309"
    assert record["official_native_binary_sha256"] == audit.BINARY_SHA
    assert record["independent_auditor_sha256"] == file_sha(AUDITOR)
    assert set(record["per_host_original_native_proof"]) == {"rpi-a", "rpi-b"}
    assert record["all_original_host_private_replays_byte_identical"] is True
    assert record["two_host_shell_modified_nested_file_proven"] is True
    assert record["two_host_same_continuing_session_for_verify_and_code_review"] is True
    for host, evidence in record["per_host_original_native_proof"].items():
        assert evidence["host"] == host
        assert evidence["original_target_native"] == "2.1.309"
        assert evidence["original_native_binary_sha256"] == audit.BINARY_SHA
        assert evidence["auditor_source_sha256"] == file_sha(AUDITOR)
        assert evidence["fixture_sha256"] == audit.FIXTURE_HASHES
        assert evidence["three_actual_model_results"] == 3
        assert evidence["one_continuing_native_session"] is True
        assert evidence["preexisting_git_baseline_verified"] is True
        assert evidence["shell_change_only_one_nested_file"] is True
        assert evidence["actual_models"] == ["claude-sonnet-5-5"]
        for key in (
            "original_wire_sha256",
            "original_debug_sha256",
            "shell_side_changed_file_sha256",
        ):
            assert re.fullmatch(r"[0-9a-f]{64}", evidence[key])
        for rel, expected in audit.FIXTURE_HASHES.items():
            assert file_sha(FIXTURE / rel) == expected
        assert record["private_replayed_original_host_evidence_sha256"][host]
        assert re.fullmatch(
            r"[0-9a-f]{64}", record["private_replayed_original_host_evidence_sha256"][host]
        )


def test_after_shell_edit_native_verify_actual_skill_invocation_is_host_scoped():
    first = report()["per_host_original_native_proof"]["rpi-a"]
    second = report()["per_host_original_native_proof"]["rpi-b"]
    assert first["native_dynamic_nested_skill_discovery_logged"] is True
    assert second["native_dynamic_nested_skill_discovery_logged"] is True
    assert first["verify_detected_off_by_one"] is True
    assert second["verify_detected_off_by_one"] is True
    assert first["verify_uses"] == ["Bash", "Skill", "Bash", "Bash"]
    assert first["verify_actual_skill_tool_targets"] == [audit.SKILL]
    assert first["verify_used_natively_invoked_nested_skill"] is True
    assert second["verify_uses"] == ["Bash", "Bash", "Bash"]
    assert second["verify_actual_skill_tool_targets"] == []
    assert second["verify_only_read_nested_skill_source"] is True
    assert second["verify_used_natively_invoked_nested_skill"] is False
    for host in (first, second):
        assert host["verify_runtime_execution_blocked"] is True
        assert host["verify_full_runtime_pass"] is False


def test_bundled_code_review_is_not_claimed_to_have_invoked_nested_skill():
    record = report()
    pi = record["per_host_original_native_proof"]["rpi-a"]
    sextant = record["per_host_original_native_proof"]["rpi-b"]
    assert pi["code_review_uses"] == ["Bash", "Read"]
    assert pi["code_review_status"] == "partial_read_fallback_found_correct_regression"
    assert sextant["code_review_uses"] == ["Bash"]
    assert sextant["code_review_status"] == "read_only_git_diff_permission_blocked"
    assert pi["code_review_native_skill_tool_invoked"] is False
    assert sextant["code_review_native_skill_tool_invoked"] is False
    assert record["code_review_skill_tool_invocation_proven"] is False
    assert record["code_review_outcome_consistent_across_hosts"] is False
    assert record["full_runtime_verify_pass"] is False
    assert record["one_host_verify_native_skill_tool_pass"] is True
    assert record["other_host_verify_read_skill_source_without_native_skill_tool"] is True


def test_synthetic_native_result_groups_never_prove_extra_turns():
    example = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill"}]}},
        {"type": "result", "subtype": "success"},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
        {"type": "result", "subtype": "success"},
    ]
    with pytest.raises(audit.BundledNativeInvalid, match="MISSING_NATIVE_BUNDLED_COMMAND_TURNS"):
        audit._test_results(example)
    with pytest.raises(audit.BundledNativeInvalid, match="EXTRA_NATIVE_QA_TURN"):
        audit._test_results([*example, {"type": "result"}, {"type": "result"}, {"type": "result"}])


def test_no_309_claim_approval_or_full_product_release_from_bounded_recipe_fixture():
    data = report()
    assert data["native_code_modifications_outside_disposable_scratch"] is False
    assert data["production_cli_skill_plugin_unmodified_by_QA"] is True
    assert all(
        original["complete_mods_ssot_model_answer_quality_pass"] is False
        for original in data["per_host_original_native_proof"].values()
    )
    assert data["new_cli309_claim_approvals"] == 0
    assert data["chat_mode_acceptance_proven"] is False
    assert data["stable_release_authorized"] is False
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.309", "cli") == []
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(
            ROOT, api_version="2.1.309", surface="cli", source_revision="bundled-qa-unapproved"
        )


def test_public_report_contains_only_digest_facts_not_private_native_text():
    text = REPORT.read_text()
    for item in (
        "/home/",
        "/Users/",
        "Authorization:",
        "Cookie:",
        "access_token",
        "session_id",
        "tool_use_id",
        "BEGIN PRIVATE KEY",
        "sandbox:/mnt/data",
    ):
        assert item not in text
    assert (
        re.search(
            r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])",
            text,
        )
        is None
    )


def test_missing_private_original_native_wire_cannot_be_fabricated_from_public_summary(
    tmp_path: Path,
):
    with pytest.raises((audit.BundledNativeInvalid, OSError, ValueError)):
        audit.audit(tmp_path, FIXTURE, tmp_path / "nonexistent-native-binary", host="rpi-a")
