"""Real Chat-mode candidate regression evidence must stay complete and private-safe.

This validates independently collected, source/version-scoped observations. It
never calls a model, fetches private conversations or claims semantic QA passes.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-14-v030beta1-full46-automatic-chat.json"
SUMMARY = ROOT / "docs/reports/2026-10-14-v030beta1-full46-automatic-chat.md"
SUITE = ROOT / "evals/p4_cases.json"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _report() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_full_46_distinct_real_auto_chat_conversations_are_preserved() -> None:
    data = _report()
    assert data["schema_version"] == 1
    assert data["evaluation"] == "real-ordinary-chat-automatic-structural-only"
    assert data["plugin_version"] == "0.3.0-beta.1"
    assert data["source_revision"] == "158acdc7c785df6aa9fbecb11187e29ac400392b"
    assert data["send_status_counts"] == {"sent": 46}
    assert data["reply_status_counts"] == {"collected": 46}
    assert data["independent_semantic_review_complete"] is False
    assert data["stable_release_ready"] is False
    result = data["report"]
    assert result["plugin_version"] == data["plugin_version"]
    assert result["source_revision"] == data["source_revision"]
    assert result["mode"] == "chat"
    items = result["items"]
    suite = json.loads(SUITE.read_text())
    expected = {c["id"]: c for c in suite["cases"]}
    assert len(items) == len(expected) == 46
    assert {x["id"] for x in items} == set(expected)
    assert len({x["conversation_sha256"] for x in items}) == 46
    assert len({x["response_sha256"] for x in items}) == 46
    for row in items:
        case = expected[row["id"]]
        assert row["category"] == case["category"]
        assert row["expected_activation"] is case["expected_activation"]
        assert row["invocation_mode"] == "automatic"
        assert row["received"] is True
        assert _HEX64.fullmatch(row["conversation_sha256"])
        assert _HEX64.fullmatch(row["response_sha256"])
        if row["skill_loaded"]:
            assert _HEX64.fullmatch(row["plugin_id_sha256"])
            assert row["resource_uris"]
            skill_uri = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
            assert all(
                uri == skill_uri or uri.startswith(skill_uri + "/") for uri in row["resource_uris"]
            )
        else:
            assert row["plugin_id_sha256"] is None
            assert row["resource_uris"] == []


def test_unqualified_candidate_routing_and_structure_cannot_count_as_release_pass() -> None:
    data = _report()
    result = data["report"]
    summary = result["summary"]
    assert summary["total"] == summary["observed"] == 46
    assert summary["passed"] == 8
    assert summary["failed"] == 38
    assert summary["blocked"] == summary["inconclusive"] == summary["not_run"] == 0
    assert summary["full_qa_pass"] is False
    grouped = {
        name: [x for x in result["items"] if x["category"] == name]
        for name in ("positive", "negative", "boundary")
    }
    assert {name: len(rows) for name, rows in grouped.items()} == {
        "positive": 30,
        "negative": 8,
        "boundary": 8,
    }
    assert sum(x["skill_loaded"] for x in grouped["positive"]) == 3
    assert all(x["final_verdict"] == "failed" for x in grouped["positive"])
    assert all(x["structural_verdict"] == "fail" for x in grouped["positive"])
    assert all(
        not x["skill_loaded"] and x["final_verdict"] == "passed" for x in grouped["negative"]
    )
    assert all(
        not x["skill_loaded"] and x["final_verdict"] == "failed" for x in grouped["boundary"]
    )
    assert summary["activation_metrics"]["positive"]["correct_loading_rate"] == 0.1
    assert summary["activation_metrics"]["negative"]["false_activation_rate"] == 0.0
    assert summary["activation_metrics"]["boundary"]["correct_loading_rate"] == 0.0
    assert result["status"] != "FULL_SUITE_LIVE_CHAT_MODE_PASS"


def test_four_known_risk_cases_are_retained_not_reclassified_as_semantic_passes() -> None:
    data = _report()
    risk = {item["case_id"]: item["known_risk_flags"] for item in data["known_risk_cases"]}
    assert risk == {
        "POS-E-02": ["historical-early-access-types-reference"],
        "POS-S-02": ["unsupported-default-register-destructuring"],
        "POS-Q-02": ["historical-early-access-types-reference"],
        "POS-U-03": ["historical-early-access-types-reference"],
    }
    assert all("semantic_review" not in item for item in data["report"]["items"])
    assert all(
        x["structural_verdict"] == "fail"
        for x in data["report"]["items"]
        if x["category"] == "positive"
    )


def test_evidence_and_published_report_have_no_raw_account_material() -> None:
    raw = REPORT.read_text(encoding="utf-8")
    md = SUMMARY.read_text(encoding="utf-8")
    for marker in (
        "conversation_id",
        "chatgpt.com/c/",
        "Cookie:",
        "Authorization:",
        "Plugin_",
        "access_token",
        "refresh_token",
        "/home/grammy-jiang/",
        "/Users/grammy-jiang/",
        "sk-proj-",
        "ghp_",
    ):
        assert marker not in raw
        assert marker not in md
    assert not re.search(r"https://chatgpt\.com/c/[a-f0-9-]{30,}", raw + md)
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", raw + md)
    assert Counter(item["category"] for item in _report()["report"]["items"]) == {
        "positive": 30,
        "negative": 8,
        "boundary": 8,
    }
    assert "0/30" in md and "3/30" in md and "0/8" in md
    assert "not a randomized contemporaneous A/B trial" in md
