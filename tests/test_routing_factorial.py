"""Synthetic-only fail-closed tests; NOT simulated ChatGPT model acceptance."""

from __future__ import annotations

import hashlib
import json
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
URI = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development/SKILL.md"


@pytest.fixture(scope="module")
def suite() -> dict:
    return json.loads((ROOT / "evals/p4_cases.json").read_text())


@pytest.fixture
def report(suite: dict) -> dict:
    cases = {case["id"]: case for case in suite["cases"]}
    rows = []
    stats = {}
    for arm_idx, arm in enumerate(ARMS):
        counter = {"early": 0, "explicit": 0, "late": 0}
        for phase, case_id, category, invocation in EXPECTED_CASES:
            case_idx = counter[phase]
            counter[phase] += 1
            loaded = category == "positive" and phase == "explicit"
            sample = {
                "arm": arm,
                "case_key": f"{phase}-{case_idx}-{case_id}",
                "case_id": case_id,
                "category": category,
                "phase": phase,
                "invocation_mode": invocation,
                "plugin_version": (
                    "0.2.0-beta.1" if arm in ("A0", "A1") else EXPECTED_VARIANTS[arm][0]
                ),
                "status": "collected",
                "skill_loaded": loaded,
                "resource_uris": [URI] if loaded else [],
                "plugin_id_sha256": "d" * 64 if loaded else None,
                "structural_verdict": "fail" if category != "negative" else "pass",
                "quality_flags": [],
                "known_risks": [],
                "observed_claim_ids": ["K-0007"] if loaded else [],
                "model": "gpt-6-thinking",
                "effort": "standard",
                "conversation_sha256": hashlib.sha256(
                    f"fake-only-{arm_idx}-{phase}-{case_idx}-{case_id}".encode()
                ).hexdigest(),
                "response_sha256": "f" * 64,
                "prompt_sha256": hashlib.sha256(cases[case_id]["prompt"].encode()).hexdigest(),
            }
            rows.append(sample)
        stats[arm] = {
            "run_observed": True,
            "collected": 7,
            "planned": 7,
            "positive_auto_total": 4,
            "positive_auto_skill_loads": 0,
            "positive_auto_structural_pass": 0,
            "boundary_auto_total": 1,
            "boundary_auto_skill_loads": 0,
            "unrelated_negative_total": 1,
            "unrelated_false_skill_loads": 0,
            "explicit_control_observed": 1,
            "explicit_control_skill_loads": 1,
            "early_e01_skill_loaded": False,
            "late_e01_skill_loaded": False,
        }
    return {
        "schema_version": 1,
        "is_complete": True,
        "arms_order": list(ARMS),
        "planned_arms_count": 6,
        "observed_arms_count": 6,
        "real_case_records_observed": 42,
        "baseline_zip_sha256": "a" * 64,
        "rollback_verified_after_full_run": True,
        "case_results": rows,
        "stats": stats,
        "arm_conditions": {
            arm: {
                "early_to_late_seconds": 191,
                "advertised_metadata_matched_early": True,
                "advertised_metadata_matched_late": True,
                "source_download_matched": True,
                "auto_send_hints_absent": True,
                "explicit_control_hint_matched": True,
            }
            for arm in ARMS
        },
        "metadata_experiments": {
            arm: {
                "package_version": info[0],
                "plugin_description_new": info[1],
                "skill_description_new": info[2],
                "knowledge_body_new": info[3],
                "changed_files": sorted(info[4]),
                "zip_sha256": "b" * 64,
            }
            for arm, info in EXPECTED_VARIANTS.items()
        },
    }


