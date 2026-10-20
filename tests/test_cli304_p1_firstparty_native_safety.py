"""Proof boundary: 31 fresh official anchors + six *synthetic* native cases.

The official 304 HTML/Markdown and native binary were verified privately.
CI checks frozen public SHA provenance and fails closed on any promotion
claim, scope drift, fake success count or untrusted source revision.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "docs/reports/2026-10-20-cli304-p1-all31-fresh-primary-anchor-matrix.json"
NATIVE = ROOT / "docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json"
OLDER = ROOT / "docs/reports/2026-10-20-cli304-31-claim-preapproval-audit.json"
FIXTURES = ROOT / "evals/fixtures/cli304-toolcheck-p1-boundaries"
BINARY_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
ARCHIVE_SHA = "17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _script(filename: str):
    spec = importlib.util.spec_from_file_location(
        "cli304_p1_" + filename, ROOT / "scripts" / filename
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_all_31_original_claim_identities_and_32_official_anchors_attested():
    matrix = json.loads(PRIMARY.read_text())
    prior = json.loads(OLDER.read_text())
    source = {row["original_reviewed_claim_id"]: row for row in prior["claims"]}
    assert matrix["source_capture_day_sydney"] == "2026-10-20"
    assert matrix["review_target"] == "2.1.304"
    assert matrix["prior_reviewed_target"] == "2.1.302"
    assert matrix["prior_302_claims_checked"] == 31
    assert matrix["fresh_official_html_and_markdown_pages"] == 7
    assert matrix["first_party_original_locator_occurrences_verified"] == 32
    assert matrix["unique_fresh_html_heading_ids_verified"] == 22
    assert matrix["all_31_current_official_anchors_are_present"] is True
    assert matrix["original_31_claim_preapproval_sha256"] == digest(OLDER)
    rows = matrix["claim_review_queue"]
    assert len(rows) == len(source) == 31
    assert {row["prior_302_claim"] for row in rows} == set(source)
    assert sum(len(row["current_304_official_anchor_checks"]) for row in rows) == 32
    observed_pairs = set()
    for row in rows:
        cid = row["prior_302_claim"]
        previous = source[cid]
        assert row["subject"] == previous["subject"]
        assert row["original_claim_sha256"] == digest(ROOT / f"claims/{cid}.json")
        assert row["original_decision_sha256"] == digest(ROOT / f"decisions/{cid}.json")
        assert row["original_claim_sha256"] == previous["original_claim_sha256"]
        assert row["original_decision_sha256"] == previous["original_decision_sha256"]
        assert row["review_lane"] == previous["review_lane"]
        assert row["api_semantics_verified_for_304"] is False
        assert row["new_304_claim_approved"] is False
        assert row["first_party_structural_verdict"] == "ANCHORS_VERIFIED_ONLY"
        assert len(row["specific_review_question"]) >= 40
        assert set(
            x["firstparty_original_exact_locator"]
            for x in row["current_304_official_anchor_checks"]
        ) == set(previous["original_302_exact_official_urls"])
        for anchor in row["current_304_official_anchor_checks"]:
            assert anchor["html_anchor_present_once"] is True
            assert anchor["matching_heading_in_markdown"] is True
            assert anchor["current_html_heading_tag"] in ("h2", "h3", "h4")
            assert 3 <= len(anchor["current_html_heading"]) < 120
            url = anchor["firstparty_original_exact_locator"]
            assert url.startswith("https://code.claude.com/docs/en/plugins/mods/")
            assert "#" in url
            observed_pairs.add(url)
    assert len(observed_pairs) == 22
    expected_lanes = {
        "first_party_delta_touchpoint": 8,
        "native_mock_subset_not_full_host": 8,
        "fresh_target_official_review_required": 14,
        "known_302_source_type_conflict_blocking_promotion": 1,
    }
    assert Counter(row["review_lane"] for row in rows) == expected_lanes
    assert matrix["review_lane_counts"] == expected_lanes


def test_all_seven_independent_first_party_page_digest_pairs_are_recorded():
    matrix = json.loads(PRIMARY.read_text())
    registry = load_registry(ROOT / "sources/registry.json")
    pages = matrix["source_pages"]
    assert len(pages) == 7
    assert {entry["official_url"].rsplit("/", 1)[-1] for entry in pages} == {
        "admin",
        "create",
        "events",
        "interface",
        "overview",
        "reference",
        "test",
    }
    for entry in pages:
        source = registry[entry["source_id"]]
        assert entry["official_url"] == source["url"]
        assert entry["original_registry_pinned_html_sha256"] == source["snapshot"]["sha256"]
        assert entry["original_pinned_revision_not_modified"] is True
        assert entry["fresh_html_sha256"] != entry["original_registry_pinned_html_sha256"]
        assert len(entry["fresh_html_sha256"]) == 64
        assert len(entry["fresh_markdown_sha256"]) == 64
        assert 1000 < entry["fresh_html_bytes"] < 2_000_000
        assert 1000 < entry["fresh_markdown_bytes"] < 100_000
    assert matrix["fresh_source_revisions_not_promoted_into_approved_SSOT"] is True


def test_native_permission_sandbox_proves_only_six_synthetic_cases():
    result = json.loads(NATIVE.read_text())
    matrix = json.loads(PRIMARY.read_text())
    manifest = json.loads((FIXTURES / "source-hashes.json").read_text())
    assert result["reviewed_target_cli"] == "2.1.304"
    assert result["official_native_binary_sha256"] == BINARY_SHA
    assert result["official_release_tar_sha256"] == ARCHIVE_SHA
    assert result["trusted_fixture_manifest_sha256"] == digest(FIXTURES / "source-hashes.json")
    assert len(manifest["fixtures"]) == 4
    assert len(manifest["expected_test_cases"]) == 6
    for path, expected_sha in manifest["fixtures"].items():
        fixture = FIXTURES / path
        assert fixture.is_file() and not fixture.is_symlink()
        assert digest(fixture) == expected_sha
    assert result["strict_plugin_validation_with_catch_passed"] is True
    assert result["native_synthetic_permission_cases_passed"] == 6
    assert result["native_synthetic_permission_cases_failed"] == 0
    assert result["simulated_read_without_explicit_metadata_isReadOnly"] == "undefined"
    assert result["synthetic_explicit_isReadOnly_true_handled"] is True
    assert result["native_mock_event_and_input_deep_frozen"] is True
    assert result["synthetic_write_ask_preserved_and_person_decider"] is True
    assert result["synthetic_write_deny_preserved"] is True
    assert result["synthetic_write_allow_preserved"] is True
    assert result["synthetic_hook_exception_denied"] is True
    assert result["unsafe_missing_catch_warning_exit_zero_rejected"] is True
    assert result["unsafe_permission_deny_override_mock_rejected"] is True
    assert result["sandbox_unshares_network"] is True
    assert result["real_model_requests"] == 0
    assert matrix["native_synthetic_permission_tests_passed"] == 6
    assert matrix["toolcheck_native_test_evidence_sha256"] == digest(NATIVE)


def test_permission_host_and_stable_release_remain_explicitly_blocked():
    matrix = json.loads(PRIMARY.read_text())
    native = json.loads(NATIVE.read_text())
    for field in (
        "all_31_target_api_semantics_verified",
        "real_host_permission_callback_verified",
        "full_native_304_host_acceptance",
        "p4_chat_mode_acceptance",
        "stable_release_authorized",
    ):
        assert matrix[field] is False
    assert matrix["approved_new_304_claims"] == 0
    for field in (
        "actual_host_readonly_classification_verified",
        "actual_host_person_dialog_approved",
        "actual_managed_rule_precedence_verified",
        "actual_cross_plugin_skip_transcript_verified",
        "actual_failed_reload_lifecycle_verified",
        "real_user_tools_or_credentials_exposed",
        "all_31_claims_approved_for_304",
        "stable_release_authorized",
    ):
        assert native[field] is False
    sources = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.304", "cli") == []
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(ROOT, api_version="2.1.304", surface="cli", source_revision="p1")


def test_fail_closed_mock_gate_rejects_warnings_and_fabricated_six_pass(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    native = _script("audit_cli304_toolcheck_p1_sandbox.py")
    normal = "gating hook with .catch: tool.check\nValidation passed"
    native.assert_strict_with_catch(0, normal)
    with pytest.raises(native.P1Native304Blocked):
        native.assert_strict_with_catch(
            0, "gating hook without .catch: tool.check\nValidation passed"
        )
    with pytest.raises(native.P1Native304Blocked):
        native.assert_strict_with_catch(1, normal)
    with pytest.raises(native.P1Native304Blocked):
        native.assert_strict_with_catch(0, "Warning: unreviewed native hook" + chr(10) + normal)
    forged = "6 pass\n0 fail\nRan 6 tests across 1 file."
    with pytest.raises(native.P1Native304Blocked):
        native.assert_mock_six(0, forged)
    with pytest.raises(native.P1Native304Blocked):
        native.assert_mock_six(1, forged)


def test_source_audit_refuses_absent_private_official_documents(tmp_path):
    source = _script("audit_cli304_fresh_firstparty_claim_matrix.py")
    with pytest.raises(source.Current304SourceBlocked):
        source.audit(ROOT, tmp_path)


def test_public_reports_expose_no_raw_first_party_docs_or_user_secrets():
    for file in (PRIMARY, NATIVE):
        text = file.read_text()
        for forbidden in (
            "/Users/",
            "/home/",
            "Authorization:",
            "Cookie:",
            "Plugin_",
            "TASK_ID:",
            "chatgpt.com/c/",
            "raw_reply",
            "sandbox:/mnt/data",
            "declare module 'claude-code'",
        ):
            assert forbidden not in text
    assert not list((ROOT / "evals/fixtures/cli304-toolcheck-p1-boundaries").rglob("*.d.ts"))
