"""Sanitized real Chat Mode Beta2 telemetry must retain semantic fail-stop.

Tests are only consistency/privacy checks over a separately obtained real
browser/model report. They do not themselves invoke models or authenticate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/reports/2026-10-16-agent-communication-chatmode-beta2-qa.json"
MD = ROOT / "docs/reports/2026-10-16-agent-communication-chatmode-beta2-qa.md"


def test_real_five_case_beta2_chat_qas_remain_fail_closed() -> None:
    d = json.loads(DATA.read_text())
    assert d["normal_chat_mode_only"] is True and d["work_mode_tested"] is False
    assert d["source_revision"] == "9c0b7b8213b9edda3a52130239b180ff0202c266"
    assert d["candidate_plugin_version"] == "0.3.3-beta.2"
    assert d["knowledge_revision"] == "0.1.2"
    assert d["model"] == "gpt-6-thinking" and d["effort"] == "standard"
    assert d["case_count"] == d["distinct_final_verified_count"] == 5
    assert [c["case_id"] for c in d["test_cases"]] == [
        "NEG-HVAC",
        "BOUND-VERSION-NEW",
        "POS-U-01",
        "POS-Q-01",
        "POS-E-01",
    ]
    assert all(c["final_verified"] for c in d["test_cases"])
    assert sum(c["actual_scoped_skill_loaded"] for c in d["test_cases"]) == 4
    assert d["real_scoped_mods_skill_reads"] == d["in_scope_relevant_count"] == 4
    assert d["test_cases"][0]["actual_scoped_skill_loaded"] is False
    assert d["negative_unwanted_skill_reads"] == 0
    assert sum(c["actual_canonical_resource_reads"] for c in d["test_cases"]) == 18
    assert sum(c["matched_exact_approved_claim_sources"] for c in d["test_cases"]) == 23
    assert d["total_missing_exact_approved_claim_sources"] == 0
    assert [c["semantic_verdict"] for c in d["test_cases"]] == [
        "pass",
        "pass",
        "review-needed",
        "review-needed",
        "fail",
    ]
    assert sum(c["blocking_failure"] for c in d["test_cases"]) == 1
    assert d["stop_on_last_semantic_failure"] is True
    assert d["candidate_promoted"] is False and d["stable_release_eligible"] is False


def test_transparent_observer_failure_is_not_overwritten_by_claim_source_pass() -> None:
    d = json.loads(DATA.read_text())
    e = next(c for c in d["test_cases"] if c["case_id"] == "POS-E-01")
    assert e["actual_scoped_skill_loaded"] is True
    assert e["matched_exact_approved_claim_sources"] == 9
    assert e["missing_exact_approved_claim_sources"] == 0
    assert e["semantic_verdict"] == "fail" and e["blocking_failure"] is True
    assert e["independent_known_risk_flags_after_fix"] == [
        "observer-post-next-diagnostics-not-isolated",
        "observer-catch-diagnostics-can-mask-error",
    ]
    assert d["original_model_code_executed"] is False
    assert d["synthetic_node_diagnostics_contract_proven"] is True


def test_original_account_restored_and_unrelated_plugins_preserved() -> None:
    d = json.loads(DATA.read_text())
    assert d["temporary_plugin_account_source_download_verified"] is True
    assert d["temporary_account_package_files"] == 10
    assert d["temporary_account_server_sidecar_verified"] is True
    assert d["published_baseline_restored"] == "0.2.0-beta.1"
    assert d["published_baseline_account_files_verified"] == 10
    assert d["published_baseline_server_sidecar_verified"] is True
    assert d["unrelated_personal_plugin_count"] == 10
    assert d["unrelated_personal_plugins_unchanged"] is True
    assert len(d["candidate_zip_sha256"]) == 64


def test_no_private_chat_deep_links_account_ids_or_credentials_in_public_qa() -> None:
    for file in (DATA, MD):
        text = file.read_text()
        for forbidden in (
            r"https?://chatgpt[.]com/c/[0-9a-f-]{20,}",
            r"Plugin_[0-9a-f]{20,}",
            r"g-p-[a-z0-9]{24,}",
            r"(?i)gh[pous]_[a-z0-9]{20,}",
            r"(?i)sk-[a-z0-9_-]{30,}",
            r"(?i)(authorization: bearer|cookie:|session_token=)",
        ):
            assert re.search(forbidden, text) is None
    data = json.loads(DATA.read_text())
    for c in data["test_cases"]:
        assert not any(
            key in c for key in ("conversation_id", "project_id", "raw_response", "plugin_id")
        )
