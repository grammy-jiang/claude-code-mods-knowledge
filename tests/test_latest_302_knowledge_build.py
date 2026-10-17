"""Current CLI 2.1.302 must never silently source historic 2.1.296 Claims."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import compile_knowledge
from mods_knowledge.evidence_delivery import make_verified_task_context
from mods_knowledge.registry import load_registry
from mods_knowledge.task_evidence import (
    EvidenceSelectionError,
    render_evidence_pack,
    route_task,
    select_task_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
LATEST = "2.1.302"
OLD = "2.1.296"
NEW_IDS = {f"K-{i:04d}" for i in range(39, 70)}
CITATION_ROOT = "https://code.claude.com/docs/en/plugins/mods/"


@pytest.fixture(scope="module")
def all_claims() -> dict[str, dict]:
    return load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )


def test_exact_version_approvals_are_independent_and_fully_scoped(all_claims: dict) -> None:
    old = {x["claim_id"] for x in approved_claims(all_claims, OLD, "cli")}
    latest = {x["claim_id"] for x in approved_claims(all_claims, LATEST, "cli")}
    assert len(old) == len(latest) == 31
    assert latest == NEW_IDS
    assert not (old & latest)
    for item in (all_claims[cid] for cid in latest):
        assert item["lifecycle"] == "approved"
        assert item["applies_to"]["claude_code"] == {
            "min_inclusive": LATEST,
            "max_exclusive": "2.1.303",
        }
        assert len(item["supersedes"]) == 1
        assert item["supersedes"][0] in old
        assert "2.1.296" not in item["statement"]
        for source in item["evidence"]:
            assert source["locator"].startswith(CITATION_ROOT)
            assert "#" in source["locator"]
    assert not approved_claims(all_claims, "2.1.303", "cli")
    normative = all_claims["K-0039"]
    assert normative["authority"] == "normative"
    assert normative["verification"]["runtime"] == "smoke-pass"
    assert normative["verification"]["runtime_profiles"] == ["macbook-20261017-claude302"]


def test_task_evidence_defaults_latest_and_preserves_explicit_historical(all_claims: dict) -> None:
    prompt = "How to test a Claude Code Mod offline with .test.ts?"
    assert route_task(prompt)["target"] == LATEST
    selected = select_task_evidence(prompt, all_claims)
    assert selected["ready"]
    assert selected["target"] == LATEST
    assert all(
        row["claim_id"] in NEW_IDS and row["version"] == LATEST for row in selected["claims"]
    )
    context = make_verified_task_context(selected)
    assert f"Claude Code CLI {LATEST}" in context
    assert OLD not in context
    assert render_evidence_pack(selected).count(CITATION_ROOT) > 0
    old = select_task_evidence(prompt, all_claims, version=OLD)
    assert old["ready"] and old["target"] == OLD
    assert all(row["claim_id"] not in NEW_IDS for row in old["claims"])


def test_target_and_unrelated_controls_never_receive_mods_evidence(all_claims: dict) -> None:
    wrong_version = "Write a Claude Code Mods tool.call for CLI 2.1.296"
    blocked = select_task_evidence(wrong_version, all_claims)
    assert blocked["intent"] == "blocked" and not blocked["ready"]
    with pytest.raises(EvidenceSelectionError):
        make_verified_task_context(blocked)
    unrelated = select_task_evidence("How do I write a generic Python asyncio task?", all_claims)
    assert not unrelated["ready"]
    assert unrelated["intent"] == "unrelated"
    assert not select_task_evidence("Claude Code Mods pane API", all_claims, version="2.1.303")[
        "ready"
    ]


def test_four_downstream_skills_are_byte_identical_without_stale_latest_claims() -> None:
    artifacts = compile_knowledge(
        ROOT,
        api_version=LATEST,
        surface="cli",
        package_version="0.4.7-beta.1",
        knowledge_version="0.4.7",
        source_revision="version-302-unit-test",
    )
    prefix = "claude-code-mods-development"
    first = artifacts[f"common/{prefix}/SKILL.md"]
    assert first == artifacts[f"claude-code/.claude/skills/{prefix}/SKILL.md"]
    assert first == artifacts[f"codex/.agents/skills/{prefix}/SKILL.md"]
    assert first == artifacts[f"pi/.agents/skills/{prefix}/SKILL.md"]
    assert first == artifacts[f"chatgpt/claude-code-mods-knowledge/skills/{prefix}/SKILL.md"]
    page = first.decode()
    assert LATEST in page and OLD not in page
    assert "K-0064" in page and "K-0040" in page and "K-0069" in page
    assert "K-0031" not in page and "K-0007" not in page and "K-0038" not in page
    manifest = json.loads(artifacts["manifests/build-manifest.json"])
    assert manifest["approved_claim_ids"] == sorted(NEW_IDS)
    assert manifest["target"] == {"api_version": LATEST, "surface": "cli"}
    assert (
        manifest["artifact_sha256"][f"common/{prefix}/SKILL.md"]
        == hashlib.sha256(first).hexdigest()
    )
    plugin = json.loads(artifacts["chatgpt/claude-code-mods-knowledge/plugin.json"])
    assert plugin["version"] == "0.4.7-beta.1"
    assert plugin["name"] == "claude-code-mods-knowledge"
    assert not any(x.endswith(("hooks.json", "mcp.json")) for x in artifacts)


def test_reviewed_new_sha_is_not_equivalent_to_unreviewed_digest(all_claims: dict) -> None:
    from mods_knowledge.claims import _is_pinned_official_support
    from mods_knowledge.registry import load_registry

    sources = load_registry(ROOT / "sources/registry.json")
    new = all_claims["K-0040"]["evidence"][0]
    old = all_claims["K-0007"]["evidence"][0]
    index = json.loads((ROOT / "sources/snapshots/index.json").read_text())["sources"]
    observed = {key: value for key, value in index.items()}
    assert _is_pinned_official_support(
        new, sources["M004"], ROOT / "sources/snapshots", observed, required_version=LATEST
    )
    assert not _is_pinned_official_support(
        {**new, "snapshot_sha256": "f" * 64},
        sources["M004"],
        ROOT / "sources/snapshots",
        observed,
        required_version=LATEST,
    )
    assert not _is_pinned_official_support(
        new, sources["M004"], ROOT / "sources/snapshots", observed, required_version="2.1.303"
    )
    assert _is_pinned_official_support(
        old, sources["M004"], ROOT / "sources/snapshots", observed, required_version=OLD
    )
