"""Offline P4 resource evaluation; no model, ChatGPT Work, or token-spending calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.evaluator import EvaluationError, evaluate_suite, validate_suite

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals/p4_cases.json"


def test_suite_has_46_distinct_positive_negative_boundary_cases() -> None:
    suite = json.loads(SUITE.read_text())
    assert suite["schema_version"] == 1
    assert len(suite["cases"]) == 46
    assert len({c["id"] for c in suite["cases"]}) == 46
    counts = {
        name: sum(c["category"] == name for c in suite["cases"])
        for name in ("positive", "negative", "boundary")
    }
    assert counts == {"positive": 30, "negative": 8, "boundary": 8}
    validate_suite(suite)


def test_resource_coverage_is_complete_but_chatgpt_runtime_remains_unverified() -> None:
    result = evaluate_suite(ROOT, SUITE)
    assert result["target"] == {"claude_code_version": "2.1.296", "surface": "cli"}
    assert result["cases_total"] == 46
    assert result["resource_checks_passed"] == 46
    assert result["resource_checks_failed"] == 0
    assert result["host_runtime_cases_passed"] == 0
    assert result["host_runtime_cases_pending"] == 46
    assert result["status"] == "STATIC_PASS_HOST_NOT_TESTED"
    assert result["activation_accuracy"] is None
    assert result["model_response_accuracy"] is None
    assert "ChatGPT" in result["host_runtime_caveat"]
    assert result["source_revision"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c[1].update(id=c[0]["id"]),
        lambda c: c[0].update(expected_claim_ids=["K-0001"]),
        lambda c: c[0].update(expected_claim_ids=["K-8888"]),
        lambda c: c[0].update(expected_areas=["P"]),
        lambda c: c[-1].update(expected_activation=False),
        lambda c: c[30].update(expected_claim_ids=["K-0007"]),
        lambda c: c[0].update(prompt=""),
    ],
)
def test_bad_eval_suite_is_rejected_without_claiming_chatgpt_pass(mutation) -> None:
    payload = json.loads(SUITE.read_text())
    mutation(payload["cases"])
    with pytest.raises(EvaluationError):
        evaluate_suite(ROOT, payload)


def test_version_mismatch_is_not_silently_graded_against_other_release() -> None:
    payload = json.loads(SUITE.read_text())
    payload["target"]["claude_code_version"] = "2.1.297"
    with pytest.raises(EvaluationError, match="version|scope|compatible"):
        evaluate_suite(ROOT, payload)


def test_non_mod_prompt_never_receives_fake_activation_result() -> None:
    result = evaluate_suite(ROOT, SUITE)
    negatives = [item for item in result["results"] if item["category"] == "negative"]
    assert len(negatives) == 8
    assert all(item["expected_activation"] is False for item in negatives)
    assert all(item["host_status"] == "not_run" for item in negatives)
    assert all(item["static_status"] == "pass" for item in negatives)


def test_report_does_not_embed_raw_untrusted_prompt_as_an_agent_instruction() -> None:
    result = evaluate_suite(ROOT, SUITE)
    assert all("prompt" not in row for row in result["results"])
    assert not result.get("model_executed", True)


def test_requires_skill_description_to_be_explicitly_mods_scoped() -> None:
    result = evaluate_suite(ROOT, SUITE)
    assert result["activation_description_scoped"] is True
