"""Codex Sol/medium comparison cannot claim semantic pass or fabricate trials."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_p5_codex_paired import FIXTURES, MODEL, frozen  # noqa: E402
from score_p5_codex_paired import grade, summarize  # noqa: E402


def test_freeze_same_p5_source_and_model_not_maximal() -> None:
    manifest = frozen()
    assert (
        hashlib.sha256((ROOT / "evals/p4_cases.json").read_bytes()).hexdigest()
        == manifest["source_sha256"]
    )
    assert len(set(manifest["case_ids"])) == 12
    assert manifest["repetitions"] == 3
    assert manifest["expected_total_model_trials"] == 72
    assert MODEL == "gpt-6.1-sol"
    assert set(FIXTURES) == {"NEG-PYTHON", "NEG-MCP", "NEG-TYPESCRIPT", "NEG-LEGACY-HOOK"}


def accepted() -> dict:
    return {
        "raw_output_exposed": False,
        "raw_transcript_private": True,
        "evidence": {
            "state": "native_turn_recorded",
            "model_server_resolved": "gpt-6.1-sol",
            "effort_server_resolved": "medium",
            "model_provenance": "same-thread-app-server-response+thread-read",
            "prompt_matched": True,
            "agent_completed": True,
            "answer_present": True,
            "skill_loaded": True,
            "source_verdict": "pass",
            "risk_flags": [],
            "manual_review_flags": [],
        },
    }


def test_positive_source_pass_is_only_structural() -> None:
    sample = accepted()
    assert grade(sample, "positive") == "positive_source_structure_only"
    sample["evidence"]["source_verdict"] = "fail"
    assert grade(sample, "positive") == "positive_exact_claim_or_source_missing"
    sample["evidence"]["skill_loaded"] = False
    assert grade(sample, "positive") == "positive_skill_not_loaded"


def test_wrong_model_effort_or_prompt_fails_closed() -> None:
    for key, val in (
        ("model_server_resolved", "gpt-6-astra"),
        ("effort_server_resolved", "max"),
        ("prompt_matched", False),
    ):
        sample = accepted()
        sample["evidence"][key] = val
        assert grade(sample, "positive") == "model_or_prompt_provenance_failed"


def test_negative_and_boundary_classification_conservative() -> None:
    sample = accepted()
    assert grade(sample, "negative") == "negative_false_skill_activation"
    sample["evidence"]["skill_loaded"] = False
    assert grade(sample, "negative") == "negative_nonactivation_observed"
    sample["evidence"]["skill_loaded"] = True
    assert grade(sample, "boundary") == "boundary_manual_review_required"
    sample["evidence"]["manual_review_flags"] = ["unreviewed-version-implementation-present"]
    assert grade(sample, "boundary") == "boundary_scope_violated"
    sample["evidence"]["skill_loaded"] = False
    assert grade(sample, "boundary") == "boundary_scope_violated"


def test_incomplete_turns_and_private_exposure_never_pass() -> None:
    sample = accepted()
    sample["evidence"]["state"] = "blocked_or_incomplete"
    assert grade(sample, "positive") == "incomplete_or_tool_failure"
    sample = accepted()
    sample["raw_output_exposed"] = True
    assert grade(sample, "positive") == "invalid_or_exposed_evidence"


def test_missing_native_evidence_is_not_a_model_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import score_p5_codex_paired as scorer

    monkeypatch.setattr(scorer, "PRIVATE", tmp_path)
    summary = summarize()
    assert summary["codex_observed"] == 0
    assert summary["codex_unobserved"] == 36
    assert all(x["status"] == "not_observed" for x in summary["rows"])
    assert summary["full_p5_acceptance"] is False
    assert summary["native_mod_runtime_verified"] is False


def test_mutated_private_event_sha_never_laundered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import score_p5_codex_paired as scorer

    monkeypatch.setattr(scorer, "PRIVATE", tmp_path)
    dir = tmp_path / "paired/gpt-6.1-sol/POS-E-01/trial-1"
    dir.mkdir(parents=True)
    wire = dir / "native-wire.jsonl"
    wire.write_text(json.dumps({"id": 2, "result": {}}))
    doc = {
        "case_id": "POS-E-01",
        "trial": 1,
        "candidate": "codex",
        "model_requested": MODEL,
        "effort_requested": "medium",
        "source_revision": "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e",
        "original_case_file_sha256": frozen()["source_sha256"],
        "raw_output_exposed": False,
        "semantic_review_complete": False,
        "native_mod_runtime_verified": False,
        "evidence": accepted()["evidence"],
        "native_wire_sha256": "0" * 64,
    }
    (dir / "report.json").write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        summarize()
