#!/usr/bin/env python3
"""Seed seven *UNAPPROVED* fresh CLI304 official-source HTML observations.

This does NOT review API semantics, change previously pinned registry sources,
create/approve Claims, install Skills, touch ChatGPT, call models, or store
upstream HTML/Markdown text in git. Input is already independently captured,
SHA-bound private source pages. Snapshot-store writes use existing immutable,
atomically indexed observation machinery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.collector import FetchResult
from mods_knowledge.registry import load_registry
from mods_knowledge.storage import record_observation, verify_snapshot_store

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/reports/2026-10-20-cli304-p1-all31-fresh-primary-anchor-matrix.json"
SNAPSHOTS = ROOT / "sources/snapshots"
REGISTRY = ROOT / "sources/registry.json"


class UnapprovedSourceBlocked(ValueError):
    """Refuse to record mismatched or already-promoted first-party revisions."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_public_audit() -> dict:
    if not AUDIT.is_file() or AUDIT.is_symlink() or AUDIT.stat().st_size > 180_000:
        raise UnapprovedSourceBlocked("CLI304 fresh primary source review absent")
    report = json.loads(AUDIT.read_text())
    if (
        report.get("review_target") != "2.1.304"
        or report.get("prior_302_claims_checked") != 31
        or report.get("approved_new_304_claims") != 0
        or report.get("fresh_official_html_and_markdown_pages") != 7
        or report.get("first_party_original_locator_occurrences_verified") != 32
        or report.get("fresh_source_revisions_not_promoted_into_approved_SSOT") is not True
    ):
        raise UnapprovedSourceBlocked("Source anchors are unreviewed or incompatible")
    return report


def bounded_cached_sources(private: Path) -> list[tuple[dict, bytes, datetime]]:
    if not private.is_dir() or private.is_symlink():
        raise UnapprovedSourceBlocked("Private current-source cache missing")
    report = read_public_audit()
    registry = load_registry(REGISTRY)
    approved = load_claims(ROOT / "claims", registry, SNAPSHOTS, ROOT / "decisions")
    if len(approved_claims(approved, "2.1.302", "cli")) != 31 or approved_claims(
        approved, "2.1.304", "cli"
    ):
        raise UnapprovedSourceBlocked("Unexpected approved Claim target migration")
    inputs = []
    for page in report["source_pages"]:
        source = registry.get(page["source_id"])
        if (
            not source
            or source["url"] != page["official_url"]
            or source["snapshot"]["sha256"] != page["original_registry_pinned_html_sha256"]
            or source["review_state"] != "pinned"
        ):
            raise UnapprovedSourceBlocked("Original SSOT source registry identity changed")
        name = source["url"].rsplit("/", 1)[-1]
        file = private / (name + ".html")
        if not file.is_file() or file.is_symlink() or not 1000 < file.stat().st_size < 2_000_000:
            raise UnapprovedSourceBlocked("Private original HTML source not bounded or available")
        raw = file.read_bytes()
        if len(raw) != page["fresh_html_bytes"] or sha(raw) != page["fresh_html_sha256"]:
            raise UnapprovedSourceBlocked("Current HTML bytes differ from reviewed first-party URL")
        observed = datetime.fromtimestamp(file.stat().st_mtime, UTC)
        if not datetime(2026, 10, 20, tzinfo=UTC) <= observed < datetime(2026, 10, 22, tzinfo=UTC):
            raise UnapprovedSourceBlocked("Captured official source clock is out of scope")
        inputs.append((source, raw, observed))
    if len(inputs) != 7 or len({s["source_id"] for s, _, _ in inputs}) != 7:
        raise UnapprovedSourceBlocked("Missing current official versioned source")
    return inputs


def audit_and_record(private: Path) -> dict:
    indexed = bounded_cached_sources(private)
    original_registry_hash = sha(REGISTRY.read_bytes())
    old_index = json.loads((SNAPSHOTS / "index.json").read_text())
    original_pins = {s["source_id"]: s["snapshot"]["sha256"] for s, _, _ in indexed}
    results = []
    for source, raw, observed in indexed:
        fetched = FetchResult(
            url=source["url"],
            sha256=sha(raw),
            byte_length=len(raw),
            content_type="text/html",
            etag=None,  # The first HTML capture did not pin HTTP ETag headers.
            last_modified=None,
        )
        changed = record_observation(SNAPSHOTS, source, fetched, observed)
        if changed.status not in ("changed", "unchanged"):
            raise UnapprovedSourceBlocked("New unapproved snapshot state unexpected")
        metadata = SNAPSHOTS / "metadata" / source["source_id"] / (fetched.sha256 + ".json")
        data = json.loads(metadata.read_text())
        if (
            data["approval_status"] != "not-approved"
            or data["semantic_status"] != "not-assessed"
            or data["content_sha256"] != fetched.sha256
            or data["observed_at"] != observed.isoformat().replace("+00:00", "Z")
        ):
            raise UnapprovedSourceBlocked("Recorded source metadata was accidentally promoted")
        results.append(
            {
                "source_id": source["source_id"],
                "official_url": source["url"],
                "original_302_registry_pin_sha256": original_pins[source["source_id"]],
                "new_304_observed_html_sha256": fetched.sha256,
                "new_304_metadata_sha256": sha(metadata.read_bytes()),
                "observed_at": data["observed_at"],
                "snapshot_approval": "not-approved",
                "semantic_assessment": "not-assessed",
                "historical_registry_pin_preserved": True,
                "current_snapshot_metadata_only_not_a_reviewed_304_claim": True,
            }
        )
    if verify_snapshot_store(SNAPSHOTS):
        raise UnapprovedSourceBlocked("Official source observation index integrity failure")
    new_index = json.loads((SNAPSHOTS / "index.json").read_text())
    for row in results:
        if new_index["sources"][row["source_id"]]["current"] != row["new_304_observed_html_sha256"]:
            raise UnapprovedSourceBlocked("New unapproved metadata not current")
    if (
        sha(REGISTRY.read_bytes()) != original_registry_hash
        or any(s["snapshot"]["sha256"] != original_pins[s["source_id"]] for s, _, _ in indexed)
        or any(
            row["original_302_registry_pin_sha256"]
            not in old_index["sources"][row["source_id"]]["revisions"]
            for row in results
        )
    ):
        raise UnapprovedSourceBlocked("Original approved 302 source revision was modified")
    return {
        "schema_version": 1,
        "capture_day": "2026-10-20",
        "target_version_under_review": "2.1.304",
        "prior_approved_target_unchanged": "2.1.302",
        "first_party_documents_recorded_unapproved": 7,
        "prior_registry_sha256_unchanged": original_registry_hash,
        "original_html_or_markdown_text_committed_to_git": False,
        "revision_review_attestations_created": 0,
        "approved_304_claims": 0,
        "new_304_skills_or_plugin_published": False,
        "existing_302_claims_or_decision_records_changed": False,
        "snapshot_integrity_verified": True,
        "snapshot_metadata_observations": results,
        "full_304_semantic_compatibility_verified": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-official-pages", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable unapproved 304 snapshot record exists")
    try:
        report = audit_and_record(args.private_official_pages)
    except (UnapprovedSourceBlocked, ValueError, OSError, KeyError, TypeError):
        raise SystemExit("BLOCKED: current 304 documentation observations not intact") from None
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "official_unapproved_observations": report[
                    "first_party_documents_recorded_unapproved"
                ],
                "new_304_claims_approved": 0,
                "old_registry_pins_changed": False,
                "snapshot_store_integrity": report["snapshot_integrity_verified"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
