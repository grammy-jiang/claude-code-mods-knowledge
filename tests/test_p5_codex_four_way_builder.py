"""Offline checks: do not report the Codex-vs-Pi benchmark before all real turns."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_p5_codex_four_way as builder  # noqa: E402


def models() -> dict:
    keys = ("codex", "codex_no_web", "qwen", "gemma31")
    result = {}
    for key in keys:
        result[key] = {
            "model": key,
            "observed": 36,
            "not_observed": 0,
            "native_completed": 36,
            "states": {},
            "median_seconds_completed": 22.0,
            "p95_seconds_completed_nearest_rank": 35.0,
            "positive_exact_source_structural": 12,
            "negative_nonactivation_observed": 12,
            "boundary_scope_violations": 0,
            "boundary_copyable_code_requires_manual_review": 0,
            "incomplete_or_tool_failure": 0,
        }
    return result


def fixture_rows(model: str) -> list[dict]:
    catalog = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    categories = {x["id"]: x["category"] for x in catalog}
    manifest = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())
    rows = []
    for cid in manifest["case_ids"]:
        for trial in (1, 2, 3):
            category = categories[cid]
            outcome = {
                "positive": "positive_source_structure_only",
                "negative": "negative_nonactivation_observed",
                "boundary": "boundary_manual_review_required",
            }[category]
            rows.append(
                {
                    "case_id": cid,
                    "trial": trial,
                    "model": model,
                    "category": category,
                    "status": outcome,
                }
            )
    return rows


def fixture_codex(key: str, count: int) -> dict:
    return {
        "codex_observed": count,
        "codex_unobserved": 36 - count,
        "source_sha256": "a" * 64,
        "source_revision": "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e",
        "stat": models()[key],
        "rows": [
            row
            | {
                "provider_and_model_verified": True,
                "full_mod_semantic_acceptance": False,
                "native_web_search_calls": 0,
            }
            for row in fixture_rows(key)[:count]
        ],
        "complete_timing_observations": 36,
    }


def fixture_pi(tmp_path: Path) -> Path:
    path = tmp_path / "pi.json"
    path.write_text(
        json.dumps(
            {
                "observed_calls": 72,
                "rows": fixture_rows("qwen") + fixture_rows("gemma31"),
                "source_sha256": "a" * 64,
                "models": [models()["qwen"], models()["gemma31"]],
            }
        )
    )
    return path


@pytest.mark.parametrize("web_count, offline_count", [(35, 36), (36, 35), (12, 35)])
def test_no_partial_comparison_is_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    web_count: int,
    offline_count: int,
) -> None:
    monkeypatch.setattr(builder, "PI_REPORT", fixture_pi(tmp_path))
    monkeypatch.setattr(builder, "with_web", lambda: fixture_codex("codex", web_count))
    monkeypatch.setattr(builder, "no_web", lambda: fixture_codex("codex_no_web", offline_count))
    with pytest.raises(ValueError):
        builder.report()


def test_actual_web_search_in_no_web_cohort_invalidates_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "PI_REPORT", fixture_pi(tmp_path))
    monkeypatch.setattr(builder, "with_web", lambda: fixture_codex("codex", 36))
    wrong = fixture_codex("codex_no_web", 36)
    wrong["rows"][0]["native_web_search_calls"] = 1
    monkeypatch.setattr(builder, "no_web", lambda: wrong)
    with pytest.raises(ValueError):
        builder.report()


def test_correct_full_synthetic_does_not_grant_mods_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "PI_REPORT", fixture_pi(tmp_path))
    monkeypatch.setattr(builder, "with_web", lambda: fixture_codex("codex", 36))
    monkeypatch.setattr(builder, "no_web", lambda: fixture_codex("codex_no_web", 36))
    monkeypatch.setattr(builder, "_total_web_calls", lambda: (36, 12))
    report, md = builder.report()
    assert report["total_native_model_calls"] == 144
    assert report["native_codex_web_search_calls_in_default_cohort"] == 12
    assert report["native_codex_web_search_calls_disabled_cohort"] == 0
    assert report["full_p5_production_semantic_acceptance"] is False
    assert "not a fully controlled pure llm architecture test" in md.lower()
    assert "unrestricted" in md.lower()
