"""Real beta048 46 original Chat Mode cases are evidence of failure, not green."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-claude302-chatmode-beta048-full46-original.json"


def test_genuine_46_case_original_routing_failure_is_not_relabeled() -> None:
    study = json.loads(REPORT.read_text())
    assert study["plugin_version"] == "0.4.8-beta.1"
    assert study["target_cli"] == "2.1.302"
    assert study["source_revision"] == "12a5bf492faa8778a4bc411e0150cbbe8d780c66"
    assert study["original_unique_sends_with_receipts"] == 46
    assert study["original_completed_final_replies_sha256_verified"] == 46
    assert study["categories"] == {"positive": 30, "negative": 8, "boundary": 8}
    assert study["structural_verdicts"] == {
        "structural_fail": 30,
        "negative_nonactivation_pass": 8,
        "boundary_activation_fail": 8,
    }
    assert study["actual_plugin_activation_counts_from_original_collector"] == {}
    assert study["per_category_structural_success_counts"] == {"negative": 8}
    assert study["stable_release_authorized"] is False
    assert study["all_original_responses_semantically_approved"] is False
    assert study["tool_metadata_independently_refetched"] is False
    assert study["full_report_verified_without_new_http_requests"] is True
    rows = study["per_case_redacted_metadata"]
    assert len(rows) == 46
    assert len({r["case_id"] for r in rows}) == 46
    assert dict(Counter(r["category"] for r in rows)) == study["categories"]
    assert all(r["plugin_activated_in_original_collector"] is False for r in rows)
    assert all(re.fullmatch(r"[0-9a-f]{64}", r["original_visible_reply_sha256"]) for r in rows)


def test_published_chat_metadata_contains_no_accounts_secrets_or_original_text() -> None:
    source = REPORT.read_text()
    for forbidden in (
        "chatgpt.com/c/",
        "/home/",
        "/Users/",
        "Authorization:",
        "Cookie:",
        "Plugin_",
        "TASK_ID:",
        "raw_reply",
        "raw_prompt",
        "OPENAI_API_KEY",
    ):
        assert forbidden not in source
    assert re.search(r"https?://chatgpt\.com/c/", source, re.I) is None
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", source) is None
