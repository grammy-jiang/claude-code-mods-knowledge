#!/usr/bin/env python3
"""Read original private first-party v2.1.305–309 release notes into scoped SSOT research.

Never commits full upstream release bodies. Never widens 302 approval or ships
309 Skills/ChatGPT Plugin. This is a deterministic source/provenance auditor,
not a semantic/runtime/host/model acceptance test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry
from mods_knowledge.storage import verify_snapshot_store

ROOT = Path(__file__).resolve().parents[1]
WINDOW = tuple(f"2.1.{n}" for n in range(305, 310))
LATEST = "2.1.309"
EXPECTED_OFFICIAL_SOURCE_IDS = ("M003", "M004", "M033")
PRIOR_SOURCE_OBSERVATIONS = {
    "M003": "ba69cfd0a140de3b286361be3630e79a3e10d4b0765b50820ca496d28683eb16",
    "M004": "ca95c067e1feddc7391e5ccd337813e8554677c2d6034510a38c75501bec5662",
    "M033": "3ba8d33cbdd67cf068953a7b2e6772096aab3111ba3ce07707b64efc7459d557",
}
EXPECTED_NEW_OBSERVATIONS = {
    "M003": "0ac7c1bb9b43a7e9f0cc90b78e531fdce0538d102387823311395215dc7b226d",
    "M004": "207faf9ed71d9acfbd0ccefa28ef7b1080140215bb883efa8bf11df1efbe6f07",
    "M033": "1bc708ca9dc103735afff057e4845269eb4d0f9a1a97f976205e0fd24585890d",
}
SOURCE_URL_BASE = "https://github.com/anthropics/claude-code/releases/tag/v"

# A release-note mention is a version-specific observation, not a verified
# native feature, version-widened Claim, cross-model Skill or publication gate.
SELECTORS = {
    "2.1.305": (
        (
            "gateway.tool-search-retry",
            "Fixed every request failing on Vertex,",
            "Tool-search gateway fallback.",
        ),
        (
            "mod.interface.image-render",
            "Improved a mod's `Image`",
            "iTerm2 fullscreen Mod Image rendering.",
        ),
        (
            "mod.interface.dock-width",
            "Changed a mod's docked pane",
            "Mod dock pane maximum-width behavior.",
        ),
    ),
    "2.1.306": (),
    "2.1.307": (
        (
            "mcp.http.replay-safety",
            "Fixed HTTP MCP tool calls being sent twice",
            "HTTP MCP reconnect and idempotency behavior.",
        ),
        (
            "sdk.mcp.background-tool-refresh",
            "Fixed a turn sometimes starting without an SDK MCP server's latest tools",
            "SDK MCP tool discovery after background work.",
        ),
    ),
    "2.1.308": (),
    "2.1.309": (
        (
            "skill.additional-directory.name-conflict",
            "Fixed a skill in an `--add-dir` folder being unreachable",
            "Qualified invocation for same-name additional-directory Skills.",
        ),
        (
            "skill.nested-package.discovery",
            "Fixed `/verify` and `/code-review` not finding a nested package's own skill",
            "Nested package Skill discovery after shell changes.",
        ),
        (
            "mod.turn-step.model-alias",
            "Fixed a mod's `turn.step` hook that names a model by alias",
            "Model alias resolution in turn.step Hooks.",
        ),
        (
            "skill.synced.disk-read-recovery",
            "Fixed plugins and skills synced from claude.ai being removed",
            "Cloud-synced Skill persistence after disk-read errors.",
        ),
    ),
}
MAX_PRIVATE_NOTE = 120_000
PINNED_PREFIX = "https://code.claude.com/docs/en/"


class LatestSourceWindowBlocked(ValueError):
    """Unable to attest exact official source identities or safe SSOT scope."""


def require(check: bool, reason: str) -> None:
    if not check:
        raise LatestSourceWindowBlocked(reason)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def audit_release_notes(private: Path) -> list[dict]:
    require(
        private.is_dir() and not private.is_symlink(), "MISSING_PRIVATE_RELEASE_NOTES_DIRECTORY"
    )
    rows = []
    all_topics: set[str] = set()
    for version in WINDOW:
        tag = "v" + version
        path = private / f"{tag}.json"
        require(path.is_file() and not path.is_symlink(), "MISSING_FIRST_PARTY_RELEASE")
        require(100 < path.stat().st_size < MAX_PRIVATE_NOTE, "INVALID_RELEASE_BODY_SIZE")
        doc = json.loads(path.read_text())
        require(
            isinstance(doc, dict)
            and set(doc) == {"tagName", "body", "publishedAt", "isDraft", "isPrerelease"},
            "UNEXPECTED_UPSTREAM_RELEASE_SCHEMA",
        )
        require(
            doc["tagName"] == tag
            and doc["isDraft"] is False
            and doc["isPrerelease"] is False
            and isinstance(doc["publishedAt"], str)
            and re.fullmatch(r"2026-10-(20|21|22|23)T[0-9:]+Z", doc["publishedAt"]) is not None,
            "UNREVIEWED_RELEASE_TAG_OR_PUBLISH_DATE",
        )
        body = doc["body"]
        require(
            isinstance(body, str) and 10 < len(body) < MAX_PRIVATE_NOTE,
            "INVALID_RELEASE_NOTES_TEXT",
        )
        bullets = [s.strip() for s in body.splitlines() if s.strip().startswith("- ")]
        require(
            len(bullets) >= 1 and len(bullets) == len(set(bullets)),
            "MISSING_OR_DUPLICATED_UPSTREAM_BULLETS",
        )
        topics = []
        for topic, exact_lead, short_summary in SELECTORS[version]:
            matched = [b for b in bullets if b.startswith("- " + exact_lead)]
            require(len(matched) == 1, "MISSING_OR_AMBIGUOUS_OFFICIAL_DELTA")
            require(topic not in all_topics, "DUPLICATED_REVIEW_TOPIC_ID")
            all_topics.add(topic)
            topics.append(
                {
                    "topic_id": topic,
                    "scope": "VERSION_SPECIFIC_RELEASE_NOTE_ONLY",
                    "source_release_bullet_sha256": sha(matched[0].encode("utf-8")),
                    "authored_summary": short_summary,
                    "source_review": "PENDING_EXACT_TARGET_DOC_AND_NATIVE_QA",
                    "eligible_for_claim_approval": False,
                    "eligible_for_skills_or_plugin_publication": False,
                }
            )
        rows.append(
            {
                "version": version,
                "upstream_tag": tag,
                "source_url": SOURCE_URL_BASE + version,
                "published_at_utc": doc["publishedAt"],
                "official_release_body_sha256": sha(body.encode("utf-8")),
                "official_release_bullet_count": len(bullets),
                "targeted_relevant_deltas": topics,
                "scoped_release_note_deltas": len(topics),
                "semantic_mods_api_compatibility_proven": False,
                "actual_native_target_host_verified": False,
            }
        )
    require(len(rows) == len(WINDOW) and len(all_topics) == 9, "INCOMPLETE_RELEASE_WINDOW")
    return rows


def source_observations(repo: Path) -> list[dict]:
    registry_file = repo / "sources/registry.json"
    registry_raw = registry_file.read_bytes()
    registry = json.loads(registry_raw)
    index = json.loads((repo / "sources/snapshots/index.json").read_text())
    require(
        isinstance(registry, dict) and isinstance(registry.get("sources"), list),
        "INVALID_ORIGINAL_SSOT_REGISTRY",
    )
    require(
        isinstance(index, dict) and isinstance(index.get("sources"), dict),
        "INVALID_OFFICIAL_SNAPSHOT_INDEX",
    )
    source_map = {x["source_id"]: x for x in registry["sources"]}
    records = []
    for source_id in EXPECTED_OFFICIAL_SOURCE_IDS:
        original = source_map[source_id]
        require(
            original["trust_layer"] in ("L0", "L1", "L2")
            and original["url"].startswith(PINNED_PREFIX)
            and original["review_state"] in ("pinned", "indexed"),
            "NOT_AN_EXPLICIT_OFFICIAL_REGISTRY_SOURCE",
        )
        original_sha = original["snapshot"]["sha256"]
        # M033 is an indexed official changelog without any original Registry
        # SHA pin. Do not falsely describe its previous observation as approved.
        if source_id == "M033":
            require(
                original_sha is None and original["review_state"] == "indexed",
                "CHANGED_CHANGELOG_REGISTRY_SCOPE",
            )
        else:
            require(
                isinstance(original_sha, str)
                and re.fullmatch(r"[a-f0-9]{64}", original_sha) is not None
                and original["review_state"] == "pinned",
                "PINNED_MODS_REGISTRY_SCOPE_CHANGED",
            )
        entry = index["sources"][source_id]
        current = entry["current"]
        prior = PRIOR_SOURCE_OBSERVATIONS[source_id]
        require(
            current == EXPECTED_NEW_OBSERVATIONS[source_id]
            and prior != current
            and prior in entry["revisions"]
            and current in entry["revisions"]
            and (original_sha is None or original_sha in entry["revisions"]),
            "UNEXPECTED_OFFICIAL_REVISION_HISTORY",
        )
        metadata = repo / f"sources/snapshots/metadata/{source_id}/{current}.json"
        payload = metadata.read_bytes()
        doc = json.loads(payload)
        require(
            doc["source_id"] == source_id
            and doc["content_sha256"] == current
            and doc["approval_status"] == "not-approved"
            and doc["semantic_status"] == "not-assessed"
            and doc["url"] == original["url"]
            and doc["hash_basis"] == "raw-http-response-bytes"
            and sha(payload) == entry["revisions"][current]["metadata_sha256"],
            "SOURCE_OBSERVATION_NOT_UNAPPROVED_OR_HASH_BOUND",
        )
        records.append(
            {
                "source_id": source_id,
                "official_url": original["url"],
                "historic_registry_pin_sha256": original_sha,
                "previous_unapproved_index_observation_sha256": prior,
                "new_observed_raw_html_sha256": current,
                "source_metadata_sha256": sha(payload),
                "observed_at_utc": doc["observed_at"],
                "approval_status": doc["approval_status"],
                "semantic_review_status": doc["semantic_status"],
                "historical_registry_source_pin_unchanged": True,
                "original_registry_source_was_pinned": original_sha is not None,
            }
        )
    return records


def audit(repo: Path, private_notes: Path, *, latest: str) -> dict:
    require(latest == LATEST, "OFFICIAL_LATEST_CHANGED_REQUIRE_REVIEW")
    snapshots = repo / "sources/snapshots"
    require(not verify_snapshot_store(snapshots), "SSOT_SNAPSHOT_STORE_CORRUPTED")
    approved = load_claims(
        repo / "claims",
        load_registry(repo / "sources/registry.json"),
        snapshots,
        repo / "decisions",
    )
    old_approved = len(approved_claims(approved, "2.1.302", "cli"))
    newest_approved = len(approved_claims(approved, latest, "cli"))
    require(old_approved == 31 and newest_approved == 0, "UNEXPECTED_SSOT_CLAIM_APPROVAL_DRIFT")
    return {
        "schema_version": 1,
        "upstream_project": "anthropics/claude-code",
        "target_latest_npm_tag_checked": latest,
        "latest_github_release_checked": latest,
        "source_review_status": "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI309_API_CLAIMS",
        "releases": audit_release_notes(private_notes),
        "observed_official_html_sources": source_observations(repo),
        "original_ssot_registry_sha256": sha((repo / "sources/registry.json").read_bytes()),
        "previous_approved_302_claims_unchanged": old_approved,
        "exact_latest_309_claims_approved": newest_approved,
        "official_release_note_full_bodies_committed_to_git": False,
        "new_claims_or_approval_decisions_created": False,
        "new_latest_skills_compiled_or_installed": False,
        "chatgpt_chat_mode_plugin_published": False,
        "native_309_mods_runtime_verified": False,
        "target_309_skill_discovery_model_test_passed": False,
        "latest_release_current_at_future_publication": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-release-notes", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--verified-latest", required=True)
    parser.add_argument("--out", type=Path, required=True)
    opt = parser.parse_args()
    if opt.out.exists() or opt.out.is_symlink():
        raise SystemExit("BLOCKED: immutable release evidence path already exists")
    try:
        result = audit(opt.root, opt.private_release_notes, latest=opt.verified_latest)
    except (LatestSourceWindowBlocked, ValueError, KeyError, OSError, TypeError) as exc:
        print(
            f"BLOCKED: official release-note review source/SSOT gate: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2
    opt.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "official_versions": len(result["releases"]),
                "targeted_release_note_facts": sum(
                    r["scoped_release_note_deltas"] for r in result["releases"]
                ),
                "new_observations": len(result["observed_official_html_sources"]),
                "approved_latest_claims": result["exact_latest_309_claims_approved"],
                "publication_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
