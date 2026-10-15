"""Fail-closed public checks for real, but protocol-imperfect, ChatGPT QA.

The published source is sanitized evidence only. Unit tests do not speak for
model semantics or authenticate private account/transport traces.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from mods_knowledge.routing_factorial import (
    ARMS,
    EXPECTED_CASES,
    EXPECTED_VARIANTS,
    RoutingExperimentError,
    validate_routing_factorial,
)

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / "docs/reports/2026-10-15-six-arm-automatic-routing-observations.json"
TEXT = ROOT / "docs/reports/2026-10-15-six-arm-automatic-routing-observations.md"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(JSON.read_text())


@pytest.fixture(scope="module")
def suite() -> dict:
    return json.loads((ROOT / "evals/p4_cases.json").read_text())


def test_all_42_actual_observations_match_source_and_have_unique_hashes(
    report: dict, suite: dict
) -> None:
    cases = {case["id"]: case for case in suite["cases"]}
    rows = report["case_results"]
    assert report["arms_order"] == list(ARMS)
    assert report["observed_arms_count"] == report["planned_arms_count"] == 6
    assert report["real_case_records_observed"] == len(rows) == 42
    assert report["all_model_replies_collected"] is True
    assert len({row["conversation_sha256"] for row in rows}) == 42
    assert len({row["case_key"] + row["arm"] for row in rows}) == 42
    for row in rows:
        source = cases[row["case_id"]]
        assert row["prompt_sha256"] == hashlib.sha256(source["prompt"].encode()).hexdigest()
        assert row["category"] == source["category"]
        assert row["status"] == "collected"
        assert row["model"] == "gpt-6-thinking" and row["effort"] == "standard"
        assert re.fullmatch(r"[a-f0-9]{64}", row["response_sha256"])
        assert re.fullmatch(r"[a-f0-9]{64}", row["conversation_sha256"])
        assert row["invocation_mode"] == ("explicit" if row["phase"] == "explicit" else "automatic")
        assert row["structural_verdict"] in ("pass", "fail", "inconclusive")
    for arm in ARMS:
        subset = [r for r in rows if r["arm"] == arm]
        assert len(subset) == 7
        assert Counter(
            (r["phase"], r["case_id"], r["category"], r["invocation_mode"]) for r in subset
        ) == Counter(EXPECTED_CASES)


def test_source_arm_isolation_and_account_rollback_are_not_assumed(report: dict) -> None:
    assert report["schema_version"] == 1
    assert report["report_type"] == "REAL_CHAT_MODE_SIX_ARM_FULL_OBSERVATIONS_TIMING_DEVIATION"
    assert report["source_revision"] == "62ea0714c1340ab6b64220b1e9e256e180d9fb99"
    assert report["metadata_experiments"].keys() == EXPECTED_VARIANTS.keys()
    for arm, (version, plugin, skill, knowledge, changed) in EXPECTED_VARIANTS.items():
        row = report["metadata_experiments"][arm]
        assert row["package_version"] == version
        assert row["plugin_description_new"] is plugin
        assert row["skill_description_new"] is skill
        assert row["knowledge_body_new"] is knowledge
        assert set(row["changed_files"]) == changed
        assert re.fullmatch(r"[a-f0-9]{64}", row["zip_sha256"])
    assert report["rollback_verified_after_full_run"] is True
    assert report["restored_published_plugin_version"] == "0.2.0-beta.1"
    assert report["restored_archive_checked_files"] == 10
    assert report["other_personal_plugins_unchanged"] is True
    assert report["other_personal_plugins_count"] == 10
    assert report["stable_release_qualified"] is False
    assert report["causal_routing_difference_established"] is False


def test_automatic_and_explicit_routing_are_distinct_in_all_arms(report: dict) -> None:
    rows = report["case_results"]
    assert len([r for r in rows if r["invocation_mode"] == "automatic"]) == 36
    assert len([r for r in rows if r["invocation_mode"] == "explicit"]) == 6
    assert report["total_auto_positive_reads"] == 0
    assert report["total_auto_positive_cases"] == 24
    assert report["total_auto_boundary_reads"] == 0
    assert report["total_auto_boundary_cases"] == 6
    assert report["total_auto_unrelated_false_reads"] == 0
    assert report["total_auto_unrelated_cases"] == 6
    assert report["total_explicit_control_reads"] == report["total_explicit_controls"] == 6
    for arm, metrics in report["stats"].items():
        group = [r for r in rows if r["arm"] == arm]
        assert metrics["run_observed"] is True and metrics["collected"] == 7
        positives = [
            r for r in group if r["category"] == "positive" and r["invocation_mode"] == "automatic"
        ]
        boundaries = [r for r in group if r["category"] == "boundary"]
        negatives = [r for r in group if r["category"] == "negative"]
        explicit = [r for r in group if r["invocation_mode"] == "explicit"]
        assert len(positives) == 4 and len(boundaries) == len(negatives) == len(explicit) == 1
        assert all(r["skill_loaded"] is False for r in positives + boundaries + negatives)
        assert all(r["skill_loaded"] is True for r in explicit)
        assert (
            metrics["positive_auto_skill_loads"]
            == metrics["boundary_auto_skill_loads"]
            == metrics["unrelated_false_skill_loads"]
            == 0
        )
        assert metrics["explicit_control_skill_loads"] == 1
        assert metrics["early_e01_skill_loaded"] is False
        assert metrics["late_e01_skill_loaded"] is False


def test_time_and_metadata_protocol_deviation_rejects_full_admission(
    report: dict, suite: dict
) -> None:
    assert report["is_complete"] is False
    assert report["protocol_all_arms_admitted"] is False
    for arm in ARMS:
        conditions = report["arm_conditions"][arm]
        assert all(
            conditions[k] is True
            for k in (
                "advertised_metadata_matched_early",
                "advertised_metadata_matched_late",
                "source_download_matched",
                "auto_send_hints_absent",
                "explicit_control_hint_matched",
            )
        )
        seconds = conditions["early_to_late_seconds"]
        if arm == "A1":
            assert seconds == 55
        else:
            assert 180 <= seconds <= 300
    assert any("55 s" in item for item in report["protocol_deviation"])
    # Factual fully populated records must NOT satisfy the strict validator.
    forced = copy.deepcopy(report)
    forced["is_complete"] = True
    with pytest.raises(RoutingExperimentError, match="timing|wait|protocol"):
        validate_routing_factorial(forced, suite)
    with pytest.raises(RoutingExperimentError, match="Incomplete experiment"):
        validate_routing_factorial(report, suite)


def test_public_report_retains_no_raw_account_ids_or_conversation_data(report: dict) -> None:
    for file in (JSON, TEXT):
        raw = file.read_text()
        for marker in (
            r"https?://(?:chatgpt[.]com|chat[.]openai[.]com)/c/",
            r"Plugin_[0-9a-f]{20,}",
            r"(?i)gh[opsu]_[a-z0-9]{20,}",
            r"(?i)sk-[a-z0-9_-]{30,}",
            r"(?i)(?:authorization: bearer|session_token=|cookie:)",
        ):
            assert re.search(marker, raw) is None
    assert all(
        set(row)
        <= {
            "arm",
            "case_key",
            "case_id",
            "category",
            "phase",
            "invocation_mode",
            "plugin_version",
            "status",
            "skill_loaded",
            "plugin_id_sha256",
            "resource_uris",
            "structural_verdict",
            "quality_flags",
            "known_risks",
            "observed_claim_ids",
            "model",
            "effort",
            "conversation_sha256",
            "response_sha256",
            "prompt_sha256",
        }
        for row in report["case_results"]
    )
