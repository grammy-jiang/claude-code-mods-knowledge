"""K-0074 source REVIEW is auditable and can NOT silently become APPROVED.

For target CLI304+ security/permission guidance, a user-host integration-pass
is required in addition to an official Markdown section review. Synthetic
native permissions alone must never unlock a production Skill.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.decisions import _hash, transition_claim, validate_ledger
from mods_knowledge.errors import ClaimError
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-21-cli304-k0074-source-reviewed-only.json"
LEDGER = ROOT / "decisions/K-0074.json"
CLAIM = ROOT / "claims/K-0074.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_new_exact_official_review_has_one_audited_decision_event_not_approval():
    report = json.loads(REPORT.read_text())
    claim = json.loads(CLAIM.read_text())
    ledger = json.loads(LEDGER.read_text())
    assert report["schema_version"] == 1
    assert report["target_version"] == "2.1.304"
    assert report["source_reviewed_only_claim"] == "K-0074"
    assert report["current_reviewed_claim_file_sha256"] == sha(CLAIM)
    assert report["transition_ledger_sha256"] == sha(LEDGER)
    assert report["reviewed_claim_canonical_sha256"] == _hash(claim)
    assert claim["lifecycle"] == "reviewed"
    assert claim["verification"] == {
        "source": "reviewed",
        "runtime": "not-run",
        "runtime_profiles": [],
        "test_evidence": [],
    }
    assert claim["decision_record"] == "decisions/K-0074.json"
    assert len(ledger["events"]) == 1
    event = ledger["events"][0]
    assert event["from_state"] == "candidate"
    assert event["to_state"] == "reviewed"
    assert event["event_sha256"] == report["one_source_review_transition_event_sha256"]
    assert event["claim_after_sha256"] == report["reviewed_claim_canonical_sha256"]
    assert event["claim_before_sha256"] == report["pre_review_candidate_canonical_sha256"]
    assert event["previous_event_sha256"] is None
    assert "No real human permission host" in event["rationale"]
    validate_ledger(claim, ledger)
    assert report["original_302_approved_claims_or_decisions_rewritten"] is False
    assert report["reviewer_label_is_cryptographic_identity"] is False


def test_only_exact_current_official_catch_section_supports_reviewed_claim():
    report = json.loads(REPORT.read_text())
    doc = json.loads(
        (ROOT / "docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json").read_text()
    )
    source = next(x for x in doc["findings"] if x["claim_id"] == "K-0074")
    assert source["semantic_determination"] == "direct_documented_behavior_narrow_native_subset"
    assert report["first_party_reviewed_section_sha256"] == source["section_sha256"]
    assert report["exact_reviewed_target_source"] == source["locator"]
    assert report["official_source_review_report_sha256"] == sha(
        ROOT / "docs/reports/2026-10-21-cli304-five-reviewed-firstparty-sections.json"
    )
    assert report["native_synthetic_toolcheck_report_sha256"] == sha(
        ROOT / "docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json"
    )
    assert report["native_synthetic_permission_tests_observed"] == 6
    assert report["real_human_permission_host_verified"] is False
    assert report["runtime_host_permission_test_status"] == "not-run"


def test_reviewed_k0074_and_other_four_candidate_do_not_generate_an_approved_304_skill():
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(claims) == 74
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert approved_claims(claims, "2.1.304", "cli") == []
    assert sum(x["lifecycle"] == "reviewed" for x in claims.values()) == 1
    assert sum(x["lifecycle"] == "candidate" for x in claims.values()) == 9
    assert claims["K-0074"]["lifecycle"] == "reviewed"
    assert all(claims[f"K-{i:04d}"]["lifecycle"] == "candidate" for i in range(70, 74))
    assert report_state() == (1, 9, 0)


def report_state() -> tuple[int, int, int]:
    r = json.loads(REPORT.read_text())
    assert r["approved_304_skill_compilable"] is False
    assert r["stable_release_authorized"] is False
    return (
        r["reviewed_lifecycle_count"],
        r["still_unapproved_candidates_count"],
        r["approved_304_claims"],
    )


def test_security_guidance_approved_transition_with_only_source_review_fails_closed(tmp_path):
    # Use an ISOLATED copy of all audit artifacts. Never mutate the real
    # K-0074 ledger or create a review approval in the actual working tree.
    for item in ("sources", "claims", "decisions", "targets", "evidence"):
        shutil.copytree(ROOT / item, tmp_path / item)
    claim_file = tmp_path / "claims/K-0074.json"
    ledger_file = tmp_path / "decisions/K-0074.json"
    before_claim, before_ledger = claim_file.read_bytes(), ledger_file.read_bytes()
    with pytest.raises(
        ClaimError, match="permission/security guidance requires real target host integration-pass"
    ):
        transition_claim(
            tmp_path,
            "K-0074",
            "approved",
            "offline-negative-control",
            "A source-only reviewed permission guard cannot bypass genuine target-host checks",
            at=datetime.now(UTC),
        )
    assert claim_file.read_bytes() == before_claim
    assert ledger_file.read_bytes() == before_ledger
    assert json.loads(claim_file.read_text())["lifecycle"] == "reviewed"
    assert len(json.loads(ledger_file.read_text())["events"]) == 1


def test_old_host_guidance_is_not_retroactively_rejected_by_new_permission_gate():
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.296", "cli")) == 31
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    assert not approved_claims(claims, "2.1.304", "cli")


def test_public_review_record_contains_only_hashes_not_original_raw_document():
    text = REPORT.read_text()
    for secret in (
        "/Users/",
        "/home/",
        "Authorization:",
        "Cookie:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
        "declare module 'claude-code'",
        "<html",
    ):
        assert secret not in text
