"""V3 native A/B/C reports require actual original raw model evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_p5_codex_evidence_ab_report as builder  # noqa: E402


def test_final_report_fails_closed_without_144_original_native_turns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def incomplete(*, complete: bool = False) -> dict:
        assert complete is True
        raise ValueError("no original native evidence")

    monkeypatch.setattr(builder, "original_score", incomplete)
    with pytest.raises(ValueError):
        builder.report()


def test_heldout_not_conflated_with_original_frozen_source() -> None:
    original = json.loads((ROOT / "evals/p5_codex_evidence_ab_20261017.json").read_text())
    holdout = json.loads((ROOT / "evals/p5_codex_ab_holdout_20261017.json").read_text())
    assert set(original["case_ids"]).isdisjoint(holdout["case_ids"])
    assert original["native_turns_planned"] == 108
    assert holdout["native_turns_planned"] == 36
    assert original["frozen_skill_sha256"] == holdout["frozen_skill_sha256"]
    assert original["source_sha256"] != holdout["source_sha256"]
    assert original["model"] == holdout["model"] == "gpt-6.1-sol"
    assert original["web_search"] == holdout["web_search"] == "disabled"


def test_new_holdout_paired_scores_are_not_mixed_with_original() -> None:
    rows = [
        {
            "condition": condition,
            "case_id": cid,
            "trial": trial,
            "category": "positive",
            "raw_exact_source_pass": condition in ("B_context", "C_context_gate"),
        }
        for condition in ("A_v3", "B_context", "C_context_gate")
        for cid in ("HOLD-E-01", "HOLD-T-01")
        for trial in (1, 2, 3)
    ]
    pairs = builder._paired_improvement(rows)
    ab = pairs["A_v3_vs_B_context"]
    assert ab["paired_cases_and_trial_slots"] == 6
    assert ab["improved"] == 6 and ab["regressed"] == 0
    bc = pairs["B_context_vs_C_context_gate"]
    assert bc["improved"] == bc["regressed"] == 0
    assert bc["both_pass"] == 6


def test_published_native_scores_are_anonymized_and_gate_counts_are_separate() -> None:
    """Only typed metadata/hashes enter Git, never original Codex text."""
    import re

    base = ROOT / "docs/reports/2026-10-17-p5-codex-skill-evidence-context-ab"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    assert json_path.is_file() and md_path.is_file()
    content = json_path.read_text()
    markdown = md_path.read_text()
    for text in (content, markdown):
        assert "/Users/" not in text
        assert "/home/" not in text
        assert "Models.noindex" not in text
        assert "native-wire.jsonl" not in text
        assert "native-stderr.log" not in text
        assert ".codex/" not in text
        assert "threadId" not in text
        assert not re.search(r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    study = json.loads(content)
    assert study["total_real_original_native_model_turns"] == 144
    assert study["production_codex_gate_deployed"] is False
    assert study["native_2_1_296_mod_semantics_verified"] is False
    assert study["production_skill_replaced"] is False
    assert study["model_weights_or_settings_changed"] is False
    assert study["developer_context_delivery_is_not_proven_model_consumption"] is True
    assert study["P3_is_a_postflight_filter_not_raw_model_intelligence"] is True
    assert study["P3_gate_by_category_frozen"]["positive"]["allowed_structural_only"] == 6
    assert study["P3_gate_by_category_frozen"]["boundary"]["allowed_structural_only"] == 0
    assert study["P3_gate_by_category_holdout"]["positive"]["allowed_structural_only"] == 0
    assert study["P3_gate_by_category_holdout"]["boundary"]["allowed_structural_only"] == 0
    assert "Boundary cases flagged for manual review" in markdown
    assert "holdout" in markdown.lower()
    safe_rows = {
        "condition",
        "case_id",
        "trial",
        "category",
        "status",
        "native_completed",
        "actual_v3_skill_read",
        "raw_exact_source_pass",
        "raw_exact_source_and_skill_pass",
        "negative_no_mods_skill_completed",
        "boundary_rule_detected_risk",
        "native_source_verdict",
        "native_scorer_verdict",
        "SSOT_task_context_submitted",
        "native_developer_context_sha256",
        "SSOT_evidence_consumed_confirmed",
        "P3_structural_candidate_allowed",
        "P3_gate_reasons",
        "native_duration_seconds",
        "original_event_sha256",
        "original_answer_sha256",
        "model_weights_or_effort_changed",
        "raw_model_text_exported",
        "semantic_mod_runtime_verified",
    }
    for cohort, n in (("frozen_original_12x3", 108), ("new_independent_holdout_4x3", 36)):
        data = study[cohort]
        assert len(data["rows"]) == n
        assert all(x["status"] == "observed" for x in data["rows"])
        for item in data["rows"]:
            assert set(item) <= safe_rows
            assert item["raw_model_text_exported"] is False
            assert item["SSOT_evidence_consumed_confirmed"] is False
            assert item["semantic_mod_runtime_verified"] is False
            assert re.fullmatch(r"[0-9a-f]{64}", item["original_event_sha256"])
            assert re.fullmatch(r"[0-9a-f]{64}", item["original_answer_sha256"])
