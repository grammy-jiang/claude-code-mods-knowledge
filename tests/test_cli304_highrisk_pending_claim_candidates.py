"""P1 high-risk *candidate-only* 304 Claims cannot silently inherit 302 approval.

The five pending ideas link to new SHA-observed official docs only as
CONTEXT, not reviewed evidence. A real target-scoped official section review,
new lifecycle decisions and native host permission/lifecycle acceptance are
required before an approved CLI304 Skill can ever be compiled.
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

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-20-cli304-five-highrisk-pending-claims.json"
SOURCE = ROOT / "docs/reports/2026-10-20-cli304-seven-unapproved-source-observations.json"
RELEASE = ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
NATIVE = ROOT / "docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json"
ANCHORS = ROOT / "docs/reports/2026-10-20-cli304-five-candidate-anchor-evidence.json"
SECTIONS = ROOT / "docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json"
IDS = {"K-0070", "K-0071", "K-0072", "K-0073", "K-0074"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exactly_five_pending_304_claims_have_original_immutable_provenance():
    report = json.loads(REPORT.read_text())
    sources = load_registry(ROOT / "sources/registry.json")
    observations = json.loads(SOURCE.read_text())
    pins = {x["source_id"]: x for x in observations["snapshot_metadata_observations"]}
    items = report["pending_claims"]
    assert report["schema_version"] == 1
    assert report["reviewed_target"] == "2.1.304"
    assert report["candidate_total"] == len(items) == 5
    assert report["official_release_notes_sha256"] == sha(RELEASE)
    assert report["native_permission_mock_sha256"] == sha(NATIVE)
    assert report["unapproved_source_observations_sha256"] == sha(SOURCE)
    assert {item["claim_id"] for item in items} == IDS
    expected = {
        "K-0070": "M004",
        "K-0071": "M003",
        "K-0072": "M004",
        "K-0073": "M006",
        "K-0074": "M004",
    }
    for row in items:
        cid = row["claim_id"]
        path = ROOT / "claims" / f"{cid}.json"
        claim = json.loads(path.read_text())
        # The immutable source-candidate report records the ORIGINAL candidate
        # hash; K-0074 later gained a separate reviewed source + decision event.
        if cid == "K-0074":
            exact = next(
                x for x in json.loads(SECTIONS.read_text())["findings"] if x["claim_id"] == cid
            )
            assert row["claim_sha256"] == exact["original_candidate_sha256"]
            assert sha(path) != row["claim_sha256"]
        else:
            assert row["claim_sha256"] == sha(path)
        assert claim["claim_id"] == cid
        assert claim["subject"] == row["subject"]
        assert len(claim["statement"]) >= 170
        assert claim["lifecycle"] == ("reviewed" if cid == "K-0074" else "candidate")
        assert claim["authority"] == "guidance"
        assert claim["verification"] == {
            "source": "reviewed" if cid == "K-0074" else "indexed",
            "runtime": "not-run",
            "runtime_profiles": [],
            "test_evidence": [],
        }
        assert claim["applies_to"]["claude_code"] == (
            {"min_inclusive": "2.1.304", "max_exclusive": "2.1.305"}
        )
        assert claim["applies_to"]["surfaces"] == ["cli"]
        assert claim["decision_record"] == ("decisions/K-0074.json" if cid == "K-0074" else None)
        assert claim["supersedes"] == []
        assert row["status"] == "candidate_only_no_decision"
        assert len(claim["evidence"]) == 1
        evidence = claim["evidence"][0]
        sid = expected[cid]
        assert evidence["source_id"] == sid
        assert evidence["kind"] == "official-doc"
        assert evidence["role"] == ("supports" if cid == "K-0074" else "context")
        assert evidence["commit_sha"] is None
        assert evidence["locator"].startswith(sources[sid]["url"] + "#")
        assert evidence["snapshot_sha256"] == pins[sid]["new_304_observed_html_sha256"]
        assert evidence["snapshot_sha256"] != sources[sid]["snapshot"]["sha256"]
        assert evidence["snapshot_sha256"] == row["official_source_snapshot"]
        assert pins[sid]["snapshot_approval"] == "not-approved"
        assert pins[sid]["semantic_assessment"] == "not-assessed"
        if cid == "K-0074":
            assert (ROOT / f"decisions/{cid}.json").is_file()
        else:
            assert not (ROOT / f"decisions/{cid}.json").exists()
        # A later exact official section REVIEW can exist while the Claim remains
        # candidate/context/not-run. Such a review alone must never promote it.
        revision = ROOT / f"sources/reviews/revisions/{sid}/{evidence['snapshot_sha256']}.json"
        assert revision.is_file() and not revision.is_symlink()
        reviewed = json.loads(revision.read_text())
        assert any(
            section["anchor"] == evidence["locator"].split("#", 1)[1]
            for section in reviewed["sections"]
        )
        assert "no target-304 Claim approval" in reviewed["scope"]


def test_unreviewed_304_cli_skill_generation_and_old_claim_promotion_are_still_blocked():
    sources = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.304", "cli") == []
    assert len(claims) == 74
    for cid in IDS:
        assert claims[cid]["lifecycle"] == ("reviewed" if cid == "K-0074" else "candidate")
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(ROOT, api_version="2.1.304", surface="cli", source_revision="p1")
    report = json.loads(REPORT.read_text())
    assert report["prior_302_approved_claims_untouched"] == 31
    for flag in (
        "firstparty_source_section_review_completed",
        "real_host_permission_callback_verified",
        "full_304_semantics_approved",
        "compiled_304_skill_allowed",
        "historical_decision_ledgers_modified",
        "stable_release_authorized",
    ):
        assert report[flag] is False
    assert report["cli304_new_claims_approved"] == 0


def test_redacted_candidate_report_has_no_private_or_normative_approved_claims():
    raw = REPORT.read_text()
    for secret in (
        "/Users/",
        "/home/",
        "Authorization:",
        "Cookie:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
        "declare module 'claude-code'",
    ):
        assert secret not in raw


def test_candidate_creator_fails_closed_once_claim_ids_exist(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "prepare_cli304_highrisk_claim_candidates",
        ROOT / "scripts/prepare_cli304_highrisk_claim_candidates.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(module.New304CandidateBlocked):
        module.create_candidates()


def test_all_five_candidate_anchors_are_independently_hashed_and_unapproved(monkeypatch):
    report = json.loads(ANCHORS.read_text())
    rows = report["rows"]
    assert report["target"] == "2.1.304"
    assert report["schema_version"] == 1
    assert report["pending_claims"] == 5
    assert report["fresh_official_heading_matches"] == 5
    assert report["version_specific_source_reviews_signed"] == 0
    assert report["approved_304_claims"] == 0
    assert report["real_host_semantics_verified"] is False
    assert report["stable_release_authorized"] is False
    assert {item["claim_id"] for item in rows} == IDS
    for item in rows:
        claim = ROOT / "claims" / (item["claim_id"] + ".json")
        original = json.loads(claim.read_text())
        if item["claim_id"] == "K-0074":
            assert item["claim_sha256"] != sha(claim)  # Frozen old candidate fingerprint.
            earlier = next(
                r for r in json.loads(SECTIONS.read_text())["findings"] if r["claim_id"] == "K-0074"
            )
            assert item["claim_sha256"] == earlier["original_candidate_sha256"]
        else:
            assert item["claim_sha256"] == sha(claim)
        assert item["current_html_sha256"] == original["evidence"][0]["snapshot_sha256"]
        assert item["exact_current_official_locator"] == original["evidence"][0]["locator"]
        assert item["anchor_verified_against_html_and_markdown"] is True
        assert item["current_html_heading_tag"] in ("h2", "h3", "h4")
        assert 3 <= len(item["current_html_heading"]) < 120
        assert len(item["current_markdown_sha256"]) == 64
        assert item["first_party_section_semantics_fully_reviewed"] is False
        assert item["claim_approved"] is False

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "audit_cli304_five_candidate_source_anchors",
        ROOT / "scripts/audit_cli304_five_candidate_source_anchors.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(module.CandidateAnchorBlocked):
        module.audit(ROOT / "sources/snapshots")  # No user/private full official docs in repo.
