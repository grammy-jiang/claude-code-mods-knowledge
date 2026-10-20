#!/usr/bin/env python3
"""Deterministic, nonpromoting 31-Claim CLI302 -> unapproved CLI304 review.

The canonical historical approved Claims and decisions are NEVER changed.
A genuine 304 release note, native core .d.ts difference and sandboxed
permission mock are useful only as preapproval evidence; they do not
qualify even one 304 Skill/Plugin Claim. Source fingerprints, 304 scoped
mock evidence and all 31 explicit review questions are individually
reverified before emitting sanitized, CI-stable triage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
POLICY = "evals/cli304_claim_transition_triage.json"
RELEASE_SHA_304 = "7a6144fde0e5e4733c1108e1890430722c12839159aeb1a5be7bec8aaa881cf8"
CORE_SHA_302 = "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
CORE_SHA_304 = "6694767741c445872577d96a55fb08816d0f4b5783bc49e1eacd55f27b383308"
EXPECTED_COUNT = 31
REVIEW_LANES = frozenset(
    (
        "first_party_delta_touchpoint",
        "native_mock_subset_not_full_host",
        "fresh_target_official_review_required",
        "known_302_source_type_conflict_blocking_promotion",
    )
)
KNOWN_304_DIFFERENCES = frozenset(
    (
        "tool.check.answer.decider.person",
        "tool.check.event.isReadOnly",
        "mod.hook.skip.transcript.diagnostic",
        "mod.hot_reload.failure.recovery",
    )
)


class TransitionBlocked(ValueError):
    """Do not publish incomplete, forged or unreviewed target-scoped facts."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(root: Path, relative: str) -> dict:
    target = root / relative
    if not target.is_file() or target.is_symlink() or not 0 < target.stat().st_size < 180_000:
        raise TransitionBlocked("Missing or untrusted reviewed source record: " + relative)
    obj = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise TransitionBlocked("Reviewed evidence record must be JSON object")
    return obj


