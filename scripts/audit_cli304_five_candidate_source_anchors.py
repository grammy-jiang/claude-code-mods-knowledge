#!/usr/bin/env python3
"""Verify five pending CLI304 candidate anchors against PRIVATE official docs.

This is a structural, source-content SHA integrity check, not an actual
Claim review attestation, runtime approval, or 304 API compatibility proof.
The original upstream HTML and Markdown remain outside git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "docs/reports/2026-10-20-cli304-seven-unapproved-source-observations.json"
CLAIMS = tuple(f"K-{i:04d}" for i in range(70, 75))


class CandidateAnchorBlocked(ValueError):
    """First-party anchor, 304 observation or candidate identity not proved."""


class Headings(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current: dict | None = None
        self.headers: dict[str, dict] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("h2", "h3", "h4"):
            self.current = {"id": dict(attrs).get("id"), "tag": tag, "text": []}

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is not None and tag == self.current["tag"]:
            item = self.current
            name = item["id"]
            if name:
                if name in self.headers:
                    raise CandidateAnchorBlocked("Ambiguous HTML anchor")
                self.headers[name] = {
                    "tag": tag,
                    "heading": " ".join("".join(item["text"]).replace("\u200b", "").split()),
                }
            self.current = None


def audit(cache: Path) -> dict:
    if not cache.is_dir() or cache.is_symlink():
        raise CandidateAnchorBlocked("Missing private official document cache")
    registry = load_registry(ROOT / "sources/registry.json")
    observation = json.loads(SEED.read_text())
    pins = {row["source_id"]: row for row in observation["snapshot_metadata_observations"]}
    rows = []
    for cid in CLAIMS:
        path = ROOT / "claims" / (cid + ".json")
        if not path.is_file() or path.is_symlink():
            raise CandidateAnchorBlocked("Original candidate source does not exist")
        raw = path.read_bytes()
        claim = json.loads(raw)
        if claim.get("claim_id") != cid or claim.get("lifecycle") != "candidate":
            raise CandidateAnchorBlocked("Original claim was promoted or mutated")
        if len(claim.get("evidence", [])) != 1:
            raise CandidateAnchorBlocked("Unsupported candidate source evidence list")
        evidence = claim["evidence"][0]
        sid = evidence["source_id"]
        source = registry[sid]
        url = urlsplit(evidence["locator"])
        page = source["url"].rsplit("/", 1)[-1]
        if (
            evidence["role"] != "context"
            or url.fragment == ""
            or url.scheme != "https"
            or url.netloc != "code.claude.com"
            or evidence["snapshot_sha256"] != pins[sid]["new_304_observed_html_sha256"]
            or url.path != urlsplit(source["url"]).path
            or pins[sid]["snapshot_approval"] != "not-approved"
        ):
            raise CandidateAnchorBlocked("Candidate source cannot be promoted from this evidence")
        html = cache / (page + ".html")
        md = cache / (page + ".md")
        if any(
            not path.is_file() or path.is_symlink() or not 1000 < path.stat().st_size < 2_000_000
            for path in (html, md)
        ):
            raise CandidateAnchorBlocked("Missing bounded first-party document")
        html_raw, md_raw = html.read_bytes(), md.read_bytes()
        html_sha = hashlib.sha256(html_raw).hexdigest()
        if html_sha != evidence["snapshot_sha256"]:
            raise CandidateAnchorBlocked("First-party HTML SHA does not match source candidate")
        headings = Headings()
        headings.feed(html_raw.decode("utf-8"))
        entry = headings.headers.get(url.fragment)
        if not entry or entry["heading"].lower() not in md_raw.decode("utf-8").lower():
            raise CandidateAnchorBlocked("Official candidate section not in HTML and Markdown")
        rows.append(
            {
                "claim_id": cid,
                "claim_sha256": hashlib.sha256(raw).hexdigest(),
                "source_id": sid,
                "exact_current_official_locator": evidence["locator"],
                "current_html_sha256": html_sha,
                "current_markdown_sha256": hashlib.sha256(md_raw).hexdigest(),
                "current_html_heading": entry["heading"],
                "current_html_heading_tag": entry["tag"],
                "anchor_verified_against_html_and_markdown": True,
                "claim_approved": False,
                "first_party_section_semantics_fully_reviewed": False,
            }
        )
    if len(rows) != 5:
        raise CandidateAnchorBlocked("Incomplete pending claim source set")
    return {
        "schema_version": 1,
        "target": "2.1.304",
        "pending_claims": 5,
        "fresh_official_heading_matches": 5,
        "version_specific_source_reviews_signed": 0,
        "approved_304_claims": 0,
        "real_host_semantics_verified": False,
        "stable_release_authorized": False,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-firstparty-docs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: source anchor attestation output exists")
    try:
        report = audit(args.private_firstparty_docs)
    except (CandidateAnchorBlocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: current target source anchors are not verified") from None
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidate_anchors_verified": len(report["rows"]),
                "claim_approvals": 0,
                "full_host_runtime_approved": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
