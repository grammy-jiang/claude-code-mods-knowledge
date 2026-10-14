"""Public-repository QA summary privacy and historical-evidence invariants."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/reports/2026-10-14-beta3-chat-qa-summary.json"


def test_public_qa_report_is_sanitized_and_has_no_account_conversation_identifiers() -> None:
    text = PATH.read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["schema_version"] == 1
    assert data["cases_total"] == 18
    assert data["case_ids_sent"] == 18
    assert data["cases_collected"] == 17
    assert data["cases_uncollected"] == ["NEG-HVAC"]
    assert data["account_now_installed_version"] == "0.2.0-beta.1"
    assert data["account_rollback_verified"] is True
    assert data["full_suite_version_specific_qa_pass"] is False
    assert data["semantic_answer_review_complete"] is False
    assert "chatgpt.com/c/" not in text.lower()
    assert "Plugin_" not in text
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text)
    assert not re.search(r"sk-[A-Za-z0-9_-]{20,}", text)
    for item in data["cases"]:
        assert set(item) <= {
            "case_id",
            "category",
            "send_status",
            "observation_status",
            "skill_loaded",
            "structural_quality",
            "quality_flags",
            "observed_claim_ids",
        }
    assert len({item["case_id"] for item in data["cases"]}) == 18
    assert all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in data["local_evidence_file_sha256"].values()
    )


def test_public_report_does_not_reclassify_blocked_case_as_failed_model_answer() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    last = next(item for item in data["cases"] if item["case_id"] == "NEG-HVAC")
    assert last["send_status"] == "sent"
    assert last["observation_status"] == "read_not_completed"
    assert last["structural_quality"] is None
    assert last["skill_loaded"] is None
    assert data["boundary_auto_loaded"] == 0
    assert data["boundary_observed"] == 8
    assert data["positive_observed"] == 9
    assert data["positive_auto_loaded"] == 3
    assert data["positive_structural"] == {"fail": 8, "inconclusive": 0, "pass": 1}
    assert data["comparison_from_beta2"]["structurally_recovered"] == ["POS-Q-03"]
    assert data["comparison_from_beta2"]["structurally_regressed"] == ["POS-E-01", "POS-E-02"]
