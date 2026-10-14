"""Public real Chat-mode evidence cannot be inflated into host compatibility claims."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_beta5_observed_chat_automatic_and_explicit_paths_are_separate() -> None:
    d = json.loads((ROOT / "docs/reports/2026-10-14-beta5-chat-mode-qa.json").read_text())
    assert d["schema_version"] == 1
    assert d["mode"] == "ordinary_chat"
    assert d["installed_test_version"] == "0.2.0-beta.5"
    assert d["automatic_cases_total"] == 14
    cats = d["automatic_by_category"]
    assert cats["positive"] == {"observed": 8, "skill_loaded": 0, "strict_structural_pass": 0}
    assert cats["boundary"] == {"observed": 4, "skill_loaded": 0, "strict_structural_pass": 0}
    assert cats["negative"] == {"observed": 2, "skill_loaded": 0, "strict_structural_pass": 2}
    assert d["explicit_cases_total"] == 3
    assert len(d["explicit_observations"]) == 3
    assert all(
        item["plugin_resource_read"] and item["reply_received"]
        for item in d["explicit_observations"]
    )
    assert all(item["first_party_source_cited"] for item in d["explicit_observations"])
    assert d["all_46_cases_version_5_executed"] is False
    assert d["answer_semantic_qa_complete"] is False
    assert d["account_rollback_status"] == "verified_installed_and_enabled"
    assert d["account_version_after_qa"] == "0.2.0-beta.1"


def test_beta5_explicit_known_claim_ids_are_present_and_not_an_auto_pass() -> None:
    d = json.loads((ROOT / "docs/reports/2026-10-14-beta5-chat-mode-qa.json").read_text())
    by = {row["test_id"]: row for row in d["explicit_observations"]}
    assert {"K-0032", "K-0031"} <= set(by["EXPLICIT-REGISTER"]["approved_claim_ids"])
    assert "K-0033" in by["EXPLICIT-TEST"]["approved_claim_ids"]
    assert by["EXPLICIT-REGISTER"]["named_register_signature_present"] is True
    assert by["EXPLICIT-TEST"]["test_directory_command_present"] is True
    assert d["automatic_by_category"]["positive"]["skill_loaded"] == 0


def test_strict_manifest_validation_cases_do_not_mislabel_author_as_schema_required() -> None:
    d = json.loads((ROOT / "docs/reports/2026-10-14-strict-author-validation.json").read_text())
    assert d["schema_version"] == 1
    assert d["claim_id"] == "K-0034"
    assert d["target"] == "Claude Code 2.1.296 CLI"
    first, second, third = d["observed_validation"]
    assert (
        first["author_present"] is False
        and first["strict"] is False
        and first["reported_success"] is True
    )
    assert (
        second["author_present"] is False
        and second["strict"] is True
        and second["reported_success"] is False
    )
    assert second["exit_code"] == 1 and "author" in second["manifest_warnings"][0].lower()
    assert (
        third["author_present"] is True
        and third["strict"] is True
        and third["reported_success"] is True
    )


def test_public_evidence_never_includes_original_conversation_text_or_ids() -> None:
    files = [
        ROOT / "docs/reports/2026-10-14-beta5-chat-mode-qa.json",
        ROOT / "docs/reports/2026-10-14-strict-author-validation.json",
        ROOT / "docs/reports/2026-10-14-strict-author-investigation.md",
    ]
    for file in files:
        raw = file.read_text()
        for forbidden in (
            "conversation_id",
            "chatgpt.com/c/",
            "Plugin_",
            "access_token",
            "Cookie:",
            "Authorization: Bearer",
        ):
            assert forbidden not in raw, (file, forbidden)
