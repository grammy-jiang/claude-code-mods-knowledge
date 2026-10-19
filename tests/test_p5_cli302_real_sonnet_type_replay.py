"""Public hashes of genuine Sonnet CLI302 code lint; never reproduce raw answers."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-20-cli302-sonnet-original-console-type-replay.json"
HISTORY = ROOT / "docs/reports/2026-10-18-claude302-sonnet-beta012-five-native-observations.json"


def test_two_unchanged_original_natural_sonnet_replies_are_correctly_scored():
    data = json.loads(REPORT.read_text())
    prev = json.loads(HISTORY.read_text())
    prior = {x["case_id"]: x for x in prev["cases"]}
    assert data["reviewed_cli"] == "2.1.302"
    assert data["model"] == "claude-sonnet-5-5"
    assert data["original_real_native_responses_verified"] == 2
    assert data["historical_model_rerun_performed"] is False
    assert data["new_model_or_network_requests"] == 0
    assert data["real_bad_example_correctly_flagged"] is True
    assert data["real_control_not_falsely_flagged"] is True
    assert data["real_indented_codeblocks_recovered"] == 3
    by_case = {x["case_id"]: x for x in data["cases"]}
    assert set(by_case) == {"POS-E-01", "POS-Q-01"}
    assert by_case["POS-E-01"]["known_cli302_console_type_risk"] is True
    assert by_case["POS-E-01"]["actual_markdown_fenced_snippets_detected"] == 3
    assert by_case["POS-Q-01"]["known_cli302_console_type_risk"] is False
    for cid, item in by_case.items():
        assert item["original_wire_sha256"] == prior[cid]["original_wire_sha256"]
        assert item["original_final_sha256"] == prior[cid]["original_final_answer_sha256"]
        assert item["full_semantic_quality_verified"] is False
    assert data["complete_current_p5_host_acceptance"] is False
    assert data["old_p4_strict_activation_gate_modified"] is False
    assert data["stable_release_authorized"] is False


def test_original_native_model_text_and_identity_remain_private():
    report = REPORT.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Cookie:",
        "Authorization:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
    ):
        assert forbidden not in report
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", report) is None
    obj = json.loads(report)
    assert obj["raw_original_answers_prompts_paths_or_credentials_exported"] is False
    assert all(re.fullmatch(r"[a-f0-9]{64}", row["original_wire_sha256"]) for row in obj["cases"])
