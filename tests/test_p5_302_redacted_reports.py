"""Regression contracts for privacy-safe current-version QA publications."""

import json
from pathlib import Path

REPORTS = Path(__file__).resolve().parents[1] / "docs/reports"


def test_native_campaign_original_count_and_cohort_separation():
    r = json.loads((REPORTS / "2026-10-17-claude302-native-abc-redacted.json").read_text())
    assert r["target_cli"] == "2.1.302"
    assert r["planned_original_native_turns"] == r["verified_original_native_turns"] == 144
    assert r["unique_native_wire_sha256"] == r["unique_native_answer_sha256"] == 144
    assert r["per_cell_sha256_and_single_completed_turn_verified"]
    assert not r["raw_prompts_or_transcripts_exported"]
    assert not r["native_mod_semantics_verified"]
    groups = r["group_results"]
    assert len(groups) == 18
    assert sum(x["observed"] for x in groups) == 144
    for arm in ("A_v3", "B_context", "C_context_gate"):
        subset = [x for x in groups if x["condition"] == arm]
        assert sum(x["positive_exact_source"] for x in subset) == 18
        assert sum(x["negative_no_skill"] for x in subset) == 15
    positives = [
        x for x in groups if x["condition"] == "C_context_gate" and x["category"] == "positive"
    ]
    assert sum(x["gate_candidate"] for x in positives) == 7


def test_chat_mode_originals_not_mistaken_for_full_live_qualification():
    r = json.loads((REPORTS / "2026-10-17-claude302-chatmode-four-redacted.json").read_text())
    assert r["installed_version"] == "0.4.7-beta.1"
    assert r["sent_chat_count"] == r["original_finished_chat_count"] == len(r["cases"]) == 4
    assert r["composer_hints_present"] == 0
    assert [x["canonical_read_count"] for x in r["cases"]] == [4, 0, 4, 4]
    assert all(not x["semantic_native_pass"] for x in r["cases"])
    assert r["full_46_case_live_suite"] == "not_executed_for_this_version"
    assert not r["private_transcripts_or_prompts_exported"]
    for case in r["cases"]:
        assert all(k not in case for k in ("conversation_id", "transcript", "answer", "raw_prompt"))
