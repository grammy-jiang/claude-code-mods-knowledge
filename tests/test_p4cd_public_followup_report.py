"""Historical and current real Chat QA remain independently scoped and fail closed."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-16-p4cd-source-recovery-and-artifact-audit.json"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def load() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_new_real_boundary_text_pass_is_not_file_artifact_pass() -> None:
    doc = load()
    a = doc["existing_boundaries"]
    assert a["frozen_original_case_count"] == 8
    assert a["previous_bounded_text_pass_count"] == 6
    assert a["additional_case_id"] == "BOUND-SKILL-ROLE"
    assert a["additional_case_final"] == "FINAL_VERIFIED_READ_ONLY_RECOVERED"
    assert a["new_prompt_sent_count"] == 1
    assert a["new_prompt_resends"] == 0
    assert a["newly_scoped_skill_resource_read_count"] == 5
    assert a["newly_matched_approved_claim_source_count"] == 7
    assert len(set(a["newly_matched_approved_claim_ids"])) == 7
    assert SHA256.fullmatch(a["full_visible_reply_sha256"])
    assert a["new_boundary_text_safe"] is True
    assert a["file_artifact_offered"] is True
    assert a["file_trace_status"] == "FILE_ARTIFACT_UNVERIFIED"
    assert a["file_bytes_read_back"] is False
    assert a["file_contents_independently_reviewed_safe"] is False
    assert a["new_boundary_overall_semantic_status"] == "REVIEW_REQUIRED_ARTIFACT"
    assert a["full_boundary_acceptance"] is False


def test_original_unknown_case_is_not_silently_replayed_or_substituted() -> None:
    a = load()["existing_boundaries"]
    assert a["old_unresolved_case_id"] == "BOUND-PLUGIN-PRIV"
    assert a["old_unresolved_receipt_state"] == "OUTCOME_UNKNOWN"
    assert a["old_unresolved_latest_read_only_reconciliation"] == "READ_INCOMPLETE"
    assert a["old_unresolved_no_resend"] is True


def test_historical_46_reaudit_does_not_substitute_for_current_candidate() -> None:
    x = load()
    old = x["historical_beta1_reaudit"]
    assert (
        old["original_real_chat_case_count"] == old["archived_private_replies_read_offline"] == 46
    )
    assert old["original_positive_case_count"] == 30
    assert old["read_failure_count"] == 0
    assert set(old["historical_hard_risks"]) == {"POS-E-02", "POS-T-03", "POS-Q-01"}
    assert set(old["historical_manual_review_signals"]) == {"POS-E-01", "POS-E-04"}
    assert old["newly_confirmed_model_semantic_passes"] == 0
    assert old["historical_not_counted_as_current_candidate_acceptance"] is True
    current = x["remaining_p4c"]
    assert current["new_current_candidate_positive_cases_required"] == 6
    assert current["new_current_candidate_positive_cases_completed"] == 0
    assert current["model_origin_code_native_validation_completed"] is False
    assert current["p4c_closed"] is False
    assert x["p4d_closed"] is False
    assert x["release_status"] == "STABLE_RELEASE_BLOCKED"


def test_sanitized_public_report_has_no_private_identifiers_or_model_file_url() -> None:
    x = load()
    assert x["target_cli"] == "2.1.296"
    assert re.fullmatch(r"[0-9a-f]{40}", x["current_source_revision"])
    assert re.fullmatch(r"[0-9a-f]{40}", x["candidate_source_revision"])
    assert x["account"]["baseline_restored"] == "0.2.0-beta.1"
    assert x["account"]["baseline_enabled_and_skill_on"] is True
    assert x["account"]["candidate_release_not_published"] is True
    raw = REPORT.read_text(encoding="utf-8")
    assert re.search(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", raw) is None
    assert re.search(r"Plugin_[0-9a-f]{32}", raw) is None
    assert "sandbox:/mnt/data/" not in raw
    assert "TASK_ID:" not in raw
    assert "bearer " not in raw.lower()