def audit(root: Path = ROOT) -> dict:
    root = Path(root)
    policy = _load(root, POLICY)
    release = _load(root, policy["official_release_evidence_path"])
    core = _load(root, policy["official_core_diff_path"])
    permission = _load(root, policy["official_native_mock_path"])
    original_type = _load(root, policy["original_302_type_conflict_path"])
    if (
        policy.get("schema_version") != 1
        or policy.get("baseline_reviewed_cli") != "2.1.302"
        or policy.get("candidate_unapproved_cli") != "2.1.304"
        or policy.get("triage_not_a_claim_approval") is not True
        or policy.get("approval_outcome") != "ALL_31_REQUIRE_INDEPENDENT_TARGET_304_CLAIM_REVIEW"
        or release.get("source_review_status")
        != "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI304_API_CLAIMS"
        or release.get("version_304_api_compatibility_proven") is not False
        or core.get("new_304_core_types_sha256") != CORE_SHA_304
        or core.get("reference_302_core_types_sha256") != CORE_SHA_302
        or core.get("same_source_302_rejected_and_304_accepted") is not True
        or core.get("complete_304_api_contract_verified") is True
        or permission.get("real_user_approval_dialog_tested") is not False
        or permission.get("fully_reviewed_cli304_skill_approved") is not False
        or original_type.get("core_declarations_sha256") != CORE_SHA_302
        or original_type.get("original_fail") != 3
        or original_type.get("test_only_ui_log_remediation_typecheck_pass") != 5
    ):
        raise TransitionBlocked("304 first-party evidence or 302 historical result mismatch")
    upstream_releases = {
        release_row.get("version"): release_row for release_row in release.get("releases", [])
    }
    upstream304 = upstream_releases.get("2.1.304")
    if (
        not isinstance(upstream304, dict)
        or upstream304.get("official_body_sha256") != RELEASE_SHA_304
        or {item.get("kind") for item in upstream304.get("relevant_mods_deltas", [])}
        != KNOWN_304_DIFFERENCES
        or release.get("compiler_version_304_publish_authorized") is not False
    ):
        raise TransitionBlocked("Official 304 release provenance changed or missing")

    sources = load_registry(root / "sources/registry.json")
    all_claims = load_claims(
        root / "claims",
        sources,
        root / "sources/snapshots",
        root / "decisions",
    )
    historical = approved_claims(all_claims, "2.1.302", "cli")
    current = approved_claims(all_claims, "2.1.304", "cli")
    if len(historical) != EXPECTED_COUNT or current:
        raise TransitionBlocked("304 target was promoted or original 31 Claims changed")
    historical_by_id = {c["claim_id"]: c for c in historical}
    policy_rows = policy.get("decisions")
    if (
        not isinstance(policy_rows, dict)
        or set(policy_rows) != set(historical_by_id)
        or len(policy_rows) != EXPECTED_COUNT
    ):
        raise TransitionBlocked("No partial 304 review matrix is allowed")
    legacy = historical_by_id.get("K-0068")
    if (
        not legacy
        or "console.log(" not in legacy["statement"]
        or "tool.call" not in legacy["statement"]
        or "K-0037" not in legacy.get("supersedes", [])
        or policy_rows["K-0068"].get("review_lane")
        != "known_302_source_type_conflict_blocking_promotion"
        or original_type.get("original_known_console_type_errors") != 3
    ):
        raise TransitionBlocked("Known 302 approved source/type contradiction must remain visible")

    rows = []
    for cid, claim in sorted(historical_by_id.items()):
        review = policy_rows[cid]
        if (
            not isinstance(review, dict)
            or review.get("review_lane") not in REVIEW_LANES
            or review.get("new_304_claim_authorized") is not False
            or not isinstance(review.get("specific_review_question"), str)
            or not 40 <= len(review["specific_review_question"]) <= 260
        ):
            raise TransitionBlocked("Each individual Claim needs a source-specific review reason")
        scope = claim["applies_to"]["claude_code"]
        if scope.get("min_inclusive") != "2.1.302" or scope.get("max_exclusive") != "2.1.303":
            raise TransitionBlocked("Reviewed 302 Claim unexpectedly covers unreviewed 304")
        primary = claim["areas"]["primary"]
        official_urls = sorted(
            {
                evidence["locator"]
                for evidence in claim["evidence"]
                if evidence.get("role") == "supports"
                and evidence.get("kind") == "official-doc"
                and evidence.get("locator", "").startswith(
                    "https://code.claude.com/docs/en/plugins/mods/"
                )
            }
        )
        if not official_urls or not primary:
            raise TransitionBlocked("Baseline Claim is missing exact official provenance")
        original_file = root / "claims" / f"{cid}.json"
        decision_file = root / "decisions" / f"{cid}.json"
        if not original_file.is_file() or not decision_file.is_file():
            raise TransitionBlocked("Original source Claim and approval decision must exist")
        rows.append(
            {
                "original_reviewed_claim_id": cid,
                "subject": claim["subject"],
                "original_claim_sha256": _sha(original_file.read_bytes()),
                "original_decision_sha256": _sha(decision_file.read_bytes()),
                "area": primary[0],
                "original_302_exact_official_urls": official_urls,
                "original_302_scope": "[2.1.302, 2.1.303)",
                "review_lane": review["review_lane"],
                "specific_review_question": review["specific_review_question"],
                "target_304_approval": "NOT_APPROVED_NEEDS_NEW_TARGET_REVIEW",
                "new_304_claim_created_or_approved": False,
            }
        )
    lane_counts = Counter(item["review_lane"] for item in rows)
    if lane_counts["known_302_source_type_conflict_blocking_promotion"] != 1:
        raise TransitionBlocked("Known original model type conflict must be individually blocked")
    return {
        "schema_version": 1,
        "reviewed_source_version": "2.1.302",
        "preapproval_only_target": "2.1.304",
        "approved_302_claims_scanned": EXPECTED_COUNT,
        "approved_304_claims_now": 0,
        "human_304_claim_review_completed": False,
        "target_304_skill_compilation_authorized": False,
        "target_304_model_host_qualification_completed": False,
        "full_46_chat_mode_304_qualified": False,
        "stable_release_authorized": False,
        "original_302_claim_or_decision_mutated": False,
        "review_plan_sha256": _sha((root / POLICY).read_bytes()),
        "official_304_release_body_sha256": RELEASE_SHA_304,
        "302_core_types_sha256": CORE_SHA_302,
        "304_core_types_sha256": CORE_SHA_304,
        "known_302_approved_claim_id_with_type_conflict": "K-0068",
        "issue": "Legacy K-0068 inline console logging example cannot typecheck under verified 302 core types",
        "review_lane_counts": dict(sorted(lane_counts.items())),
        "claims": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable prior preapproval report exists")
    try:
        report = audit()
    except (TransitionBlocked, OSError, KeyError, TypeError, ValueError):
        raise SystemExit("BLOCKED: incomplete/new target Claim preapproval") from None
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(
        {
            "source_302_claims": report["approved_302_claims_scanned"],
            "new_304_claims_approved": report["approved_304_claims_now"],
            "known_baseline_source_type_conflict": report[
                "known_302_approved_claim_id_with_type_conflict"
            ],
            "304_release_eligible": False,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
