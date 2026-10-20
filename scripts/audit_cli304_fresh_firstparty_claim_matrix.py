#!/usr/bin/env python3
"""Audit all 31 CLI302 Claims against CURRENT CLI304 first-party anchors.

The tool accepts independently fetched official HTML and Markdown in a
PRIVATE local directory, checks original source/decision byte identities,
then emits a sanitized *anchor-location and review-queue* report. Presence
of an anchor or matching heading is NOT semantic compatibility or Claim
approval; 304 requires new source revisions and host-specific decisions.
No network calls, model requests, or user account updates occur here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = "docs/reports/2026-10-20-cli304-31-claim-preapproval-audit.json"
TRIAGE = "evals/cli304_claim_transition_triage.json"
RELEASE = "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
CORE = "docs/reports/2026-10-20-cli304-official-core-type-compatibility.json"
NATIVE = "docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json"
PAGES = ("admin", "create", "events", "interface", "overview", "reference", "test")
LANES = {
    "first_party_delta_touchpoint": 8,
    "native_mock_subset_not_full_host": 8,
    "fresh_target_official_review_required": 14,
    "known_302_source_type_conflict_blocking_promotion": 1,
}


class Current304SourceBlocked(ValueError):
    """At least one first-party document, Claim or decision is unverified."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 150_000:
        raise Current304SourceBlocked("Unavailable or unbounded source evidence JSON")
    result = json.loads(path.read_text())
    if not isinstance(result, dict):
        raise Current304SourceBlocked("Source evidence JSON must be an object")
    return result


class HeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[dict] = []
        self.current: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("h2", "h3", "h4"):
            self.current = {"tag": tag, "id": dict(attrs).get("id"), "text": []}

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is not None and tag == self.current["tag"]:
            heading = self.current
            heading["text"] = " ".join("".join(heading["text"]).replace("\u200b", "").split())
            self.headings.append(heading)
            self.current = None


def read_page(page: str, private: Path) -> dict:
    if page not in PAGES:
        raise Current304SourceBlocked("Unreviewed first-party page")
    html_file = private / f"{page}.html"
    md_file = private / f"{page}.md"
    if any(
        not path.is_file() or path.is_symlink() or not 1000 < path.stat().st_size < 2_000_000
        for path in (html_file, md_file)
    ):
        raise Current304SourceBlocked("Missing bounded official documentation HTML/Markdown")
    html_raw = html_file.read_bytes()
    md_raw = md_file.read_bytes()
    if (
        b"code.claude.com" not in html_raw
        or b"Claude Code" not in html_raw
        or b"> ## Documentation Index" not in md_raw[:400]
        or bytes((10, 35, 32)) not in md_raw[:2500]
    ):
        raise Current304SourceBlocked("Official docs response is wrong or blocked")
    parsed = HeadingParser()
    parsed.feed(html_raw.decode("utf-8"))
    ids = {}
    for entry in parsed.headings:
        if entry["id"] is not None:
            if entry["id"] in ids:
                raise Current304SourceBlocked("Ambiguous first-party anchor in HTML headings")
            ids[entry["id"]] = entry
    return {
        "html_sha256": sha(html_raw),
        "markdown_sha256": sha(md_raw),
        "html_bytes": len(html_raw),
        "markdown_bytes": len(md_raw),
        "headings": ids,
        "markdown_text_lower": md_raw.decode("utf-8").lower(),
    }


