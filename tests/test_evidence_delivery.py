"""Static exact provenance of native Skill evidence context injection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import load_claims
from mods_knowledge.evidence_delivery import evidence_fingerprint, make_verified_task_context
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import EvidenceSelectionError, select_task_evidence

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def claims() -> dict:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def test_frozen_positives_produce_short_source_pinned_native_context(claims: dict) -> None:
    all_cases = {
        c["id"]: c for c in json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    }
    frozen = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())["case_ids"]
    for item in (all_cases[cid] for cid in frozen):
        if item["category"] != "positive":
            continue
        selected = select_task_evidence(item["prompt"], claims, version="2.1.296")
        assert selected["ready"]
        evidence = make_verified_task_context(selected)
        assert "Claude Code CLI 2.1.296" in evidence
        assert len(evidence) <= 6200
        assert item["prompt"] not in evidence
        for cid in item["expected_claim_ids"]:
            assert cid in evidence
        for entry in selected["claims"]:
            for official in entry["official_urls"]:
                assert official in evidence
        assert evidence_fingerprint(evidence) == hashlib.sha256(evidence.encode()).hexdigest()


def test_native_skill_context_never_injects_into_unrelated_or_boundary(claims: dict) -> None:
    all_cases = {
        c["id"]: c for c in json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    }
    frozen = json.loads((ROOT / "evals/p5_pi_auto_12x3.json").read_text())["case_ids"]
    for item in (all_cases[cid] for cid in frozen):
        if item["category"] == "positive":
            continue
        selected = select_task_evidence(item["prompt"], claims, version="2.1.296")
        with pytest.raises(EvidenceSelectionError):
            make_verified_task_context(selected)


def test_malformed_context_or_injection_rejected() -> None:
    for fake in ("", "oversized" * 800, None):
        with pytest.raises(EvidenceSelectionError):
            evidence_fingerprint(fake)
    with pytest.raises(EvidenceSelectionError):
        make_verified_task_context({"ready": True, "intent": "unrelated", "claims": []})
