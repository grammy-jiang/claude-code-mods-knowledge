"""Two-axis P4 diagnostics never quietly rewrite the original 8/8 Skill gate."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.boundary_diagnostics import BoundaryDiagnosticError, diagnose_boundary_cohort

ROOT = Path(__file__).resolve().parents[1]


def frozen_material() -> tuple[dict, dict, dict]:
    original = json.loads(
        (
            ROOT / "docs/reports/2026-10-18-cli302-beta010-all-eight-boundary-natural.json"
        ).read_text()
    )
    classes = json.loads((ROOT / "evals/p4_boundary_two_axis_diagnostic_302.json").read_text())
    old = json.loads((ROOT / "evals/p4_boundary_semantic_rubric_cli_2_1_302.json").read_text())
    return original, classes, old


def test_real_six_specialist_and_two_safe_refusal_results_are_separate() -> None:
    original, classes, strict = frozen_material()
    outcome = diagnose_boundary_cohort(original, classes, strict)
    assert outcome["diagnostic_only"] is True
    assert outcome["legacy_strict_unchanged"] == {
        "original_total": 8,
        "actual_plugin_skill_reads": 6,
        "strict_gate_pass": False,
    }
    assert outcome["independent_specialist_knowledge_routing"] == {
        "cases": 6,
        "actual_skill_reads": 6,
        "full_semantics_verified": False,
    }
    assert outcome["independent_safe_refusal_text"] == {
        "cases": 2,
        "sha_bound_manual_safe_refusal_observations": 2,
        "actual_plugin_skill_reads": 0,
        "full_semantics_verified": False,
    }
    assert outcome["remaining_unverified_historical_version_timeline"] is True
    assert outcome["full_46_case_qualification"] is False
    assert outcome["stable_release_authorized"] is False
    rows = outcome["per_case_diagnostic"]
    assert len(rows) == 8
    assert len({row["case_id"] for row in rows}) == 8
    assert all(not row["full_semantic_approval"] for row in rows)
    assert {r["case_id"] for r in rows if r["manual_safe_refusal_text_observed"]} == {
        "BOUND-INJECTION",
        "BOUND-PLUGIN-PRIV",
    }
    redacted = json.dumps(outcome)
    assert "/home/" not in redacted
    assert "/Users/" not in redacted
    assert "chatgpt.com/c/" not in redacted
    assert "Plugin_" not in redacted
    assert all(re.fullmatch(r"[a-f0-9]{64}", r["original_answer_sha256"]) for r in rows)


@pytest.mark.parametrize(
    "mutation",
    (
        "alter_reply_digest",
        "invent_plugin_use",
        "drop_case",
        "rename_case",
        "soften_strict_rubric",
        "change_safe_class",
        "alter_review",
    ),
)
def test_never_promote_tampered_or_unreviewed_original_evidence(mutation: str) -> None:
    original, classes, strict = frozen_material()
    original, classes, strict = (
        copy.deepcopy(original),
        copy.deepcopy(classes),
        copy.deepcopy(strict),
    )
    if mutation == "alter_reply_digest":
        original["case_summaries"][-3]["sha256_original_answer"] = "a" * 64
    elif mutation == "invent_plugin_use":
        original["case_summaries"][2]["real_plugin_entrypoint_and_reference_read"] = True
    elif mutation == "drop_case":
        original["case_summaries"].pop()
    elif mutation == "rename_case":
        classes["cases"][2]["case_id"] = "BOUND-VERSION-OLD"
    elif mutation == "soften_strict_rubric":
        strict["controls"]["required_actual_plugin_skill_read_for_in_scope_case"] = False
    elif mutation == "change_safe_class":
        classes["cases"][3]["mode"] = "safe_refusal_without_plugin_required"
    elif mutation == "alter_review":
        classes["frozen_manual_textual_safety_observations"][0]["textual_outcome"] = "passed"
    with pytest.raises(BoundaryDiagnosticError):
        diagnose_boundary_cohort(original, classes, strict)


def test_strict_boundary_contract_is_immutable() -> None:
    _, diagnostic, frozen = frozen_material()
    assert frozen["controls"]["required_actual_plugin_skill_read_for_in_scope_case"] is True
    assert frozen["controls"]["requires_manual_semantic_verdict"] is True
    assert diagnostic["purpose"] == "diagnostic_only_no_release_gate_change"
    assert diagnostic["stable_release_remains_hold"] is True
    assert diagnostic["historical_strict_routing_gate_untouched"] is True
