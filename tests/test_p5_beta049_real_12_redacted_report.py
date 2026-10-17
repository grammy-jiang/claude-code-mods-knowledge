"""Actual beta049 12-case Chat Mode failure remains a release blocker."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-claude302-chatmode-beta049-targeted12-original.json"


def test_full_original_twelve_case_beta049_auto_routing_failure() -> None:
    obj = json.loads(REPORT.read_text())
    assert obj["plugin_candidate"] == "0.4.9-beta.1"
    assert obj["source_revision"] == "e00f395509030382398df41ae14ef389490bea51"
    assert obj["target_cli"] == "2.1.302"
    assert obj["new_distinct_sends_verified"] == 12
    assert obj["canonical_final_replies_verified"] == 12
    assert obj["family_counts"] == {"positive": 2, "negative": 2, "boundary": 8}
    assert obj["structural_results"] == {
        "structural_fail": 2,
        "negative_nonactivation_pass": 2,
        "boundary_activation_fail": 8,
    }
    assert obj["actual_skill_activation_by_category"] == {
        "positive": 0,
        "negative": 0,
        "boundary": 0,
    }
    assert obj["structural_successes_by_category"] == {
        "positive": 0,
        "negative": 2,
        "boundary": 0,
    }
    assert obj["full_46_case_plugin_qualification"] is False
    assert obj["stable_release_approved"] is False
    assert obj["model_generated_code_semantics_verified"] is False
    assert obj["original_tool_calls_independently_refetched"] is False
    rows = obj["per_case_metadata"]
    assert len(rows) == 12
    assert len({r["case_id"] for r in rows}) == 12
    assert dict(Counter(r["category"] for r in rows)) == obj["family_counts"]
    assert all(r["automatic_skill_activation_from_collector"] is False for r in rows)


def test_original_twelve_case_report_is_redacted() -> None:
    raw = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "Plugin_",
        "Authorization:",
        "Cookie:",
        "chatgpt.com/c/",
        "TASK_ID:",
        "raw_reply",
        "raw_prompt",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in raw
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", raw) is None
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", r["original_answer_sha256"])
        for r in json.loads(raw)["per_case_metadata"]
    )
