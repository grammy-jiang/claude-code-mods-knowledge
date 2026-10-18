"""Public diagnostic report is a deterministic transform of unmodified QA."""

from __future__ import annotations

import json
from pathlib import Path

from mods_knowledge.boundary_diagnostics import diagnose_boundary_cohort

ROOT = Path(__file__).resolve().parents[1]


def test_public_diagnostic_report_recomputes_exactly_without_private_rescoring() -> None:
    original = json.loads(
        (
            ROOT / "docs/reports/2026-10-18-cli302-beta010-all-eight-boundary-natural.json"
        ).read_text()
    )
    contract = json.loads((ROOT / "evals/p4_boundary_two_axis_diagnostic_302.json").read_text())
    strict = json.loads((ROOT / "evals/p4_boundary_semantic_rubric_cli_2_1_302.json").read_text())
    frozen = json.loads(
        (ROOT / "docs/reports/2026-10-18-cli302-boundary-two-axis-diagnostic.json").read_text()
    )
    assert diagnose_boundary_cohort(original, contract, strict) == frozen
    assert frozen["legacy_strict_unchanged"]["strict_gate_pass"] is False
    assert frozen["independent_specialist_knowledge_routing"]["actual_skill_reads"] == 6
    assert (
        frozen["independent_safe_refusal_text"]["sha_bound_manual_safe_refusal_observations"] == 2
    )
    assert frozen["full_46_case_qualification"] is False
    assert frozen["stable_release_authorized"] is False
    assert all(x["full_semantic_approval"] is False for x in frozen["per_case_diagnostic"])
