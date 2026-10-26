#!/usr/bin/env python3
"""Immutable, source-only first-party CLI310 research; NO Claim promotion.

The original official release body stays in the host's private 0700 archive.
Public output holds scoped release-bullet SHA256 facts and append-only HTML
metadata digests, never full upstream text or user-account/session evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry
from mods_knowledge.storage import verify_snapshot_store

ROOT = Path(__file__).resolve().parents[1]
TARGET = "2.1.310"
OFFICIAL_BODY_SHA = "4a2790d850518ceec4ab9ae097c315dfef5284c2765870a6d682011ae4ea9d89"
OFFICIAL_PUBLISHED_AT = "2026-10-23T23:39:00Z"
PRIOR_309_HTML = {
    "M003": "0ac7c1bb9b43a7e9f0cc90b78e531fdce0538d102387823311395215dc7b226d",
    "M004": "207faf9ed71d9acfbd0ccefa28ef7b1080140215bb883efa8bf11df1efbe6f07",
    "M033": "1bc708ca9dc103735afff057e4845269eb4d0f9a1a97f976205e0fd24585890d",
}
OBSERVED_310_HTML = {
    "M003": "3876d8279a90afb41874830940bd0bae63ca145187b0f132ba3cb399aee07a5c",
    "M004": "d5beb3abca68a424e61d94c1777e06790ab51e08bc1c5ef465a3a57278350d27",
    "M033": "70ca2e8ab711dbb97053217799ba27332936bb32fd2d16c0e95a7eece966eaa2",
}
# Exact first-party prefix matching; one version-scoped release note per topic.
SELECTORS = (
    (
        "monitor.plugin-availability",
        "Added the Monitor tool and plugin monitors",
        "Release-note fact: availability varies by provider/telemetry mode; native checks pending.",
    ),
    (
        "read.permission.symlink-target",
        "Fixed file read permission prompts not showing where a symbolic link leads",
        "Release-note fact: target path visibility in read permission prompts; real-host QA pending.",
    ),
    (
        "windows.hook.pretool-missing-git-bash",
        "Windows: Fixed PreToolUse and PermissionRequest hooks",
        "Windows-scoped compatibility note only; not relevant evidence for Linux/macOS host semantics.",
    ),
    (
        "mods.ui.image-fullscreen",
        "Improved a mod's ",
        "Release-note fact: terminal-dependent Mod Image rendering; not a cross-terminal PASS.",
    ),
    (
        "mcp.noninteractive.elicitation-timeout",
        "Changed the error for an MCP tool call that times out",
        "Release-note fact: error-reporting change, not proof of MCP retry safety.",
    ),
)


class Source310Blocked(ValueError):
    """Untrusted, incomplete or unsafely promoted release observations."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Source310Blocked(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def release_facts(private: Path) -> dict:
    require(
        private.is_file() and not private.is_symlink() and 200 < private.stat().st_size <= 90_000,
        "ORIGINAL_PRIVATE_RELEASE_MISSING_OR_UNSAFE",
    )
    doc = json.loads(private.read_text())
    require(
        isinstance(doc, dict)
        and set(doc) == {"tagName", "publishedAt", "isDraft", "isPrerelease", "body"}
        and doc["tagName"] == "v2.1.310"
        and doc["publishedAt"] == OFFICIAL_PUBLISHED_AT
        and doc["isDraft"] is False
        and doc["isPrerelease"] is False,
        "OFFICIAL_RELEASE_IDENTITY_NOT_CONFIRMED",
    )
    body = doc["body"]
    require(
        isinstance(body, str) and sha(body.encode()) == OFFICIAL_BODY_SHA,
        "ORIGINAL_OFFICIAL_RELEASE_BODY_SHA_MISMATCH",
    )
    bullets = [line.strip() for line in body.splitlines() if line.strip().startswith("- ")]
    require(bullets and len(set(bullets)) == len(bullets), "DUPLICATE_OR_EMPTY_RELEASE_NOTES")
    changes = []
    for topic, leading_text, summary in SELECTORS:
        hits = [b for b in bullets if b.startswith("- " + leading_text)]
        require(len(hits) == 1, "EXPECTED_VERSION_SPECIFIC_BULLET_MISSING_OR_AMBIGUOUS")
        changes.append(
            {
                "topic_id": topic,
                "official_release_bullet_sha256": sha(hits[0].encode()),
                "scoped_summary": summary,
                "evidence_kind": "RELEASE_NOTE_FACT_NOT_NATIVE_API_PROOF",
                "runtime_verified": False,
                "approved_claim": False,
            }
        )
    return {
        "upstream_tag": doc["tagName"],
        "official_release_url": "https://github.com/anthropics/claude-code/releases/tag/v2.1.310",
        "published_at_utc": doc["publishedAt"],
        "official_release_body_sha256": OFFICIAL_BODY_SHA,
        "official_release_bullet_count": len(bullets),
        "targeted_deltas": changes,
    }


