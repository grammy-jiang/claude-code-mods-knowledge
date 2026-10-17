"""Independent native candidate report cannot silently claim semantic acceptance."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "docs/reports/2026-10-18-claude302-beta048-native-abc-redacted.json"


def test_latest_candidate_real_native_144_is_hash_bound_and_not_a_release() -> None:
    raw = FILE.read_text()
    report = json.loads(raw)
    assert report["target_cli"] == "2.1.302"
    assert report["candidate_plugin_version"] == "0.4.8-beta.1"
    assert report["model"] == "gpt-6.1-sol"
    assert report["effort"] == "medium"
    assert report["web_search"] == "disabled"
    assert report["verified_original_native_turns"] == 144
    assert report["unique_native_wire_sha256"] == 144
    assert report["unique_native_answer_sha256"] == 144
    assert report["per_cell_sha256_and_single_completed_turn_verified"] is True
    assert report["old_302_native_originals_untouched"] is True
    assert report["native_mod_semantics_verified"] is False
    assert report["native_semantic_execution_of_model_origin_code_not_claimed"] is True
    assert report["production_release_eligible_from_this_evidence_alone"] is False
    assert len(report["private_cell_ledger_sha256"]) == 64
    assert report["private_cell_ledger_sha256"] != report["previous_302_native_144_ledger_sha256"]
    for kind in ("A_v3", "B_context", "C_context_gate"):
        arm = report["aggregate_per_condition"][kind]
        assert arm["observed"] == arm["native_completed"] == 48
        assert arm["positive_exact_source"] == 18
        assert arm["negative_no_skill"] == 15
    # The C gate also marks unrelated negative tasks as safe non-Mod candidates.
    # Exactly six of the eighteen positive cases qualified for further review.
    positive = [
        item
        for item in report["group_results"]
        if item["condition"] == "C_context_gate" and item["category"] == "positive"
    ]
    boundary = [
        item
        for item in report["group_results"]
        if item["condition"] == "C_context_gate" and item["category"] == "boundary"
    ]
    assert sum(item["gate_candidate"] for item in positive) == 6
    assert sum(item["gate_needs_review"] for item in boundary) == 15
    for private in ("/Users/", "/home/", "Models.noindex", "conversation_id", "native-wire.jsonl"):
        assert private not in raw
