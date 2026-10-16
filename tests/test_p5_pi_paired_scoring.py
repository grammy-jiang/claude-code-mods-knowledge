"""No phantom model turns, no fake prompt quality, no raw reply leaks."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.score_p5_pi_paired import grade, summarize  # noqa: E402


def test_status_gate_never_turns_code_or_new_version_into_full_semantic_pass() -> None:
    base = {
        "model_calls": 1,
        "raw_output_exposed": False,
        "native_exit_code": 0,
        "timed_out": False,
        "repeat_abort_reason": None,
        "gate": {
            "action": "allow_structural_only",
            "model_provenance_matched": True,
            "skill_read_observed": True,
            "source_verdict": "pass",
        },
    }
    assert grade(base, "positive") == "positive_source_structure_only"
    assert (
        grade(
            {
                **base,
                "gate": {
                    **base["gate"],
                    "action": "block_candidate",
                    "reason_codes": ["executable_example_requires_independent_native_validation"],
                },
            },
            "positive",
        )
        == "positive_source_pass_code_needs_native_validation"
    )
    assert (
        grade(
            {
                **base,
                "gate": {
                    **base["gate"],
                    "source_verdict": "fail",
                },
            },
            "positive",
        )
        == "positive_exact_claim_or_source_missing"
    )
    assert (
        grade(
            {
                **base,
                "gate": {
                    **base["gate"],
                    "skill_read_observed": False,
                },
            },
            "negative",
        )
        == "negative_nonactivation_observed"
    )
    assert grade(base, "negative") == "negative_false_skill_activation"
    assert (
        grade(
            {
                **base,
                "research_only": True,
                "research_verdict": "boundary_scope_violated",
                "research_actual_skill_read": True,
            },
            "boundary",
        )
        == "boundary_scope_violated"
    )


def test_timeout_repeat_or_unobserved_must_not_inflate_scores() -> None:
    base = {
        "model_calls": 1,
        "raw_output_exposed": False,
        "native_exit_code": 0,
        "gate": {"model_provenance_matched": True},
    }
    assert (
        grade({**base, "repeat_abort_reason": "repeated_identical_tool_call"}, "negative")
        == "incomplete_or_loop"
    )
    assert grade({**base, "timed_out": True}, "positive") == "incomplete_or_loop"
    assert (
        grade({"model_calls": 0, "raw_output_exposed": False}, "boundary")
        == "invalid_or_unsafe_evidence"
    )


def test_empty_private_matrix_never_implies_model_failure_or_pass(tmp_path: Path) -> None:
    report = summarize(tmp_path)
    assert report["planned_model_turns"] == 72
    assert report["observed"] == 0
    assert report["unobserved"] == 72
    assert report["full_p5_acceptance"] is False
    assert all(x["status"] == "not_observed" for x in report["rows"])


def test_fake_native_trace_digest_rejected_and_no_private_text_leaked(tmp_path: Path) -> None:
    p = tmp_path / "paired/qwen/POS-E-01/trial-1"
    p.mkdir(parents=True)
    private_model_text = "PRIVATE_MODEL_RESULT_SHOULD_NOT_BE_EXPORTED"
    (p / "events.jsonl").write_text(private_model_text)
    (p / "report.json").write_text(
        json.dumps(
            {
                "case_id": "POS-E-01",
                "candidate": "qwen",
                "trial": 1,
                "model_calls": 1,
                "raw_output_exposed": False,
                "event_sha256": "0" * 64,
                "gate": {"action": "block_candidate"},
            }
        )
    )
    import pytest

    with pytest.raises(ValueError):
        summarize(tmp_path)
    proper = json.loads((p / "report.json").read_text())
    proper["event_sha256"] = hashlib.sha256(private_model_text.encode()).hexdigest()
    (p / "report.json").write_text(json.dumps(proper))
    output = summarize(tmp_path)
    assert private_model_text not in json.dumps(output)
    assert output["observed"] == 1
    assert output["unobserved"] == 71


def test_boundary_model_provenance_mismatch_is_never_counted_as_a_success(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "paired/qwen/BOUND-VERSION-NEW/trial-1"
    folder.mkdir(parents=True)
    raw = '{"type":"message_end","message":{"role":"assistant","content":[]}}\n'
    (folder / "events.jsonl").write_text(raw)
    (folder / "report.json").write_text(
        json.dumps(
            {
                "case_id": "BOUND-VERSION-NEW",
                "candidate": "qwen",
                "trial": 1,
                "model_calls": 1,
                "raw_output_exposed": False,
                "native_exit_code": 0,
                "timed_out": False,
                "event_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "research_only": True,
                "research_verdict": "boundary_manual_review_required",
                "observed_model": "unknown-provider/wrong-model",
                "gate": {"action": "block_candidate"},
            }
        )
    )
    score = summarize(tmp_path)
    matches = [
        r
        for r in score["rows"]
        if r["case_id"] == "BOUND-VERSION-NEW" and r["model"] == "qwen" and r["trial"] == 1
    ]
    assert len(matches) == 1
    assert matches[0]["status"] == "invalid_model_provenance"
    assert matches[0]["provider_and_model_verified"] is False
