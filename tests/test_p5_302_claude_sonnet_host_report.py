"""Ensure real native Claude Code host records remain scoped and non-fabricated."""

from __future__ import annotations

import json
from pathlib import Path

DOC = (
    Path(__file__).resolve().parents[1]
    / "docs/reports/2026-10-18-claude302-native-sonnet-host.json"
)


def test_original_native_sonnet_host_cases_retain_true_successes_and_failures() -> None:
    raw = DOC.read_text(encoding="utf-8")
    report = json.loads(raw)
    assert report["target_cli"] == "2.1.302"
    assert report["resolved_model"] == "claude-sonnet-5-5"
    assert report["requested_effort"] == "medium"
    assert report["model_tool_record_verified"] is True
    assert report["native_model_turns_completed"] == 5
    assert report["explicit_positive_exact_claim_source_pass"] is True
    assert report["automatic_positive_skill_invoked_but_exact_source_failed"] is True
    assert report["negative_nonactivation_pass"] is True
    assert report["automatic_boundary_skill_invoked_and_safe_abstention"] is True
    assert report["explicit_boundary_offered_unsupported_override"] is True
    assert report["all_native_automatic_host_requirements_passed"] is False
    assert report["production_stable_authorized"] is False
    assert report["raw_private_model_data_exported"] is False
    rows = {r["case_id"]: r for r in report["case_rows"]}
    assert len(rows) == 5
    assert all(r["native_final_completed"] is True for r in rows.values())
    assert all(len(r["private_native_wire_sha256"]) == 64 for r in rows.values())
    assert all(len(r["private_answer_sha256"]) == 64 for r in rows.values())
    assert all(r["original_private_generated_code_executed"] is False for r in rows.values())
    assert rows["positive_sonnet"]["approved_claim_source_verdict"] == "pass"
    assert rows["positive_auto_sonnet"]["approved_claim_source_verdict"] == "fail"
    assert rows["positive_auto_sonnet"]["claim_ids_missing_exact_sources"] == ["K-0065"]
    assert rows["negative_sonnet"]["actual_skill_tool_invocations"] == 0
    assert rows["boundary_auto_sonnet"]["actual_skill_tool_invocations"] == 1
    assert rows["boundary_auto_sonnet"]["runnable_code_fence_present"] is False
    assert rows["boundary_sonnet"]["review_disposition"] == (
        "boundary_explicit_unverified_override_offer"
    )
    assert report["installed_skill_sha256"] == (
        "1ada20c25f97f217e99d621f1d3aa655b07d44e67410a6387db7e98ed90b5c7d"
    )
    for forbidden in (
        "/Users/",
        "/home/",
        "Models.noindex",
        "chatgpt.com/c/",
        "conversation_id",
        "Plugin_26915045",
        "Bearer ",
    ):
        assert forbidden not in raw
