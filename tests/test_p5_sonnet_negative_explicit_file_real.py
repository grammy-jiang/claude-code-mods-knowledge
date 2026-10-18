"""Supplementary real native Sonnet negative does not launder frozen P5 scores."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "evals/p5_native_negative_typescript_explicit_file_302.json"
REPORT = ROOT / "docs/reports/2026-10-18-p5-sonnet-negative-explicit-file-real.json"


def test_exact_fixture_is_available_for_native_read_without_glob() -> None:
    case = json.loads(CASE.read_text())
    fixture = ROOT / case["fixture_root"] / case["relative_file"]
    assert case["id"] == "NEG-TYPESCRIPT-EXPLICIT-PATH"
    assert case["target_cli"] == "2.1.302"
    assert case["relative_file"] == "src/overloads.ts"
    assert case["case_explicitly_says_non_mods"] is True
    assert fixture.is_file()
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == case["fixture_sha256"]
    assert "src/overloads.ts" in case["request_body"]
    assert "This is not a Claude Code Mod task." in case["request_body"]
    assert case["allowed_native_tools"] == ["Read", "Skill"]
    assert case["full_p5_host_acceptance_claimed"] is False


def test_original_native_sonnet_source_read_without_mods_activation() -> None:
    case = json.loads(CASE.read_text())
    data = json.loads(REPORT.read_text())
    assert data["source_candidate"] == case["candidate_skill"]
    assert data["reviewed_target_cli"] == "2.1.302"
    assert data["native_model"] == "claude-sonnet-5-5"
    assert data["case_id"] == case["id"]
    assert data["source_fixture_sha256"] == case["fixture_sha256"]
    assert data["model_completion_success"] is True
    assert data["actual_native_read_tool_calls"] == 1
    assert data["actual_read_of_explicit_source_file"] is True
    assert data["native_read_errors"] == 0
    assert data["claude_code_mods_skill_calls"] == 0
    assert data["mods_knowledge_claim_ids_cited"] is False
    assert data["unrelated_skill_isolation_pass"] is True
    assert data["native_generated_code_executed"] is False
    assert data["actual_project_files_modified"] is False
    assert data["native_model_effort_provider_verified"] is False
    assert data["correctness_of_suggested_typescript_changes_verified"] is False
    assert data["replaces_original_five_case_verdict"] is False
    assert data["full_native_host_semantics_certified"] is False
    assert data["stable_release_authorized"] is False
    assert data["estimated_model_cost_usd"] == 0.564
    for name in (
        "original_prompt_sha256",
        "source_fixture_sha256",
        "native_original_wire_sha256",
        "native_full_visible_answer_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", data[name])


def test_redacted_report_is_not_raw_private_native_answer() -> None:
    text = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Authorization:",
        "Cookie:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in text
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text) is None
