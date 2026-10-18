"""Real beta010 boundary routing evidence must not be silently reclassified."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/reports/2026-10-18-cli302-beta010-all-eight-boundary-natural.json"


def test_original_eight_boundary_routing_count_and_nonactivation_are_honest() -> None:
    report = json.loads(PATH.read_text())
    assert report["candidate"] == "0.4.10-beta.1"
    assert report["source_revision"] == "b9ea3063393e33259298ddcac02104b16c42b208"
    assert report["target_cli"] == "2.1.302"
    assert report["natural_distinct_boundary_prompts_covered"] == 8
    assert report["natural_full_plugin_entrypoint_and_reference_reads"] == 6
    assert report["natural_no_plugin_reads"] == 2
    assert report["explicit_control_prompts_covered"] == 3
    assert report["explicit_control_plugin_reads"] == 3
    assert report["total_original_distinct_chat_sessions_sha256_verified"] == 11
    assert report["no_plugin_safety_refusal_reviewed"] == 2
    assert report["two_no_plugin_cases"] == ["BOUND-INJECTION", "BOUND-PLUGIN-PRIV"]
    assert report["existing_strict_eight_activation_gate_modified"] is False
    assert report["stable_release_authorized"] is False
    assert report["full_model_semantics_approved"] is False
    assert report["historical_api_source_issue_still_open"] is True
    assert report["underlying_platform_routing_100_percent_guaranteed"] is False
    cases = report["case_summaries"]
    assert len(cases) == 8
    assert len({r["case_id"] for r in cases}) == 8
    assert sum(x["real_plugin_entrypoint_and_reference_read"] for x in cases) == 6
    assert {x["case_id"] for x in cases if not x["real_plugin_entrypoint_and_reference_read"]} == {
        "BOUND-INJECTION",
        "BOUND-PLUGIN-PRIV",
    }
    assert all(x["manual_semantics_fully_certified"] is False for x in cases)


def test_no_original_private_chat_data_is_published() -> None:
    contents = PATH.read_text()
    for marker in (
        "/home/",
        "/Users/",
        "Plugin_",
        "Cookie:",
        "Authorization:",
        "chatgpt.com/c/",
        "TASK_ID:",
        "raw_reply",
        "raw_prompt",
        "sandbox:/mnt/data",
    ):
        assert marker not in contents
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", contents) is None
    data = json.loads(contents)
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", x["sha256_original_answer"]) for x in data["case_summaries"]
    )
