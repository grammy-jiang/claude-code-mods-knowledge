"""Real P4 model/effort experiment and text-only explicit Plugin control."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_p4_model_routing_controls.py"
REPORT = ROOT / "docs/reports/2026-10-27-p4-model-routing-text-directed-evidence.json"
PRIOR = ROOT / "docs/reports/2026-10-27-p4-beta012-live-routing-pilot-evidence.json"
SUITE = ROOT / "evals/p4_cases_cli_2_1_302.json"
_spec = importlib.util.spec_from_file_location("p4_model_controls", SCRIPT)
assert _spec and _spec.loader
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def source() -> dict:
    return json.loads(REPORT.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_citation_identity_and_model_arms_are_pinned():
    d = source()
    assert d["schema_version"] == 1
    assert d["auditor_source_sha256"] == sha(SCRIPT)
    assert d["source_frozen_46_suite_sha256"] == sha(SUITE) == audit.FROZEN_SUITE_SHA
    assert d["original_pr126_real_chat_baseline_sha256"] == sha(PRIOR) == audit.PRIOR_PUBLIC_SHA
    assert d["plugin_name"] == "claude-code-mods-knowledge"
    assert d["installed_account_version"] == "0.4.12-beta.1"
    assert d["reviewed_target_cli"] == "2.1.302"
    assert re.fullmatch(r"[a-f0-9]{64}", d["plugin_instance_sha256"])
    assert set(x["arm"] for x in d["cases"]) == set(audit.ARM_INFO)
    assert len({x["original_chat_id_sha256"] for x in d["cases"]}) == 6


def test_three_alternative_model_effort_settings_did_not_fix_auto_selection():
    r = source()
    assert r["real_model_arms_without_plugin_selection"] == 3
    assert r["real_model_arms_skill_auto_loads"] == 0
    models = {x["arm"]: (x["actual_model"], x["actual_effort"]) for x in r["cases"]}
    assert models["HIGH-POS-E-01"] == ("gpt-6-thinking", "extended")
    assert models["EXTRA-POS-E-01"] == ("gpt-6-thinking", "max")
    assert models["OLD-POS-E-01"] == ("gpt-5-6-thinking", "standard")
    natural = [x for x in r["cases"] if x["user_request_mode"] == "automatic"]
    assert len(natural) == 3
    for x in natural:
        assert x["case_id"] == "POS-E-01"
        assert x["selected_plugin_system_hint"] is False
        assert x["skill_loaded"] is False
        assert x["real_plugin_resource_reads"] == 0
        assert x["answer_structural_verdict"] == "fail"


def test_three_text_only_direct_requests_genuinely_use_correct_plugin():
    r = source()
    assert r["text_explicit_plugin_name_controls"] == 3
    assert r["text_explicit_plugin_name_skill_loads"] == 3
    named = [x for x in r["cases"] if x["user_request_mode"] == "text_directed"]
    assert {x["case_id"] for x in named} == {"POS-E-01", "POS-T-01", "POS-U-01"}
    assert len(named) == 3
    assert all(x["selected_plugin_system_hint"] is False for x in named)
    assert all(x["skill_loaded"] is True for x in named)
    assert all(x["real_plugin_resource_reads"] >= 3 for x in named)
    assert all(x["real_plugin_instance_matched"] is True for x in named)
    assert all(x["answer_structural_verdict"] == "pass" for x in named)
    assert all(x["independent_semantic_review"] == "not_run" for x in named)
    assert all(x["native_executable_code_review"] == "not_run" for x in named)
    assert Counter(x["visible_reply_segments"] for x in named)


def test_text_controls_must_not_masquerade_as_automatic_or_stable_acceptance():
    d = source()
    assert d["automatic_baseline_standard_9_positive_loads"] == 0
    assert d["text_request_is_explicit_intent_not_native_automatic_invocation"] is True
    assert d["first_party_routing_causality_proven"] is False
    assert d["source_or_plugin_metadata_modified"] is False
    assert d["account_or_global_model_setting_modified"] is False
    assert d["new_provider_auto_selection_fix_proven"] is False
    assert d["full_p4_46_case_accepted"] is False
    assert d["stable_release_authorized"] is False
    assert d["private_model_text_account_ids_and_auth_not_committed"] is True


def test_public_report_only_bounded_source_hashes_not_private_messages_or_accounts():
    raw = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Cookie:",
        "Authorization:",
        "access_token",
        '"conversation_id":',
        '"session_id":',
        '"tool_use_id":',
        "BEGIN PRIVATE KEY",
        "chatgpt.com/c/",
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
    for case in source()["cases"]:
        for field in (
            "original_prompt_sha256",
            "original_send_receipt_sha256",
            "original_chat_id_sha256",
            "original_conversation_sha256",
            "complete_visible_reply_sha256",
        ):
            assert re.fullmatch(r"[0-9a-f]{64}", case[field])


def test_missing_private_model_traces_cannot_reproduce_case_passes(tmp_path: Path):
    with pytest.raises((audit.ModelRoutingBlocked, OSError, ValueError)):
        audit.audit(tmp_path, SUITE, PRIOR, tmp_path / "account-show.private.log")
