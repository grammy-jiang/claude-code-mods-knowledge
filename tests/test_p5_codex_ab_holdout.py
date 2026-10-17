"""Heldout Codex Skill evidence scenarios are frozen and scored separately."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_p5_codex_ab_holdout_batch as cohort  # noqa: E402
import run_p5_codex_ab_holdout_case as single  # noqa: E402
import run_p5_codex_ab_holdout_native as native  # noqa: E402
import score_p5_codex_ab_holdout as scoring  # noqa: E402

from mods_knowledge.claims import load_claims  # noqa: E402
from mods_knowledge.registry import load_registry  # noqa: E402
from mods_knowledge.task_evidence import select_task_evidence  # noqa: E402


def test_four_fresh_holdout_cases_frozen_before_original_cohort_completion() -> None:
    p = json.loads(single.MANIFEST.read_text())
    original = json.loads((ROOT / "evals/p5_codex_evidence_ab_20261017.json").read_text())
    cases = {x["id"]: x for x in json.loads((ROOT / p["source_file"]).read_text())["cases"]}
    assert len(cases) == 4
    assert set(cases) == set(p["case_ids"])
    assert not set(cases) & set(original["case_ids"])
    assert hashlib.sha256((ROOT / p["source_file"]).read_bytes()).hexdigest() == p["source_sha256"]
    assert p["repetitions"] == 3 and p["native_turns_planned"] == 36
    assert p["frozen_skill_sha256"] == original["frozen_skill_sha256"]
    assert p["not_used_to_design_task_selector"] is True
    assert p["separate_from_original_p4_cohort"] is True
    assert cohort.RUNNER == ROOT / "scripts/run_p5_codex_ab_holdout_case.py"
    assert native.SKILL_SHA == single.TARGET_SKILL_SHA


def test_holder_exactly_36_original_trials_and_no_cross_campaign_replays() -> None:
    cells = cohort.expected_cells()
    assert len(cells) == len(set(cells)) == 36
    assert all(x[2].startswith("HOLD-") for x in cells)
    assert {x[0] for x in cells} == set(single.CONDITIONS)
    assert {x[1] for x in cells} == {1, 2, 3}


def test_new_questions_route_without_model_setting_changes() -> None:
    p = json.loads(single.MANIFEST.read_text())
    c = json.loads((ROOT / p["source_file"]).read_text())["cases"]
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    for x in c:
        result = select_task_evidence(x["prompt"], claims)
        if x["category"] == "positive":
            assert result["ready"] and result["intent"] == "mods"
            assert set(x["expected_claim_ids"]) <= {r["claim_id"] for r in result["claims"]}
        elif x["category"] == "negative":
            assert not result["ready"] and result["intent"] == "unrelated"
        elif x["category"] == "boundary":
            assert not result["ready"] and result["intent"] == "blocked"


def test_holdout_scorer_refuses_missing_raw_model_turns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(scoring, "PRIVATE", tmp_path)
    data = scoring.score()
    assert data["verified_original_native_turns"] == 0
    assert data["unobserved_original_native_turns"] == 36
    assert data["no_historical_holdout_baseline"] is True
    assert all(r["status"] == "not_observed" for r in data["rows"])
    with pytest.raises(scoring.CodexABEvidentiaryError):
        scoring.score(complete=True)


def test_holdout_runner_accepts_only_verified_original_native_case_data() -> None:
    text = (ROOT / "scripts/run_p5_codex_ab_holdout_native.py").read_text()
    assert "case_override" in text
    assert 'case_override.get("category") not in' in text
    assert '"HOME": str(private_agent_home)' in text
    assert "developerInstructions" in text
    assert "session" not in single.MANIFEST.read_text().lower()
