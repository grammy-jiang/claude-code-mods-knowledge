"""Keep CLI304 original model warning gates separate from native exit codes.

This is a deterministic, source-anchored audit of a real Bubblewrap run.
CI must not download binaries, call a model or grant user permissions.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.compiler import CompilerError, compile_knowledge
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-20-cli304-original-model-uncaught-gating-native-review.json"
PRIOR = ROOT / "docs/reports/2026-10-20-cli304-native-prior-observer-compat-mock.json"
ORIGINAL = ROOT / "evals/fixtures/p5-native-model-code-302/manifest.json"


def _model_sources():
    manifest = json.loads(ORIGINAL.read_text())
    model_sources = {}
    for item in manifest["model_candidate_sources"]:
        for index, fixture in enumerate(item.get("fixtures", []), 1):
            key = f"{Path(fixture['path']).parts[0]}-{index:02d}"
            model_sources[key] = fixture["code_sha256"]
        for block in item.get("source", {}).get("blocks", []):
            if block.get("fixture_path") and not block["is_shell_command_not_mod_code"]:
                key = f"sonnet-{block['ordinal']:02d}"
                model_sources[key] = block["code_sha256"]
    return model_sources


def test_original_cli304_native_validator_returned_zero_but_all_hooks_unsafe():
    report = json.loads(REPORT.read_text())
    prior = json.loads(PRIOR.read_text())
    assert report["reviewed_target_cli"] == prior["target_cli"] == "2.1.304"
    assert report["official_native_executable_sha256"] == prior["official_native_bin_sha256"]
    assert report["prior_mock_evidence_sha256"] == hashlib.sha256(PRIOR.read_bytes()).hexdigest()
    assert report["official_native_archive_sha256"] == (
        "17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5"
    )
    assert report["native_original_302_model_candidates"] == 5
    assert report["native_strict_validator_exit_zero"] == 5
    assert report["native_uncaught_tool_call_warnings"] == 5
    assert report["additional_fail_closed_safety_gate_blocks"] == 5
    assert report["historical_mocked_read_denial_tests_passed_not_rerun"] == 10
    assert prior["backward_compatible_mocked_read_denial_tests_passed"] == 10
    assert (
        report["original_source_manifest_sha256"]
        == hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    )


def test_original_304_source_fingerprints_and_fail_closed_results():
    report = json.loads(REPORT.read_text())
    cases = report["cases"]
    assert len(cases) == 5
    expected = _model_sources()
    assert set(expected) == {"codex-01", "codex-02", "sonnet-01", "sonnet-02", "sonnet-03"}
    assert {c["candidate"]: c["original_model_source_sha256"] for c in cases} == expected
    for c in cases:
        assert c["native_strict_validation_exit_code"] == 0
        assert c["native_validator_reported_pass"] is True
        assert c["native_uncaught_tool_call_warning"] is True
        assert c["additional_fail_closed_gate"] == "BLOCKED"
        assert c["source_code_type_correctness_certified"] is False


def test_warning_evidence_does_not_promote_unreviewed_304_host_or_claims():
    report = json.loads(REPORT.read_text())
    for field in (
        "host_home_or_credentials_mounted",
        "real_permission_host_or_dynamically_generated_types_verified",
        "no_catch_original_model_hooks_approved_for_deployment",
        "all_31_cli304_claims_approved",
        "full_native_model_skill_acceptance",
        "chatgpt_plugin_release_authorized",
        "stable_release_authorized",
    ):
        assert report[field] is False
    assert report["all_execution_in_linux_bubblewrap_without_network"] is True
    assert report["real_model_calls_or_user_tools_performed"] == 0
    sources = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", sources, ROOT / "sources/snapshots", ROOT / "decisions")
    assert not approved_claims(claims, "2.1.304", "cli")
    with pytest.raises(CompilerError, match="No approved Claims"):
        compile_knowledge(ROOT, api_version="2.1.304", surface="cli", source_revision="hold304")


def test_same_warning_gate_does_not_accept_zero_exit_with_unsafe_hook(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    audit303 = importlib.import_module("audit_cli303_official_native_parity")
    safe = "gating hook with .catch: tool.call\nValidation passed"
    audit303.fail_closed_validation_gate(0, safe)
    with pytest.raises(audit303.Native303Blocked):
        audit303.fail_closed_validation_gate(
            0, "gating hook without .catch: tool.call\nValidation passed"
        )


def test_report_excludes_private_model_answers_and_native_source():
    raw = REPORT.read_text()
    for text in (
        "/Users/",
        "/home/",
        "Authorization:",
        "Cookie:",
        "Plugin_",
        "TASK_ID:",
        "chatgpt.com/c/",
        "raw_reply",
        "declare module 'claude-code'",
        "sandbox:/mnt/data",
    ):
        assert text not in raw
    assert not list(ROOT.glob("evals/fixtures/**/*.d.ts"))
