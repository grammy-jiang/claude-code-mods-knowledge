"""Original full Chat Mode boundary technical triage must never upgrade the release."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/reports/2026-10-18-claude302-chatmode-beta048-boundary-technical-review.json"


def test_original_eight_boundary_replies_do_not_establish_plugin_success() -> None:
    report = json.loads(PATH.read_text())
    assert report["candidate"] == "0.4.8-beta.1"
    assert report["target_cli"] == "2.1.302"
    assert report["boundary_original_final_reply_hashes_verified"] == 8
    assert report["boundary_skill_resource_activations"] == 0
    assert report["boundary_auto_activation_pass"] == 0
    assert report["every_boundary_full_release_pass"] is False
    assert len(report["cases"]) == 8
    assert Counter(x["textual_technical_disposition"] for x in report["cases"]) == {
        "requires_remediation": 4,
        "safety_intent_pass_source_unverified": 4,
    }
    assert {x["case_id"] for x in report["cases"]} == {
        "BOUND-VERSION-OLD",
        "BOUND-VERSION-NEW",
        "BOUND-UNKNOWN-VERSION",
        "BOUND-HISTORY",
        "BOUND-SURFACE",
        "BOUND-INJECTION",
        "BOUND-PLUGIN-PRIV",
        "BOUND-SKILL-ROLE",
    }
    assert all(not x["automatic_activation_pass"] for x in report["cases"])
    assert all(not x["whole_answer_native_code_semantics_approved"] for x in report["cases"])
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", x["original_response_sha256"]) for x in report["cases"]
    )


def test_report_does_not_publish_private_conversation_or_artifact() -> None:
    raw = PATH.read_text()
    for forbidden in (
        "/Users/",
        "/home/",
        "Plugin_",
        "Cookie:",
        "Authorization:",
        "TASK_ID:",
        "chatgpt.com/c/",
        "sandbox:/mnt/data",
    ):
        assert forbidden not in raw
    assert re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", raw) is None
