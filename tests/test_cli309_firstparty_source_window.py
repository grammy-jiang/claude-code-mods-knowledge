"""CLI309 upstream source revisions are not approved SSOT/Skill capabilities."""

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
REPORT = ROOT / "evidence/upstream/claude_code_v2_1_305_309_release_notes_20261023.json"
AUDITOR = ROOT / "scripts/audit_cli309_release_window.py"
NOTES_SHA = {
    "2.1.305": "4583d891dd961543b92896dc6bdfb0975eec2b3745c6c6bc658b0c2bda26ce19",
    "2.1.306": "64316990dc01dcdc7c60f27244dd28be2097e7c48fc68aef36afa31b1f660688",
    "2.1.307": "152c2991aa158dd2d2b494933dbfb985b784e633a0897b666387105dc5565928",
    "2.1.308": "dd490d3f4e93c8165c0322324024d1202fe097b1be5a232b6035fd40bfee97cc",
    "2.1.309": "dd4f32907cc0b7742b53f3919e5dc0bdce8b5813ffb403d7954b528afd856a9c",
}
TOPICS_309 = {
    "skill.additional-directory.name-conflict": "5530a975a628944f2704c5f64e163c145d5d991f0d3e3d390ecea90ff89338ec",
    "skill.nested-package.discovery": "38b445b8a686a08d94b10fbc432fbdd171c9356b9a865dfd5bd95ae2b2e74a99",
    "mod.turn-step.model-alias": "89640152470ae1badec3483605946b1e1704c56ba08889067271a4834e939ff7",
    "skill.synced.disk-read-recovery": "d1e58a76e2d40db29b9d289f3104a931c59488acdf01c22c35f169ad2a8a1d5d",
}
NEW_HTML = {
    "M003": "0ac7c1bb9b43a7e9f0cc90b78e531fdce0538d102387823311395215dc7b226d",
    "M004": "207faf9ed71d9acfbd0ccefa28ef7b1080140215bb883efa8bf11df1efbe6f07",
    "M033": "1bc708ca9dc103735afff057e4845269eb4d0f9a1a97f976205e0fd24585890d",
}
_spec = importlib.util.spec_from_file_location("audit_cli309_release_window", AUDITOR)
assert _spec and _spec.loader
a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a)


def report() -> dict:
    return json.loads(REPORT.read_text())


