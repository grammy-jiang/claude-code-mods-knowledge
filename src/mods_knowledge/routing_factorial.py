"""Fail-closed, source-matched verification of *sanitized* P4 routing experiments.

Input is independently collected actual ordinary Chat-mode evidence, not an
instruction to contact an account or run a model. This validates structure and
provenance consistency only; it cannot authenticate private provider traces,
prove why model routing changed, or substitute for semantic review.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping

from .chat_mode_evidence import is_plugin_skill_resource_uri

ARMS = ("A0", "V", "D", "K", "F", "A1")
_SKILL = "skills/claude-code-mods-development/SKILL.md"
_TYPES = "skills/claude-code-mods-development/references/types.md"
_TESTING = "skills/claude-code-mods-development/references/testing.md"
EXPECTED_VARIANTS = {
    "V": ("0.3.1-beta.1", False, False, False, {"plugin.json"}),
    "D": ("0.3.1-beta.4", True, True, False, {"plugin.json", _SKILL}),
    "K": ("0.3.1-beta.5", False, False, True, {"plugin.json", _SKILL, _TYPES, _TESTING}),
    "F": ("0.3.1-beta.6", True, True, True, {"plugin.json", _SKILL, _TYPES, _TESTING}),
}
EXPECTED_CASES = (
    ("early", "POS-E-01", "positive", "automatic"),
    ("explicit", "POS-E-01", "positive", "explicit"),
    ("late", "POS-E-01", "positive", "automatic"),
    ("late", "POS-Q-01", "positive", "automatic"),
    ("late", "POS-U-01", "positive", "automatic"),
    ("late", "BOUND-HISTORY", "boundary", "automatic"),
    ("late", "NEG-HVAC", "negative", "automatic"),
)
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ALLOWED_ROWS = frozenset(
    {
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
)


class RoutingExperimentError(ValueError):
    """Missing, contradictory, or potentially private routing experiment data."""


def _require(test: bool, message: str) -> None:
    if not test:
        raise RoutingExperimentError(message)


def validate_routing_factorial(report: Mapping, suite: Mapping) -> dict:
    """Accept only all six complete observed cohorts with distinct real turns.

    Caveat: hashes/identity are operator-provided and cannot cryptographically
    authenticate the ChatGPT session or the model's server-side selection.
    No member of an explicit-control cohort is counted as automatic routing.
    """
    _require(isinstance(report, Mapping) and isinstance(suite, Mapping), "Invalid report inputs")
    _require(report.get("schema_version") == 1, "Unexpected experiment schema")
    _require(report.get("is_complete") is True, "Incomplete experiment cannot qualify")
    _require(report.get("arms_order") == list(ARMS), "Changed experimental arm order")
    _require(
        report.get("planned_arms_count") == report.get("observed_arms_count") == 6,
        "Missing experiment arm",
    )
    _require(report.get("real_case_records_observed") == 42, "Missing real model observations")
    _require(
        isinstance(report.get("baseline_zip_sha256"), str)
        and bool(_SHA.fullmatch(report["baseline_zip_sha256"])),
        "Missing release source digest",
    )
    _require(
        isinstance(report.get("metadata_experiments"), Mapping),
        "Missing variant packaging provenance",
    )
    variants = report["metadata_experiments"]
    _require(set(variants) == set(EXPECTED_VARIANTS), "Unexpected version arm labels")
    for arm, (
        version,
        plugin_desc,
        skill_desc,
        knowledge,
        expected_files,
    ) in EXPECTED_VARIANTS.items():
        val = variants[arm]
        _require(isinstance(val, Mapping), "Invalid package description")
        _require(val.get("package_version") == version, "Mismatched version arm")
        for key, expected in (
            ("plugin_description_new", plugin_desc),
            ("skill_description_new", skill_desc),
            ("knowledge_body_new", knowledge),
        ):
            _require(
                type(val.get(key)) is bool and val[key] is expected,
                "Non-isolated candidate factors",
            )
        _require(
            isinstance(val.get("changed_files"), list)
            and set(val["changed_files"]) == expected_files
            and len(val["changed_files"]) == len(expected_files),
            "Candidate source files changed outside factor plan",
        )
        _require(
            isinstance(val.get("zip_sha256"), str) and bool(_SHA.fullmatch(val["zip_sha256"])),
            "Candidate ZIP checksum missing",
        )

    # Real beta routing comparisons require their declared time and metadata
    # conditions, in addition to complete tool/read events. A final baseline
    # bookend with a 55-second early-to-late interval is observational evidence
    # but cannot be admitted as a completed 180-second propagation test.
    conditions = report.get("arm_conditions")
    _require(
        isinstance(conditions, Mapping) and set(conditions) == set(ARMS),
        "Missing arm protocol conditions",
    )
    expected_bool_conditions = (
        "advertised_metadata_matched_early",
        "advertised_metadata_matched_late",
        "source_download_matched",
        "auto_send_hints_absent",
        "explicit_control_hint_matched",
    )
    for arm in ARMS:
        entry = conditions[arm]
        _require(
            isinstance(entry, Mapping)
            and set(entry) == {"early_to_late_seconds", *expected_bool_conditions},
            "Malformed timing/metadata protocol conditions",
        )
        spacing = entry["early_to_late_seconds"]
        _require(
            type(spacing) in (int, float) and spacing >= 180 and spacing <= 86_400,
            f"{arm}: early-to-late timing wait did not meet planned protocol",
        )
        for field in expected_bool_conditions:
            _require(
                type(entry[field]) is bool and entry[field] is True,
                f"{arm}: metadata/send protocol condition was not confirmed",
            )

    cases = suite.get("cases")
    _require(isinstance(cases, list), "Expected original P4 evaluation suite")
    mapped = {x.get("id"): x for x in cases if isinstance(x, Mapping)}
    _require(len(mapped) == len(cases), "Duplicate original P4 case identity")
    for _, cid, category, _ in EXPECTED_CASES:
        item = mapped.get(cid)
        _require(
            isinstance(item, Mapping)
            and item.get("category") == category
            and isinstance(item.get("prompt"), str),
            "Original P4 case mismatch",
        )

    rows = report.get("case_results")
    _require(
        isinstance(rows, list) and len(rows) == 42, "Report must contain 42 real final replies"
    )
    checked: dict[str, list[dict]] = {arm: [] for arm in ARMS}
    all_conversations: set[str] = set()
    instance_digests: set[str] = set()
    for row in rows:
        _require(
            isinstance(row, dict) and set(row) <= _ALLOWED_ROWS, "Unsafe or unknown case fields"
        )
        arm = row.get("arm")
        _require(arm in checked, "Unknown case arm")
        phase, cid, category, mode = (
            row.get("phase"),
            row.get("case_id"),
            row.get("category"),
            row.get("invocation_mode"),
        )
        _require(
            (phase, cid, category, mode) in EXPECTED_CASES,
            "Changed P4 prompt, category, or invocation mode",
        )
        in_phase = [sample for sample in EXPECTED_CASES if sample[0] == phase]
        phase_index = next(i for i, sample in enumerate(in_phase) if sample[1] == cid)
        _require(
            row.get("case_key") == f"{phase}-{phase_index}-{cid}",
            "Unexpected case key",
        )
        version = "0.2.0-beta.1" if arm in ("A0", "A1") else EXPECTED_VARIANTS[arm][0]
        _require(row.get("plugin_version") == version, "Wrong installed Plugin version")
        _require(row.get("status") == "collected", "Missing completed original model turn")
        _require(type(row.get("skill_loaded")) is bool, "Unobserved Skill activation")
        _require(
            row.get("model") == "gpt-6-thinking" and row.get("effort") == "standard",
            "Actual model or reasoning effort drift",
        )
        _require(
            row.get("structural_verdict") in ("pass", "fail", "inconclusive"),
            "Missing structural result",
        )
        _require(
            isinstance(row.get("quality_flags"), list)
            and all(isinstance(v, str) for v in row["quality_flags"]),
            "Invalid quality flags",
        )
        _require(
            isinstance(row.get("known_risks"), list)
            and all(isinstance(v, str) for v in row["known_risks"]),
            "Invalid known-risk metadata",
        )
        _require(
            isinstance(row.get("observed_claim_ids"), list)
            and all(
                isinstance(v, str) and re.fullmatch(r"K-[0-9]{4,}", v)
                for v in row["observed_claim_ids"]
            ),
            "Invalid Claim ID",
        )
        resources = row.get("resource_uris")
        _require(
            isinstance(resources, list) and len(resources) == len(set(resources)),
            "Invalid/duplicate resource URIs",
        )
        _require(
            all(is_plugin_skill_resource_uri(uri) for uri in resources),
            "Noncanonical plugin resource read",
        )
        if row["skill_loaded"]:
            # Source URI alone is not enough: resource reads must belong to a
            # single exact installed plugin instance across all six arms.
            _require(
                bool(resources)
                and isinstance(row.get("plugin_id_sha256"), str)
                and bool(_SHA.fullmatch(row["plugin_id_sha256"])),
                "Unsubstantiated Skill read",
            )
            instance_digests.add(row["plugin_id_sha256"])
        else:
            # Plugin digest is present in the private collector only for a
            # canonical observed Skill load, never infer it for misses.
            _require(not resources, "Unloaded Skill has claimed read URIs")
        _require(len(instance_digests) <= 1, "Multiple Plugin identities across experiment")
        for name in ("conversation_sha256", "response_sha256", "prompt_sha256"):
            _require(
                isinstance(row.get(name), str) and bool(_SHA.fullmatch(row[name])),
                "Missing real content evidence hash",
            )
        _require(
            row["conversation_sha256"] not in all_conversations,
            "Reused real conversation or duplicate send",
        )
        all_conversations.add(row["conversation_sha256"])
        _require(
            row["prompt_sha256"] == hashlib.sha256(mapped[cid]["prompt"].encode()).hexdigest(),
            "Prompt no longer matches frozen original P4",
        )
        checked[arm].append(row)

    computed = {}
    for arm, samples in checked.items():
        _require(len(samples) == 7, "Missing samples for one candidate")
        keys = [(x["phase"], x["case_id"], x["category"], x["invocation_mode"]) for x in samples]
        _require(Counter(keys) == Counter(EXPECTED_CASES), "Missing/duplicated arm-case provenance")
        automatic = [x for x in samples if x["invocation_mode"] == "automatic"]
        positive = [x for x in automatic if x["category"] == "positive"]
        boundary = [x for x in automatic if x["category"] == "boundary"]
        negative = [x for x in automatic if x["category"] == "negative"]
        explicit = [x for x in samples if x["invocation_mode"] == "explicit"]
        _require(
            (len(positive), len(boundary), len(negative), len(explicit)) == (4, 1, 1, 1),
            "Incorrect case-family counts",
        )
        stats = report.get("stats", {}).get(arm)
        _require(isinstance(stats, Mapping), "Missing per-arm metrics")
        expected = {
            "run_observed": True,
            "collected": 7,
            "planned": 7,
            "positive_auto_total": 4,
            "positive_auto_skill_loads": sum(x["skill_loaded"] for x in positive),
            "positive_auto_structural_pass": sum(
                x["structural_verdict"] == "pass" for x in positive
            ),
            "boundary_auto_total": 1,
            "boundary_auto_skill_loads": sum(x["skill_loaded"] for x in boundary),
            "unrelated_negative_total": 1,
            "unrelated_false_skill_loads": sum(x["skill_loaded"] for x in negative),
            "explicit_control_observed": 1,
            "explicit_control_skill_loads": sum(x["skill_loaded"] for x in explicit),
            "early_e01_skill_loaded": next(
                x["skill_loaded"] for x in positive if x["phase"] == "early"
            ),
            "late_e01_skill_loaded": next(
                x["skill_loaded"]
                for x in positive
                if x["phase"] == "late" and x["case_id"] == "POS-E-01"
            ),
        }
        for key, value in expected.items():
            _require(
                stats.get(key) == value and type(stats.get(key)) is type(value),
                "Forged/mismatched per-arm metric",
            )
        computed[arm] = {
            "positive_read_count": expected["positive_auto_skill_loads"],
            "positive_denominator": 4,
            "boundary_read_count": expected["boundary_auto_skill_loads"],
            "negative_false_read_count": expected["unrelated_false_skill_loads"],
            "explicit_read_count": expected["explicit_control_skill_loads"],
            "early_e01_read": expected["early_e01_skill_loaded"],
            "late_e01_read": expected["late_e01_skill_loaded"],
        }
    _require(
        report.get("rollback_verified_after_full_run") is True,
        "Published Beta.1 account rollback not verified",
    )
    return {
        "schema_version": 1,
        "status": "REAL_SIX_ARM_STRUCTURAL_OBSERVATIONS_ONLY",
        "arms": computed,
        "real_distinct_conversations": len(all_conversations),
        "automatic_observations": 6 * 6,
        "explicit_controls": 6,
        "causal_selection_effect_established": False,
        "model_semantics_verified": False,
        "full_46_case_ChatGPT_acceptance": False,
        "stable_release_ready": False,
        "caveat": "Serial same-account cohorts; small samples and model-mediated routing do not prove which configuration caused differences. Private tool traces must be independently trusted.",
    }
