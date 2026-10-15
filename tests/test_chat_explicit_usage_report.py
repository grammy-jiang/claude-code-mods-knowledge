"""Auditable, sanitized QA claims for real Chat Mode direct Plugin usage.

These are consistency/privacy checks over bounded observations. Passing tests
never turns explicit invocation into model auto-routing or executable code QA.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-15-chat-mode-explicit-usage-qa.json"
SUMMARY = ROOT / "docs/reports/2026-10-15-chat-mode-explicit-usage-qa.md"


def load_report() -> dict:
    return json.loads(REPORT.read_text())


def test_paired_prompt_text_is_identical_but_plugin_hint_provenance_differs() -> None:
    data = load_report()
    source = {
        case["id"]: case for case in json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    }
    assert data["chat_surface"] == "chat" and data["work_mode_included"] is False
    assert data["installed_plugin_version"] == "0.2.0-beta.1"
    assert data["knowledge_revision"] == "0.1.0"
    assert data["model"] == "gpt-6-thinking" and data["effort"] == "standard"
    assert data["complete_conversations"] == len(data["cases"]) == 12
    assert len({item["conversation_sha256"] for item in data["cases"]}) == 12
    paired = data["paired_exact_identical_input_cases"]
    assert paired == ["POS-E-01", "POS-Q-01", "POS-U-01", "BOUND-VERSION-NEW"]
    for cid in paired:
        cases = [x for x in data["cases"] if x["case_id"] == cid]
        assert len(cases) == 2
        assert {x["variant"] for x in cases} == {"plain-text-mention", "selected-plugin"}
        assert len({x["sent_text_sha256"] for x in cases}) == 1
        assert len({x["conversation_sha256"] for x in cases}) == 2
        assert cases[0]["text_mentions_plugin"] is True
        assert cases[1]["text_mentions_plugin"] is True
        assert cases[0]["ui_selected"] is False
        assert cases[1]["ui_selected"] is True
    for item in data["cases"]:
        assert item["category"] == source[item["case_id"]]["category"]
        assert item["expected_claims"] == source[item["case_id"]].get("expected_claim_ids", [])
        assert re.fullmatch(r"[a-f0-9]{64}", item["sent_text_sha256"])
        assert re.fullmatch(r"[a-f0-9]{64}", item["full_response_sha256"])
        assert item["plugin_version"] == "0.2.0-beta.1"
        assert item["model"] == "gpt-6-thinking" and item["effort"] == "standard"
        assert item["skill_loaded"] is True and item["resource_uris"]
        assert all(
            uri.startswith(
                "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"
            )
            for uri in item["resource_uris"]
        )
        assert item["invocation_mode"] == ("explicit" if item["ui_selected"] else "automatic")


def test_full_visible_turn_scoring_does_not_count_the_last_fragment_only() -> None:
    data = load_report()
    rows = data["cases"]
    expected = {"1": 1, "2": 9, "3": 2}
    assert data["response_segments_histogram"] == expected
    assert Counter(row["assistant_text_segments"] for row in rows) == {1: 1, 2: 9, 3: 2}
    assert sum(row["assistant_text_segments"] > 1 for row in rows) == 11
    assert all(sum(row["segment_lengths"]) <= row["full_response_chars"] for row in rows)
    assert data["positive_structural_passes_total"] == 9
    assert data["positive_cases_total"] == 9
    for row in rows:
        assert row["official_source_cited"] is True
        if row["category"] == "positive":
            assert row["expected_claims_covered"] is True
            assert row["structural_verdict"] == "pass"
        else:
            assert row["structural_verdict"] == "inconclusive"
    assert len(data["prior_six_explicit_controls"]) == 6
    assert all(x["assistant_visible_segments"] == 1 for x in data["prior_six_explicit_controls"])


def test_native_verified_example_failures_are_not_papered_over_by_claims() -> None:
    data = load_report()
    classes = Counter(row["independent_review_class"] for row in data["cases"])
    assert classes["native_reproduced_invalid_example"] == 3
    assert classes["boundary_abstention_with_invalid_example"] == 1
    assert data["positive_native_invalid_example_cases"] == 3
    assert data["boundaries_with_invalid_reference_example"] == 1
    assert data["not_complete_semantic_acceptance"] is True
    assert data["no_stable_routing_claim"] is True
    faulty = [
        row
        for row in data["cases"]
        if row["independent_review_class"] == "native_reproduced_invalid_example"
    ]
    assert {row["test_id"] for row in faulty} == {
        "01-plain-text-mention-POS-E-01",
        "02-selected-plugin-POS-E-01",
        "04-selected-plugin-POS-Q-01",
    }
    assert all(row["known_risk_flags"] for row in faulty)
    native = data["native_reproductions"]
    assert native["claude_cli"] == "2.1.296"
    assert native["register_default_destructured"]["strict_validate_exit"] == 1
    assert native["register_named_on"]["strict_validate_exit"] == 0
    assert native["plugin_test_single_test_file"]["exit_code"] == 1
    assert native["plugin_test_plugin_root"]["exit_code"] == 0
    assert native["static_import_helper_with_named_register"]["observed_event_name"] == "tool.call"


def test_public_qa_has_no_private_accounts_chats_or_raw_answers() -> None:
    data = load_report()
    assert data["all_12_actual_canonical_skill_reads"] is True
    assert data["summaries"]["plain_text_mention"]["actual_skill_loads"] == 4
    assert data["summaries"]["ui_selected_plugin"]["actual_skill_loads"] == 8
    for file in (REPORT, SUMMARY):
        raw = file.read_text()
        for forbidden in (
            r"https?://(?:chatgpt[.]com|chat[.]openai[.]com)/c/",
            r"Plugin_[a-f0-9]{24,}",
            r"(?i)(?:ghp_|github_pat_)[a-z0-9_]{20,}",
            r"(?i)sk-[a-z0-9_-]{30,}",
            r"/home/grammy-jiang/",
            r"(?i)(?:authorization: bearer|session_token=|cookie:)",
        ):
            assert re.search(forbidden, raw) is None
    assert all(
        "conversation_id" not in item and "raw_response" not in item for item in data["cases"]
    )


def test_full_answer_hashes_are_not_reused_to_fabricate_multiple_conversations() -> None:
    rows = load_report()["cases"]
    assert len({row["conversation_sha256"] for row in rows}) == 12
    assert len({row["full_response_sha256"] for row in rows}) == 12
    assert all(len(row["full_response_sha256"]) == hashlib.sha256().digest_size * 2 for row in rows)
