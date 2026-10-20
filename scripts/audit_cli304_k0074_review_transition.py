#!/usr/bin/env python3
"""Audit K-0074 as source-REVIEWED only; no production host approval.

This checks original candidate SHA, current reviewed section, legal
candidate->reviewed event chain, and strict CLI304 publication blockers.
No account, model, external network or file mutation is performed by audit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from mods_knowledge.claims import (
    _is_pinned_official_support,
    _known_observations,
    approved_claims,
    load_claims,
)
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.decisions import _hash, validate_ledger
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
CID = "K-0074"
SOURCE = ROOT / "docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json"
CREATED = ROOT / "docs/reports/2026-10-20-cli304-five-highrisk-pending-claims.json"
NATIVE = ROOT / "docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json"


class CLI304ReviewBlocked(ValueError):
    """Unreviewed target version or untrusted approval event detected."""


def sha(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def audit(root: Path = ROOT) -> dict:
    claim_file = root / "claims/K-0074.json"
    ledger_file = root / "decisions/K-0074.json"
    if any(not p.is_file() or p.is_symlink() for p in (claim_file, ledger_file)):
        raise CLI304ReviewBlocked("Missing official Claim or decision event")
    claims = load_claims(
        root / "claims",
        load_registry(root / "sources/registry.json"),
        root / "sources/snapshots",
        root / "decisions",
    )
    claim = claims.get(CID)
    ledger = json.loads(ledger_file.read_text())
    review = json.loads((root / SOURCE.relative_to(ROOT)).read_text())
    old = json.loads((root / CREATED.relative_to(ROOT)).read_text())
    native = json.loads((root / NATIVE.relative_to(ROOT)).read_text())
    old_row = next(x for x in old["pending_claims"] if x["claim_id"] == CID)
    found = next(x for x in review["findings"] if x["claim_id"] == CID)
    if (
        claim is None
        or claim["lifecycle"] != "reviewed"
        or claim["authority"] != "guidance"
        or claim["verification"]
        != {"source": "reviewed", "runtime": "not-run", "runtime_profiles": [], "test_evidence": []}
        or claim["applies_to"]["claude_code"]
        != {"min_inclusive": "2.1.304", "max_exclusive": "2.1.305"}
        or claim["decision_record"] != "decisions/K-0074.json"
        or len(claim["evidence"]) != 1
        or claim["evidence"][0]["role"] != "supports"
        or claim["evidence"][0]["locator"] != found["locator"]
        or found["semantic_determination"] != "direct_documented_behavior_narrow_native_subset"
        or found["source_section_reviewed"] is not True
        or found["source_html_sha256"] != claim["evidence"][0]["snapshot_sha256"]
        or old_row["claim_sha256"] != found["original_candidate_sha256"]
        or native["reviewed_target_cli"] != "2.1.304"
        or native["native_synthetic_permission_cases_passed"] != 6
        or native["actual_host_person_dialog_approved"] is not False
    ):
        raise CLI304ReviewBlocked("Incomplete genuine source-reviewed K-0074 provenance")
    validate_ledger(claim, ledger)
    if len(ledger["events"]) != 1:
        raise CLI304ReviewBlocked("K-0074 must have exactly one source-review transition")
    event = ledger["events"][0]
    if (
        event["from_state"] != "candidate"
        or event["to_state"] != "reviewed"
        or not event["actor"].startswith("ChatGPT-CLI304-P1-source-review")
        or "No real human permission host" not in event["rationale"]
        or event["claim_after_sha256"] != _hash(claim)
    ):
        raise CLI304ReviewBlocked("K-0074 transition is not an audited source review")
    before = copy.deepcopy(claim)
    before["lifecycle"] = "candidate"
    before["decision_record"] = None
    if event["claim_before_sha256"] != _hash(before):
        raise CLI304ReviewBlocked("Audited pre-transition candidate source revision differs")
    registry = load_registry(root / "sources/registry.json")
    source = registry["M004"]
    snapshots = root / "sources/snapshots"
    if not _is_pinned_official_support(
        claim["evidence"][0],
        source,
        snapshots,
        _known_observations(snapshots),
        required_version="2.1.304",
    ):
        raise CLI304ReviewBlocked("First-party target source revision review missing")
    if (
        len(approved_claims(claims, "2.1.302", "cli")) != 31
        or approved_claims(claims, "2.1.304", "cli")
        or sum(c["lifecycle"] == "candidate" for c in claims.values()) != 9
        or sum(c["lifecycle"] == "reviewed" for c in claims.values()) != 1
    ):
        raise CLI304ReviewBlocked("Version-specific new Claim unintentionally promoted")
    try:
        compile_knowledge(root, api_version="2.1.304", surface="cli", source_revision="review-only")
    except CompilerError as exc:
        if "No approved Claims" not in str(exc):
            raise CLI304ReviewBlocked("Unexpected new-version compiler gate") from exc
    else:
        raise CLI304ReviewBlocked("Forbidden 304 Skill compiled without approved Claims")
    return {
        "schema_version": 1,
        "source_reviewed_only_claim": CID,
        "target_version": "2.1.304",
        "previous_unapproved_candidate_file_sha256": old_row["claim_sha256"],
        "current_reviewed_claim_file_sha256": sha(claim_file),
        "reviewed_claim_canonical_sha256": _hash(claim),
        "pre_review_candidate_canonical_sha256": _hash(before),
        "one_source_review_transition_event_sha256": event["event_sha256"],
        "transition_ledger_sha256": sha(ledger_file),
        "first_party_reviewed_section_sha256": found["section_sha256"],
        "official_source_review_report_sha256": sha(root / SOURCE.relative_to(ROOT)),
        "native_synthetic_toolcheck_report_sha256": sha(root / NATIVE.relative_to(ROOT)),
        "exact_reviewed_target_source": found["locator"],
        "native_synthetic_permission_tests_observed": 6,
        "reviewed_lifecycle_count": 1,
        "still_unapproved_candidates_count": 9,
        "approved_302_claims_unchanged": 31,
        "approved_304_claims": 0,
        "runtime_host_permission_test_status": "not-run",
        "real_human_permission_host_verified": False,
        "approved_304_skill_compilable": False,
        "reviewer_label_is_cryptographic_identity": False,
        "original_302_approved_claims_or_decisions_rewritten": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable source-reviewed-only report exists")
    try:
        result = audit()
    except (CLI304ReviewBlocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: K-0074 source-only review or release gate invalid") from None
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "reviewed": 1,
                "candidate": result["still_unapproved_candidates_count"],
                "approved_cli304": result["approved_304_claims"],
                "real_host_permission_verified": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
