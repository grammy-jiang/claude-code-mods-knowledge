"""Codex V3 three-factor experiment: frozen user prompts and source provenance."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_p5_codex_ab_native as adapter  # noqa: E402
import run_p5_codex_evidence_ab_batch as queue  # noqa: E402
import run_p5_codex_evidence_ab_case as native  # noqa: E402
import score_p5_codex_evidence_ab as scoring  # noqa: E402

from mods_knowledge.claims import load_claims  # noqa: E402
from mods_knowledge.evidence_delivery import make_verified_task_context  # noqa: E402
from mods_knowledge.registry import load_registry  # noqa: E402
from mods_knowledge.task_evidence import select_task_evidence  # noqa: E402


@pytest.fixture(scope="module")
def claims() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


@pytest.fixture(scope="module")
def cases() -> dict:
    return {x["id"]: x for x in json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]}


def test_exact_frozen_skill_and_natively_separate_context_field() -> None:
    plan = json.loads(native.MANIFEST.read_text())
    assert plan["frozen_skill_sha256"] == adapter.SKILL_SHA
    assert plan["model"] == "gpt-6.1-sol"
    assert plan["effort"] == "medium"
    assert plan["web_search"] == "disabled"
    assert plan["conditions"] == ["A_v3", "B_context", "C_context_gate"]
    assert plan["native_turns_planned"] == 108
    assert plan["repetitions"] == 3
    assert len(plan["case_ids"]) == 12
    assert (
        hashlib.sha256((ROOT / plan["source_file"]).read_bytes()).hexdigest()
        == plan["source_sha256"]
    )
    source = (ROOT / "scripts/run_p5_codex_ab_native.py").read_text()
    assert 'thread_params["developerInstructions"] = developer_instructions' in source
    assert '"input": [{"type": "text", "text": case["prompt"]}]' in source
    assert '"HOME": str(private_agent_home)' in source
    assert '"CODEX_HOME": str(private_agent_home)' in source
    assert 'web_search="disabled"' in source


def test_balanced_108_cells_and_no_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs = queue.expected_cells()
    assert len(jobs) == len(set(jobs)) == 108
    frozen = json.loads(native.MANIFEST.read_text())["case_ids"]
    assert set(jobs) == {
        (condition, trial, case_id)
        for condition in native.CONDITIONS
        for trial in (1, 2, 3)
        for case_id in frozen
    }
    monkeypatch.setattr(queue, "PRIVATE", tmp_path)
    assert queue.observed_native(("A_v3", 1, frozen[0])) is None
    incomplete = tmp_path / "cases/A_v3" / frozen[0] / "trial-1"
    incomplete.mkdir(parents=True)
    with pytest.raises(queue.EvidenceRunError):
        queue.observed_native(("A_v3", 1, frozen[0]))


def test_version_boundary_never_becomes_deliverable(claims: dict, cases: dict) -> None:
    for cid in ("BOUND-VERSION-NEW", "BOUND-VERSION-OLD", "BOUND-SURFACE", "BOUND-HISTORY"):
        case = cases[cid]
        selection = select_task_evidence(case["prompt"], claims, version="2.1.296")
        assert selection["ready"] is False
        verdict = native._postflight_gate(
            case,
            raw_answer="I would not implement that unreviewed Mod API.",
            selection=selection,
            model_resolved=True,
            skill_read=True,
            native_completed=True,
            claims=claims,
        )
        assert verdict["blocked"] is True
        assert "unsupported_boundary_preflight" in verdict["reasons"]
        assert verdict["native_mod_semantics_approved"] is False
        assert verdict["original_model_text_delivered_to_user"] is False


def test_negative_controls_do_not_get_skill_evidence(claims: dict, cases: dict) -> None:
    for cid in ("NEG-TYPESCRIPT", "NEG-PYTHON", "NEG-MCP", "NEG-LEGACY-HOOK"):
        selection = select_task_evidence(cases[cid]["prompt"], claims, version="2.1.296")
        assert selection["intent"] == "unrelated" and not selection["ready"]
        verdict = native._postflight_gate(
            cases[cid],
            raw_answer="This is an unrelated programming control.",
            selection=selection,
            model_resolved=True,
            skill_read=False,
            native_completed=True,
            claims=claims,
        )
        assert verdict["allowed_structural_candidate_only"] is True
        wrong = native._postflight_gate(
            cases[cid],
            raw_answer="This is an unrelated programming control.",
            selection=selection,
            model_resolved=True,
            skill_read=True,
            native_completed=True,
            claims=claims,
        )
        assert wrong["blocked"] is True


def test_p3_never_fixes_a_missing_claim_by_rewriting_model_text(claims: dict, cases: dict) -> None:
    cid = "POS-S-02"
    item = cases[cid]
    selected = select_task_evidence(item["prompt"], claims, version="2.1.296")
    context = make_verified_task_context(selected)
    assert "K-0012" in context
    bad = native._postflight_gate(
        item,
        raw_answer="The state can be reinitialized after branch resume.",
        selection=selected,
        model_resolved=True,
        skill_read=True,
        native_completed=True,
        claims=claims,
    )
    assert bad["blocked"] is True
    assert "missing_exact_ssot_task_claim_or_url" in bad["reasons"]
    clean = native._postflight_gate(
        item,
        raw_answer=context,
        selection=selected,
        model_resolved=True,
        skill_read=True,
        native_completed=True,
        claims=claims,
    )
    assert clean["allowed_structural_candidate_only"] is True
    assert clean["native_mod_semantics_approved"] is False


def test_missing_original_results_cannot_be_published(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(scoring, "PRIVATE", tmp_path)
    results = scoring.score()
    assert results["verified_original_native_turns"] == 0
    assert results["unobserved_original_native_turns"] == 108
    with pytest.raises(scoring.CodexABEvidentiaryError):
        scoring.score(complete=True)
