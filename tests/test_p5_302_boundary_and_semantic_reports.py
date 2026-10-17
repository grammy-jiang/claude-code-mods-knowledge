"""Ensure redacted target-native evidence does not overclaim production safety."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs/reports"


def test_native_boundary_report_has_all_45_original_case_metadata() -> None:
    p = REPORTS / "2026-10-17-claude302-boundary-audit.json"
    raw = p.read_text()
    report = json.loads(raw)
    assert report["target_cli"] == "2.1.302"
    assert report["original_native_boundary_answers_verified"] == 45
    assert report["boundary_answers_with_refusal_language"] == 45
    assert report["boundary_answers_with_runnable_code"] == 0
    assert report["P3_boundary_holds"] == 15
    assert report["automated_refusal_signal_is_semantic_approval"] is False
    assert report["raw_model_or_account_content_exported"] is False
    assert len(report["case_rows"]) == 45
    for entry in report["case_rows"]:
        assert set(entry) == {
            "case_id",
            "arm",
            "trial",
            "original_answer_verified",
            "contains_refusal_or_non_guarantee_language",
            "contains_runnable_code_fence",
            "P3_refused_boundary_delivery",
        }
        assert entry["contains_runnable_code_fence"] is False
    for forbidden in ("/Users/", "/home/", "Models.noindex", "conversation_id", "raw_answer"):
        assert forbidden not in raw


def test_partial_native_semantic_certification_is_never_full_release_approval() -> None:
    p = REPORTS / "2026-10-17-claude302-model-observer-semantic-review.json"
    raw = p.read_text()
    report = json.loads(raw)
    assert report["original_positive_answers"] == 18
    assert report["manually_reviewed_generated_javascript_blocks"] == 8
    assert report["whitelisted_transparent_passthrough_blocks"] == 3
    assert report["whitelisted_fail_isolated_logging_blocks"] == 5
    assert report["unreviewed_javascript_blocks_detected"] == 0
    assert report["exact_original_model_snippet_native_strict_validation"] is True
    assert report["exact_original_model_snippet_native_mock_tests"]["total_pass"] == 3
    assert report["exact_original_model_snippet_independent_node_tests"]["total_pass"] == 6
    assert report["native_mod_semantics_verified_only_for_single_reviewed_snippet"] is True
    assert report["other_model_snippets_separately_native_executed"] is False
    assert report["all_generated_mod_code_production_approved"] is False
    assert report["full_generated_answer_semantic_acceptance"] is False
    assert report["raw_private_model_content_exported"] is False
    assert "SKILL.md" not in raw
    for forbidden in ("/Users/", "/home/", "Models.noindex", "conversation_id"):
        assert forbidden not in raw
