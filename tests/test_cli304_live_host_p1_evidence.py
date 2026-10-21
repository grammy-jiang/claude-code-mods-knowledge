"""Offline, fail-closed review of real CLI304 receipts; no private model logs in CI."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-21-cli304-real-host-p1-evidence.json"
FIXTURE = ROOT / "evals/fixtures/cli304-real-host-p1-20261021"
AUDIT = ROOT / "scripts/audit_cli304_live_host_p1.py"
_spec = importlib.util.spec_from_file_location("audited_cli304_actual_host", AUDIT)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
EXPECTED_SOURCES = _module.EXPECTED_SOURCES
OFFICIAL_ASSET_SHA = _module.OFFICIAL_ASSET_SHA
OFFICIAL_NATIVE_SHA = _module.OFFICIAL_NATIVE_SHA
IncompleteHostEvidence = _module.IncompleteHostEvidence
audit = _module.audit


def digest(path: Path) -> str:
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report() -> dict:
    return json.loads(REPORT.read_text())


def test_real_native_host_evidence_is_source_and_auditor_pinned():
    r = report()
    assert r["schema_version"] == 1
    assert r["target_cli"] == "2.1.304"
    assert r["actual_model_identified_by_native_wire"] == "claude-sonnet-5-5"
    assert r["official_native_binary_sha256"] == OFFICIAL_NATIVE_SHA
    assert r["official_release_archive_sha256"] == OFFICIAL_ASSET_SHA
    assert r["audit_script_sha256"] == digest(AUDIT)
    assert r["tested_source_sha256"] == EXPECTED_SOURCES
    for rel, expected in EXPECTED_SOURCES.items():
        public_rel = (
            "chain/qa-outer304/hooks/register.shortcircuit.js" if rel.startswith("raw/") else rel
        )
        assert digest(FIXTURE / public_rel) == expected
    assert len(r["runs"]) == 6
    assert set(r["runs"]) == {
        "read",
        "person",
        "chain",
        "chain-control",
        "reload-corrected",
        "guard-reload",
    }
    assert 0 < r["total_reported_model_cost_usd"] < 0.10
    for run in r["runs"].values():
        assert "claude-sonnet-5-5" in run["model_names_from_native_wire"]
        assert run["event_counts"]["result"] == len(run["result_turns"])
        assert run["cost_usd"] < 0.40
        for field in ("wire_sha256", "debug_sha256", "stderr_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", run[field])
        assert run["stderr_sha256"] == hashlib.sha256(b"").hexdigest()


def test_real_permission_evidence_cannot_be_conflated_with_full_approval():
    r = report()
    o = r["observations"]
    assert o["K-0070"] == {
        "actual_ask_to_person_unattended_denied": True,
        "target_write_absent": True,
        "interactive_human_approval_tested": False,
    }
    assert o["K-0071"] == {
        "real_host_read_isReadOnly_true": True,
        "full_readonly_classification_matrix_tested": False,
    }
    assert o["K-0072"] == {
        "real_two_plugin_short_circuit": True,
        "real_two_plugin_passthrough_control": True,
        "user_visible_skipped_hook_transcript_proven": False,
    }
    assert o["K-0074"]["native_actual_tool_check_exception_caught_and_denied"] is True
    assert o["K-0074"]["all_host_security_precedence_tested"] is False
    assert r["runs"]["read"]["real_tool_use_names"] == ["Read", "Read"]
    assert r["runs"]["read"]["real_tool_result_errors"] == 2
    assert r["runs"]["person"]["real_tool_use_names"] == ["Write"]
    assert r["runs"]["person"]["real_tool_result_errors"] == 1


def test_actual_failed_reload_security_regression_is_never_reported_as_success():
    r = report()
    reload = r["observations"]["K-0073"]
    assert reload["reload_ack_despite_parse_error"] is True
    assert reload["previous_hook_module_unloaded"] is True
    assert reload["old_command_name_still_callable"] is True
    assert reload["new_command_content_active_after_failed_reload"] is True
    assert reload["previous_benign_guard_denied_before_reload"] is True
    assert reload["previous_benign_guard_lost_after_reload"] is True
    assert reload["old_version_security_hook_preserved"] is False
    assert reload["target_profile_pass"] is False
    assert r["runs"]["guard-reload"]["result_turns"] == [0, 0, 1]
    assert r["runs"]["reload-corrected"]["result_turns"] == [1, 0, 1]
    assert r["release"] == {
        "new_cli304_claims_approved": 0,
        "all_p1_host_semantics_verified": False,
        "cli304_skill_deployment_authorized": False,
        "stable_release_authorized": False,
    }


def test_real_host_receipts_do_not_leak_private_raw_data_to_git():
    data = REPORT.read_text()
    assert r"QA304_BENIGN_BLOCK_THIS" not in data
    assert "claude.ai" not in data
    assert "Authorization:" not in data
    assert "access_token" not in data
    assert "conversation_id" not in data
    assert "session_id" not in data
    assert re.search(r"(?i)https?://chatgpt.com/c/", data) is None
    assert "raw_logs_remain_on_source_host" in data
    assert report()["privacy"]["actual_write_tools_executed"] is False


def test_auditor_rejects_absent_private_model_evidence(tmp_path: Path):
    with pytest.raises(IncompleteHostEvidence):
        audit(tmp_path, tmp_path / "absent_native", tmp_path / "absent_asset")


def test_no_cli304_claim_was_accidentally_approved():
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert approved_claims(claims, "2.1.304", "cli") == []
    assert len(registry) > 0
    for n in range(70, 75):
        claim = ROOT / f"claims/K-{n:04}.json"
        obj = json.loads(claim.read_text())
        assert obj["verification"]["runtime"] != "integration-pass"
        assert obj["lifecycle"] != "approved"
