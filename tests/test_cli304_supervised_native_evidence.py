"""Exact genuine two-Pi CLI304 native supervision proof, never a Stable gate."""

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
REPORT = ROOT / "docs/reports/2026-10-22-cli304-two-pi-supervised-native-evidence.json"
AUDITOR = ROOT / "scripts/audit_cli304_supervised_native.py"
PROBE = ROOT / "scripts/cli304_supervised_qa.py"
HOOK = ROOT / "scripts/cli304_supervised_pretool.py"
SIGNER = ROOT / "src/mods_knowledge/cli304_supervised_attestation.py"
LEASE = ROOT / "src/mods_knowledge/cli304_supervised_lease.py"

_spec = importlib.util.spec_from_file_location("actual_cli304_supervised_auditor", AUDITOR)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def report() -> dict:
    return json.loads(REPORT.read_text())


def test_original_two_distinct_pi_native_binaries_source_and_session_modes():
    r = report()
    assert r["schema"] == 1
    assert r["target_cli"] == "2.1.304"
    hosts = r["actual_native_qa_hosts"]
    assert set(hosts) == {"rpi-a", "rpi-b"}
    source_mapping = {
        "code/mods_knowledge/cli304_supervised_lease.py": LEASE,
        "code/mods_knowledge/cli304_supervised_attestation.py": SIGNER,
        "scripts/cli304_supervised_pretool.py": HOOK,
        "scripts/cli304_supervised_qa.py": PROBE,
    }
    for host, proof in hosts.items():
        assert proof["host_label"] == host
        assert proof["auditor_sha256"] == sha(AUDITOR)
        assert proof["actual_official_native_binary_sha256"] == m.OFFICIAL_SHA
        assert proof["reviewed_source_sha256"] == {
            name: sha(source) for name, source in source_mapping.items()
        }
        assert set(proof["actual_native_modes"]) == {"freeze", "lease-expiry"}
        assert proof["proof_of_heartbeat_expiry_refusal"] is True
        assert proof["proof_of_active_external_freeze_refusal"] is True
        assert proof["full_running_host_inventory_attested"] is False
        for name, detail in proof["actual_native_modes"].items():
            assert detail["mode"] == name
            assert detail["same_native_session_reused"] is True
            assert detail["read_allowed_before_freeze"] is True
            assert detail["read_denied_after_freeze_or_expiry"] is True
            assert detail["actual_native_tools"] == ["Read", "Read"]
            assert detail["original_native_result_turn_counts"] == [2, 2]
            assert detail["managed_policy_onFailure_block"] is True
            assert detail["global_host_coverage_proven"] is False
            for field in (
                "managed_policy_sha256",
                "original_host_wire_sha256",
                "original_host_debug_sha256",
            ):
                assert re.fullmatch(r"[a-f0-9]{64}", detail[field])


def test_signed_live_at_issue_proofs_are_historical_and_now_expired():
    q = report()["signed_live_supervisor_historical_quorum"]
    assert q["actual_signed_live_qa_hosts_at_issue"] == 2
    assert q["host_ids"] == ["rpi-a", "rpi-b"]
    assert q["earliest_witness_expiry"] > q["verification_epoch"]
    assert q["historical_as_of_override"] is True
    assert q["live_witness_is_not_current_after_expiry"] is True
    assert q["complete_global_session_inventory_proven"] is False
    assert q["production_wide_quiescence_authorized"] is False
    assert q["stable_release_authorized"] is False
    assert len(q["signed_receipt_sha256"]) == 2
    assert len(q["public_key_sha256"]) == 2
    assert all(re.fullmatch(r"[a-f0-9]{64}", x) for x in q["signed_receipt_sha256"].values())
    assert report()["historical_witness_was_rejected_as_current_after_expiry"] is True


def test_no_private_identifiers_and_no_version_claim_promotion():
    r = report()
    assert r["all_native_QA_runs_confined_to_private_bwrap_managed_settings"] is True
    assert r["production_host_configuration_unmodified"] is True
    assert r["other_running_sessions_unattested"] is True
    assert r["full_cross_machine_enforcement_not_proven"] is True
    assert r["cli304_claims_approved"] == 0
    assert r["stable_release_authorized"] is False
    text = REPORT.read_text()
    for bad in (
        "/home/",
        "/Users/",
        "session_id",
        "tool_use_id",
        "access_token",
        "Cookie:",
        "Authorization:",
        "parent_supervisor_pid",
        "child_bwrap_pid",
        "boot_id",
        "QA_SUPERVISED_READ_OK_20261022",
    ):
        assert bad not in text
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions")
    assert approved_claims(claims, "2.1.304", "cli") == []


def test_no_private_original_native_logs_cannot_attest_real_host(tmp_path):
    with pytest.raises((m.NativeQAInvalid, OSError, ValueError)):
        m.audit(tmp_path, tmp_path / "nonexistent-native-304", host="rpi-a")
