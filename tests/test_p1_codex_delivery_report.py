"""Frozen public P1 A/B report contract, independent of raw model transcripts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.score_p1_codex_delivery import summarize_rows

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def published() -> tuple[dict, dict]:
    manifest = json.loads((ROOT / "evals/p1_codex_delivery_ab.json").read_text())
    report = json.loads(
        (ROOT / "docs/reports/2026-10-17-p1-codex-knowledge-delivery-ab.json").read_text()
    )
    return manifest, report


def test_native_p1_a_b_evidence_integrity_and_counts(published: tuple[dict, dict]) -> None:
    plan, report = published
    assert report["source_sha256"] == plan["source_sha256"]
    assert report["frozen_skill_sha256"] == plan["frozen_skill_sha256"]
    assert report["real_native_turns"] == plan["planned_trials"] == 24
    assert report["arms"] == summarize_rows(report["rows"], plan)
    a = report["arms"]["file_only"]
    b = report["arms"]["preload"]
    assert a["positive_exact_claim_source_structure_pass"] == 5
    assert b["positive_exact_claim_source_structure_pass"] == 7
    assert b["positive_developer_payload_thread_accepted"] == 8
    assert a["positive_developer_payload_thread_accepted"] == 0
    assert a["positive_selected_pack_file_reads"] == 0
    assert b["positive_selected_pack_file_reads"] == 1
    assert a["negative_completed_without_mod_skill"] == 4
    assert b["negative_completed_without_mod_skill"] == 4
    assert a["native_completed"] == b["native_completed"] == 12
    assert b["negative_wrongly_injected"] == a["negative_wrongly_injected"] == 0
    assert report["generated_mod_code_semantics_verified"] is False
    assert report["stable_release_qualified"] is False
    assert report["chatgpt_chat_mode_plugin_activation_verified"] is False
    assert report["pi_native_payload_accepted"] is None


def test_invalid_matrix_does_not_pass_as_finished_a_b(published: tuple[dict, dict]) -> None:
    plan, report = published
    missing = copy.deepcopy(report["rows"][:-1])
    with pytest.raises(ValueError):
        summarize_rows(missing, plan)
    repeated = copy.deepcopy(report["rows"])
    repeated[-1] = repeated[0]
    with pytest.raises(ValueError):
        summarize_rows(repeated, plan)


def test_exactly_only_in_scope_cases_get_p1_injection(published: tuple[dict, dict]) -> None:
    plan, report = published
    assert set(plan["arms"]) == {"file_only", "preload"}
    for r in report["rows"]:
        expected = r["category"] == "positive" and r["arm"] == "preload"
        assert (r["payload_sha256"] is not None) is expected
        assert r["thread_accepted_evidence"] is expected
        assert r["model_verified"] is True
        assert len(r["native_wire_sha256"]) == 64
        assert r["native_completed"] is True
    text = json.dumps(report)
    for private_field in ("user_prompt", "model_answer", "conversation_id", "account_id", "private_path"):
        assert private_field not in text
