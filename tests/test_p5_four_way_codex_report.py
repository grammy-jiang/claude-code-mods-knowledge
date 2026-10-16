"""Native Codex 12×3 comparison must not inflate source or safety acceptance."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs/reports/2026-10-17-p5-four-way-codex-vs-local-12x3.json"
TEXT = ROOT / "docs/reports/2026-10-17-p5-four-way-codex-vs-local-12x3.md"
EXPECTED = {"qwen", "gemma31", "codex", "codex_no_web"}


def test_four_way_report_is_complete_144_real_model_turns() -> None:
    data = json.loads(PUBLIC.read_text())
    assert data["schema_version"] == 1
    assert data["total_native_model_calls"] == 144
    assert data["pi_native_model_calls"] == 72
    assert data["codex_web_available_model_calls"] == 36
    assert data["codex_web_disabled_model_calls"] == 36
    assert set(data["models"]) == EXPECTED
    assert all(x["observed"] == 36 for x in data["models"].values())
    assert data["case_count_per_stack"] == 12
    assert data["repetitions_per_case"] == 3
    assert data["full_p5_production_semantic_acceptance"] is False
    assert len(data["codex_web_available_rows"]) == 36
    assert len(data["codex_web_disabled_rows"]) == 36
    assert len(data["per_case"]) == 12
    assert all(set(entry["scores"]) == EXPECTED for entry in data["per_case"])
    assert all(
        set(entry["scores"][m].values()) <= set(range(4))
        for entry in data["per_case"]
        for m in EXPECTED
    )


def test_no_web_is_verified_from_original_native_events() -> None:
    data = json.loads(PUBLIC.read_text())
    assert data["native_codex_web_disabled_config_verified"] is True
    assert data["native_codex_web_search_calls_disabled_cohort"] == 0
    assert data["native_codex_web_search_calls_in_default_cohort"] > 0
    assert data["codex_no_web_observed_timing_count"] == 35
    assert data["codex_no_web_timing_records_missing"] == 1
    for name, rows in (
        ("web", data["codex_web_available_rows"]),
        ("no-web", data["codex_web_disabled_rows"]),
    ):
        assert len({(x["case_id"], x["trial"]) for x in rows}) == 36
        assert all(x["provider_and_model_verified"] is True for x in rows), name
        assert all(x["full_mod_semantic_acceptance"] is False for x in rows)
        assert all(re.fullmatch(r"[0-9a-f]{64}", x["wire_sha256"]) for x in rows)
        assert all(x["status"] != "not_observed" for x in rows)
    assert all(x["native_web_search_calls"] == 0 for x in data["codex_web_disabled_rows"])


def test_summary_counts_do_not_confuse_boundary_violations_with_safe_passes() -> None:
    j = json.loads(PUBLIC.read_text())
    summaries = j["models"]
    assert summaries["qwen"]["positive_exact_source_structural"] == 2
    assert summaries["gemma31"]["positive_exact_source_structural"] == 3
    assert summaries["codex"]["positive_exact_source_structural"] == 11
    assert summaries["codex_no_web"]["positive_exact_source_structural"] == 12
    assert summaries["qwen"]["negative_nonactivation_observed"] == 6
    assert summaries["gemma31"]["negative_nonactivation_observed"] == 10
    assert summaries["codex"]["negative_nonactivation_observed"] == 12
    assert summaries["codex_no_web"]["negative_nonactivation_observed"] == 12
    assert summaries["qwen"]["boundary_scope_violations"] == 3
    assert summaries["gemma31"]["boundary_scope_violations"] == 3
    assert summaries["codex"]["boundary_scope_violations"] == 0
    assert summaries["codex_no_web"]["boundary_scope_violations"] == 0
    assert (
        Counter(row["status"] for row in j["codex_web_available_rows"])[
            "positive_exact_claim_or_source_missing"
        ]
        == 1
    )


def test_public_document_contains_no_private_ids_paths_or_auth_material() -> None:
    data = PUBLIC.read_text()
    document = TEXT.read_text()
    text = document + data
    assert "not a fully controlled pure llm architecture test" in text.lower()
    assert "NOT" in text and "2.1.296" in text
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-", text)
    assert not re.search(r"chatgpt.com/c/[0-9a-f-]{36}", text, re.I)
    assert not re.search(r"Bearer\s+[A-Za-z0-9._-]{20,}", text)
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", text)