def test_complete_synthetic_matrix_only_passes_structural_consistency(
    report: dict, suite: dict
) -> None:
    result = validate_routing_factorial(report, suite)
    assert result["real_distinct_conversations"] == 42
    assert result["automatic_observations"] == 36
    assert result["explicit_controls"] == 6
    assert set(result["arms"]) == set(ARMS)
    assert all(
        x["positive_read_count"] == 0 and x["explicit_read_count"] == 1
        for x in result["arms"].values()
    )
    assert result["causal_selection_effect_established"] is False
    assert result["model_semantics_verified"] is False
    assert result["full_46_case_ChatGPT_acceptance"] is False
    assert result["stable_release_ready"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(is_complete=False),
        lambda r: r.update(observed_arms_count=5),
        lambda r: r["case_results"].pop(),
        lambda r: r["case_results"][1].update(invocation_mode="automatic"),
        lambda r: r["case_results"][0].update(model="unknown"),
        lambda r: r["case_results"][0].update(effort="extended"),
        lambda r: r["case_results"][0].update(prompt_sha256="f" * 64),
        lambda r: r["case_results"][0].update(plugin_version="0.3.0-beta.9"),
        lambda r: r["case_results"][0].update(
            conversation_sha256=r["case_results"][1]["conversation_sha256"]
        ),
        lambda r: r["case_results"][0].update(
            resource_uris=["skills://plugins/other-plugin/skill.md"]
        ),
        lambda r: r["case_results"][1].update(plugin_id_sha256="e" * 64),
        lambda r: r["metadata_experiments"]["V"].update(knowledge_body_new=True),
        lambda r: r["metadata_experiments"]["D"].update(changed_files=["plugin.json"]),
        lambda r: r["stats"]["A0"].update(explicit_control_skill_loads=0),
        lambda r: r.update(rollback_verified_after_full_run=False),
        lambda r: r["case_results"][0].update(conversation_id="private-account-identifier"),
        lambda r: r["case_results"][0].update(case_key="late-0-POS-E-01"),
        lambda r: r["case_results"][0].update(category="negative"),
    ],
)
def test_forged_or_incomplete_factorial_records_fail_closed(
    report: dict, suite: dict, mutation
) -> None:
    mutation(report)
    with pytest.raises(RoutingExperimentError):
        validate_routing_factorial(report, suite)


def test_false_skill_read_rejected_without_canonical_resource_and_instance(
    report: dict, suite: dict
) -> None:
    item = report["case_results"][0]
    item["skill_loaded"] = True
    item["plugin_id_sha256"] = None
    with pytest.raises(RoutingExperimentError):
        validate_routing_factorial(report, suite)


def test_manually_fabricated_new_arm_cannot_be_counted(report: dict, suite: dict) -> None:
    report["arms_order"].append("BYPASS")
    with pytest.raises(RoutingExperimentError):
        validate_routing_factorial(report, suite)


def test_protocol_wait_violation_does_not_pass_full_factorial_admission(
    report: dict, suite: dict
) -> None:
    # Unlike generic cohort counts, descriptor-propagation timing is a
    # requirement of this specific experiment. The real A1 final baseline
    # was sent after only 55 s between its early and late Chat turns.
    report["arm_conditions"] = {
        arm: {
            "early_to_late_seconds": 191 if arm != "A1" else 55,
            "advertised_metadata_matched_early": True,
            "advertised_metadata_matched_late": True,
            "source_download_matched": True,
            "auto_send_hints_absent": True,
            "explicit_control_hint_matched": True,
        }
        for arm in ARMS
    }
    with pytest.raises(RoutingExperimentError, match="timing|wait|protocol"):
        validate_routing_factorial(report, suite)


def test_missing_metadata_advertisement_provenance_is_rejected(report: dict, suite: dict) -> None:
    report["arm_conditions"] = {
        arm: {
            "early_to_late_seconds": 191,
            "advertised_metadata_matched_early": True,
            "advertised_metadata_matched_late": True,
            "source_download_matched": True,
            "auto_send_hints_absent": True,
            "explicit_control_hint_matched": True,
        }
        for arm in ARMS
    }
    report["arm_conditions"]["D"]["advertised_metadata_matched_late"] = False
    with pytest.raises(RoutingExperimentError, match="metadata|protocol"):
        validate_routing_factorial(report, suite)


def test_cannot_claim_full_experiment_without_arm_conditions(report: dict, suite: dict) -> None:
    report.pop("arm_conditions")
    with pytest.raises(RoutingExperimentError, match="conditions|protocol"):
        validate_routing_factorial(report, suite)