def audit(root: Path, private_docs: Path) -> dict:
    if not private_docs.is_dir() or private_docs.is_symlink():
        raise Current304SourceBlocked("Current first-party docs not captured privately")
    prior = read_json(root / HISTORICAL)
    triage = read_json(root / TRIAGE)
    official = read_json(root / RELEASE)
    core = read_json(root / CORE)
    native = read_json(root / NATIVE)
    registry = load_registry(root / "sources/registry.json")
    claims = load_claims(root / "claims", registry, root / "sources/snapshots", root / "decisions")
    if (
        prior["approved_302_claims_scanned"] != 31
        or prior["approved_304_claims_now"] != 0
        or len(prior["claims"]) != 31
        or len(approved_claims(claims, "2.1.302", "cli")) != 31
        or approved_claims(claims, "2.1.304", "cli")
        or triage["approval_outcome"] != "ALL_31_REQUIRE_INDEPENDENT_TARGET_304_CLAIM_REVIEW"
        or len(triage["decisions"]) != 31
        or official["source_review_status"]
        != "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI304_API_CLAIMS"
        or official["version_304_api_compatibility_proven"] is not False
        or core["same_source_302_rejected_and_304_accepted"] is not True
        or native["reviewed_target_cli"] != "2.1.304"
        or native["native_synthetic_permission_cases_passed"] != 6
        or native["actual_host_person_dialog_approved"] is not False
        or native["actual_host_readonly_classification_verified"] is not False
    ):
        raise Current304SourceBlocked("Version-mismatched, promoted or incomplete review baseline")
    pages = {name: read_page(name, private_docs) for name in PAGES}
    rows = []
    matched = 0
    seen_ids = set()
    used_anchors: set[tuple[str, str]] = set()
    lane_counts = Counter()
    for original in prior["claims"]:
        cid = original["original_reviewed_claim_id"]
        if cid in seen_ids or cid not in triage["decisions"] or cid not in claims:
            raise Current304SourceBlocked("Duplicate or unrecognized historical target Claim")
        seen_ids.add(cid)
        target = claims[cid]
        if (
            sha((root / f"claims/{cid}.json").read_bytes()) != original["original_claim_sha256"]
            or sha((root / f"decisions/{cid}.json").read_bytes())
            != original["original_decision_sha256"]
            or target["lifecycle"] != "approved"
            or target["applies_to"]["claude_code"]
            != {"min_inclusive": "2.1.302", "max_exclusive": "2.1.303"}
        ):
            raise Current304SourceBlocked("Original version-reviewed Claim/decision drift")
        lane = original["review_lane"]
        rule = triage["decisions"][cid]
        if lane != rule["review_lane"] or rule["new_304_claim_authorized"] is not False:
            raise Current304SourceBlocked("Unrecognized target-304 risk classification")
        anchors = []
        for url in original["original_302_exact_official_urls"]:
            parsed = urlsplit(url)
            page = parsed.path.rsplit("/", 1)[-1]
            source = next((s for s in registry.values() if s["url"] == url.split("#")[0]), None)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "code.claude.com"
                or page not in pages
                or not source
                or source["trust_layer"] not in ("L0", "L1", "L2")
                or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", parsed.fragment)
            ):
                raise Current304SourceBlocked("Untrusted source URL or original anchor")
            heading = pages[page]["headings"].get(parsed.fragment)
            if not heading or heading["text"].lower() not in pages[page]["markdown_text_lower"]:
                raise Current304SourceBlocked("Official target anchor missing from HTML/Markdown")
            used_anchors.add((page, parsed.fragment))
            matched += 1
            anchors.append(
                {
                    "firstparty_original_exact_locator": url,
                    "source_id": source["source_id"],
                    "current_html_heading": heading["text"],
                    "current_html_heading_tag": heading["tag"],
                    "html_anchor_present_once": True,
                    "matching_heading_in_markdown": True,
                }
            )
        lane_counts[lane] += 1
        rows.append(
            {
                "prior_302_claim": cid,
                "subject": original["subject"],
                "original_claim_sha256": original["original_claim_sha256"],
                "original_decision_sha256": original["original_decision_sha256"],
                "current_304_official_anchor_checks": anchors,
                "review_lane": lane,
                "specific_review_question": rule["specific_review_question"],
                "first_party_structural_verdict": "ANCHORS_VERIFIED_ONLY",
                "api_semantics_verified_for_304": False,
                "new_304_claim_approved": False,
                "next_required_verification": (
                    "review_exact_target_docs_and_types_then_native_host_semantics_and_decision"
                ),
            }
        )
    if len(rows) != 31 or dict(lane_counts) != LANES or matched != 32:
        raise Current304SourceBlocked("Incomplete 304 claim/anchor coverage")
    source_pages = []
    for page, data in sorted(pages.items()):
        source = next(s for s in registry.values() if s["url"].endswith("/" + page))
        source_pages.append(
            {
                "source_id": source["source_id"],
                "official_url": source["url"],
                "original_registry_pinned_html_sha256": source["snapshot"]["sha256"],
                "fresh_html_sha256": data["html_sha256"],
                "fresh_markdown_sha256": data["markdown_sha256"],
                "fresh_html_bytes": data["html_bytes"],
                "fresh_markdown_bytes": data["markdown_bytes"],
                "original_pinned_revision_not_modified": True,
            }
        )
    return {
        "schema_version": 1,
        "source_capture_day_sydney": "2026-10-20",
        "review_target": "2.1.304",
        "prior_reviewed_target": "2.1.302",
        "prior_302_claims_checked": 31,
        "fresh_official_html_and_markdown_pages": len(source_pages),
        "first_party_original_locator_occurrences_verified": matched,
        "unique_fresh_html_heading_ids_verified": len(used_anchors),
        "all_31_current_official_anchors_are_present": True,
        "all_31_target_api_semantics_verified": False,
        "approved_new_304_claims": 0,
        "review_lane_counts": dict(lane_counts),
        "native_synthetic_permission_tests_passed": native[
            "native_synthetic_permission_cases_passed"
        ],
        "unreviewed_default_readonly_mock_isReadOnly": native[
            "simulated_read_without_explicit_metadata_isReadOnly"
        ],
        "real_host_permission_callback_verified": False,
        "toolcheck_native_test_evidence_sha256": sha((root / NATIVE).read_bytes()),
        "original_31_claim_preapproval_sha256": sha((root / HISTORICAL).read_bytes()),
        "official_release_fact_evidence_sha256": sha((root / RELEASE).read_bytes()),
        "official_core_type_evidence_sha256": sha((root / CORE).read_bytes()),
        "fresh_source_revisions_not_promoted_into_approved_SSOT": True,
        "full_native_304_host_acceptance": False,
        "p4_chat_mode_acceptance": False,
        "stable_release_authorized": False,
        "source_pages": source_pages,
        "claim_review_queue": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-official-pages", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    opts = parser.parse_args()
    if opts.out.exists() or opts.out.is_symlink():
        raise SystemExit("REFUSED: first-party review report is immutable")
    try:
        report = audit(ROOT, opts.private_official_pages)
    except (Current304SourceBlocked, ValueError, OSError, KeyError, TypeError):
        raise SystemExit("BLOCKED: CLI304 first-party 31-Claim anchor evidence invalid") from None
    opts.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "prior_claims_reviewed_structurally": report["prior_302_claims_checked"],
                "firstparty_source_pages": report["fresh_official_html_and_markdown_pages"],
                "exact_anchors_verified": report[
                    "first_party_original_locator_occurrences_verified"
                ],
                "unique_anchors": report["unique_fresh_html_heading_ids_verified"],
                "native_synthetic_permission_cases": report[
                    "native_synthetic_permission_tests_passed"
                ],
                "new_304_claims_approved": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
