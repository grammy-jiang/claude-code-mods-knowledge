"""Pinned, unapproved first-party CLI310 source facts and immutable 309 history."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry
from mods_knowledge.storage import verify_snapshot_store

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-27-cli310-official-source-evidence.json"
SCRIPT = ROOT / "scripts/audit_cli310_official_source_window.py"
PREVIOUS = ROOT / "evidence/upstream/claude_code_v2_1_305_309_release_notes_20261023.json"

_spec = importlib.util.spec_from_file_location("audit_source310", SCRIPT)
assert _spec and _spec.loader
auditor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditor)


def report() -> dict:
    return json.loads(REPORT.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_official_release_scope_and_bullet_hashes_not_promoted():
    data = report()
    version = data["release"]
    assert data["schema_version"] == 1
    assert data["official_npm_latest_observed"] == "2.1.310"
    assert version["official_release_url"] == (
        "https://github.com/anthropics/claude-code/releases/tag/v2.1.310"
    )
    assert version["upstream_tag"] == "v2.1.310"
    assert version["published_at_utc"] == auditor.OFFICIAL_PUBLISHED_AT
    assert version["official_release_body_sha256"] == auditor.OFFICIAL_BODY_SHA
    assert version["official_release_bullet_count"] >= 5
    assert len(version["targeted_deltas"]) == 5
    assert {b["topic_id"] for b in version["targeted_deltas"]} == {
        row[0] for row in auditor.SELECTORS
    }
    for item in version["targeted_deltas"]:
        assert re.fullmatch(r"[a-f0-9]{64}", item["official_release_bullet_sha256"])
        assert item["evidence_kind"] == "RELEASE_NOTE_FACT_NOT_NATIVE_API_PROOF"
        assert item["runtime_verified"] is False
        assert item["approved_claim"] is False
    assert data["original_upstream_release_body_private_not_committed"] is True
    assert data["generated_310_skill_or_plugin_published"] is False
    assert data["native_310_behavior_verified"] is False
    assert data["stable_release_authorized"] is False


def test_unapproved_310_fingerprints_are_integral_and_prior_309_remains():
    data = report()
    assert not verify_snapshot_store(ROOT / "sources/snapshots")
    assert data["original_registry_sha256"] == sha(ROOT / "sources/registry.json")
    actual = auditor.observations(ROOT)
    assert actual == data["source_observations"]
    assert len(actual) == 3
    index = json.loads((ROOT / "sources/snapshots/index.json").read_text())
    registry = json.loads((ROOT / "sources/registry.json").read_text())
    by_source = {r["source_id"]: r for r in registry["sources"]}
    for row in actual:
        sid = row["source_id"]
        original = by_source[sid]
        old, new = auditor.PRIOR_309_HTML[sid], auditor.OBSERVED_310_HTML[sid]
        assert row["official_url"] == original["url"]
        assert row["historical_registry_pin_sha256"] == original["snapshot"]["sha256"]
        assert row["previous_309_raw_html_sha256"] == old
        assert row["observed_raw_html_sha256"] == new
        assert row["observation_approved"] is False
        assert row["semantic_assessed"] is False
        assert index["sources"][sid]["current"] in index["sources"][sid]["revisions"]
        assert old in index["sources"][sid]["revisions"]
        assert new in index["sources"][sid]["revisions"]
        metadata = ROOT / f"sources/snapshots/metadata/{sid}/{new}.json"
        assert sha(metadata) == row["metadata_sha256"]
        assert index["sources"][sid]["revisions"][new]["metadata_sha256"] == sha(metadata)
    assert by_source["M033"]["snapshot"]["sha256"] is None
    assert by_source["M033"]["review_state"] == "indexed"


def test_historical_309_observations_remain_replayable_without_current_pointer():
    previous = json.loads(PREVIOUS.read_text())
    path = ROOT / "scripts/audit_cli309_release_window.py"
    spec = importlib.util.spec_from_file_location("audit_source309_historical", path)
    assert spec and spec.loader
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    assert old.source_observations(ROOT) == previous["observed_official_html_sources"]


def test_approved_old_scopes_and_new_310_fail_closed():
    data = report()
    assert data["approved_claims_by_target"] == {
        "2.1.296": 31,
        "2.1.302": 31,
        "2.1.309": 0,
        "2.1.310": 0,
    }
    assert data["new_claims_approved_or_promoted"] is False
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.310", "cli") == []
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(
            ROOT, api_version="2.1.310", surface="cli", source_revision="310-unapproved"
        )


def test_private_release_identity_and_wrong_latest_rejected(tmp_path):
    file = tmp_path / "private-original.json"
    fake = {
        "tagName": "v2.1.310",
        "publishedAt": auditor.OFFICIAL_PUBLISHED_AT,
        "isDraft": False,
        "isPrerelease": False,
        "body": "- Fake release note that does not match original SHA\n"
        + "- Synthetic note\n" * 20,
    }
    file.write_text(json.dumps(fake))
    with pytest.raises(
        auditor.Source310Blocked, match="ORIGINAL_OFFICIAL_RELEASE_BODY_SHA_MISMATCH"
    ):
        auditor.release_facts(file)
    with pytest.raises(auditor.Source310Blocked, match="TARGET_LATEST_DIST_TAG_NOT_VERIFIED"):
        auditor.audit(ROOT, file, "2.1.309")


def test_no_private_original_text_or_machine_identity_in_public_evidence():
    raw = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Authorization:",
        "Cookie:",
        "access_token",
        "BEGIN PRIVATE KEY",
        "chatgpt.com/c/",
        '"session_id":',
        '"tool_use_id":',
    ):
        assert forbidden not in raw
    assert (
        re.search(
            r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])",
            raw,
        )
        is None
    )
