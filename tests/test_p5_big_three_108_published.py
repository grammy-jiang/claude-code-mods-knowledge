"""Publication is complete only for real 108-turn evidence and 18 safe Mac rollbacks."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / "docs/reports/2026-10-17-p5-120b-three-way-12x3.json"
MD = ROOT / "docs/reports/2026-10-17-p5-120b-three-way-12x3.md"

BIG = ("gpt-oss", "mistral", "heretic")
ALL = BIG + ("qwen", "gemma31", "codex", "codex_no_web")
CASES = (
    "POS-E-01",
    "POS-Q-01",
    "POS-S-02",
    "POS-P-01",
    "NEG-TYPESCRIPT",
    "NEG-PYTHON",
    "NEG-MCP",
    "NEG-LEGACY-HOOK",
    "BOUND-VERSION-NEW",
    "BOUND-VERSION-OLD",
    "BOUND-SURFACE",
    "BOUND-HISTORY",
)


def test_public_score_has_exactly_108_original_model_observations() -> None:
    data = json.loads(JSON.read_text())
    assert data["schema_version"] == 1
    assert data["new_local_big_model_turns"] == 108
    assert data["previous_verified_reference_turns"] == 144
    assert data["combined_native_turn_evidence"] == 252
    assert data["test_cases_per_stack"] == 12
    assert data["independent_repetitions"] == 3
    assert data["model_stacks"] == 7
    assert set(data["models"]) == set(ALL)
    rows = data["new_big_model_rows"]
    assert len(rows) == 108
    assert len({(r["model"], r["case_id"], r["trial"]) for r in rows}) == 108
    assert set(r["model"] for r in rows) == set(BIG)
    assert all(
        r["status"] not in {"not_observed", "partial_native_trace_no_final_report"} for r in rows
    )
    assert all(
        r["raw_model_output_exposed"] is False and r["full_mod_semantic_approval"] is False
        for r in rows
    )
    assert all(re.fullmatch(r"[0-9a-f]{64}", r["event_sha256"]) for r in rows)
    for model in BIG:
        candidate = [r for r in rows if r["model"] == model]
        assert len(candidate) == 36
        assert all(
            {(r["case_id"], r["trial"]) for r in candidate}
            == {(case, trial) for case in CASES for trial in (1, 2, 3)}
            for _ in (0,)
        )


def test_score_distinguishes_native_exit_from_substantive_response() -> None:
    d = json.loads(JSON.read_text())["models"]
    assert [
        (d[key]["observed"], d[key]["native_completed"], d[key]["strict_substantive_completed"])
        for key in BIG
    ] == [(36, 36, 24), (36, 34, 22), (36, 33, 26)]
    assert [d[key]["positive_exact_source_structural"] for key in BIG] == [0, 0, 0]
    assert [d[key]["negative_nonactivation_observed"] for key in BIG] == [11, 5, 6]
    assert [d[key]["boundary_scope_violations"] for key in BIG] == [1, 1, 2]
    assert [
        d[key]["positive_exact_source_structural"]
        for key in ("qwen", "gemma31", "codex_no_web", "codex")
    ] == [2, 3, 12, 11]
    assert [
        d[key]["negative_nonactivation_observed"]
        for key in ("qwen", "gemma31", "codex_no_web", "codex")
    ] == [6, 10, 12, 12]
    assert all(d[key]["strict_substantive_completed"] < 36 for key in BIG)


def test_eighteen_window_rollbacks_and_current_model_configuration() -> None:
    info = json.loads(JSON.read_text())
    resources = info["verified_service_windows"]
    assert len(resources) == 18
    assert len({(r["model"], r["trial"], r["part"]) for r in resources}) == 18
    assert Counter(r["model"] for r in resources) == {
        "gpt-oss": 6,
        "mistral": 6,
        "heretic": 6,
    }
    assert all(r["candidate_unloaded"] and r["all_original_services_restored"] for r in resources)
    assert info["all_18_original_service_restorations_verified"] is True


def test_no_private_model_prompt_or_config_secrets_in_public_report() -> None:
    data = json.loads(JSON.read_text())
    text = JSON.read_text() + "\n" + MD.read_text()
    assert data["production_mod_semantics_approved"] is False
    assert data["version_boundary_fully_approved"] is False
    assert data["all_raw_model_answers_and_prompts_remain_private"] is True
    assert "STRUCTURAL" in MD.read_text()
    assert "unrestricted" in text
    assert not re.search(r"/Users/[^/\s]+|/home/grammy-jiang/|/tmp/mods-", text)
    assert not re.search(r"sk-[A-Za-z0-9]{20,}", text)
    assert not re.search(r"Bearer\s+[A-Za-z0-9._-]{20,}", text)
    assert not re.search(r"chatgpt.com/c/[0-9a-f-]{36}", text, re.I)
