"""Genuine beta010 root-fix pilot must not be overstated as full acceptance."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-18-claude302-beta010-yaml-fix-real-chat-pilot.json"


def test_beta010_exact_source_real_four_case_pilot_and_remaining_boundary_fail() -> None:
    x = json.loads(REPORT.read_text())
    assert x["source_git_sha"] == "b9ea3063393e33259298ddcac02104b16c42b208"
    assert x["plugin_version"] == "0.4.10-beta.1"
    assert x["tested_target_cli"] == "2.1.302"
    assert x["model"] == "gpt-6-thinking" and x["effort"] == "standard"
    assert x["invocation_mode"] == "automatic"
    assert x["composer_plugin_selected"] is False
    assert x["installed_account_plugin_zip_files_matched"] == 11
    assert x["cross_host_reproducible_artifacts"] == 53
    assert x["all_four_sends_and_complete_finals_sha256_verified"] == 4
    assert x["positive_actual_skill_read_and_exact_source_structure"] == 2
    assert x["positive_total"] == 2
    assert x["unrelated_negative_nonactivation"] == 1
    assert x["unrelated_negative_total"] == 1
    assert x["unsupported_version_boundary_skill_read"] == 0
    assert x["unsupported_version_boundary_total"] == 1
    assert x["full_46_case_qualification"] is False
    assert x["all_boundary_qualification"] is False
    assert x["code_semantics_certified"] is False
    assert x["stable_release_authorized"] is False
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", x[key])
        for key in ("cross_host_source_skill_sha256", "cross_host_plugin_zip_sha256")
    )
    assert len(x["cases"]) == 4
    assert [c["case_id"] for c in x["cases"]] == [
        "POS-E-01",
        "POS-U-01",
        "NEG-HVAC",
        "BOUND-VERSION-NEW",
    ]
    for c in x["cases"]:
        assert c["model_effort_verified"] is True
        assert c["complete_generated_code_semantics_certified"] is False
        assert all(
            re.fullmatch(r"[a-f0-9]{64}", c[k])
            for k in ("original_conversation_sha256", "original_visible_reply_sha256")
        )
    for c in x["cases"][:2]:
        assert c["result"] == "structural_pass_semantic_pending"
        assert c["actual_plugin_skill_entrypoint_and_reference_read"] is True
        assert c["actual_matching_plugin_resource_reads"] >= 2
        assert c["source_structural_verdict"] == "pass"
        assert not c["missing_required_claims"]
        assert not c["missing_exact_official_source_claims"]
    assert x["cases"][2]["result"] == "negative_nonactivation_pass"
    assert not x["cases"][2]["actual_plugin_skill_entrypoint_and_reference_read"]
    assert x["cases"][3]["result"] == "boundary_activation_fail"
    assert not x["cases"][3]["actual_plugin_skill_entrypoint_and_reference_read"]


def test_postfix_public_artifacts_do_not_expose_private_original_content() -> None:
    source = REPORT.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "Plugin_",
        "Cookie:",
        "Authorization:",
        "chatgpt.com/c/",
        "TASK_ID:",
        "sandbox:/mnt/data",
        "raw_reply",
    ):
        assert forbidden not in source
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", source) is None
