"""Immutable manually-reviewed boundary triage must not imply Plugin activation."""

from __future__ import annotations

import json
from pathlib import Path

DOC = (
    Path(__file__).resolve().parents[1]
    / "docs/reports/2026-10-18-chatmode-046-boundary-manual-review.json"
)


def test_all_eight_real_boundary_sha_bound_and_release_remains_hold() -> None:
    raw = DOC.read_text(encoding="utf-8")
    d = json.loads(raw)
    assert d["target_cli"] == "2.1.302"
    assert d["plugin_version"] == "0.4.7-beta.1"
    assert d["boundary_cases_reviewed"] == 8
    assert d["boundary_actual_plugin_reads"] == 0
    assert d["boundary_plugin_activation_pass"] == 0
    assert d["boundary_safety_or_cautious_abstention_text"] == 4
    assert d["boundary_requires_remediation_or_source_proof"] == 4
    assert d["semantic_review_is_not_verified_plugin_activation"] is True
    assert d["full_boundary_release_pass"] is False
    assert d["all_46_release_pass"] is False
    assert d["disposition"] == "HOLD"
    assert d["reply_text_account_identity_or_artifact_exported"] is False
    assert len(d["cases"]) == 8
    assert len({c["case_id"] for c in d["cases"]}) == 8
    assert all(len(c["reply_sha256"]) == 64 for c in d["cases"])
    assert all(c["observed_plugin_reads"] == 0 for c in d["cases"])
    assert {
        c["case_id"] for c in d["cases"] if c["manual_text_disposition"] == "requires_remediation"
    } == {
        "BOUND-VERSION-OLD",
        "BOUND-VERSION-NEW",
        "BOUND-UNKNOWN-VERSION",
        "BOUND-SKILL-ROLE",
    }
    for forbidden in (
        "/home/",
        "/Users/",
        "Models.noindex",
        "conversation_id",
        "Plugin_26915045",
        "chatgpt.com/c/",
        "sk-ant",
        "sk-proj",
        "Bearer ",
    ):
        assert forbidden not in raw
