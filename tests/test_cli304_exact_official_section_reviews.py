"""New 304 Markdown SECTION reviews do not approve any new version Claims.

Private HTML/Markdown is SHA-pinned but never distributed in the repository.
The review is a declared reviewer attribution, NOT cryptographic authority.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from mods_knowledge.claims import (
    _is_pinned_official_support,
    _known_observations,
    approved_claims,
    load_claims,
)
from mods_knowledge.registry import load_registry
from mods_knowledge.review_evidence import validate_official_review

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json"
ORIGINAL = ROOT / "docs/reports/2026-10-20-cli304-five-candidate-anchor-evidence.json"
SNAP = ROOT / "sources/snapshots"


def sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def test_five_exact_bounded_current_sections_and_semantic_review_lanes():
    doc = json.loads(REPORT.read_text())
    old = {r["claim_id"]: r for r in json.loads(ORIGINAL.read_text())["rows"]}
    assert doc["schema_version"] == 1
    assert doc["review_target"] == "2.1.304"
    assert doc["source_sections_reviewed"] == 5
    assert doc["unique_current_official_source_revisions"] == 3
    assert doc["target_304_claims_approved"] == 0
    assert doc["candidate_304_claims_unchanged"] == 5
    assert set(doc["review_record_hashes"]) == {"M003", "M004", "M006"}
    assert doc["firstparty_document_semantics_directly_sufficient_for_full_release_delta"] == 0
    assert doc["firstparty_document_supports_narrow_catch_guidance"] == 1
    assert doc["source_context_only_pending_release_delta"] == 4
    assert doc["real_host_permission_dialog_verified"] is False
    assert doc["real_host_reload_and_skip_transcript_verified"] is False
    assert doc["original_registry_pins_unchanged"] is True
    assert doc["public_source_text_exported"] is False
    assert doc["reviewer_identity_cryptographically_attested"] is False
    assert datetime.fromisoformat(doc["reviewed_at"].replace("Z", "+00:00")).utcoffset() is not None
    rows = doc["findings"]
    assert len(rows) == 5
    assert {row["claim_id"] for row in rows} == set(old)
    for row in rows:
        original = old[row["claim_id"]]
        assert row["original_candidate_sha256"] == original["claim_sha256"]
        assert row["source_html_sha256"] == original["current_html_sha256"]
        assert row["source_markdown_sha256"] == original["current_markdown_sha256"]
        assert row["locator"] == original["exact_current_official_locator"]
        assert row["source_section_reviewed"] is True
        assert row["native_real_host_verified"] is False
        assert row["full_new_release_behavior_verified"] is False
        assert row["claim_lifecycle_unchanged_candidate"] is True
        assert row["line_start"] >= 1
        assert row["line_end"] > row["line_start"]
        assert row["line_end"] - row["line_start"] < 230
        assert len(row["section_sha256"]) == 64
    assert Counter(r["semantic_determination"] for r in rows) == {
        "context_only_release_delta": 4,
        "direct_documented_behavior_narrow_native_subset": 1,
    }
    assert [r["claim_id"] for r in rows if r["semantic_determination"].startswith("direct")] == [
        "K-0074"
    ]


def test_separate_revision_attestations_are_checkable_without_overwriting_old_registry():
    evidence = json.loads(REPORT.read_text())
    registry = load_registry(ROOT / "sources/registry.json")
    source_index = _known_observations(SNAP)
    for sid, entry in evidence["review_record_hashes"].items():
        path = ROOT / entry["review_path"]
        assert path.is_file() and not path.is_symlink()
        assert entry["review_sha256"] == sha(path)
        data = json.loads(path.read_text())
        source = registry[sid]
        assert data["source_id"] == sid
        assert data["html_url"] == source["url"]
        assert data["markdown_url"] == source["url"] + ".md"
        assert data["reviewed_at"] == evidence["reviewed_at"]
        assert "CLI 2.1.304" in data["scope"]
        assert "no target-304 Claim approval" in data["scope"]
        assert data["reviewer"].startswith("ChatGPT-CLI304")
        assert data["html_sha256"] in source_index[sid]["revisions"]
        assert data["html_sha256"] != source["snapshot"]["sha256"]
        assert len(data["markdown_sha256"]) == 64
        assert data["schema_version"] == 1
        assert data["sections"]
        revised_source = dict(source)
        revised_source["snapshot"] = {
            **source["snapshot"],
            "sha256": data["html_sha256"],
            "checked_at": data["reviewed_at"],
        }
        for section in data["sections"]:
            assert len(section["section_sha256"]) == 64
            assert validate_official_review(
                revised_source,
                data["html_sha256"],
                section["anchor"],
                ROOT / "sources/reviews",
                SNAP,
                revision_review_file=path,
            )
            hypothetical = {
                "source_id": sid,
                "locator": source["url"] + "#" + section["anchor"],
                "snapshot_sha256": data["html_sha256"],
                "kind": "official-doc",
                "role": "supports",
            }
            assert _is_pinned_official_support(
                hypothetical, source, SNAP, source_index, required_version="2.1.304"
            )
        # Never claim an unrelated current 304 section was reviewed.
        missing = {
            "source_id": sid,
            "locator": source["url"] + "#definitely-not-reviewed-304",
            "snapshot_sha256": data["html_sha256"],
            "kind": "official-doc",
            "role": "supports",
        }
        assert not _is_pinned_official_support(
            missing, source, SNAP, source_index, required_version="2.1.304"
        )


def test_reviewed_k0074_is_not_approved_and_four_others_remain_candidate():
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, SNAP, ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.304", "cli") == []
    for i in range(70, 75):
        claim = claims[f"K-{i:04d}"]
        if i == 74:
            assert claim["lifecycle"] == "reviewed"
            assert claim["verification"]["source"] == "reviewed"
            assert claim["decision_record"] == "decisions/K-0074.json"
            assert all(e["role"] == "supports" for e in claim["evidence"])
        else:
            assert claim["lifecycle"] == "candidate"
            assert claim["verification"]["source"] == "indexed"
            assert claim["decision_record"] is None
            assert all(e["role"] == "context" for e in claim["evidence"])
        assert claim["verification"]["runtime"] == "not-run"


def test_private_docs_absent_or_modified_cannot_be_replayed_as_first_party_304(
    tmp_path, monkeypatch
):
    # Production script import inside pytest needs the project src and script path.
    spec = importlib.util.spec_from_file_location(
        "review_cli304_exact_official_sections",
        ROOT / "scripts/review_cli304_exact_official_sections.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(module.Section304Blocked):
        module.audit(tmp_path)
    with pytest.raises(module.Section304Blocked):
        module.audit(ROOT / "sources/snapshots")


def test_public_source_review_records_are_plain_provenance_not_raw_docs_or_credentials():
    report = json.loads(REPORT.read_text())
    files = [REPORT] + [
        ROOT / data["review_path"] for data in report["review_record_hashes"].values()
    ]
    for file in files:
        text = file.read_text()
        for forbidden in (
            "/Users/",
            "/home/",
            "Authorization:",
            "Cookie:",
            "Plugin_",
            "TASK_ID:",
            "chatgpt.com/c/",
            "raw_reply",
            "sandbox:/mnt/data",
            "<html",
            "declare module 'claude-code'",
        ):
            assert forbidden not in text
    assert not any(p.name.endswith(".private.md") for p in ROOT.rglob("*.private.md"))
