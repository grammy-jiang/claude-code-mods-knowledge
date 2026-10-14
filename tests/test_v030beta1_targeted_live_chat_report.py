"""The pilot must never be mislabeled a full P4/P6 or model-host acceptance pass."""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA = (
    Path(__file__).resolve().parents[1]
    / "docs/reports/2026-10-14-v030beta1-real-chat-targeted.json"
)
SHA = re.compile(r"[a-f0-9]{64}\Z")


def test_real_pilot_is_explicitly_partial_and_source_bound() -> None:
    r = json.loads(DATA.read_text())
    assert r["schema_version"] == 1
    assert r["plugin_version"] == "0.3.0-beta.1"
    assert (
        r["installed_candidate_reviewed_source_revision"]
        == "158acdc7c785df6aa9fbecb11187e29ac400392b"
    )
    assert r["target_claude_code_cli"] == "2.1.296"
    assert r["chat_surface"] == "ordinary_chat"
    assert r["summary"]["planned_cases"] == 6
    assert r["summary"]["confirmed_sent_and_collected"] == 4
    assert r["summary"]["ambiguous_send_timeouts_never_retried"] == 2
    assert r["summary"]["full_p4_46_case_suite_pass"] is False
    assert r["summary"]["stable_release_ready"] is False
    assert r["native_evidence"]["real_claude_model_inference"] == "not_run"
    assert r["native_evidence"]["observer_mutation_control"] == "expected_1_fail_detected"


def test_real_pilot_counts_are_derived_from_genuine_distinct_records() -> None:
    r = json.loads(DATA.read_text())
    rows = r["cases"]
    assert len(rows) == 6
    assert [row["case_id"] for row in rows] == [
        "POS-E-01",
        "POS-Q-01",
        "POS-T-STRICT-AUTHOR",
        "BOUND-VERSION-NEW",
        "POS-E-01-AUTO",
        "NEG-TYPESCRIPT",
    ]
    assert len({row["case_id"] for row in rows}) == 6
    assert all(SHA.fullmatch(row["prompt_sha256"]) for row in rows)
    ambiguous = [row for row in rows if row["send_status"] == "ambiguous_timeout_no_retry"]
    assert len(ambiguous) == 2
    assert all(
        row["reply_status"] == "not_run" and "response_sha256" not in row for row in ambiguous
    )
    observed = [row for row in rows if row["send_status"] == "sent"]
    assert len(observed) == 4
    assert all(
        row["reply_status"] == "collected" and SHA.fullmatch(row["response_sha256"])
        for row in observed
    )
    assert len({row["response_sha256"] for row in observed}) == 4
    assert len({row["private_evidence_sha256"] for row in observed}) == 4
    assert all(row["known_risk_flags"] == [] for row in observed)
    assert [(row["case_id"], row["actual_plugin_skill_read"]) for row in observed] == [
        ("POS-T-STRICT-AUTHOR", True),
        ("BOUND-VERSION-NEW", True),
        ("POS-E-01-AUTO", True),
        ("NEG-TYPESCRIPT", False),
    ]
    assert r["summary"]["positive_auto_observed"] == 1
    assert r["summary"]["positive_auto_skill_loads"] == 1
    assert r["summary"]["negative_auto_observed"] == 1
    assert r["summary"]["negative_auto_false_activations"] == 0
    assert r["summary"]["explicit_collected"] == 2
    assert r["summary"]["explicit_skill_loads"] == 2
    assert next(x for x in observed if x["category"] == "boundary")["invocation_mode"] == "explicit"


def test_real_pilot_content_hashes_are_sanitized_and_not_account_proof() -> None:
    text = DATA.read_text()
    for forbidden in (
        "conversation_id",
        "Plugin_",
        "chatgpt.com/c/",
        "Cookie:",
        "Authorization:",
        "refresh_token",
        "/home/",
        "/Users/",
        "private_reply",
        "user_id",
    ):
        assert forbidden not in text
    r = json.loads(text)
    bundle = r["account_download_content_validation"]
    assert bundle["canonical_files_matched"] == 10
    assert bundle["sidecar_validation"] == "pass"
    assert SHA.fullmatch(bundle["canonical_content_sha256"])
    assert SHA.fullmatch(bundle["uploaded_zip_sha256"])
    assert SHA.fullmatch(bundle["downloaded_zip_sha256"])
    assert bundle["uploaded_zip_sha256"] != bundle["downloaded_zip_sha256"]
    assert len(r["native_evidence"]["private_log_sha256"]) == 4
    assert all(SHA.fullmatch(h) for h in r["native_evidence"]["private_log_sha256"].values())
