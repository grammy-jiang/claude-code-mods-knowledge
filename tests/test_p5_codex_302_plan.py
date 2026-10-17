"""Current CLI version must use a new source and immutable native model ledger."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_p5_codex_302_abc as native302  # noqa: E402


def test_native_302_plans_are_distinct_and_complete() -> None:
    plan = json.loads((ROOT / "evals/p5_codex_302_abc_plan_20261017.json").read_text())
    source = ROOT / plan["source_file"]
    assert plan["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert plan["target_cli"] == "2.1.302"
    assert plan["model"] == "gpt-6.1-sol"
    assert plan["thinking"] == "medium" and plan["web_search"] == "disabled"
    assert len(plan["frozen_case_ids"]) == 12
    assert len(plan["heldout_case_ids"]) == 4
    assert set(plan["frozen_case_ids"]).isdisjoint(plan["heldout_case_ids"])
    assert len(native302.cells(plan)) == len(set(native302.cells(plan))) == 144
    assert plan["source_file"] != "evals/p4_cases.json"
    assert (
        plan["skill_sha256"] == "a808ab573ecc0ba7c38b45230008e71b1435fc93e44f8a8072b55823d96adc9a"
    )


def test_latest_case_positives_are_version_correct_and_no_old_claim_ids() -> None:
    cases = json.loads((ROOT / "evals/p5_codex_302_cases_20261017.json").read_text())
    assert len(cases["cases"]) == 16
    for case in cases["cases"]:
        assert "2.1.296" not in case["prompt"]
        for claim_id in case["expected_claim_ids"]:
            assert 39 <= int(claim_id.split("-")[1]) <= 69
        if case["category"] == "negative":
            assert case["expected_activation"] is False
        if case["category"] == "boundary":
            assert case["expected_claim_ids"] == []


def test_partial_private_native_cell_cannot_be_silently_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native302, "PRIVATE", tmp_path)
    row = ("A_v3", 1, "POS-E-01")
    root = native302.folder(row)
    root.mkdir(parents=True)
    plan = json.loads(native302.PLAN.read_text())
    with pytest.raises(ValueError, match="Partial"):
        native302.observed(row, plan)


def test_native_302_plan_never_overwrites_original_historical_plan() -> None:
    old = json.loads((ROOT / "evals/p5_codex_evidence_ab_20261017.json").read_text())
    new = json.loads(native302.PLAN.read_text())
    assert old["frozen_skill_sha256"] != new["skill_sha256"]
    assert old["source_sha256"] != new["source_sha256"]
    assert old["model"] == new["model"] == "gpt-6.1-sol"
    assert old["web_search"] == new["web_search"] == "disabled"
    assert old["native_turns_planned"] == 108 and new["turns_planned"] == 144
    assert new["source_revision"] == "e1f080ea46102cb257ad57a64f2fecf9fe1cf037"
