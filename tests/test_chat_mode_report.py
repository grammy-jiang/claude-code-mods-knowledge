"""Real Chat-mode P4 acceptance report must not confuse static checks with model QA."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from mods_knowledge.chat_mode_report import ChatReportError, aggregate_chat_mode_results

ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / "evals/p4_cases.json").read_text())


def case_result(cid: str, category: str, *, loaded: bool = True, grade: str = "pass") -> dict:
    return {
        "case_id": cid,
        "category": category,
        "plugin_version": "0.2.0-beta.1",
        "conversation_sha256": hashlib.sha256(cid.encode()).hexdigest(),
        "response_sha256": "b" * 64,
        "plugin_id_sha256": "c" * 64 if loaded else None,
        "skill_loaded": loaded,
        "resource_uris": [
            "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
        ]
        if loaded
        else [],
        "expected_activation": category != "negative",
        "observed_claim_ids": ["K-0007", "K-0031"] if category == "positive" else [],
        "official_source_cited": category == "positive",
        "code_callback_signature_correct": True if cid == "POS-E-01" else None,
        "answer_quality": grade,
        "quality_flags": ["nonactivation-observed"] if category == "negative" else [],
        "notes": "This is a test fixture, not a real ChatGPT conversation.",
    }


def build(records, **kwargs):
    return aggregate_chat_mode_results(
        SUITE,
        records,
        plugin_version="0.2.0-beta.1",
        source_revision="33706131f05f0aedf49fbb1fc0459854a579316d",
        **kwargs,
    )


def test_incomplete_suite_is_explicitly_not_a_full_pass() -> None:
    results = [
        case_result("POS-E-01", "positive"),
        case_result("NEG-HVAC", "negative", loaded=False),
    ]
    report = build(
        results,
        manual_reviews={
            "POS-E-01": {
                "verdict": "pass",
                "rationale": "Checked complete three-parameter callback.",
            }
        },
        blocked_case_ids={"POS-E-03"},
    )
    assert report["target"]["surface"] == "cli"
    assert report["mode"] == "chat"
    assert report["summary"]["total"] == 46
    assert report["summary"]["observed"] == 2
    assert report["summary"]["passed"] == 2
    assert report["summary"]["blocked"] == 1
    assert report["summary"]["not_run"] == 43
    assert report["summary"]["full_qa_pass"] is False
    assert report["status"] == "PARTIAL_LIVE_CHAT_MODE_EVALUATION"
    assert report["summary"]["by_category"]["positive"]["passed"] == 1
    assert report["summary"]["by_category"]["negative"]["passed"] == 1
    assert report["summary"]["by_category"]["boundary"]["not_run"] == 8


def test_structural_pass_without_independent_semantic_review_stays_inconclusive() -> None:
    report = build([case_result("POS-E-01", "positive")])
    assert report["summary"]["observed"] == 1
    assert report["summary"]["inconclusive"] == 1
    assert report["summary"]["passed"] == 0
    assert report["items"][0]["final_verdict"] == "inconclusive"
    assert "manual_review_required" in report["items"][0]["quality_flags"]


def test_structural_failure_cannot_be_manually_overridden_to_pass() -> None:
    record = case_result("POS-E-01", "positive", loaded=False, grade="fail")
    rec = build(
        [record],
        manual_reviews={
            "POS-E-01": {
                "verdict": "pass",
                "rationale": "Someone tried to waive missing Skill loading",
            }
        },
    )
    assert rec["summary"]["failed"] == 1
    assert rec["summary"]["full_qa_pass"] is False


def test_boundary_case_requires_both_actual_plugin_and_manual_review() -> None:
    record = case_result("BOUND-VERSION-NEW", "boundary", loaded=True, grade="inconclusive")
    record["quality_flags"] = ["manual-semantic-review-required"]
    report = build(
        [record],
        manual_reviews={
            "BOUND-VERSION-NEW": {
                "verdict": "pass",
                "rationale": "The reply refused to assume new API compatibility.",
            }
        },
    )
    assert report["summary"]["passed"] == 1
    assert (
        next(x for x in report["items"] if x["id"] == "BOUND-VERSION-NEW")["final_verdict"]
        == "passed"
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda x: x.append(deepcopy(x[0])),
        lambda x: x[0].update(case_id="UNKNOWN-01"),
        lambda x: x[0].update(plugin_version="0.2.0-beta.2"),
        lambda x: x[0].update(conversation_sha256="not-a-hash"),
        lambda x: x[0].update(resource_uris=["http://fake.invalid"]),
        lambda x: x[0].update(reply="untrusted model text"),
        lambda x: x[0].update(prompt="a private user message"),
        lambda x: x[0].update(expected_activation=False),
    ],
)
def test_untrusted_or_duplicate_records_are_rejected(mutate) -> None:
    rows = [case_result("POS-E-01", "positive")]
    mutate(rows)
    with pytest.raises(ChatReportError):
        build(rows)


def test_manual_verdict_requires_existing_record_and_explanation() -> None:
    with pytest.raises(ChatReportError):
        build([], manual_reviews={"POS-E-01": {"verdict": "pass", "rationale": "All looks good"}})
    with pytest.raises(ChatReportError):
        build(
            [case_result("POS-E-01", "positive")],
            manual_reviews={"POS-E-01": {"verdict": "pass", "rationale": ""}},
        )


def test_blocked_never_counts_as_model_failure_and_never_as_pass() -> None:
    report = build([], blocked_case_ids={"POS-E-03", "NEG-HVAC"})
    assert report["summary"]["blocked"] == 2
    assert report["summary"]["failed"] == 0
    assert report["summary"]["passed"] == 0
    assert report["summary"]["full_qa_pass"] is False


def test_report_never_exposes_actual_chat_ids_or_prompts() -> None:
    report = build([case_result("POS-E-01", "positive")])
    body = json.dumps(report)
    assert "Design Claude Code" not in body
    assert "conversation_id" not in body
    assert "reply" not in body
    assert "chatgpt.com/c/" not in body


def test_full_suite_require_complete_real_rows_and_manual_review_for_all_non_negatives() -> None:
    records = []
    reviews = {}
    for case in SUITE["cases"]:
        category = case["category"]
        record = case_result(
            case["id"],
            category,
            loaded=(category != "negative"),
            grade="pass" if category != "boundary" else "inconclusive",
        )
        record["observed_claim_ids"] = case["expected_claim_ids"]
        record["code_callback_signature_correct"] = True if case["id"] == "POS-E-01" else None
        record["quality_flags"] = ["nonactivation-observed"] if category == "negative" else []
        records.append(record)
        if category != "negative":
            reviews[case["id"]] = {
                "verdict": "pass",
                "rationale": "Manually reviewed the supported API claim and safety semantics.",
            }
    out = build(records, manual_reviews=reviews)
    assert out["summary"]["total"] == 46
    assert out["summary"]["observed"] == 46
    assert out["summary"]["passed"] == 46
    assert out["summary"]["full_qa_pass"] is True
    assert out["status"] == "FULL_SUITE_LIVE_CHAT_MODE_PASS"


def test_activation_metrics_use_only_observed_cases_as_rate_denominator() -> None:
    rows = [
        case_result("POS-E-01", "positive", loaded=True),
        case_result("POS-E-02", "positive", loaded=False, grade="fail"),
        case_result("NEG-HVAC", "negative", loaded=False),
        case_result("NEG-PYTHON", "negative", loaded=True, grade="fail"),
    ]
    summary = build(rows)["summary"]
    active = summary["activation_metrics"]
    assert active["positive"]["observed"] == 2
    assert active["positive"]["correct_loaded"] == 1
    assert active["positive"]["correct_loading_rate"] == 0.5
    assert active["positive"]["suite_coverage"] == 2 / 30
    assert active["negative"]["observed"] == 2
    assert active["negative"]["false_activations"] == 1
    assert active["negative"]["false_activation_rate"] == 0.5
    assert active["negative"]["suite_coverage"] == 2 / 8
    assert summary["observed"] == 4


def test_incomplete_zero_observations_have_null_not_fake_zero_accuracy() -> None:
    summary = build([])["summary"]
    for name in ("positive", "negative", "boundary"):
        x = summary["activation_metrics"][name]
        assert x["observed"] == 0
        assert x["correct_loading_rate"] is None
        assert x["false_activation_rate"] is None
        assert x["suite_coverage"] == 0


def test_two_cases_cannot_reuse_the_same_real_conversation_id_digest() -> None:
    first = case_result("POS-E-01", "positive")
    second = case_result("POS-E-02", "positive")
    second["conversation_sha256"] = first["conversation_sha256"]
    with pytest.raises(ChatReportError, match="conversation|duplicate"):
        build([first, second])


def test_all_loaded_chat_cases_must_use_the_same_plugin_instance() -> None:
    first = case_result("POS-E-01", "positive")
    second = case_result("POS-E-02", "positive")
    second["conversation_sha256"] = "d" * 64
    second["plugin_id_sha256"] = "f" * 64
    with pytest.raises(ChatReportError, match="plugin|instance"):
        build([first, second])


def test_explicit_selected_plugin_must_not_inflate_automatic_activation_suite() -> None:
    record = case_result("POS-E-01", "positive")
    record["invocation_mode"] = "explicit"
    with pytest.raises(ChatReportError, match="explicit|automatic"):
        build([record])