def observations(root: Path) -> list[dict]:
    registry = json.loads((root / "sources/registry.json").read_text())
    current = json.loads((root / "sources/snapshots/index.json").read_text())
    lookup = {row["source_id"]: row for row in registry["sources"]}
    rows = []
    for sid in sorted(OBSERVED_310_HTML):
        entry = current["sources"][sid]
        observed = OBSERVED_310_HTML[sid]
        prior = PRIOR_309_HTML[sid]
        original = lookup[sid]
        original_pin = original["snapshot"]["sha256"]
        require(
            original["url"].startswith("https://code.claude.com/docs/en/")
            and original["trust_layer"] in ("L0", "L1", "L2")
            and original["review_state"] in ("pinned", "indexed"),
            "SOURCE_REGISTRY_LOCATION_OR_TRUST_CHANGED",
        )
        if sid == "M033":
            require(
                original_pin is None and original["review_state"] == "indexed",
                "INDEXED_UNPINNED_CHANGELOG_HISTORIC_IDENTITY_CHANGED",
            )
        else:
            require(
                isinstance(original_pin, str) and original["review_state"] == "pinned",
                "ORIGINAL_PINNED_MODS_REGISTRY_IDENTITY_CHANGED",
            )
        require(
            prior != observed
            and prior in entry["revisions"]
            and observed in entry["revisions"]
            and entry["current"] in entry["revisions"]
            and (original_pin is None or original_pin in entry["revisions"]),
            "SOURCE_HISTORY_NOT_APPEND_ONLY",
        )
        path = root / f"sources/snapshots/metadata/{sid}/{observed}.json"
        raw = path.read_bytes()
        d = json.loads(raw)
        require(
            d["source_id"] == sid
            and d["url"] == original["url"]
            and d["content_sha256"] == observed
            and d["approval_status"] == "not-approved"
            and d["semantic_status"] == "not-assessed"
            and d["hash_basis"] == "raw-http-response-bytes"
            and sha(raw) == entry["revisions"][observed]["metadata_sha256"],
            "UNREVIEWED_310_SOURCE_METADATA_NOT_VERIFIABLE",
        )
        rows.append(
            {
                "source_id": sid,
                "official_url": original["url"],
                "observed_raw_html_sha256": observed,
                "previous_309_raw_html_sha256": prior,
                "metadata_sha256": sha(raw),
                "observed_at_utc": d["observed_at"],
                "historical_registry_pin_sha256": original_pin,
                "observation_approved": False,
                "semantic_assessed": False,
                "original_source_registry_unchanged": True,
            }
        )
    return rows


def audit(root: Path, private: Path, latest: str) -> dict:
    require(latest == TARGET, "TARGET_LATEST_DIST_TAG_NOT_VERIFIED")
    require(not verify_snapshot_store(root / "sources/snapshots"), "CURRENT_SNAPSHOT_INDEX_DAMAGED")
    registry = load_registry(root / "sources/registry.json")
    approved = load_claims(
        root / "claims", registry, root / "sources/snapshots", root / "decisions"
    )
    scoped = {
        v: len(approved_claims(approved, v, "cli"))
        for v in ("2.1.296", "2.1.302", "2.1.309", "2.1.310")
    }
    require(
        scoped == {"2.1.296": 31, "2.1.302": 31, "2.1.309": 0, "2.1.310": 0},
        "UNEXPECTED_CLAIM_SCOPE_OR_APPROVAL_DRIFT",
    )
    return {
        "schema_version": 1,
        "observation_day": "2026-10-27",
        "official_npm_latest_observed": latest,
        "release": release_facts(private),
        "source_observations": observations(root),
        "original_registry_sha256": sha((root / "sources/registry.json").read_bytes()),
        "approved_claims_by_target": scoped,
        "original_upstream_release_body_private_not_committed": True,
        "new_claims_approved_or_promoted": False,
        "native_310_behavior_verified": False,
        "generated_310_skill_or_plugin_published": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--private-release", type=Path, required=True)
    ap.add_argument("--verified-latest", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable research report output exists")
    try:
        result = audit(args.root, args.private_release, args.verified_latest)
    except (Source310Blocked, ValueError, KeyError, TypeError, OSError):
        raise SystemExit("BLOCKED: 310 source data incomplete or trust claim unsafe") from None
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "target": TARGET,
                "official_bullets": len(result["release"]["targeted_deltas"]),
                "source_revisions": len(result["source_observations"]),
                "new_approved_claims": 0,
                "release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
