#!/usr/bin/env python3
"""Create FIVE unapproved CLI304 high-risk claim CANDIDATES from fresh evidence.

No source review or Claim transition is performed. The candidates refer to
SHA-indexed *unreviewed* HTML observations and separately pinned 304 release
facts/native mocks, explicitly disclose missing real host proof, and must NOT
be included in compiled Skills. Existing 302 Claims/decisions stay immutable.
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
RELEASE = ROOT / "evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json"
NATIVE = ROOT / "docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json"
OBS = ROOT / "docs/reports/2026-10-20-cli304-seven-unapproved-source-observations.json"
BASE = "https://code.claude.com/docs/en/plugins/mods/"
RELEASE_URL = "https://github.com/anthropics/claude-code/releases/tag/v2.1.304"
# New ideas are NOT an approval to reuse older 302 code or permission behavior.
SPEC = {
    "K-0070": {
        "subject": "mods.tool-check-human-only-person-decider-cli304-pending",
        "statement": (
            "CLI 2.1.304 release notes describe an optional tool.check answer decider "
            "'person' for an ask: the actual human permission dialog or host callback "
            "must approve, and an unattended request is refused. The reviewed 304 "
            "synthetic native test preserves a mocked Write ask with decider 'person', "
            "but real dialogs, absence of a person, managed policy precedence and "
            "actual tool side effects remain untested. This is a pending source "
            "and runtime compatibility question, NOT a release-ready API promise."
        ),
        "source_id": "M004",
        "anchor": "approve-or-refuse-a-tool-call-before-the-user-is-asked",
        "kind": "behavior",
        "areas": {"primary": ["P"], "secondary": ["E", "Q"]},
        "related": ["K-0043", "K-0058"],
    },
    "K-0071": {
        "subject": "mods.tool-check-readonly-input-metadata-cli304-pending",
        "statement": (
            "CLI 2.1.304 release notes introduce optional e.isReadOnly metadata for "
            "tool.check, and the exact native 304 core declaration accepts "
            "isReadOnly?: true. A native synthetic Read check left e.isReadOnly "
            "undefined by default, while explicitly injected true was observable. "
            "Actual real-host read-only classification, agent distinctions, "
            "event immutability across plugins and permission precedence remain "
            "unverified, so this candidate cannot authorize host behavior."
        ),
        "source_id": "M003",
        "anchor": "events",
        "kind": "behavior",
        "areas": {"primary": ["T"], "secondary": ["P", "E"]},
        "related": ["K-0041", "K-0048", "K-0058"],
    },
    "K-0072": {
        "subject": "mods.prior-plugin-hook-skip-transcript-cli304-pending",
        "statement": (
            "CLI 2.1.304 release notes report a new user-facing transcript line "
            "when an earlier plugin skips a later Mod hook, naming the event "
            "and the plugin. The current official Events section documents "
            "hook ordering, but target-matched two-plugin skip propagation, "
            "transcript readback and host surface consistency have not yet "
            "been verified. Keep this as an unapproved behavior candidate."
        ),
        "source_id": "M004",
        "anchor": "the-order-mods-run-in",
        "kind": "behavior",
        "areas": {"primary": ["E"], "secondary": ["Q", "U"]},
        "related": ["K-0042", "K-0063"],
    },
    "K-0073": {
        "subject": "mods.failed-reload-existing-tools-recovery-cli304-pending",
        "statement": (
            "CLI 2.1.304 release notes say a failed Mod reload no longer "
            "removes the commands and tools of the previously loaded version "
            "and improves reporting of which version remains active. Current "
            "state documentation is accessible, but genuine failed reload, "
            "session lifetime, state retention and command-tool availability "
            "are not yet covered by original target host evidence. This is "
            "only a pending version-scoped review candidate."
        ),
        "source_id": "M006",
        "anchor": "keep-state",
        "kind": "behavior",
        "areas": {"primary": ["S"], "secondary": ["E", "Q"]},
        "related": ["K-0044", "K-0045"],
    },
    "K-0074": {
        "subject": "mods.tool-check-registration-catch-deny-cli304-pending",
        "statement": (
            "The current official Events documentation describes registration "
            "catch behavior and recommends a deny outcome for a failed "
            "tool.check gate. In six synthetic native 304 tests a guarded "
            "permission hook preserved allow/ask/deny and denied a forced "
            "exception; negative controls caught an unguarded gate and a "
            "denial-to-allow override. Real host managed-rule precedence, "
            "human approval and genuine user tools remain untested, so this "
            "source-scoped diagnostic is NOT a fully approved 304 Claim."
        ),
        "source_id": "M004",
        "anchor": "handle-a-hook-that-fails",
        "kind": "best-practice",
        "areas": {"primary": ["P"], "secondary": ["E", "Q"]},
        "related": ["K-0043", "K-0058", "K-0068"],
    },
}


class New304CandidateBlocked(ValueError):
    """Unreviewed new 304 evidence cannot become an approved Claim."""


def _sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _read(file: Path) -> dict:
    if not file.is_file() or file.is_symlink() or file.stat().st_size > 180_000:
        raise New304CandidateBlocked("Missing SHA-pinned official 304 source record")
    return json.loads(file.read_text())


def create_candidates() -> list[dict]:
    registry = load_registry(ROOT / "sources/registry.json")
    all_claims = load_claims(
        ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions"
    )
    if len(approved_claims(all_claims, "2.1.302", "cli")) != 31 or approved_claims(
        all_claims, "2.1.304", "cli"
    ):
        raise New304CandidateBlocked("Wrong versioned original approvals")
    if any(cid in all_claims or (ROOT / f"claims/{cid}.json").exists() for cid in SPEC):
        raise New304CandidateBlocked("Refuse to overwrite existing Claim")
    if verify_snapshot_store(ROOT / "sources/snapshots"):
        raise New304CandidateBlocked("Immutable source store checksum mismatch")
    obs, upstream, native = (_read(file) for file in (OBS, RELEASE, NATIVE))
    captured = {x["source_id"]: x for x in obs["snapshot_metadata_observations"]}
    release = upstream["releases"][1]
    if (
        obs["target_version_under_review"] != "2.1.304"
        or obs["approved_304_claims"] != 0
        or obs["first_party_documents_recorded_unapproved"] != 7
        or upstream["source_review_status"]
        != "RELEASE_NOTE_FACTS_CAPTURED_NOT_APPROVED_CLI304_API_CLAIMS"
        or release["upstream_url"] != RELEASE_URL
        or native["reviewed_target_cli"] != "2.1.304"
        or native["native_synthetic_permission_cases_passed"] != 6
        or native["actual_host_person_dialog_approved"] is not False
        or native["actual_host_readonly_classification_verified"] is not False
    ):
        raise New304CandidateBlocked("Missing official release and native caveats")
    out = []
    for cid, spec in SPEC.items():
        source = registry[spec["source_id"]]
        snapshot = captured[spec["source_id"]]
        digest = snapshot["new_304_observed_html_sha256"]
        if (
            digest == source["snapshot"]["sha256"]
            or snapshot["snapshot_approval"] != "not-approved"
            or snapshot["semantic_assessment"] != "not-assessed"
            or not (
                ROOT / f"sources/snapshots/metadata/{spec['source_id']}/{digest}.json"
            ).is_file()
        ):
            raise New304CandidateBlocked("New version source was secretly approved")
        locator = BASE + source["url"].rsplit("/", 1)[1] + "#" + spec["anchor"]
        if not locator.startswith(source["url"] + "#"):
            raise New304CandidateBlocked("Untrusted official source heading")
        claim = {
            "claim_id": cid,
            "subject": spec["subject"],
            "statement": spec["statement"],
            "kind": spec["kind"],
            "areas": spec["areas"],
            "authority": "guidance",
            "lifecycle": "candidate",
            "applies_to": {
                "claude_code": {
                    "min_inclusive": "2.1.304",
                    "max_exclusive": "2.1.305",
                },
                "surfaces": ["cli"],
                "notes": "First-party 304 release delta and native subset; not approved for model use.",
            },
            "evidence": [
                {
                    "source_id": spec["source_id"],
                    "locator": locator,
                    "role": "context",
                    "kind": "official-doc",
                    "snapshot_sha256": digest,
                    "commit_sha": None,
                    "notes": (
                        "Unapproved HTML observation only, NOT an independently "
                        "reviewed supporting source section. Additional official "
                        "release: "
                        + RELEASE_URL
                        + "; native subset: "
                        + str(NATIVE.relative_to(ROOT))
                    ),
                }
            ],
            "related_claims": spec["related"],
            "supersedes": [],
            "decision_record": None,
            "verification": {
                "source": "indexed",
                "runtime": "not-run",
                "runtime_profiles": [],
                "test_evidence": [],
            },
        }
        out.append(claim)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-report", type=Path, required=True)
    args = parser.parse_args()
    if args.out_report.exists() or args.out_report.is_symlink():
        raise SystemExit("REFUSED: candidate preview output already exists")
    try:
        candidates = create_candidates()
    except (New304CandidateBlocked, OSError, ValueError, KeyError, TypeError):
        raise SystemExit("BLOCKED: approved 304 source evidence incomplete") from None
    preview = []
    for claim in candidates:
        path = ROOT / "claims" / (claim["claim_id"] + ".json")
        if path.exists() or path.is_symlink():
            raise SystemExit("REFUSED: a Claim ID is already allocated")
        raw = json.dumps(claim, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
        with path.open("x", encoding="utf-8") as handle:
            handle.write(raw)
        preview.append(
            {
                "claim_id": claim["claim_id"],
                "subject": claim["subject"],
                "claim_sha256": _sha(path),
                "status": "candidate_only_no_decision",
                "official_source_snapshot": claim["evidence"][0]["snapshot_sha256"],
            }
        )
    data = {
        "schema_version": 1,
        "reviewed_target": "2.1.304",
        "candidate_total": len(preview),
        "official_release_notes_sha256": _sha(RELEASE),
        "native_permission_mock_sha256": _sha(NATIVE),
        "unapproved_source_observations_sha256": _sha(OBS),
        "prior_302_approved_claims_untouched": 31,
        "cli304_new_claims_approved": 0,
        "firstparty_source_section_review_completed": False,
        "real_host_permission_callback_verified": False,
        "full_304_semantics_approved": False,
        "compiled_304_skill_allowed": False,
        "historical_decision_ledgers_modified": False,
        "stable_release_authorized": False,
        "pending_claims": preview,
    }
    args.out_report.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"candidate_only": len(preview), "approved": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
