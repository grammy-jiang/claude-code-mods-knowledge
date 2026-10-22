"""Immutable proof fingerprints for actual two-session native QA; always HOLD."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.guarded_rollout import NATIVE_CLI304_SHA, UpdateBlocked, installed_tree
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-22-cli304-p1d-managed-cohort-evidence.json"
AUDITOR = ROOT / "scripts/audit_cli304_cohort_p1d.py"
WRAPPER = ROOT / "scripts/guard_cli304_managed_run.py"
PLUGIN = ROOT / "evals/fixtures/cli304-p1d-cohort-20261022"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data() -> dict:
    return json.loads(REPORT.read_text())


def test_two_actual_native_cohorts_private_replay_and_source_fingerprints():
    record = data()
    assert record["target_cli"] == "2.1.304"
    real = record["actual_native_cohort"]
    assert real["native_binary_sha256"] == NATIVE_CLI304_SHA
    assert real["auditor_sha256"] == sha(AUDITOR)
    assert real["original_qa_fixture_tree_sha256"] == installed_tree(PLUGIN)["sha"]
    assert real["native_proof_count"] == 8
    assert len(real["actual_native_proof_sha256"]) == 8
    assert len(real["private_wire_sha256"]) == 8
    assert len(real["private_debug_sha256"]) == 8
    for key in ("actual_native_proof_sha256", "private_wire_sha256", "private_debug_sha256"):
        assert all(re.fullmatch(r"[0-9a-f]{64}", x) for x in real[key])
    assert real["actual_host_probe_model_turns"] == 0
    assert real["actual_host_probes_are_separate_host_invocations_not_hot_reload"] is True
    assert real["external_gate_only_controls_opted_in_operations"] is True
    assert real["unregistered_or_unmediated_sessions_protected"] is False
    assert real["cross_machine_or_production_scope_validated"] is False


def test_two_native_success_and_safe_recovery_negative_case_are_distinguished():
    r = data()["actual_native_cohort"]
    assert r["managed_cohort_scenarios"] == [
        {
            "case": "normal-two-sessions",
            "final_version": "0.0.2",
            "final_epoch": 1,
            "managed_session_count": 2,
            "native_probe_count": 4,
            "native_probe_epochs": {"0": 2, "1": 2},
            "all_managed_session_health_proofs_matched": True,
            "no_outstanding_protected_permits": True,
            "unmanaged_claude_sessions_not_attested": True,
        },
        {
            "case": "rollback-two-sessions",
            "final_version": "0.0.1",
            "final_epoch": 2,
            "managed_session_count": 2,
            "native_probe_count": 4,
            "native_probe_epochs": {"0": 2, "2": 2},
            "all_managed_session_health_proofs_matched": True,
            "no_outstanding_protected_permits": True,
            "unmanaged_claude_sessions_not_attested": True,
        },
    ]


def test_opt_in_external_gate_actually_launches_native_probe_and_freezes():
    r = data()["opt_in_external_command"]
    assert r["native_binary_sha256"] == NATIVE_CLI304_SHA
    assert r["managed_wrapper_sha256"] == sha(WRAPPER)
    assert r["actual_native_cli_spawned_by_gate"] is True
    assert r["actual_claude_guard_denied_before_model"] is True
    assert r["zero_model_turns"] is True
    assert r["managed_permit_released_after_subprocess_exit"] is True
    assert r["new_external_command_rejected_during_quiescence"] is True
    assert r["blocked_command_created_no_side_effect_file"] is True
    assert r["cohort_left_blocked_after_explicit_test_end"] is True
    assert r["unregistered_processes_outside_gate_unprotected"] is True
    for name in ("healthy_native_probe_sha256", "native_binary_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", r[name])


def test_real_proof_report_is_explicitly_not_production_authorization():
    r = data()
    assert r["new_cli304_claims_approved"] == 0
    assert r["stable_release_authorized"] is False
    assert r["full_production_coverage_verified"] is False
    assert r["unmanaged_sessions_still_unprotected"] is True
    assert r["actual_native_cohort"]["stable_release_authorized"] is False
    assert r["opt_in_external_command"]["stable_release_authorized"] is False
    public = REPORT.read_text()
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f-]{27,}", public)
    for private in ("/home/", "/Users/", "access_token", "Authorization:", "session_id"):
        assert private not in public
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert approved_claims(claims, "2.1.304", "cli") == []


def test_offline_replay_requires_genuine_native_binary(tmp_path):
    # Cannot falsely certify source-only CI as a paid native model validation.
    import importlib.util

    spec = importlib.util.spec_from_file_location("native_p1d_replay", AUDITOR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises((UpdateBlocked, OSError, ValueError)):
        mod.audit(tmp_path, tmp_path / "nonexistent-official-binary")
