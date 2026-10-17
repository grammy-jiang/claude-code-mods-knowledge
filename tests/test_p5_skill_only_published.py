"""Native Skill-only QA results must not mistake better citations for Mod safety."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reports/2026-10-17-p5-skill-only-automatic-evidence.json"
REPORT = ROOT / "docs/reports/2026-10-17-p5-skill-only-automatic-evidence.md"
CATEGORIES = {
    "positive": {"POS-E-01", "POS-Q-01", "POS-S-02", "POS-P-01"},
    "negative": {"NEG-TYPESCRIPT", "NEG-PYTHON", "NEG-MCP", "NEG-LEGACY-HOOK"},
    "boundary": {"BOUND-VERSION-NEW", "BOUND-VERSION-OLD", "BOUND-SURFACE", "BOUND-HISTORY"},
}


def test_final_trial_count_and_original_native_provenance() -> None:
    info = json.loads(EVIDENCE.read_text())
    assert info["actual_native_turns_observed"] == 36
    assert info["three_independent_turns_per_case"] is True
    assert info["model_id"] == "qwen36-35b-a3b-mtp"
    assert info["all_original_native_turns_sha_verified"] is True
    assert info["same_original_model_provider_and_weights"] is True
    assert info["installed_user_skills_modified_during_experiment"] is False
    assert info["model_or_plugin_production_approved"] is False
    assert info["all_code_semantics_verified"] is False
    assert info["unreviewed_version_safety_fully_verified"] is False
    rows = info["rows"]
    assert len(rows) == 36
    assert len({(x["case_id"], x["trial"]) for x in rows}) == 36
    assert all(
        x["raw_response_released"] is False and x["model_semantics_verified"] is False for x in rows
    )
    assert all(re.fullmatch(r"[a-f0-9]{64}", x["private_native_event_sha256"]) for x in rows)
    for category, cases in CATEGORIES.items():
        rows_of_category = [x for x in rows if x["category"] == category]
        assert len(rows_of_category) == 12
        assert {(x["case_id"], x["trial"]) for x in rows_of_category} == {
            (cid, i) for cid in cases for i in (1, 2, 3)
        }


def test_structural_improvement_keeps_real_failing_routing_and_boundaries() -> None:
    s = json.loads(EVIDENCE.read_text())
    assert s["historical_old_skill_positive_source_passes"] == 2
    assert s["candidate_positive_source_passes"] == 9
    assert s["candidate_negative_no_skill_completed"] == 8
    assert s["candidate_boundary_violations_detected"] == 0
    assert s["native_incomplete_or_loop"] == 8
    categories = s["categories"]
    assert categories["positive"]["statuses"] == {
        "positive_exact_source_missing": 3,
        "positive_exact_source_structure_only": 9,
    }
    assert categories["negative"]["statuses"] == {
        "native_incomplete_or_loop": 2,
        "negative_false_activation": 2,
        "negative_nonactivation_observed": 8,
    }
    assert categories["boundary"]["statuses"] == {
        "boundary_manual_review_required": 6,
        "native_incomplete_or_loop": 6,
    }
    assert sum(v["cases"] for v in categories.values()) == 12
    legacy = s["frozen_case_results"]["NEG-LEGACY-HOOK"]
    assert legacy["statuses"]["negative_false_activation"] == 2
    assert legacy["statuses"]["native_incomplete_or_loop"] == 1
    assert "citation format does not prove claim semantics" in s["comparability_warning"]


def test_public_package_and_report_exclude_private_data() -> None:
    text = EVIDENCE.read_text() + REPORT.read_text()
    assert "2.1.296" in text
    assert "not automatically safe" in text or "NOT" in text
    assert "not independent factual correctness" in text.lower() or (
        "not an interleaved" in text.lower()
    )
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/", text)
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", text)
    assert not re.search(r"Bearer\s+[A-Za-z0-9._-]{20,}", text)
    assert not re.search(r"chatgpt.com/c/[0-9a-f-]{36}", text, re.I)
    assert set(json.loads(EVIDENCE.read_text())["categories"]) == set(CATEGORIES)
    assert (
        Counter(row["status"] for row in json.loads(EVIDENCE.read_text())["rows"])[
            "positive_exact_source_structure_only"
        ]
        == 9
    )