def digest(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def test_five_original_release_note_bodies_have_exact_sha_and_no_runtime_approval():
    data = report()
    assert data["schema_version"] == 1
    assert data["target_latest_npm_tag_checked"] == "2.1.309"
    assert data["latest_github_release_checked"] == "2.1.309"
    assert data["upstream_project"] == "anthropics/claude-code"
    assert [x["version"] for x in data["releases"]] == list(NOTES_SHA)
    assert [x["scoped_release_note_deltas"] for x in data["releases"]] == [3, 0, 2, 0, 4]
    for item in data["releases"]:
        assert item["official_release_body_sha256"] == NOTES_SHA[item["version"]]
        assert item["source_url"] == (
            "https://github.com/anthropics/claude-code/releases/tag/v" + item["version"]
        )
        assert item["upstream_tag"] == "v" + item["version"]
        assert item["official_release_bullet_count"] >= 1
        assert item["semantic_mods_api_compatibility_proven"] is False
        assert item["actual_native_target_host_verified"] is False
        for delta in item["targeted_relevant_deltas"]:
            assert re.fullmatch(r"[a-f0-9]{64}", delta["source_release_bullet_sha256"])
            assert delta["source_review"] == "PENDING_EXACT_TARGET_DOC_AND_NATIVE_QA"
            assert delta["eligible_for_claim_approval"] is False
            assert delta["eligible_for_skills_or_plugin_publication"] is False
    assert {
        x["topic_id"]: x["source_release_bullet_sha256"]
        for x in data["releases"][-1]["targeted_relevant_deltas"]
    } == TOPICS_309


def test_new_snapshots_are_unapproved_and_do_not_replace_registry_pins():
    data = report()
    assert not verify_snapshot_store(ROOT / "sources/snapshots")
    assert digest(ROOT / "sources/registry.json") == data["original_ssot_registry_sha256"]
    assert len(data["observed_official_html_sources"]) == 3
    index = json.loads((ROOT / "sources/snapshots/index.json").read_text())
    registry = json.loads((ROOT / "sources/registry.json").read_text())
    original = {x["source_id"]: x for x in registry["sources"]}
    for observation in data["observed_official_html_sources"]:
        source = observation["source_id"]
        newest = NEW_HTML[source]
        assert observation["new_observed_raw_html_sha256"] == newest
        assert observation["approval_status"] == "not-approved"
        assert observation["semantic_review_status"] == "not-assessed"
        assert observation["historic_registry_pin_sha256"] == original[source]["snapshot"]["sha256"]
        # An immutable CLI309 observation persists after a newer first-party
        # page revision becomes current, without rewriting its pinned facts.
        assert newest in index["sources"][source]["revisions"]
        assert index["sources"][source]["current"] in index["sources"][source]["revisions"]
        assert (
            observation["previous_unapproved_index_observation_sha256"]
            in index["sources"][source]["revisions"]
        )
        metadata = ROOT / f"sources/snapshots/metadata/{source}/{newest}.json"
        assert digest(metadata) == observation["source_metadata_sha256"]
        assert index["sources"][source]["revisions"][newest]["metadata_sha256"] == digest(metadata)
        assert json.loads(metadata.read_text())["approval_status"] == "not-approved"
    # The changelog was always indexed/unpinned, unlike L0 Mods documents.
    changelog = next(x for x in data["observed_official_html_sources"] if x["source_id"] == "M033")
    assert changelog["historic_registry_pin_sha256"] is None
    assert changelog["original_registry_source_was_pinned"] is False


def test_latest_309_cannot_inherit_302_approved_claims_or_generate_skill():
    r = report()
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.309", "cli") == []
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(
            ROOT, api_version="2.1.309", surface="cli", source_revision="309-unreviewed"
        )
    assert r["exact_latest_309_claims_approved"] == 0
    assert r["new_latest_skills_compiled_or_installed"] is False
    assert r["chatgpt_chat_mode_plugin_published"] is False
    assert r["stable_release_authorized"] is False


def test_missing_official_release_bullet_or_wrong_latest_never_passes(tmp_path):
    with pytest.raises(a.LatestSourceWindowBlocked, match="OFFICIAL_LATEST_CHANGED"):
        a.audit(ROOT, tmp_path, latest="2.1.308")
    for version in a.WINDOW:
        lines = [
            "- " + selector + " synthetic QA continuation"
            for _, selector, _ in a.SELECTORS[version]
        ]
        if not lines:
            lines = ["- A synthetic release note without Mods/Skill scope"]
        (tmp_path / f"v{version}.json").write_text(
            json.dumps(
                {
                    "tagName": "v" + version,
                    "body": "\n".join(lines),
                    "publishedAt": "2026-10-22T12:00:00Z",
                    "isDraft": False,
                    "isPrerelease": False,
                }
            )
        )
    assert len(a.audit_release_notes(tmp_path)) == 5
    bad = tmp_path / "v2.1.309.json"
    document = json.loads(bad.read_text())
    document["body"] = document["body"].replace("Fixed a skill in an", "Fixed a thing in an")
    bad.write_text(json.dumps(document))
    with pytest.raises(a.LatestSourceWindowBlocked, match="MISSING_OR_AMBIGUOUS"):
        a.audit_release_notes(tmp_path)


def test_public_evidence_never_includes_raw_official_body_or_private_material():
    r = report()
    raw = REPORT.read_text()
    for expression in (r"/home/", r"/Users/", r"Authorization:", r"Cookie:", r"access_token"):
        assert re.search(expression, raw, flags=re.I) is None
    assert r["official_release_note_full_bodies_committed_to_git"] is False
    assert r["new_claims_or_approval_decisions_created"] is False
    assert r["native_309_mods_runtime_verified"] is False
    assert r["target_309_skill_discovery_model_test_passed"] is False
    assert r["latest_release_current_at_future_publication"] is False
