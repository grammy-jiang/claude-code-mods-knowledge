#!/usr/bin/env python3
"""Review five CLI304 first-party markdown sections against exact HTML anchors.

The upstream HTML and Markdown remain PRIVATE. This writes SHA-bound section
revision attestations (NOT cryptographic signatures), with exact line spans,
source identity, and declared scope. Attested content supports *source review*,
not automatic Claim transitions, human permissions or runtime acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

from mods_knowledge.claims import _is_pinned_official_support, _known_observations
from mods_knowledge.registry import load_registry
from mods_knowledge.review_evidence import validate_official_review

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "sources/reviews/revisions"
SNAPSHOT = ROOT / "sources/snapshots"
ORIGINAL = ROOT / "docs/reports/2026-10-20-cli304-five-candidate-anchor-evidence.json"
OBS = ROOT / "docs/reports/2026-10-20-cli304-seven-unapproved-source-observations.json"
TARGET = "2.1.304"
# Explicit *section* review decisions; context-only means source doesn't on
# its own substantiate the NEW version's behavioral delta from the release.
SECTIONS = {
    "K-0070": (
        "M004",
        "events",
        "approve-or-refuse-a-tool-call-before-the-user-is-asked",
        "context_only_release_delta",
        ("`tool.check`", "permission rules", "`allow`", "`ask`", "`deny`"),
    ),
    "K-0071": (
        "M003",
        "reference",
        "events",
        "context_only_release_delta",
        ("`tool.check`", "`e.agentId`", "`e.ceiling`"),
    ),
    "K-0072": (
        "M004",
        "events",
        "the-order-mods-run-in",
        "context_only_release_delta",
        ("`PreToolUse`", "appendPlugins", "`next`"),
    ),
    "K-0073": (
        "M006",
        "interface",
        "keep-state",
        "context_only_release_delta",
        ("`$.state`", "`$.store`", "reload"),
    ),
    "K-0074": (
        "M004",
        "events",
        "handle-a-hook-that-fails",
        "direct_documented_behavior_narrow_native_subset",
        ("`.catch`", "`next.called`", "`tool.check`", "`deny`"),
    ),
}


class Section304Blocked(ValueError):
    """A current official section or source-review boundary could not be proved."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bounded_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 150_000:
        raise Section304Blocked("Missing reviewed original Claim/source metadata")
    return json.loads(path.read_text())


class Headings(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: dict[str, tuple[str, str]] = {}
        self.current: dict | None = None

    def handle_starttag(self, tag, attrs) -> None:
        if tag in ("h2", "h3", "h4"):
            self.current = {"tag": tag, "id": dict(attrs).get("id"), "text": []}

    def handle_data(self, data) -> None:
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag) -> None:
        if self.current is not None and tag == self.current["tag"]:
            item = self.current
            if item["id"]:
                if item["id"] in self.found:
                    raise Section304Blocked("Ambiguous duplicate official HTML id")
                self.found[item["id"]] = (
                    item["tag"],
                    " ".join("".join(item["text"]).replace("\u200b", "").split()),
                )
            self.current = None


