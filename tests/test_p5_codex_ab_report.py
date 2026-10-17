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
