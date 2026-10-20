"""Evidence-only, privacy-preserving replay of real CLI302 Sonnet/Codex A/B.

No model requests run in CI. Native CLI302+tsc findings were generated from
private, hash-pinned original model output snippets in Linux Bubblewrap.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "docs/reports/2026-10-20-p5-real-sonnet-codex-skill-ab.json"
NATIVE = ROOT / "docs/reports/2026-10-20-p5-real-sonnet-codex-native-code-qa.json"
EXPECTED_SOURCES = {
    ("sonnet", "baseline"): "476c5bd82c5e6872a46a8b5795f339cc76a2c9b81f7912f8e1d7b885b9aaea25",
    ("sonnet", "candidate"): "6c3c99dd893bf5f1e4a09a66a696932aba923a62057ff1311503ce1133d9fe10",
    ("codex", "baseline"): "9418250d4deda78afdf11ac8cd4a75df60019113e3584f6e3929836bb88632f4",
    ("codex", "candidate"): "e863ad6d85cfcecb1226f4cd29aa2c3e1fbdc633baffba3c42c8465b3e63f8e8",
}
RISK = "mods-cli302-tool-call-registration-without-catch"


def test_real_A_B_has_four_genuine_native_completions_and_exact_references():
    report = json.loads(LIVE.read_text())
    assert report["target_claude_code_cli"] == "2.1.302"
    assert report["total_valid_genuine_model_turns"] == 4
    assert report["same_user_prompt_per_agent_and_two_arms"] is True
    assert report["all_four_native_agent_finishes"] is True
    assert report["all_four_actual_project_skill_reference_reads"] is True
    assert report["baseline_risky_missing_registration_catch"] == 2
    assert report["candidate_with_registration_catch"] == 2
    assert report["all_four_exact_firstparty_claim_source_structure_pass"] is True
    assert report["frozen_source_revisions"] == {"baseline": "1531e8d", "candidate": "45dcf52"}
    assert len(report["cases"]) == 4
    cases = {(row["agent"], row["arm"]): row for row in report["cases"]}
    assert set(cases) == set(EXPECTED_SOURCES)
    for (agent, arm), item in cases.items():
        assert item["native_model_completion"] is True
        assert item["all_required_project_references_read"] is True
        assert item["required_source_file_reads_verified"] is True
        assert item["tool_errors"] == 0
        assert item["exact_source_claim_link_verdict"] == "pass"
        assert item["source_claims_cited_count"] > 0
        assert item["matched_exact_claim_links_count"] == item["source_claims_cited_count"]
        assert item["generated_code_sha256"] == EXPECTED_SOURCES[(agent, arm)]
        assert item["generated_registration_catch_state"] == (
            "missing" if arm == "baseline" else "attached"
        )
        assert item["risk_flags"] == ([RISK] if arm == "baseline" else [])
        assert item["manual_review_flags"] == []
        assert item["project_local_reference_read_count"] >= 3
        assert len(item["answer_sha256"]) == 64
        assert len(item["wire_sha256"]) == 64
    for agent in ("sonnet", "codex"):
        assert (
            cases[(agent, "baseline")]["prompt_sha256"]
            == (cases[(agent, "candidate")]["prompt_sha256"])
        )
        assert (
            cases[(agent, "baseline")]["skill_sha256"]
            != (cases[(agent, "candidate")]["skill_sha256"])
        )
    for arm in ("baseline", "candidate"):
        assert cases[("sonnet", arm)]["skill_sha256"] == cases[("codex", arm)]["skill_sha256"]


def test_identity_claims_are_scoped_to_observable_native_wire():
    data = json.loads(LIVE.read_text())
    for case in data["cases"]:
        if case["agent"] == "sonnet":
            assert case["model_reported"] == "claude-sonnet-5-5"
            assert case["model_identity_attested_in_native_wire"] is True
            assert isinstance(case["model_cost_estimate_usd"], float)
        else:
            assert case["model_reported"] == "gpt-6.1-sol"
            assert case["model_identity_attested_in_native_wire"] is False
            assert case["requested_medium_effort"] is True
            assert case["input_tokens_reported"] > 0
            assert case["cached_input_tokens_reported"] > 0


def test_model_source_hashes_link_to_exact_native_cli_and_noemit_type_evidence():
    model = json.loads(LIVE.read_text())
    native = json.loads(NATIVE.read_text())
    assert native["native_target_cli"] == "2.1.302"
    assert native["native_executable_sha256"] == (
        "2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10"
    )
    assert native["firstparty_core_types_sha256"] == (
        "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
    )
    assert native["typescript_version"] == "Version 6.0.3"
    assert (
        native["trusted_mock_source_sha256"]
        == hashlib.sha256(
            (ROOT / "evals/fixtures/p5-cli302-hook-catch/observer.test.ts").read_bytes()
        ).hexdigest()
    )
    assert native["original_model_snippets"] == 4
    assert native["native_strict_validations_exit_zero"] == 4
    assert native["old_model_code_catch_warnings"] == 2
    assert native["new_model_code_catch_warnings"] == 0
    assert native["mock_result_denial_and_single_call_tests_passed"] == 8
    assert native["native_core_typechecks_passed"] == 4
    assert native["all_mod_code_execution_only_inside_networkless_bubblewrap"] is True
    cases = {(c["agent"], c["arm"]): c for c in model["cases"]}
    assert len(native["cases"]) == 4
    for row in native["cases"]:
        key = (row["agent"], row["arm"])
        assert row["original_model_code_sha256"] == cases[key]["generated_code_sha256"]
        assert row["native_missing_catch_warning"] == (key[1] == "baseline")
        assert row["native_strict_exit_zero"] is True
        assert row["mock_read_and_denial_single_call_tests_passed"] == 2
        assert row["firstparty_core_typescript_noemit_pass"] is True
        assert row["typecheck_adaptation"] == "add On annotation to register parameter only"


def test_real_model_ab_cannot_certify_production_permissions_or_other_versions():
    model = json.loads(LIVE.read_text())
    native = json.loads(NATIVE.read_text())
    for key in (
        "historical_model_output_bytes_or_prompts_exported",
        "user_account_or_credentials_exported",
        "all_generated_code_executed_by_model",
        "native_code_semantic_quality_approved_by_this_report",
        "real_user_permission_host_verified",
        "full_model_quality_success_rate_proven",
        "full_runtime_generated_tool_types_verified",
        "stable_release_authorized",
    ):
        assert model[key] is False
    for key in (
        "real_user_tool_calls_or_account_mounted",
        "real_host_permission_callbacks_verified",
        "dynamically_merged_builtin_tool_types_verified",
        "full_model_quality_approved",
        "stable_release_authorized",
    ):
        assert native[key] is False
    assert native["model_requests_performed_in_native_validation"] == 0


def test_private_evidence_does_not_exist_in_public_repo():
    for source in (LIVE, NATIVE):
        text = source.read_text()
        for secret in (
            "/Users/",
            "/home/",
            "Cookie:",
            "Authorization:",
            "Plugin_",
            "TASK_ID:",
            "chatgpt.com/c/",
            "raw_reply",
            "sandbox:/mnt/data",
            "declare module 'claude-code'",
        ):
            assert secret not in text
    assert not any(p.name.endswith(".private.jsonl") for p in ROOT.rglob("*"))
    assert not list((ROOT / "evals").rglob("original-codex-model-answer.txt"))


def test_native_replay_refuses_missing_or_tampered_source(monkeypatch, tmp_path):

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from audit_p5_real_model_native_302 import NativeModel302Blocked, audit

    with pytest.raises(NativeModel302Blocked):
        audit(tmp_path, tmp_path / "no-binary", tmp_path / "no-core")
    from audit_p5_real_model_skill_ab import ModelSkillABBlocked
    from audit_p5_real_model_skill_ab import audit as model_audit

    with pytest.raises(ModelSkillABBlocked):
        model_audit(tmp_path)
