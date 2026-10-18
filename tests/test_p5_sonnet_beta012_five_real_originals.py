"""Sonnet native P5 original hashed results must not become full host acceptance."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-claude302-sonnet-beta012-five-native-observations.json"


def test_five_original_native_sonnet_completed_scoped_verdicts_only() -> None:
    data = json.loads(REPORT.read_text())
    assert data["schema_version"] == 1
    assert data["source_revision"] == "6f92571f0a0ab5b637b1b36607d5ff2ddd4860a8"
    assert data["source_common_skill_sha256"] == (
        "c072ebe4a3e50c041ca26ac2891c25f99b9494a51ae9daf0027f6fbeaf3de4b9"
    )
    assert data["reviewed_target_cli"] == "2.1.302"
    assert data["model"] == "claude-sonnet-5-5"
    assert data["requested_effort"] == "medium"
    assert data["effort_independently_confirmed_by_server"] is False
    assert data["native_original_completed_turns"] == 5
    assert data["positive_source_structural_passes"] == 2
    assert data["positive_source_structural_total"] == 2
    assert data["unrelated_nonactivation_observed"] == 2
    assert data["unrelated_negative_total"] == 2
    assert data["unsupported_future_version_refusal_text_observed"] == 1
    assert data["unsupported_future_version_full_skill_reference_read"] == 0
    assert data["local_typescript_fixture_failure_still_open"] is True
    assert data["stable_release_authorized"] is False
    assert data["native_model_generated_code_runtime_verified"] is False
    assert data["all_native_host_acceptance_passed"] is False
    assert data["estimated_cost_usd_total"] == 3.874
    cases = data["cases"]
    assert [c["case_id"] for c in cases] == [
        "POS-Q-01",
        "POS-E-01",
        "NEG-TYPESCRIPT",
        "BOUND-VERSION-NEW",
        "NEG-TYPESCRIPT-FIXTURE",
    ]
    assert len({c["original_prompt_sha256"] for c in cases}) == 5
    assert len({c["original_wire_sha256"] for c in cases}) == 5
    assert len({c["original_final_answer_sha256"] for c in cases}) == 5
    assert all(c["native_model"] == "claude-sonnet-5-5" for c in cases)
    assert all(c["native_model_complete"] is True for c in cases)
    assert all(c["model_generated_code_executed"] is False for c in cases)
    assert all(c["whole_answer_runtime_code_semantics_certified"] is False for c in cases)
    for c in cases[:2]:
        assert c["actual_claude_mods_skill_calls"] == 1
        assert c["native_tool_use_counts"]["Read"] == 2
        assert c["actual_read_tool_errors"] == 0
        assert c["source_structural_verdict"] == "pass"
        assert c["scoped_plugin_source_or_negative_routing_pass"] is True
        assert c["missing_exact_official_source_claim_ids"] == []
        assert c["missing_required_claim_ids"] == []
        assert c["unsupported_claim_ids"] == []
        assert c["contains_generated_code_or_api_snippet"] is True
    for c in (cases[2], cases[4]):
        assert c["actual_claude_mods_skill_calls"] == 0
        assert c["scoped_plugin_source_or_negative_routing_pass"] is True
        assert c["negative_question_fixture_workflow_complete"] is False
    boundary = cases[3]
    assert boundary["actual_claude_mods_skill_calls"] == 1
    assert boundary["reviewed_reference_filenames"] == []
    assert boundary["contains_generated_code_or_api_snippet"] is False
    assert boundary["scoped_plugin_source_or_negative_routing_pass"] is False
    assert boundary["manually_reviewed_refusal_of_unsupported_api"] is True
    assert boundary["strict_skill_and_reference_loading_pass"] is False


def test_public_original_native_report_has_no_unredacted_user_transcripts() -> None:
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
        "raw_prompt",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in text
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text) is None
    report = json.loads(text)
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", c["original_wire_sha256"])
        and re.fullmatch(r"[a-f0-9]{64}", c["original_final_answer_sha256"])
        for c in report["cases"]
    )
