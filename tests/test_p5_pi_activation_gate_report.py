"""Public P0/P1 results must preserve actual loader failure and withholding."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reports/2026-10-17-p5-pi-skill-gate-qa.json"
REPORT = ROOT / "docs/reports/2026-10-17-p5-pi-discovery-and-gate.md"


def test_gate_evidence_does_not_inflate_qualifications() -> None:
    info = json.loads(EVIDENCE.read_text())
    observations = info["mode_comparisons"]
    assert len(observations) == 7
    assert info["preflight_boundary"]["model_calls"] == 0
    assert info["preflight_boundary"]["action"] == "abstain_before_model"
    assert info["historical_replay"]["identical_read_calls"] == 18
    assert info["historical_replay"]["native_tool_errors"] == 0
    assert info["historical_replay"]["total_tool_calls"] == 24
    assert all(x["raw_output_exposed"] is False for x in observations)
    assert all(x["semantic_correctness_verified"] is False for x in observations)
    assert all(re.fullmatch(r"[a-f0-9]{64}", x["events_sha256"]) for x in observations)
    positive = [x for x in observations if x["case_id"] != "NEG-TYPESCRIPT"]
    assert len(positive) == 6
    assert Counter(x["skill_read_observed"] for x in positive) == {True: 5, False: 1}
    assert all(x["source_verdict"] == "pass" for x in positive if x["mode"] == "explicit")
    negative = next(x for x in observations if x["case_id"] == "NEG-TYPESCRIPT")
    assert negative["repeat_abort"] == "repeated_identical_tool_call"
    assert "tool_loop_or_budget" in negative["reason_codes"]
    assert all(x["gate_action"] == "block_candidate" for x in observations)


def test_report_has_no_private_directories_or_false_production_claims() -> None:
    material = REPORT.read_text() + EVIDENCE.read_text()
    assert "NOT installed" in material
    assert "2.1.296" in material
    assert "2.1.310" in material
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-", material)
    assert not re.search(r"https?://[^\s]+/oauth/", material)
