"""Full Chat-mode preview measurements are complete and not a model-quality pass."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-14-preview-full-chat-mode-qa.json"


def test_preview_46_real_chat_observations_do_not_pass_auto_routing_gate() -> None:
    report = json.loads(REPORT.read_text())
    assert report["schema_version"] == 1
    assert report["experiment_version"] == "0.2.0-preview.1"
    assert report["chat_mode"] == "ordinary_chat_only"
    assert report["auto_activation_only"] is True
    assert report["cases_total"] == 46
    assert report["model_replies_observed"] == 46
    assert report["distinct_conversations_verified"] is True
    assert report["all_active_plugin_resource_reads"] == 0
    assert report["category_results"] == {
        "positive": {
            "observed": 30,
            "skill_loaded": 0,
            "structural_pass": 0,
            "structural_fail": 30,
        },
        "negative": {
            "observed": 8,
            "skill_loaded": 0,
            "structural_pass": 8,
            "structural_fail": 0,
        },
        "boundary": {
            "observed": 8,
            "skill_loaded": 0,
            "structural_pass": 0,
            "structural_fail": 8,
        },
    }
    assert report["is_stable_release_qualified"] is False
    assert report["model_semantic_correctness_review_complete"] is False
    assert report["current_account_reverted_version"] == "0.2.0-beta.1"


def test_p4_preview_per_case_complete_and_publicly_sanitized() -> None:
    body = REPORT.read_text()
    report = json.loads(body)
    rows = report["cases"]
    assert len(rows) == len({r["case_id"] for r in rows}) == 46
    for row in rows:
        assert set(row) == {
            "case_id",
            "category",
            "skill_loaded",
            "answer_quality",
            "quality_flags",
            "read_skill_names",
            "observed_claim_ids",
            "response_sha256",
            "prompt_sha256",
        }
        assert row["read_skill_names"] == []
        assert row["skill_loaded"] is False
        assert re.fullmatch(r"[0-9a-f]{64}", row["response_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", row["prompt_sha256"])
    for token in (
        "conversation_id",
        "chatgpt.com/c/",
        "Plugin_",
        "Cookie:",
        "Authorization:",
        "access_token",
        "refresh_token",
        "/Users/",
        "/home/",
    ):
        assert token not in body
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", body)


def test_older_beta1_cannot_be_misrepresented_as_contemporaneous_control() -> None:
    report = json.loads(REPORT.read_text())
    baseline = report["older_beta1_observations"]
    assert baseline["positive"] == {
        "observed": 30,
        "skill_loaded": 27,
        "structural_pass": 15,
    }
    assert baseline["negative"] == {
        "observed": 8,
        "skill_loaded": 0,
        "structural_pass": 8,
    }
    assert baseline["boundary"] == {
        "observed": 8,
        "skill_loaded": 0,
        "structural_pass": 0,
    }
    assert any("not in a contemporaneous randomized" in caveat for caveat in report["caveats"])
    assert "per-turn version" in report["installation_account_state_during_send"]
