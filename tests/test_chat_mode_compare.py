"""Compare two actual Chat-mode runs by identical case IDs without inventing an answer pass."""

from __future__ import annotations

from copy import deepcopy

import pytest

from mods_knowledge.chat_mode_compare import ComparisonError, compare_chat_versions

REV = "33706131f05f0aedf49fbb1fc0459854a579316d"
URI = "skills://plugins/claude-code-mods-knowledge/claude-code-mods-development"


def observed(cid: str, version: str, *, loaded: bool, quality: str, category="positive") -> dict:
    return {
        "case_id": cid,
        "category": category,
        "plugin_version": version,
        "conversation_sha256": (cid + version).encode().hex()[:64].ljust(64, "a"),
        "response_sha256": "b" * 64,
        "plugin_id_sha256": "c" * 64 if loaded else None,
        "skill_loaded": loaded,
        "resource_uris": [URI] if loaded else [],
        "expected_activation": category != "negative",
        "observed_claim_ids": ["K-0007"] if loaded else [],
        "official_source_cited": loaded,
        "code_callback_signature_correct": None,
        "answer_quality": quality,
        "quality_flags": [] if quality == "pass" else ["missing-expected-claim-ids"],
        "notes": "Offline fixture only",
        "invocation_mode": "automatic",
    }


def test_exact_matched_cases_define_improvement_and_regression() -> None:
    old = [
        observed("POS-E-01", "0.2.0-beta.1", loaded=True, quality="fail"),
        observed("POS-S-01", "0.2.0-beta.1", loaded=True, quality="pass"),
        observed("POS-T-01", "0.2.0-beta.1", loaded=False, quality="fail"),
        observed("NEG-HVAC", "0.2.0-beta.1", loaded=False, quality="pass", category="negative"),
    ]
    new = [
        observed("POS-E-01", "0.2.0-beta.2", loaded=True, quality="pass"),
        observed("POS-S-01", "0.2.0-beta.2", loaded=False, quality="fail"),
        observed("POS-T-01", "0.2.0-beta.2", loaded=False, quality="fail"),
        observed("NEG-HVAC", "0.2.0-beta.2", loaded=False, quality="pass", category="negative"),
    ]
    data = compare_chat_versions(
        old, new, before_version="0.2.0-beta.1", after_version="0.2.0-beta.2"
    )
    assert data["cases_both_observed"] == 4
    assert data["structurally_recovered"] == ["POS-E-01"]
    assert data["structurally_regressed"] == ["POS-S-01"]
    assert data["persistently_failed"] == ["POS-T-01"]
    assert data["both_passed"] == ["NEG-HVAC"]
    assert data["lost_skill_activation"] == ["POS-S-01"]
    assert data["gained_skill_activation"] == []
    assert data["before_structural_pass"] == 2
    assert data["after_structural_pass"] == 2
    assert data["full_suite_qa_pass"] is False


def test_partial_comparison_does_not_impute_missing_retests() -> None:
    old = [
        observed("POS-E-01", "0.2.0-beta.1", loaded=True, quality="fail"),
        observed("POS-S-01", "0.2.0-beta.1", loaded=True, quality="pass"),
    ]
    new = [observed("POS-E-01", "0.2.0-beta.2", loaded=True, quality="pass")]
    data = compare_chat_versions(
        old, new, before_version="0.2.0-beta.1", after_version="0.2.0-beta.2"
    )
    assert data["cases_both_observed"] == 1
    assert data["cases_before_only"] == ["POS-S-01"]
    assert data["structurally_recovered"] == ["POS-E-01"]
    assert data["answer_semantics_verified"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows.append(deepcopy(rows[0])),
        lambda rows: rows[0].update(plugin_version="0.2.0-beta.999"),
        lambda rows: rows[0].update(prompt="private message"),
        lambda rows: rows[0].update(conversation_sha256="invalid"),
        lambda rows: rows[0].update(invocation_mode="explicit"),
    ],
)
def test_untrusted_run_never_accepted(mutation) -> None:
    old = [observed("POS-E-01", "0.2.0-beta.1", loaded=True, quality="fail")]
    new = [observed("POS-E-01", "0.2.0-beta.2", loaded=True, quality="pass")]
    mutation(new)
    with pytest.raises(ComparisonError):
        compare_chat_versions(old, new, before_version="0.2.0-beta.1", after_version="0.2.0-beta.2")
