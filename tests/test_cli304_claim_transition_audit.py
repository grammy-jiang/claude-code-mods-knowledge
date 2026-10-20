"""No 302 approved Claim silently becomes a 304 approved Mod API Claim.

The public 31-row review is a deterministic recomputation from original
immutable K-Claims, approval events and first-party release/type/host mock
evidence. It does NOT promote a single 304 Claim.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

SPEC = importlib.util.spec_from_file_location(
    "cli304_claim_transition_audit",
    Path(__file__).resolve().parents[1] / "scripts/audit_cli304_claim_transition.py",
)
assert SPEC and SPEC.loader
transition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transition)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-20-cli304-31-claim-preapproval-audit.json"
POLICY = ROOT / "evals/cli304_claim_transition_triage.json"


def test_all_31_review_questions_recompute_exactly_from_current_ssot():
    report = json.loads(REPORT.read_text())
    assert transition.audit(ROOT) == report
    assert report["approved_302_claims_scanned"] == 31
    assert report["approved_304_claims_now"] == 0
    assert report["human_304_claim_review_completed"] is False
    assert report["target_304_skill_compilation_authorized"] is False
    assert report["target_304_model_host_qualification_completed"] is False
    assert report["full_46_chat_mode_304_qualified"] is False
    assert report["stable_release_authorized"] is False
    assert report["original_302_claim_or_decision_mutated"] is False
    assert report["review_plan_sha256"] == hashlib.sha256(POLICY.read_bytes()).hexdigest()


def test_each_original_claim_and_approval_decision_is_exactly_fingerprinted():
    report = json.loads(REPORT.read_text())
    items = report["claims"]
    assert len(items) == 31
    assert len({x["original_reviewed_claim_id"] for x in items}) == 31
    assert {x["area"] for x in items} == set("ESTQPU")
    assert {x["review_lane"] for x in items} == transition.REVIEW_LANES
    for row in items:
        cid = row["original_reviewed_claim_id"]
        assert (
            row["original_claim_sha256"]
            == hashlib.sha256((ROOT / f"claims/{cid}.json").read_bytes()).hexdigest()
        )
        assert (
            row["original_decision_sha256"]
            == hashlib.sha256((ROOT / f"decisions/{cid}.json").read_bytes()).hexdigest()
        )
        assert row["original_302_scope"] == "[2.1.302, 2.1.303)"
        assert row["new_304_claim_created_or_approved"] is False
        assert row["target_304_approval"] == "NOT_APPROVED_NEEDS_NEW_TARGET_REVIEW"
        assert 40 <= len(row["specific_review_question"]) <= 260
        assert all(
            url.startswith("https://code.claude.com/docs/en/plugins/mods/")
            for url in row["original_302_exact_official_urls"]
        )
    assert report["review_lane_counts"] == {
        "first_party_delta_touchpoint": 8,
        "fresh_target_official_review_required": 14,
        "known_302_source_type_conflict_blocking_promotion": 1,
        "native_mock_subset_not_full_host": 8,
    }


def test_first_party_304_types_and_permission_proof_are_nonpromoting():
    release = json.loads(
        (
            ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
        ).read_text()
    )
    core = json.loads(
        (ROOT / "docs/reports/2026-10-20-cli304-official-core-type-compatibility.json").read_text()
    )
    native = json.loads(
        (
            ROOT / "docs/reports/2026-10-20-cli304-official-permission-native-sandbox.json"
        ).read_text()
    )
    assert release["source_review_status"] == (
        "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI304_API_CLAIMS"
    )
    assert {x["kind"] for x in release["releases"][1]["relevant_mods_deltas"]} == (
        transition.KNOWN_304_DIFFERENCES
    )
    assert core["same_source_302_rejected_and_304_accepted"] is True
    assert core["new_304_core_types_sha256"] != core["reference_302_core_types_sha256"]
    assert native["real_user_approval_dialog_tested"] is False
    assert native["stable_release_authorized"] is False


def test_no_304_target_build_from_unreviewed_302_source():
    sources = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert not approved_claims(claims, "2.1.304", "cli")
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(
            ROOT,
            api_version="2.1.304",
            surface="cli",
            source_revision="unreviewed-304-must-fail",
        )


def test_k0068_source_stays_immutable_but_both_compiled_evidence_surfaces_warn():
    original = json.loads((ROOT / "claims/K-0068.json").read_text())
    assert original["lifecycle"] == "approved"
    assert "console.log(" in original["statement"]
    assert original["applies_to"]["claude_code"] == {
        "min_inclusive": "2.1.302",
        "max_exclusive": "2.1.303",
    }
    for version in ("2.1.296", "2.1.302"):
        built = compile_knowledge(
            ROOT,
            api_version=version,
            surface="cli",
            source_revision="k0068-type-conflict-diagnostic",
        )
        for name in ("references/events.md", "references/claim-evidence.md"):
            text = built[f"common/claude-code-mods-development/{name}"].decode()
            has_warning = (
                "Do not copy it into runnable Mods" in text
                or "not copy-ready executable code" in text
            )
            assert has_warning == (version == "2.1.302")
            if version == "2.1.302":
                assert "console.log(" in text
                assert "$.ui.log" in text
                assert "TS2584" in text or "did not typecheck" in text
                assert "K-0068" in text


def test_partial_triage_matrix_is_rejected_before_304_approval(monkeypatch):
    policy = json.loads(POLICY.read_text())
    del policy["decisions"]["K-0068"]
    original = transition._load

    def patched(root: Path, relative: str):
        return policy if relative == transition.POLICY else original(root, relative)

    monkeypatch.setattr(transition, "_load", patched)
    with pytest.raises(transition.TransitionBlocked):
        transition.audit(ROOT)


def test_renaming_known_k0068_conflict_does_not_make_it_compatible(monkeypatch):
    policy = json.loads(POLICY.read_text())
    policy["decisions"]["K-0068"]["review_lane"] = "native_mock_subset_not_full_host"
    original = transition._load

    def patched(root: Path, relative: str):
        return policy if relative == transition.POLICY else original(root, relative)

    monkeypatch.setattr(transition, "_load", patched)
    with pytest.raises(transition.TransitionBlocked):
        transition.audit(ROOT)


def test_fabricated_304_approved_claims_do_not_pass_review(monkeypatch):
    original = transition.approved_claims

    def incorrect_approval(claims, version: str, surface: str):
        if version == "2.1.304":
            return original(claims, "2.1.302", surface)
        return original(claims, version, surface)

    monkeypatch.setattr(transition, "approved_claims", incorrect_approval)
    with pytest.raises(transition.TransitionBlocked):
        transition.audit(ROOT)


def test_public_review_never_exposes_private_model_or_user_files():
    text = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "TASK_ID:",
        "Plugin_",
        "Cookie:",
        "Authorization:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in text
