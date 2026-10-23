"""Fresh CLI304 official document observations are NOT Claim approvals.

All original 302 source/decision evidence remains valid. New HTML metadata
must stay immutable, SHA-indexed and in the `not-assessed/not-approved` state
until an independent first-party section review is recorded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import (
    _is_pinned_official_support,
    _known_observations,
    approved_claims,
    load_claims,
)
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry
from mods_knowledge.storage import verify_snapshot_store

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-20-cli304-seven-unapproved-source-observations.json"
MATRIX = ROOT / "docs/reports/2026-10-20-cli304-p1-all31-fresh-primary-anchor-matrix.json"
STORE = ROOT / "sources/snapshots"
REGISTRY_FILE = ROOT / "sources/registry.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_seven_fresh_cli304_source_observations_are_sha_indexed_and_explicitly_unapproved():
    data = json.loads(REPORT.read_text())
    matrix = json.loads(MATRIX.read_text())
    sources = load_registry(REGISTRY_FILE)
    indexed = json.loads((STORE / "index.json").read_text())
    assert data["schema_version"] == 1
    assert data["capture_day"] == "2026-10-20"
    assert data["target_version_under_review"] == "2.1.304"
    assert data["prior_approved_target_unchanged"] == "2.1.302"
    assert data["first_party_documents_recorded_unapproved"] == 7
    assert data["prior_registry_sha256_unchanged"] == digest(REGISTRY_FILE)
    assert indexed["schema_version"] == 1
    assert data["snapshot_integrity_verified"] is True
    assert len(data["snapshot_metadata_observations"]) == 7
    assert {row["source_id"] for row in data["snapshot_metadata_observations"]} == {
        row["source_id"] for row in matrix["source_pages"]
    }
    pages = {row["source_id"]: row for row in matrix["source_pages"]}
    for row in data["snapshot_metadata_observations"]:
        source = sources[row["source_id"]]
        previous = pages[row["source_id"]]
        assert row["official_url"] == source["url"] == previous["official_url"]
        assert row["original_302_registry_pin_sha256"] == (source["snapshot"]["sha256"])
        assert row["new_304_observed_html_sha256"] == previous["fresh_html_sha256"]
        assert row["snapshot_approval"] == "not-approved"
        assert row["semantic_assessment"] == "not-assessed"
        assert row["historical_registry_pin_preserved"] is True
        assert row["current_snapshot_metadata_only_not_a_reviewed_304_claim"] is True
        assert row["observed_at"].startswith("2026-10-20T")
        entry = indexed["sources"][row["source_id"]]
        # The 304 revision must remain SHA-indexed in append-only history,
        # but newer official captures may legitimately become current.
        assert row["new_304_observed_html_sha256"] in entry["revisions"]
        assert entry["current"] in entry["revisions"]
        assert row["original_302_registry_pin_sha256"] in entry["revisions"]
        meta = (
            STORE / "metadata" / row["source_id"] / (row["new_304_observed_html_sha256"] + ".json")
        )
        assert row["new_304_metadata_sha256"] == digest(meta)
        assert entry["revisions"][row["new_304_observed_html_sha256"]]["metadata_sha256"] == digest(
            meta
        )
        record = json.loads(meta.read_text())
        assert record["source_id"] == row["source_id"]
        assert record["url"] == row["official_url"]
        assert record["content_sha256"] == row["new_304_observed_html_sha256"]
        assert record["semantic_status"] == "not-assessed"
        assert record["approval_status"] == "not-approved"
        assert record["hash_basis"] == "raw-http-response-bytes"
        assert record["etag"] is None and record["last_modified"] is None
    assert verify_snapshot_store(STORE) == []


def test_new_html_snapshot_revision_cannot_be_used_as_approved_304_claim_source():
    indexed = _known_observations(STORE)
    sources = load_registry(REGISTRY_FILE)
    data = json.loads(REPORT.read_text())
    for row in data["snapshot_metadata_observations"]:
        sid = row["source_id"]
        sha = row["new_304_observed_html_sha256"]
        source = sources[sid]
        assert sha != source["snapshot"]["sha256"]
        # A new HTTP digest alone is NOT a review attestation. Later independent
        # review of some exact sections is allowed, but unknown headings and
        # new Claim publication must still fail closed.
        revision = ROOT / f"sources/reviews/revisions/{sid}/{sha}.json"
        if sid in {"M003", "M004", "M006"}:
            assert revision.is_file() and not revision.is_symlink()
            assert "CLI 2.1.304" in json.loads(revision.read_text())["scope"]
        else:
            assert not revision.exists()
        evidence = {
            "source_id": sid,
            "kind": "official-doc",
            "role": "supports",
            "locator": source["url"] + "#not-yet-reviewed-new-api",
            "snapshot_sha256": sha,
        }
        assert (
            _is_pinned_official_support(
                evidence, source, STORE, indexed, required_version="2.1.304"
            )
            is False
        )


def test_old_302_approval_remains_valid_and_304_skill_stays_blocked():
    sources = load_registry(REGISTRY_FILE)
    claims = load_claims(ROOT / "claims", sources, STORE, ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.304", "cli") == []
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(ROOT, api_version="2.1.304", surface="cli", source_revision="p1")
    data = json.loads(REPORT.read_text())
    for field in (
        "original_html_or_markdown_text_committed_to_git",
        "new_304_skills_or_plugin_published",
        "existing_302_claims_or_decision_records_changed",
        "full_304_semantic_compatibility_verified",
        "stable_release_authorized",
    ):
        assert data[field] is False
    assert data["revision_review_attestations_created"] == 0
    assert data["approved_304_claims"] == 0


def test_unindexed_or_tampered_new_observation_metadata_fails_closed(tmp_path):
    # A bounded self-contained integrity check; do not mutate the shared source tree.
    import shutil

    destination = tmp_path / "snapshots"
    shutil.copytree(STORE, destination)
    assert verify_snapshot_store(destination) == []
    data = json.loads(REPORT.read_text())
    first = data["snapshot_metadata_observations"][0]
    meta = (
        destination
        / "metadata"
        / first["source_id"]
        / (first["new_304_observed_html_sha256"] + ".json")
    )
    record = json.loads(meta.read_text())
    record["approval_status"] = "approved"
    meta.write_text(json.dumps(record, sort_keys=True))
    assert verify_snapshot_store(destination)


def test_public_record_excludes_raw_markup_and_private_machine_material():
    report = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Cookie:",
        "Authorization:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
        "<html",
        "declare module 'claude-code'",
    ):
        assert forbidden not in report
