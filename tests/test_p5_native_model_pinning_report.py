"""Validate published native-model evidence without trusting requested flags as results."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-15-p5-native-model-pinning.json"
NARRATIVE = ROOT / "docs/reports/2026-10-15-p5-native-model-pinning.md"


def data() -> dict:
    return json.loads(REPORT.read_text())


def test_native_pi_model_identity_is_explicitly_observed_not_guessed() -> None:
    report = data()
    assert report["evaluation"] == "p5-readonly-real-native-model-events-not-full-acceptance"
    assert report["acceptance"] == "P5_NOT_ACCEPTED"
    assert report["exact_source_revision"] == "81fdf78656238f8383cbeed54ed3420bdc480231"
    assert (
        report["portable_skill_sha256"]
        == "8cf14b9cd072d6ca7b8796cc863b6168694f663a4246d3fbb7da51480cb391b8"
    )
    assert len(report["pi_agent_results"]) == 18
    source = json.loads((ROOT / "evals/p4_cases.json").read_text())
    cases = {case["id"]: case for case in source["cases"]}
    for row in report["pi_agent_results"]:
        case = cases[row["case_id"]]
        assert row["category"] == case["category"]
        assert row["user_prompt_sha256"] == hashlib.sha256(case["prompt"].encode()).hexdigest()
        assert row["prompt_matched"] is True
        assert row["source_revision"] == report["exact_source_revision"]
        assert row["semantic_review_complete"] is False
        assert row["invocation_mode"] == "native-cli-skill-exposed-via-flag"
        assert re.fullmatch(r"[a-f0-9]{64}", row["trace_sha256"])
        assert row["verdict"] != "passed"
    assert len({row["trace_sha256"] for row in report["pi_agent_results"]}) == 18


def test_unpinned_qwen_is_not_mislabeled_as_earlier_gpt55_qa() -> None:
    report = data()
    cohort = report["pi_agent_cohorts"]["unfixed-default-model"]
    assert cohort["observed_cases"] == 14
    assert cohort["model_pin_matched"] == 0
    assert cohort["observed_models"] == {"mac-qwen/qwen36-35b-a3b-mtp": 14}
    assert cohort["agent_end_observed"] == 12
    assert cohort["answer_present"] == 11
    assert cohort["verdicts"] == {"blocked_or_incomplete": 3, "invalid_provenance": 11}
    rows = [x for x in report["pi_agent_results"] if x["cohort"] == "unfixed-default-model"]
    assert len(rows) == 14
    assert all(x["model_flag_explicit"] is False for x in rows)
    assert all(x["model_requested"] is None for x in rows)
    assert all(x["model_pin_matched"] is False for x in rows)


def test_pinned_gpt55_cases_retain_real_technical_failures() -> None:
    report = data()
    cohort = report["pi_agent_cohorts"]["explicit-openai-codex-gpt-5.5"]
    assert cohort["observed_cases"] == cohort["model_pin_matched"] == cohort["answer_present"] == 4
    assert cohort["observed_models"] == {"openai-codex/gpt-5.5": 4}
    assert cohort["verdicts"] == {
        "structural_failed": 2,
        "negative_nonactivation_observed": 1,
        "boundary_manual_review_required": 1,
    }
    pinned = {
        x["case_id"]: x
        for x in report["pi_agent_results"]
        if x["cohort"] == "explicit-openai-codex-gpt-5.5"
    }
    assert set(pinned) == {"POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}
    assert all(
        x["model_flag_explicit"] and x["model_pin_matched"] and x["prompt_matched"]
        for x in pinned.values()
    )
    assert all(
        pinned[case]["skill_loaded"] and pinned[case]["verdict"] == "structural_failed"
        for case in ("POS-E-01", "POS-Q-01")
    )
    assert "plugin-test-expects-mod-directory" in pinned["POS-Q-01"]["known_risk_flags"]
    assert not pinned["NEG-TYPESCRIPT"]["skill_loaded"]
    assert pinned["BOUND-VERSION-NEW"]["skill_loaded"]


def test_codex_and_claude_host_limitations_are_explicit_and_private() -> None:
    report = data()
    codex = {row["case_id"]: row for row in report["codex_exact_prompt_results"]}
    assert set(codex) == {"POS-E-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}
    assert all(
        x["native_agent_completed"] and x["claimed_model_identifier_in_native_stream"] is None
        for x in codex.values()
    )
    assert all(x["exact_model_qa_eligible"] is False for x in codex.values())
    assert codex["POS-E-01"]["skill_read_verified"]
    assert not codex["NEG-TYPESCRIPT"]["skill_read_verified"]
    assert codex["BOUND-VERSION-NEW"]["skill_read_verified"]
    assert not codex["BOUND-VERSION-NEW"]["official_mods_url_present"]
    assert "authentication_failed" in report["claude_model_host_result"]
    for file in (REPORT, NARRATIVE):
        text = file.read_text()
        for pattern in (
            r"https?://(?:chatgpt\.com|chat\.openai\.com)/c/",
            r"Plugin_[a-f0-9]{16,}",
            r"/home/grammy-jiang/",
            r"(?i)(?:ghp_|gho_|sk-)[a-z0-9_-]{30,}",
        ):
            assert not re.search(pattern, text)
