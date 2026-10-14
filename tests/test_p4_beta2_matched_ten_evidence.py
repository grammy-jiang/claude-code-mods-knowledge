"""Regression checks for an honest, privacy-preserving real Chat-mode comparison.

These checks validate a published report, not ChatGPT activation or semantic QA.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-15-beta2-matched-ten-chat-mode.json"
NARRATIVE = ROOT / "docs/reports/2026-10-15-beta2-matched-ten-chat-mode.md"


def _load() -> dict:
    return json.loads(REPORT.read_text())


def test_exact_original_p4_prompts_and_distinct_real_conversation_fingerprints() -> None:
    data = _load()
    source = json.loads((ROOT / "evals/p4_cases.json").read_text())
    expected = {row["id"]: row for row in source["cases"]}
    assert data["evaluation"] == "real-ordinary-chat-automatic-selection-two-serial-cohorts"
    assert len(data["cases"]) == data["unique_case_count_per_cohort"] == 10
    assert data["final_replies_per_cohort"] == 10
    assert len({row["case_id"] for row in data["cases"]}) == 10
    for row in data["cases"]:
        case = expected[row["case_id"]]
        assert row["category"] == case["category"]
        assert row["prompt_sha256"] == hashlib.sha256((case["prompt"] + "\n").encode()).hexdigest()
        assert row["observed_model"] == "gpt-6-thinking"
        assert row["observed_effort"] == "standard"
    for cohort in ("baseline", "candidate"):
        rows = [row[cohort] for row in data["cases"]]
        for name in ("conversation_sha256", "response_sha256"):
            values = [row[name] for row in rows]
            assert len(values) == len(set(values)) == 10
            assert all(re.fullmatch(r"[a-f0-9]{64}", value) for value in values)
        assert all(isinstance(row["skill_loaded"], bool) for row in rows)
        assert all(row["structural_verdict"] in ("pass", "fail", "inconclusive") for row in rows)


def test_comparison_retains_failed_candidate_without_fabricating_host_pass() -> None:
    data = _load()
    assert data["candidate_published"] is False
    assert data["candidate_disposition"].startswith("REJECT:")
    positive, negative, boundary = (
        data["categories"][category] for category in ("positive", "negative", "boundary")
    )
    assert positive == {
        "cases": 6,
        "baseline_skill_loaded": 3,
        "candidate_skill_loaded": 0,
        "baseline_structural_pass": 1,
        "candidate_structural_pass": 0,
    }
    assert negative == {
        "cases": 2,
        "baseline_skill_loaded": 0,
        "candidate_skill_loaded": 0,
        "baseline_structural_pass": 2,
        "candidate_structural_pass": 2,
    }
    assert boundary["cases"] == 2
    assert boundary["baseline_skill_loaded"] == boundary["candidate_skill_loaded"] == 0
    assert boundary["baseline_structural_pass"] == boundary["candidate_structural_pass"] == 0
    for category, totals in data["categories"].items():
        group = [r for r in data["cases"] if r["category"] == category]
        assert totals["cases"] == len(group)
        for cohort in ("baseline", "candidate"):
            assert totals[f"{cohort}_skill_loaded"] == sum(r[cohort]["skill_loaded"] for r in group)
            assert totals[f"{cohort}_structural_pass"] == sum(
                r[cohort]["structural_verdict"] == "pass" for r in group
            )
    assert "nonrandomized" in data["cohort_caveat"]


def test_account_rollback_evidence_restricted_to_actual_checks() -> None:
    data = _load()
    account = data["account_rollback"]
    assert account["before_version"] == account["after_version"] == "0.2.0-beta.1"
    assert account["candidate_version_observed"] == "0.3.0-beta.2"
    assert account["after_installed_and_enabled"] is True
    assert account["other_personal_plugins_count"] == 10
    assert account["other_personal_plugins_state_unchanged"] is True
    assert "Point-in-time" in account["limits"]
    audit = data["plugin_package_audit"]
    assert audit["server_sidecars_verified"] is True
    assert audit["candidate_content_files_verified"] == 10
    assert audit["rollback_content_files_verified"] == 10
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", val) for key, val in audit.items() if key.endswith("sha256")
    )
    assert audit["candidate_upload_sha256"] != audit["candidate_download_sha256"]
    assert audit["baseline_upload_sha256"] != audit["rollback_download_sha256"]
    assert (
        data["experimental_candidate_source_revision"] == "582279c9531edc39d4f22ac73bdd497b5e3bab6c"
    )


def test_no_raw_account_conversations_tokens_or_private_identifiers_in_reports() -> None:
    for path in (REPORT, NARRATIVE):
        text = path.read_text()
        for private in (
            r"https?://(?:chatgpt\.com|chat\.openai\.com)/c/",
            r"Plugin_[a-f0-9]{24,}",
            r"(?i)gh[opsu]_[a-z0-9]{20,}",
            r"(?i)sk-[a-z0-9_-]{30,}",
            r"(?i)(?:authorization: bearer|cookie:|session_token=)",
        ):
            assert re.search(private, text) is None
    data = _load()
    assert not ({"raw_reply", "conversation_id", "account_id", "prompt", "token"} & set(data))
    assert len(data["cases"]) == 10
