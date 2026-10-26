"""P5 current-source generated Skill has real citations yet failed Evidence lines."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claim_source_link_coverage import audit_claim_evidence_section
from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reports/2026-10-27-p5-cli302-generated-skill-three-arm-evidence.json"
AUDITOR = ROOT / "scripts/audit_p5_cli302_generated_skill_cohort.py"
CHECKER = ROOT / "src/mods_knowledge/claim_source_link_coverage.py"
SOURCE_REVISION = "814bbdaf385feac5d8f022ff8615991a42038ff7"
SKILL_SHA = "619787ebd651b572fc8014526d4b283501db882528f56d76920ddda5a92ca42a"


def source_data() -> dict:
    return json.loads(EVIDENCE.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_private_native_evidence_is_bound_to_this_auditor_and_real_versions():
    data = source_data()
    assert data["schema_version"] == 1
    assert data["compiled_source_revision"] == SOURCE_REVISION
    assert data["generated_skill_sha256"] == SKILL_SHA
    assert data["auditor_source_sha256"] == sha(AUDITOR)
    assert data["approved_cli302_claims"] == 31
    assert data["approved_cli309_claims"] == 0
    assert data["original_cli302_executable_sha256"] == (
        "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10"
    )
    assert data["original_cli309_executable_sha256"] == (
        "9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b"
    )
    for name in ("events.md", "claim-evidence.md"):
        assert re.fullmatch(r"[0-9a-f]{64}", data["reference_sha256"][name])
    assert re.fullmatch(r"[0-9a-f]{64}", data["build_manifest_sha256"])
    assert set(data["cases"]) == {"baseline302", "skill302", "mismatch309"}


def test_302_approved_generated_skill_was_called_but_failed_strict_evidence():
    case = source_data()["cases"]["skill302"]
    assert case["observed_native_cli_version"] == "2.1.302"
    assert case["observed_real_model"] == "claude-sonnet-5-5"
    assert case["native_skill_tool_called"] is True
    assert case["actual_tool_names"] == ["Skill", "Read", "Read", "Read"]
    assert case["native_tool_error_count"] == 0
    assert case["read_events_reference"] is True
    assert case["read_claim_evidence_reference"] is True
    assert case["official_url_anywhere_structural_verdict"] == "pass"
    assert case["opening_evidence_per_claim_verdict"] == "fail"
    assert case["missing_opening_evidence_claim_ids"] == ["K-0041", "K-0067"]
    assert len(case["cited_claim_ids"]) == 8
    assert len(case["evidence_exact_locators_attested"]) == 6
    assert case["answer_code_risk_flags"] == []
    assert case["answer_manual_review_flags"] == []
    for name in (
        "source_private_original_wire_sha256",
        "source_private_debug_sha256",
        "original_model_answer_sha256",
        "operator_prompt_file_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", case[name])


def test_baseline_read_error_is_retained_not_disguised_as_equal_source_arm():
    data = source_data()
    case = data["cases"]["baseline302"]
    assert case["native_skill_tool_called"] is False
    assert case["actual_tool_names"] == ["Read"]
    assert case["native_tool_error_count"] == 1
    assert case["cited_claim_ids"] == []
    assert case["exact_approved_claim_urls_observed"] == 0
    assert case["official_url_anywhere_structural_verdict"] == "fail"
    assert (
        data["no_skill_control_had_one_failed_read_and_is_not_a_perfectly_equivalent_source_arm"]
        is True
    )
    assert data["same_prompt_reported_for_302_arms_from_operator_private_file"] is True
    assert data["native_wires_independently_attest_identical_prompt_text"] is False
    assert (
        data["cases"]["skill302"]["operator_prompt_file_sha256"]
        == case["operator_prompt_file_sha256"]
    )


def test_old_skill_on_cli309_explicitly_abstained_not_release_authorized():
    case = source_data()["cases"]["mismatch309"]
    assert case["observed_native_cli_version"] == "2.1.309"
    assert case["observed_real_model"] == "claude-sonnet-5-5"
    assert case["native_skill_tool_called"] is True
    assert case["read_claim_evidence_reference"] is True
    assert case["read_events_reference"] is True
    assert case["native_tool_error_count"] == 0
    assert case["explicitly_warned_old_version_scope"] is True
    assert case["explicitly_abstained_from_309_guarantee"] is True
    assert case["zero_309_approved_claims"] is True
    assert case["no_309_executable_code_claim"] is True


def test_approved_scopes_and_310_missing_source_prevent_latest_skill_fiction():
    data = source_data()
    assert data["source_link_structure_is_not_semantic_correctness"] is True
    assert data["skill_cohort_evidence_section_completeness_pass"] is False
    assert data["actual_generated_mods_code_typechecked_in_this_cohort"] is False
    assert data["full_agent_quality_acceptance"] is False
    assert data["new_309_claims_approved"] == 0
    assert data["new_production_skills_or_plugin_published"] is False
    assert data["stable_release_authorized"] is False
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert len(approved_claims(claims, "2.1.302", "cli")) == 31
    for version in ("2.1.309", "2.1.310"):
        assert not approved_claims(claims, version, "cli")
        with pytest.raises(CompilerError, match="No approved Claims"):
            compile_knowledge(
                ROOT, api_version=version, surface="cli", source_revision="unapproved-latest"
            )


def test_complete_evidence_requires_scoped_opening_and_exact_locator():
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    url = next(
        e["locator"] for e in claims["K-0040"]["evidence"] if e.get("kind") == "official-doc"
    )
    sample = "## Evidence\n- K-0040 — " + url + "\n## Scope\nCLI302\n## Answer\nK-0040 is scoped.\n"
    ok = audit_claim_evidence_section(sample, claims, version="2.1.302", surface="cli")
    assert ok["structural_verdict"] == "pass"
    missing = sample.replace("## Scope", "## Scope\nK-0041").replace(
        "K-0040 is scoped.", "K-0041 is also relevant."
    )
    bad = audit_claim_evidence_section(missing, claims, version="2.1.302", surface="cli")
    assert bad["structural_verdict"] == "fail"
    assert "K-0041" in bad["cited_claim_ids_missing_exact_evidence_line"]


def test_public_evidence_has_no_original_model_or_account_identifiers():
    raw = EVIDENCE.read_text()
    for forbidden in (
        "/home/",
        "/Users/",
        "Authorization:",
        "Cookie:",
        "access_token",
        "BEGIN PRIVATE KEY",
        "chatgpt.com/c/",
        '"session_id":',
        '"tool_use_id":',
    ):
        assert forbidden not in raw
    assert (
        re.search(
            r"(?<![a-f0-9])[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}(?![a-f0-9])",
            raw,
        )
        is None
    )
    assert source_data()["original_model_text_and_session_ids_not_committed"] is True
