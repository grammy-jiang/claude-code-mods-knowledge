"""Exact-target boundary QA rubric must preserve all frozen safety obligations."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli302_eight_case_semantic_rubric_preserves_historical_strict_controls() -> None:
    frozen = json.loads((ROOT / "evals/p4_boundary_semantic_rubric.json").read_text())
    current = json.loads((ROOT / "evals/p4_boundary_semantic_rubric_cli_2_1_302.json").read_text())
    assert frozen["target_cli_version"] == "2.1.296"
    assert current["target_cli_version"] == "2.1.302"
    assert current["controls"] == frozen["controls"]
    assert current["controls"]["required_actual_plugin_skill_read_for_in_scope_case"]
    assert current["controls"]["requires_manual_semantic_verdict"]
    assert len(current["cases"]) == 8
    assert len({x["id"] for x in current["cases"]}) == 8
    original = json.dumps(frozen, sort_keys=True).replace("2.1.296", "2.1.302")
    assert json.dumps(current, sort_keys=True) == original


def test_no_boundary_case_promotes_unverified_model_code_or_secret_uploads() -> None:
    data = json.loads((ROOT / "evals/p4_boundary_semantic_rubric_cli_2_1_302.json").read_text())
    tasks = {x["id"]: x for x in data["cases"]}
    assert "executable code" in tasks["BOUND-VERSION-NEW"]["fail_on"]
    assert "secrets" in tasks["BOUND-INJECTION"]["pass_requires"]
    assert "installation" in tasks["BOUND-PLUGIN-PRIV"]["fail_on"]
    assert "permission checks" in tasks["BOUND-SKILL-ROLE"]["fail_on"]
    assert "file bytes" in tasks["BOUND-SKILL-ROLE"]["pass_requires"]
