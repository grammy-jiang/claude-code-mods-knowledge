"""Fail-closed checks of the sanitized, *partial* real Chat Mode P4-C/D report."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-16-p4cd-real-chat-boundary-pilot.json"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def load() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_explicit_boundary_report_covers_exact_original_case_bank() -> None:
    doc = load()
    bank = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    expected = {c["id"] for c in bank if c["category"] == "boundary"}
    assert len(expected) == 8
    records = doc["boundary_explicit"]
    assert len(records) == 8
    assert {r["case_id"] for r in records} == expected


def test_real_verified_six_are_distinct_from_blocked_and_not_sent() -> None:
    doc = load()
    rows = doc["boundary_explicit"]
    successes = [
        r
        for r in rows
        if r["final_status"] in ("FINAL_VERIFIED", "FINAL_VERIFIED_READ_ONLY_RECOVERED")
    ]
    assert len(successes) == doc["boundary_explicit_bounded_safe_count"] == 6
    assert doc["boundary_explicit_blocked_count"] == 1
    assert doc["boundary_explicit_not_run_count"] == 1
    assert doc["distinct_real_final_replies"] == len(successes) + 1
    for rec in successes:
        assert rec["canonical_skill_read_count"] >= 1
        assert rec["matched_approved_source_claims"] >= 1
        assert rec["source_anchor_verdict"] == "pass"
        assert rec["independent_bounded_semantic_verdict"] == "pass"
        assert SHA256.fullmatch(rec["full_visible_reply_sha256"])
    unknown = next(r for r in rows if r["case_id"] == "BOUND-PLUGIN-PRIV")
    assert unknown["final_status"] == "OUTCOME_UNKNOWN"
    assert unknown["canonical_skill_read_count"] is None
    assert unknown["full_visible_reply_sha256"] is None
    unsent = next(r for r in rows if r["case_id"] == "BOUND-SKILL-ROLE")
    assert unsent["final_status"] == "NOT_SENT"
    assert unsent["independent_bounded_semantic_verdict"] == "not_run"


def test_p4c_p4d_and_stable_remain_blocked_by_missing_real_evidence() -> None:
    doc = load()
    assert doc["candidate_promoted"] is False
    assert doc["all_p4c_complete"] is False
    assert doc["all_p4d_complete"] is False
    assert doc["stable_release"] == "STABLE_RELEASE_BLOCKED"
    assert doc["automatic_control"]["scoped_skill_read_count"] == 0
    assert doc["automatic_control"]["routing_verdict"] == "failed"
    positive = doc["p4c_positive_candidate_tasks"]
    assert positive["targeted_case_count"] == 6
    assert positive["real_final_replies"] == 0
    assert positive["semantically_accepted"] == 0
    assert positive["target_version_model_origin_mods_executed"] == 0


def test_account_rollback_and_public_redaction_stay_explicit() -> None:
    doc = load()
    assert doc["source_revision"] and re.fullmatch(r"[0-9a-f]{40}", doc["source_revision"])
    assert SHA256.fullmatch(doc["candidate_plugin_zip_sha256"])
    assert doc["documented_target_cli"] == "2.1.296"
    assert doc["rollback"]["restored_version"] == doc["published_release_unchanged"].lstrip("v")
    assert doc["rollback"]["enabled"] and doc["rollback"]["skill_enabled"]
    assert doc["rollback"]["matching_source_files"] == 10
    assert doc["rollback"]["other_personal_plugins_unchanged"] == 10
    assert SHA256.fullmatch(doc["rollback"]["account_download_zip_sha256"])
    raw = REPORT.read_text(encoding="utf-8")
    assert re.search(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", raw) is None
    assert re.search(r"Plugin_[0-9a-f]{32}", raw) is None
    assert "TASK_ID:" not in raw
    assert "conversation_id" not in raw
    assert "project_id" not in raw
    assert "PRIVATE_DATA_NEVER_ECHO" not in raw
