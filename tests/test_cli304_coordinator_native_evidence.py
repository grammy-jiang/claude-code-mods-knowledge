"""Mac-signed epoch 1 expiry and epoch 2 recovery are genuine, scoped HOLD."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.cli304_coordinator_grant import NATIVE_304
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/2026-10-22-cli304-mac-signed-epoch-two-host-evidence.json"
AUDITOR = ROOT / "scripts/audit_cli304_coordinator_native.py"

_spec = importlib.util.spec_from_file_location("original_mac_coordinator_native_auditor", AUDITOR)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence() -> dict:
    return json.loads(REPORT.read_text())


def test_real_native_mac_epoch_expiry_and_recovery_both_hosts():
    r = evidence()
    assert r["schema_version"] == 1
    assert r["target_cli"] == "2.1.304"
    assert r["mac_issued_epoch1_to_both_hosts"] is True
    assert r["mac_issued_epoch2_to_new_supervisor_generations"] is True
    assert r["epoch1_grant_delivery_stopped_and_expired"] is True
    assert r["native_tool_denied_after_mac_grant_expiry_on_both_hosts"] is True
    assert r["old_signed_mac_grants_refused_for_new_supervisor_generations"] is True
    assert r["recovery_requires_fresh_mac_authorization"] is True
    assert r["issuing_mac_public_key_sha256"] == _module.EXPECTED_MAC_PUB_SHA
    assert set(r["real_host_evidence"]) == {"rpi-a", "rpi-b"}
    for host, result in r["real_host_evidence"].items():
        assert result["host"] == host
        assert result["target_cli"] == "2.1.304"
        assert result["auditor_sha256"] == sha(AUDITOR)
        assert result["native_binary_sha256"] == NATIVE_304
        assert result["mac_coordinator_public_key_sha256"] == _module.EXPECTED_MAC_PUB_SHA
        assert set(result["real_native_epochs"]) == {"1", "2"}
        assert r["original_private_host_report_sha256"][host].isalnum()
        assert len(r["original_private_host_report_sha256"][host]) == 64
        first = result["real_native_epochs"]["1"]
        second = result["real_native_epochs"]["2"]
        assert first["epoch"] == 1 and second["epoch"] == 2
        assert first["actual_native_tool_uses"] == ["Read", "Read"]
        assert second["actual_native_tool_uses"] == ["Read"]
        assert first["actual_native_model_turn_counts"] == [2, 2]
        assert second["actual_native_model_turn_counts"] == [2]
        assert first["valid_mac_grant_native_read"] is True
        assert first["expired_grant_native_read_denied"] is True
        assert second["valid_mac_grant_native_read"] is True
        assert second["expired_grant_native_read_denied"] is False
        assert result["old_mac_grant_cannot_be_reused_in_new_host_generation"] is True
        assert result["same_original_host_process_for_pre_post_expiry"] is True
        assert all(step["local_supervisor_left_blocked_after_test"] for step in (first, second))


def test_original_code_and_private_wire_hashes_are_sha256_pinned():
    r = evidence()
    matching_sources = {
        "src/mods_knowledge/cli304_coordinator_grant.py",
        "src/mods_knowledge/cli304_supervised_lease.py",
        "scripts/cli304_coordinator_pretool.py",
        "scripts/cli304_supervised_pretool.py",
        "scripts/cli304_supervised_qa.py",
        "scripts/cli304_mac_granted_supervisor_qa.py",
    }
    for host, native in r["real_host_evidence"].items():
        assert set(native["source_sha256"]) == matching_sources
        for name, expected in native["source_sha256"].items():
            assert sha(ROOT / name) == expected
        for record in native["real_native_epochs"].values():
            for key in (
                "original_native_wire_sha256",
                "original_native_debug_sha256",
                "mac_signed_grant_sha256",
                "mac_signed_request_sha256",
                "managed_policy_sha256",
            ):
                assert re.fullmatch(r"[0-9a-f]{64}", record[key]), (host, key)


def test_evidence_does_not_claim_actual_network_partition_or_global_enforcement():
    r = evidence()
    assert r["physical_mac_to_pi_network_partition_tested"] is False
    assert r["production_system_etc_modified"] is False
    assert r["complete_native_session_inventory_proven"] is False
    assert r["unregistered_native_hosts_outside_enforcement"] is True
    assert r["mac_private_signing_key_kept_off_git"] is True
    assert r["stable_release_authorized"] is False
    assert r["new_cli304_claims_approved"] == 0
    assert all(
        native["physically_disconnected_network_tested"] is False
        and native["unregistered_native_hosts_protected"] is False
        for native in r["real_host_evidence"].values()
    )


def test_public_evidence_has_no_private_raw_identity_or_credentials():
    raw = REPORT.read_text()
    private_patterns = [
        r"/home/",
        r"/Users/",
        r"/tmp/mods-cli304",  # noqa: S108 - only a regex used to reject leaked paths
        r"Authorization:",
        r"Cookie:",
        r"access_token",
        r"BEGIN PRIVATE KEY",
        r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])",
    ]
    for expression in private_patterns:
        assert re.search(expression, raw, flags=re.I) is None
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(
        ROOT / "claims",
        registry,
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    assert approved_claims(claims, "2.1.304", "cli") == []


def test_auditor_cannot_invent_private_original_claude_host_evidence(tmp_path: Path):
    with pytest.raises((_module.NativeCoordinatorEvidenceError, OSError, ValueError)):
        _module.audit(
            tmp_path,
            tmp_path / "nonexistent-official-binary",
            "rpi-a",
            tmp_path / "missing-openssl",
        )
