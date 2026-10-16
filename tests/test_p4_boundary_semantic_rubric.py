"""Protect P4-D's human review criteria from accidental omissions or false QA shortcuts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rubric_preserves_all_eight_existing_boundary_contracts() -> None:
    suite = json.loads((ROOT / "evals/p4_cases.json").read_text())
    rubric = json.loads((ROOT / "evals/p4_boundary_semantic_rubric.json").read_text())
    expected = {
        row["id"]: row["expected_behavior"]
        for row in suite["cases"]
        if row["category"] == "boundary"
    }
    actual = {row["id"]: row["expected_behavior"] for row in rubric["cases"]}
    assert len(expected) == len(actual) == 8
    assert expected == actual
    assert rubric["target_cli_version"] == "2.1.296"
    assert rubric["schema_version"] == 1


def test_manual_gate_cannot_be_mistaken_for_static_or_auto_pass() -> None:
    rubric = json.loads((ROOT / "evals/p4_boundary_semantic_rubric.json").read_text())
    controls = rubric["controls"]
    assert controls
    assert all(value is True for value in controls.values())
    for row in rubric["cases"]:
        assert 40 <= len(row["pass_requires"]) <= 300
        assert 40 <= len(row["fail_on"]) <= 300
        assert row["pass_requires"] != row["fail_on"]


def test_skill_role_downloaded_file_needs_real_content_review() -> None:
    rubric = json.loads((ROOT / "evals/p4_boundary_semantic_rubric.json").read_text())
    case = next(row for row in rubric["cases"] if row["id"] == "BOUND-SKILL-ROLE")
    assert "exact file bytes" in case["pass_requires"]
    assert "without independent file content verification" in case["fail_on"]
    assert rubric["controls"]["generated_artifact_requires_exact_byte_and_content_review"]
