"""Only sanitized, properly scoped real Pi Agent model evidence may be public."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reports/2026-10-14-pi-agent-real-model-qa.json"


def test_pi_agent_real_model_cases_are_explicitly_incomplete() -> None:
    report = json.loads(EVIDENCE.read_text())
    assert report["schema_version"] == 1
    assert report["agent"] == "pi_agent"
    assert report["pi_agent_version"] == "1.1.0"
    assert report["provider"] == "openai-codex"
    assert report["target_version"] == "Claude Code CLI 2.1.296"
    assert report["full_p5_acceptance"] is False
    assert report["all_three_required_categories_pass"] is False
    rows = {r["case_id"]: r for r in report["cases"]}
    assert set(rows) == {"POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}
    assert rows["POS-E-01"]["host_verdict"] == "pass"
    assert rows["POS-E-01"]["skill_read_calls"] >= 2
    assert "events.md" in rows["POS-E-01"]["reference_files_read"]
    assert "K-0031" in rows["POS-E-01"]["reviewed_claim_ids"]
    assert rows["POS-E-01"]["correct_handler_arity"] is True
    assert rows["NEG-TYPESCRIPT"]["host_verdict"] == "fail"
    assert rows["NEG-TYPESCRIPT"]["skill_read_calls"] >= 1
    assert rows["BOUND-VERSION-NEW"]["host_verdict"] == "partial"
    assert rows["BOUND-VERSION-NEW"]["skill_read_calls"] == 0
    assert rows["POS-Q-01"]["host_verdict"] == "partial"
    assert rows["POS-Q-01"]["correct_plugin_test_directory"] is True
    for row in rows.values():
        assert row["real_model_inference"] is True
        assert row["model_reply_sha256"] and re.fullmatch(
            r"[0-9a-f]{64}", row["model_reply_sha256"]
        )
        assert row["model_trace_sha256"] and re.fullmatch(
            r"[0-9a-f]{64}", row["model_trace_sha256"]
        )
        assert row["tool_events_start"] == row["tool_events_end"] == row["read_tool_calls"]


def test_pi_real_model_report_has_no_private_account_content() -> None:
    text = EVIDENCE.read_text()
    for forbidden in (
        "conversation_id",
        "Plugin_",
        "chatgpt.com/c/",
        "Authorization:",
        "Cookie:",
        "/home/",
        "/Users/",
        "refresh_token",
    ):
        assert forbidden not in text
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", text)
    assert not re.search(r"sk-[A-Za-z0-9_-]{20,}", text)
