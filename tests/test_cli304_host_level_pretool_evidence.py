"""Release-blocking public review of private real CLI304 PreToolUse native QA."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.guarded_rollout import NATIVE_CLI304_SHA, UpdateBlocked, installed_tree
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-22-cli304-host-level-pretool-evidence.json"
AUDITOR = ROOT / "scripts/audit_cli304_host_tool_evidence.py"
QA_MOD = ROOT / "evals/fixtures/cli304-p1d-cohort-20261022"

_spec = importlib.util.spec_from_file_location("cli304_host_tool_evidence_auditor", AUDITOR)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def sha(path: Path) -> str:
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence() -> dict:
    return json.loads(REPORT.read_text())


def test_real_host_tool_sources_and_private_original_are_sha_attested():
    r = evidence()
    assert r["schema_version"] == 1
    assert r["target_cli"] == "2.1.304"
    assert r["official_native_binary_sha256"] == NATIVE_CLI304_SHA
    assert r["auditor_source_sha256"] == sha(AUDITOR)
    assert r["reviewed_qa_mod_tree_sha256"] == installed_tree(QA_MOD)["sha"]
    assert len(r["native_proofs_sha256"]) == 2
    assert all(re.fullmatch(r"[a-f0-9]{64}", x) for x in r["native_proofs_sha256"])
    assert set(r["reviewed_host_sources_sha256"]) == set(_module.SOURCE_FILES)
    for name, digest in r["reviewed_host_sources_sha256"].items():
        assert sha(ROOT / name) == digest
    assert re.fullmatch(r"[a-f0-9]{64}", r["settings_sha256"])


def test_native_actual_tools_are_not_fake_model_or_mock_results():
    r = evidence()
    runs = r["native_runs"]
    assert set(runs) == set(_module.RUNS)
    assert len(runs) == 6
    assert runs["unenrolled_refusal"]["native_tool_names"] == ["Read", "Write"]
    assert runs["enrolled_read_and_write"]["native_tool_names"] == ["Read", "Write"]
    assert runs["bad_mod_still_denied"]["native_tool_names"] == ["Write", "Write"]
    assert runs["broken_hook_no_block"]["native_tool_names"] == ["Read"]
    assert runs["broken_hook_block"]["native_tool_names"] == ["Read"]
    assert runs["same_host_live_freeze"]["native_tool_names"] == ["Read", "Read"]
    assert runs["same_host_live_freeze"]["native_result_turn_counts"] == [2, 2]
    assert runs["bad_mod_still_denied"]["native_result_turn_counts"] == [2, 0, 2]
    for run in runs.values():
        assert run["actual_sonnet_model_seen"] is True
        assert run["tool_result_count"] >= 1
        for field in ("native_wire_sha256", "native_debug_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", run[field])


def test_failure_is_prevented_by_host_failing_closed_not_production_stable():
    r = evidence()
    assert r["observations"] == {
        "unregistered_native_session_refused_read_and_write": True,
        "enrolled_native_session_read_allowed_write_denied": True,
        "successful_read_released_held_native_permit": True,
        "malformed_reloadable_mod_lost_guard_but_external_settings_write_denied": True,
        "missing_policy_executable_fails_open_without_onFailure_block": True,
        "same_missing_executable_blocks_with_onFailure_block": True,
        "one_continuing_host_read_allowed_then_blocked_after_quiescence": True,
        "no_qa_write_targets_created": True,
    }
    assert r["scope_limits"] == {
        "only_explicitly_launched_enrolled_host_sessions": True,
        "external_settings_are_not_organization_managed_policy": True,
        "unregistered_native_sessions_not_globally_controlled": True,
        "tools_except_qa_workspace_read_are_denied_not_live_qualified": True,
        "other_machine_session_coverage_not_proven": True,
        "private_wire_session_tokens_and_debug_excluded_from_git": True,
    }
    assert r["new_cli304_claims_approved"] == 0
    assert r["production_wide_host_protection_proven"] is False
    assert r["stable_release_authorized"] is False


def test_no_user_private_raw_events_or_identity_leak_into_git():
    raw = REPORT.read_text()
    for token in (
        "/home/",
        "/Users/",
        "Authorization:",
        "Cookie:",
        "access_token",
        "session_id",
        "tool_use_id",
        "P1D_GUARD_DENIED_",
        "QA_HOST_READ_OK_20261022",
        "QA_WRITE_HARMLESS",
        "cse_",
    ):
        assert token not in raw
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert approved_claims(claims, "2.1.304", "cli") == []


def test_auditor_refuses_missing_private_host_evidence_and_binary(tmp_path: Path):
    with pytest.raises((UpdateBlocked, OSError, ValueError)):
        _module.audit(tmp_path, tmp_path / "nonexistent-official-native")
