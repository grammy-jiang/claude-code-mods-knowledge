"""No model fine tuning: fail-closed native Skill-only outcome scoring."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_p5_skill_only_report as publish  # noqa: E402
import score_p5_skill_only_evidence as scorer  # noqa: E402


def sample() -> dict:
    return {
        "case_id": "POS-Q-01",
        "cohort": "candidate",
        "model_pin_matched": True,
        "prompt_matched": True,
        "actual_skill_read": True,
        "native_exit_code": 0,
        "native_agent_completed": True,
        "timed_out": False,
        "stop_reason_last": "stop",
        "scorer_verdict": "structural_ok_semantics_unverified",
        "exact_official_source_verdict": "pass",
        "manual_review_flags": [],
    }


def test_source_pass_not_semantic_or_version_pass() -> None:
    assert scorer.judge(sample(), "positive") == "positive_exact_source_structure_only"
    broken = sample() | {"exact_official_source_verdict": "fail"}
    assert scorer.judge(broken, "positive") == "positive_exact_source_missing"
    assert (
        scorer.judge(sample() | {"actual_skill_read": False}, "positive")
        == "skill_activation_missing"
    )
    assert (
        scorer.judge(sample() | {"stop_reason_last": "length"}, "positive")
        == "native_incomplete_or_loop"
    )
    assert scorer.judge(sample() | {"timed_out": True}, "positive") == "native_incomplete_or_loop"
    assert (
        scorer.judge(sample() | {"model_pin_matched": False}, "positive")
        == "model_or_prompt_provenance_failed"
    )


def test_unrelated_negative_requires_no_skill_read_and_native_final() -> None:
    good = sample() | {"actual_skill_read": False}
    assert scorer.judge(good, "negative") == "negative_nonactivation_observed"
    assert scorer.judge(sample(), "negative") == "negative_false_activation"
    assert (
        scorer.judge(good | {"native_exit_code": None}, "negative") == "native_incomplete_or_loop"
    )


def test_boundary_safe_rating_is_never_awarded_automatically() -> None:
    report = sample()
    assert scorer.judge(report, "boundary") == "boundary_manual_review_required"
    report["scorer_verdict"] = "boundary_scope_violated"
    assert scorer.judge(report, "boundary") == "boundary_scope_violated"
    report["scorer_verdict"] = "boundary_manual_review_required"
    report["manual_review_flags"] = ["unreviewed-version-implementation-present"]
    assert scorer.judge(report, "boundary") == "boundary_scope_violated"


def test_missing_or_drifted_skill_cohort_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(scorer, "POSITIVE", tmp_path / "absent-positive")
    monkeypatch.setattr(scorer, "CONTROL", tmp_path / "absent-control")
    with pytest.raises((ValueError, OSError)):
        scorer.private_candidate_status()
    with pytest.raises((ValueError, OSError)):
        publish.build()


def test_frozen_sha_and_case_denom_unchanged() -> None:
    plan = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())
    actual = hashlib.sha256((ROOT / plan["source_file"]).read_bytes()).hexdigest()
    assert actual == plan["source_sha256"]
    assert set(scorer.CASE_GROUPS) == {"positive", "negative", "boundary"}
    assert sum(len(x) for x in scorer.CASE_GROUPS.values()) == 12
    assert all(len(x) == 4 for x in scorer.CASE_GROUPS.values())
    assert scorer.EXPECTED_MODEL == "qwen36-35b-a3b-mtp"
