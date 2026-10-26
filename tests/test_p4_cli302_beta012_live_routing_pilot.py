"""Real authenticated Mac Chat Mode 0.4.12-beta.1 auto/explicit pilot evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts/audit_p4_cli302_beta012_live_pilot.py"
REPORT = ROOT / "docs/reports/2026-10-27-p4-beta012-live-routing-pilot-evidence.json"
SUITE = ROOT / "evals/p4_cases_cli_2_1_302.json"
_spec = importlib.util.spec_from_file_location("p4_beta012_original_auditor", AUDITOR)
assert _spec and _spec.loader
a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a)


def evidence() -> dict:
    return json.loads(REPORT.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_and_account_download_provenance_frozen():
    r = evidence()
    assert r["schema_version"] == 1
    assert r["auditor_source_sha256"] == sha(AUDITOR)
    assert r["official_frozen_test_suite_sha256"] == sha(SUITE) == a.FROZEN_SUITE_SHA
    assert r["target_version"] == a.TARGET == "2.1.302"
    assert r["plugin_version"] == a.VERSION == "0.4.12-beta.1"
    assert r["reviewed_compiled_source_revision"] == a.SOURCE_REVISION
    assert r["original_uploader_package_sha256"] == a.SOURCE_ZIP_SHA
    assert r["original_chatgpt_download_sha256"] == a.ACCOUNT_ZIP_SHA
    assert re.fullmatch(r"[0-9a-f]{64}", r["canonical_plugin_contents_sha256"])
    assert r["canonical_plugin_files_matched"] == 11
    assert r["account_current_version_installed_enabled_and_skill_on_readback"] is True
    assert re.fullmatch(r"[0-9a-f]{64}", r["account_plugin_instance_sha256"])


def test_real_fifteen_automatic_cases_in_distinct_ordinary_chats():
    r = evidence()
    assert r["total_expected_cases"] == 46
    assert r["automatic_cases_confirmed_finished_and_scored"] == 15
    assert r["confirmed_send_receipts"] == 15
    assert r["remaining_not_run_or_not_confirmed"] == 31
    assert len({c["original_conversation_sha256"] for c in r["cases"]}) == 15
    assert len({c["case_id"] for c in r["cases"]}) == 15
    suite = json.loads(SUITE.read_text())
    known = {c["id"]: c for c in suite["cases"]}
    for c in r["cases"]:
        case = known[c["case_id"]]
        assert c["category"] == case["category"]
        assert c["case_prompt_sha256"] == hashlib.sha256(case["prompt"].encode()).hexdigest()
        assert c["invocation_mode"] == "automatic"
        assert c["native_chat_resolved_model"] == "gpt-6-thinking"
        assert c["native_chat_effort"] == "standard"
        assert c["actual_correct_plugin_resource_reads"] == 0
        assert c["actual_resource_read_count"] == 0
        assert c["skill_auto_or_explicit_loaded"] is False
        assert c["semantic_review"] == "not_done"
        assert c["native_generated_code_validation"] == "not_done"
        assert c["visible_assistant_segments"] >= 1
        for field in (
            "case_prompt_sha256",
            "private_send_receipt_sha256",
            "original_conversation_sha256",
            "original_conversation_wire_sha256",
            "visible_answer_sha256",
        ):
            assert re.fullmatch(r"[a-f0-9]{64}", c[field])


def test_nine_positive_three_boundary_fail_and_three_negative_controls_pass():
    assert evidence()["automatic_cases_by_category"] == {
        "positive": {"completed": 9, "canonical_skill_loads": 0, "structural_passes": 0},
        "negative": {"completed": 3, "canonical_skill_loads": 0, "structural_passes": 3},
        "boundary": {"completed": 3, "canonical_skill_loads": 0, "structural_passes": 0},
    }
    assert Counter((c["category"], c["structural_verdict"]) for c in evidence()["cases"]) == {
        ("positive", "fail"): 9,
        ("boundary", "fail"): 3,
        ("negative", "pass"): 3,
    }


def test_exact_same_prompt_explicit_control_proves_only_selected_plugin_works():
    r = evidence()
    explicit = r["explicit_selected_positive_control"]
    automatic = next(c for c in r["cases"] if c["case_id"] == "POS-E-01")
    assert explicit["case_id"] == automatic["case_id"]
    assert explicit["case_prompt_sha256"] == automatic["case_prompt_sha256"]
    assert explicit["invocation_mode"] == "explicit"
    assert automatic["invocation_mode"] == "automatic"
    assert explicit["actual_correct_plugin_resource_reads"] == 4
    assert explicit["actual_matching_canonical_resources"] == 4
    assert explicit["skill_auto_or_explicit_loaded"] is True
    assert explicit["structural_verdict"] == "pass"
    assert automatic["skill_auto_or_explicit_loaded"] is False
    assert automatic["structural_verdict"] == "fail"
    assert r["explicit_control_is_not_part_of_automatic_denominator"] is True


def test_ambiguous_send_not_rescored_as_pass_or_resent():
    r = evidence()
    assert r["uncertain_send_not_counted_and_must_not_be_resent"] == "NEG-SPORTS"
    assert "NEG-SPORTS" not in {c["case_id"] for c in r["cases"]}
    assert r["confirmed_send_receipts"] + r["remaining_not_run_or_not_confirmed"] == 46
    assert r["full_46_case_live_chat_mode_qa_pass"] is False
    assert r["manual_semantic_review_finished"] is False
    assert r["current_target_310_compatibility_proven"] is False
    assert r["native_generated_mod_code_validated_by_this_pilot"] is False
    assert r["stable_release_authorized"] is False


def test_is_auto_catalog_field_is_not_claimed_as_unique_cause():
    r = evidence()
    assert r["system_hint_catalog_plugin_count"] == 43
    assert r["system_hint_is_auto_false_for_all_catalog_plugins"] is True
    assert r["system_hint_is_auto_is_not_evidence_of_unique_root_cause"] is True
    assert r["original_chats_session_ids_plugin_ids_and_tokens_not_committed"] is True


def test_raw_originals_absent_from_git_prevent_rerun_without_private_evidence(tmp_path: Path):
    with pytest.raises((a.PilotEvidenceBlocked, OSError, ValueError)):
        a.audit(tmp_path, SUITE)


def test_public_report_omits_personal_session_and_account_data():
    raw = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Cookie:",
        "Authorization:",
        "access_token",
        "BEGIN PRIVATE KEY",
        "chatgpt.com/c/",
        '"conversation_id":',
        '"session_id":',
        '"tool_use_id":',
        "Plugin_",
    ):
        assert forbidden not in raw
    assert (
        re.search(
            r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])",
            raw,
        )
        is None
    )
