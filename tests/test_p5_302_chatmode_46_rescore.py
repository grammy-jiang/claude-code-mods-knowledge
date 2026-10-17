"""Immutable original 46-turn Chat Mode evidence remains non-production."""

from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "docs/reports"
DOC = R / "2026-10-18-claude302-chatmode-46-rescored.json"


def test_full_original_chatmode_report_recounts_entrypoint_without_weakening_citations() -> None:
    raw = DOC.read_text()
    record = json.loads(raw)
    assert record["target_cli"] == "2.1.302"
    assert record["original_unique_chat_sends"] == 46
    assert record["original_final_answers_read"] == 46
    assert record["positive_cases"] == 30
    assert record["positive_actual_skill_entrypoint_and_references_from_recorded_uri"] == 30
    assert record["positive_exact_approved_claim_source_pass"] == 29
    assert record["positive_exact_approved_claim_source_fail"] == 1
    assert record["positive_source_failure_cited_claim_missing_exact_url"] == "K-0048"
    assert set(record["positive_original_score_false_negatives"]) == {"POS-U-01", "MODS-STATE-UI"}
    assert record["negative_nonactivation_pass"] == 8
    assert record["boundary_automatic_plugin_entrypoint_and_references"] == 0
    assert record["boundary_activation_fail"] == 8
    assert record["all_46_release_gate_pass"] is False
    assert record["candidate_release_decision"] == "HOLD"
    assert record["exact_original_account_plugin_id_rechecked_after_rescoring"] is False
    assert record["original_private_conversations_resubmitted"] is False
    assert record["original_reply_or_user_identity_exported"] is False
    for banned in ("/Users/", "/home/", "conversation_id", "private_replies", "6ad3714b"):
        assert banned not in raw