def exact_markdown_section(raw: bytes, heading: str, tag: str) -> tuple[dict, str]:
    lines = raw.decode("utf-8").splitlines(keepends=True)
    level = int(tag[1])
    head = "#" * level + " " + heading
    spans = [i for i, text in enumerate(lines) if text.rstrip("\r\n") == head]
    if len(spans) != 1:
        raise Section304Blocked("The first-party Markdown heading is missing/duplicated")
    start = spans[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        candidate = re.match(r"^(#{1,6}) +[^#]", lines[i])
        if candidate and len(candidate.group(1)) <= level:
            end = i
            break
    if end - start < 4 or end - start > 230:
        raise Section304Blocked("Official Markdown section has implausible bounds")
    content = "".join(lines[start:end])
    section = {
        "anchor": "",  # caller binds to validated first-party HTML id
        "heading": heading,
        "line_start": start + 1,
        "line_end": end,
        "section_sha256": sha(content.encode("utf-8")),
    }
    return section, content


def audit(docs: Path, *, time: datetime | None = None) -> tuple[dict, dict[str, dict]]:
    if not docs.is_dir() or docs.is_symlink():
        raise Section304Blocked("Original private first-party documents are not available")
    source_registry = load_registry(ROOT / "sources/registry.json")
    captures = bounded_json(OBS)
    prior = bounded_json(ORIGINAL)
    observation = {item["source_id"]: item for item in captures["snapshot_metadata_observations"]}
    older = {item["claim_id"]: item for item in prior["rows"]}
    if set(older) != set(SECTIONS) or len(observation) != 7:
        raise Section304Blocked("Previous candidate/source review record incomplete")
    reviewed_at = (
        (time or datetime.now(UTC))
        .astimezone(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    doc_pages: dict[str, dict] = {}
    groups: dict[str, dict] = {}
    _known_observations(SNAPSHOT)  # Check immutable index and observation integrity.
    findings = []
    for cid, (sid, page, anchor, determination, witnesses) in SECTIONS.items():
        previous = older[cid]
        candidate_file = ROOT / f"claims/{cid}.json"
        if candidate_file.is_symlink() or not candidate_file.is_file():
            raise Section304Blocked("Unsafe or missing candidate")
        candidate = json.loads(candidate_file.read_text())
        source = source_registry[sid]
        record = observation[sid]
        if (
            candidate["lifecycle"] != "candidate"
            or candidate["decision_record"] is not None
            or sha(candidate_file.read_bytes()) != previous["claim_sha256"]
            or candidate["evidence"][0]["source_id"] != sid
            or candidate["evidence"][0]["snapshot_sha256"] != record["new_304_observed_html_sha256"]
            or candidate["evidence"][0]["role"] != "context"
            or candidate["evidence"][0]["locator"] != source["url"] + "#" + anchor
            or record["snapshot_approval"] != "not-approved"
            or record["semantic_assessment"] != "not-assessed"
            or source["snapshot"]["sha256"] == record["new_304_observed_html_sha256"]
        ):
            raise Section304Blocked("Original unapproved 304 candidate was altered")
        if page not in doc_pages:
            html_file, md_file = docs / (page + ".html"), docs / (page + ".md")
            if any(
                not p.is_file() or p.is_symlink() or not 1000 < p.stat().st_size < 2_000_000
                for p in (html_file, md_file)
            ):
                raise Section304Blocked("Untrusted or unbounded original official document")
            html_raw, md_raw = html_file.read_bytes(), md_file.read_bytes()
            if sha(html_raw) != record["new_304_observed_html_sha256"]:
                raise Section304Blocked("Original observed HTML hash mismatch")
            if sha(md_raw) != previous["current_markdown_sha256"]:
                raise Section304Blocked("Original independently captured Markdown hash mismatch")
            headings = Headings()
            headings.feed(html_raw.decode("utf-8"))
            doc_pages[page] = {"html": html_raw, "md": md_raw, "headings": headings.found}
        page_data = doc_pages[page]
        actual = page_data["headings"].get(anchor)
        if (
            actual is None
            or actual[1] != previous["current_html_heading"]
            or actual[0] != previous["current_html_heading_tag"]
        ):
            raise Section304Blocked("Official HTML heading identity drift")
        section, content = exact_markdown_section(page_data["md"], actual[1], actual[0])
        if not all(w in content for w in witnesses):
            raise Section304Blocked("Reviewed section misses required technical semantics")
        # Deliberately distinguish old documentation context from new release-specific facts.
        if determination == "context_only_release_delta":
            missing_fact = {
                "K-0070": "decider: 'person'",
                "K-0071": "isReadOnly",
                "K-0072": "skips one of your mod's hooks",
                "K-0073": "failed mod reload removing the tools",
            }[cid]
            if missing_fact.lower() in content.lower():
                raise Section304Blocked(
                    "Previously missing release fact now appears; re-review determination"
                )
        section["anchor"] = anchor
        group = groups.setdefault(
            sid,
            {
                "schema_version": 1,
                "source_id": sid,
                "html_url": source["url"],
                "html_sha256": sha(page_data["html"]),
                "markdown_url": source["url"] + ".md",
                "markdown_sha256": sha(page_data["md"]),
                "reviewed_at": reviewed_at,
                "reviewer": "ChatGPT-CLI304-firstparty-section-review-20261021",
                "scope": "Claude Code CLI 2.1.304 first-party Markdown section review ONLY; no target-304 Claim approval, runtime host assertion, or user authority attestation.",
                "sections": [],
            },
        )
        if any(s["anchor"] == anchor for s in group["sections"]):
            raise Section304Blocked("Duplicate source section")
        group["sections"].append(section)
        findings.append(
            {
                "claim_id": cid,
                "original_candidate_sha256": sha(candidate_file.read_bytes()),
                "source_id": sid,
                "locator": source["url"] + "#" + anchor,
                "source_html_sha256": sha(page_data["html"]),
                "source_markdown_sha256": sha(page_data["md"]),
                "section_sha256": section["section_sha256"],
                "line_start": section["line_start"],
                "line_end": section["line_end"],
                "semantic_determination": determination,
                "source_section_reviewed": True,
                "full_new_release_behavior_verified": False,
                "native_real_host_verified": False,
                "claim_lifecycle_unchanged_candidate": True,
            }
        )
    if len(groups) != 3 or len(findings) != 5:
        raise Section304Blocked("Expected five bounded sections across exactly three sources")
    # Validate each newly prepared review without allowing a Claim transition.
    result = {
        "schema_version": 1,
        "review_target": TARGET,
        "source_sections_reviewed": len(findings),
        "unique_current_official_source_revisions": len(groups),
        "firstparty_document_semantics_directly_sufficient_for_full_release_delta": 0,
        "firstparty_document_supports_narrow_catch_guidance": 1,
        "source_context_only_pending_release_delta": 4,
        "target_304_claims_approved": 0,
        "candidate_304_claims_unchanged": 5,
        "real_host_permission_dialog_verified": False,
        "real_host_reload_and_skip_transcript_verified": False,
        "original_registry_pins_unchanged": True,
        "public_source_text_exported": False,
        "reviewer_identity_cryptographically_attested": False,
        "reviewed_at": reviewed_at,
        "findings": findings,
        "review_record_hashes": {},
    }
    for sid, record in groups.items():
        record["sections"] = sorted(record["sections"], key=lambda item: item["line_start"])
        raw = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        result["review_record_hashes"][sid] = {
            "review_path": f"sources/reviews/revisions/{sid}/{record['html_sha256']}.json",
            "review_sha256": sha(raw),
        }
    return result, groups


def save(report: dict, groups: dict, output: Path) -> None:
    if output.exists() or output.is_symlink():
        raise Section304Blocked("Do not overwrite an existing official section review report")
    paths = [ROOT / row["review_path"] for row in report["review_record_hashes"].values()]
    if any(p.exists() or p.is_symlink() for p in paths):
        raise Section304Blocked("Do not overwrite existing source revision reviews")
    for sid, group in groups.items():
        target = ROOT / report["review_record_hashes"][sid]["review_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(group, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    sources = load_registry(ROOT / "sources/registry.json")
    snapshot = _known_observations(SNAPSHOT)
    for sid, group in groups.items():
        source = sources[sid]
        sha256 = group["html_sha256"]
        reviewed_file = ROOT / report["review_record_hashes"][sid]["review_path"]
        revised_source = dict(source)
        revised_source["snapshot"] = {
            **source["snapshot"],
            "sha256": sha256,
            "checked_at": group["reviewed_at"],
        }
        for sec in group["sections"]:
            if not validate_official_review(
                revised_source,
                sha256,
                sec["anchor"],
                ROOT / "sources/reviews",
                SNAPSHOT,
                revision_review_file=reviewed_file,
            ):
                raise Section304Blocked("Official section review did not validate structurally")
            # Prove the updated review can eventually support a new CLI304 Claim,
            # but DOES NOT itself alter that Claim or grant it approved status.
            entry = {
                "source_id": sid,
                "locator": source["url"] + "#" + sec["anchor"],
                "snapshot_sha256": sha256,
                "role": "supports",
                "kind": "official-doc",
            }
            if not _is_pinned_official_support(
                entry, source, SNAPSHOT, snapshot, required_version=TARGET
            ):
                raise Section304Blocked(
                    "Reviewed revision cannot be validated by Claim source gate"
                )
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-firstparty-docs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--reviewed-at",
        default=None,
        help="Pin an existing UTC ISO timestamp for deterministic replay",
    )
    args = parser.parse_args()
    try:
        at = (
            datetime.fromisoformat(args.reviewed_at.replace("Z", "+00:00"))
            if args.reviewed_at
            else None
        )
        if at is not None and (
            at.tzinfo is None or at.utcoffset() is None or at > datetime.now(UTC)
        ):
            raise Section304Blocked("Review timestamp must be observed UTC time, not future")
        result, sections = audit(args.private_firstparty_docs, time=at)
        save(result, sections, args.out)
    except (Section304Blocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit(
            "BLOCKED: exact original official CLI304 section source was not verified"
        ) from None
    print(
        json.dumps(
            {
                "current_source_revision_records": len(sections),
                "reviewed_section_anchors": len(result["findings"]),
                "direct_narrow_hook_catch_section": 1,
                "other_release_delta_semantics_unverified": 4,
                "new_304_claims_approved": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
