"""P0 audit is offline, stage-specific and exposes no private transcript."""

from __future__ import annotations

import copy
import json

import pytest

from scripts.audit_p0_knowledge_funnel import CHAT, NATIVE, summarize


@pytest.fixture(scope="module")
def reports() -> tuple[dict, dict]:
    return (json.loads(NATIVE.read_text()), json.loads(CHAT.read_text()))


def test_existing_native_and_chat_baseline_is_reproducible(reports: tuple[dict, dict]) -> None:
    result = summarize(*reports)
    native = result["native"]
    positive = native["positive"]
    assert native["total_native_turns"] == 252
    assert positive == {
        "attempts": 84,
        "main_skill_read_observed": 76,
        "exact_claim_source_structural_pass": 39,
        "selected_evidence_file_read_observed": 1,
        "native_completed": 84,
    }
    assert native["negative"]["attempts"] == 84
    assert native["boundary"]["attempts"] == 84
    chat = result["chat_mode"]
    assert chat["automatic_positive_attempts"] == 24
    assert chat["automatic_positive_plugin_skill_reads"] == 0
    assert chat["explicit_control_attempts"] == 6
    assert chat["explicit_control_plugin_skill_reads"] == 6
    assert result["new_model_turns_run"] == 0


def test_duplicate_or_unmatched_trials_are_not_silently_counted(
    reports: tuple[dict, dict],
) -> None:
    native, chat = reports
    copy_native = copy.deepcopy(native)
    copy_native["rows"].append(copy_native["rows"][0])
    copy_native["actual_native_attempts"] += 1
    with pytest.raises(ValueError, match="duplicate"):
        summarize(copy_native, chat)
    copy_native["actual_native_attempts"] -= 1
    with pytest.raises(ValueError, match="count"):
        summarize(copy_native, chat)


def test_structural_citations_are_not_conflated_with_selected_file_reads(
    reports: tuple[dict, dict],
) -> None:
    native, chat = reports
    result = summarize(native, chat)
    positive = result["native"]["positive"]
    assert positive["exact_claim_source_structural_pass"] > positive["selected_evidence_file_read_observed"]
    assert positive["selected_evidence_file_read_observed"] <= positive["main_skill_read_observed"]


def test_no_private_transcript_or_semantic_success_claims(
    reports: tuple[dict, dict],
) -> None:
    result = summarize(*reports)
    serialized = json.dumps(result)
    assert result["raw_private_data_read"] is False
    assert result["native"]["boundary"]["verified_safe_answers"] is None
    assert "prompt" not in serialized
    assert "conversation_sha256" not in serialized
    assert "semantic_correctness_of_generated_code" in result["not_measured"]
