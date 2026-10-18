"""Frozen real Chat Mode beta011 results cannot be conflated with full QA."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-cli302-beta011-history-four-observations.json"


def test_four_original_beta011_observations_keep_version_risk_and_quality_separate() -> None:
    result = json.loads(REPORT.read_text())
    assert result["candidate"] == "0.4.11-beta.1"
    assert result["source_revision"] == "a37d96e7e018e14e27562c366ead0d3e36c2c377"
    assert result["target_cli"] == "2.1.302"
    assert result["original_sender_receipts_confirmed"] == 4
    assert result["original_completed_model_replies_observed"] == 4
    assert result["unreviewed_version_history_linter_original_live_baseline_flags"] == 1
    assert result["unreviewed_version_history_linter_beta011_repeat_flags"] == 0
    assert result["real_plugin_reads_in_two_old_version_repeats"] == 2
    assert result["positive_actual_plugin_read_and_claim_source_pass"] == 1
    assert result["negative_correct_nonactivation"] == 1
    assert result["original_reply_sha256_independently_recomputed_by_public_report"] is False
    assert result["original_tool_event_bodies_independently_refetched"] is False
    rows = result["cases"]
    assert [(x["case_id"], x["condition"]) for x in rows] == [
        ("BOUND-VERSION-OLD", "natural_repeat_a"),
        ("BOUND-VERSION-OLD", "natural_repeat_b"),
        ("POS-E-01", "natural_positive_control"),
        ("NEG-HVAC", "natural_unrelated_negative"),
    ]
    assert all(x["source_structural_verdict"] == "pass" for x in rows[:3])
    assert all(not x["unverified_version_chronology_linter_flag"] for x in rows)
    assert all(x["actual_plugin_loaded"] for x in rows[:3])
    assert rows[3]["actual_plugin_loaded"] is False
    assert rows[3]["actual_matching_plugin_skill_and_reference_reads"] == 0
    assert all(not x["manual_review_complete_for_general_runtime_semantics"] for x in rows)
    assert result["all_model_code_semantics_approved"] is False
    assert result["complete_46_case_plugin_qualification"] is False
    assert result["stable_release_authorized"] is False


def test_public_beta011_report_excludes_private_chat_material() -> None:
    data = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "Plugin_",
        "Cookie:",
        "Authorization:",
        "chatgpt.com/c/",
        "TASK_ID:",
        "raw_reply",
        "raw_prompt",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in data
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", data) is None
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", x["original_answer_sha256"])
        for x in json.loads(data)["cases"]
    )
