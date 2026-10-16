"""Do not publish a completed model report without 72 real observations
and verified restoration of every original AI service after each window.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_p5_pi_paired_report as builder  # noqa: E402


def fake_scores(*, observed: int = 72) -> dict:
    common = {
        "observed": 36,
        "native_completed": 33,
        "positive_exact_source_structural": 2,
        "negative_nonactivation_observed": 6,
        "boundary_scope_violations": 3,
        "boundary_copyable_code_requires_manual_review": 7,
        "incomplete_or_loop": 3,
        "median_seconds_completed": 15.0,
        "p95_seconds_completed_nearest_rank": 35.0,
        "states": {"positive_source_structure_only": 2, "boundary_scope_violated": 3},
    }
    return {
        "observed": observed,
        "unobserved": 72 - observed,
        "source_sha256": "a" * 64,
        "suite_id": "SYNTHETIC-UNIT-TEST",
        "model_stats": [
            common | {"model": "qwen"},
            common | {"model": "gemma31"},
        ],
        "rows": [],
    }


def fake_rollbacks(*, verified: bool = True) -> dict:
    return {
        "observed_windows": 6,
        "fully_restored_windows": 6 if verified else 5,
        "unverified_windows": 0 if verified else 1,
        "all_restorations_verified": verified,
        "per_round_window_count": {"1": 2, "2": 2, "3": 2},
    }


@pytest.mark.parametrize(
    ("observed", "restored"),
    [
        (0, True),
        (71, True),
        (72, False),
    ],
)
def test_incomplete_model_run_or_bad_restoration_never_published(
    observed: int, restored: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "summarize", lambda: fake_scores(observed=observed))
    monkeypatch.setattr(
        builder, "checked_window_rollbacks", lambda: fake_rollbacks(verified=restored)
    )
    with pytest.raises(ValueError):
        builder.report()


def test_complete_synthetic_report_still_never_claims_model_semantic_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builder, "summarize", lambda: fake_scores())
    monkeypatch.setattr(builder, "checked_window_rollbacks", fake_rollbacks)
    data, md = builder.report()
    assert data["observed_calls"] == 72
    assert data["no_gpt_oss_120b_inference"]
    assert data["model_level_full_semantic_acceptance"] is False
    assert "12×3" in md
    assert "Gemma 4 31B" in md
    assert "Neither model is approved" in md
    assert "verified" not in json.dumps(data["rows"])
