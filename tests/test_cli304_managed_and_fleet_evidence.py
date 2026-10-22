"""Pinned native managed sandbox and three-host Ed25519 observations remain HOLD."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

from mods_knowledge.claims import approved_claims, load_claims
from mods_knowledge.cli304_fleet_snapshot import FleetBlocked, audit_fleet
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
MANAGED = ROOT / "docs/reports/2026-10-22-cli304-managed-native-sandbox-evidence.json"
FLEET = ROOT / "docs/reports/2026-10-22-cli304-three-host-signed-fleet-evidence.json"
MANAGED_AUDITOR = ROOT / "scripts/audit_cli304_managed_policy.py"
FLEET_AUDITOR = ROOT / "scripts/audit_cli304_fleet_snapshots.py"
POLICY = ROOT / "evals/fixtures/cli304-managed-sandbox-20261022"
SIGNED = ROOT / "evals/fixtures/cli304-three-host-signed-20261022"

_spec = importlib.util.spec_from_file_location("managed_native_evidence_check", MANAGED_AUDITOR)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def sha(path: Path) -> str:
    assert path.is_file() and not path.is_symlink()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(path: Path) -> dict:
    return json.loads(path.read_text())


def test_original_actual_managed_host_evidence_and_source_are_pinned():
    data = report(MANAGED)
    assert data["schema_version"] == 1
    assert data["target_cli"] == "2.1.304"
    assert data["auditor_source_sha256"] == sha(MANAGED_AUDITOR)
    assert data["reviewed_source_sha256"] == _module.PINNED_FILES
    assert data["native_binary_sha256"] == _module.NATIVE_CLI_SHA
    assert set(data["native_cases"]) == set(_module.RUNS)
    for name, expected in data["reviewed_source_sha256"].items():
        # Frozen original .py evidence is deliberately stored as nonexecuting
        # text: never reformat bytes SHA-pinned to genuine host observations.
        public_name = name + ".txt" if name.endswith(".py") else name
        assert sha(POLICY / public_name) == expected
    for row in data["native_cases"].values():
        assert row["native_host_model_identified"] is True
        assert re.fullmatch(r"[0-9a-f]{64}", row["wire_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", row["debug_sha256"])
    assert data["native_cases"]["managed_deny_write"]["real_native_tool_calls"] == ["Read", "Write"]
    assert data["native_cases"]["managed_hook_not_disabled"]["real_native_tool_calls"] == ["Read"]
    assert data["native_cases"]["unmanaged_hook_suppressed"]["real_native_tool_calls"] == ["Read"]


def test_real_managed_setting_precedence_does_not_mean_organization_deployed():
    r = report(MANAGED)
    assert r["observations"] == {
        "managed_policy_read_in_isolated_official_host": True,
        "managed_deny_rule_blocks_preallowed_write": True,
        "managed_command_hook_survives_user_disableAllHooks": True,
        "lower_priority_command_hook_suppressed_by_allowManagedHooksOnly": True,
        "no_test_file_created": True,
    }
    assert r["real_system_etc_not_modified"] is True
    assert r["test_scope"] == "bwrap-only Linux ARM64 managed policy overlay"
    assert r["managed_source_not_deployed_to_any_production_host"] is True
    assert r["organization_team_server_policy_precedence_not_verified"] is True
    assert r["complete_live_session_inventory_proven"] is False
    assert r["stable_release_authorized"] is False
    assert r["new_cli304_claims_approved"] == 0


def test_three_real_host_ed25519_receipts_verify_only_at_original_time():
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("OpenSSL unavailable: cannot claim Ed25519 verification")
    actual = report(FLEET)
    assert actual["schema"] == 1
    assert actual["target"] == "fleet-readonly-qa"
    assert actual["signature_verification_source_sha256"] == sha(
        ROOT / "src/mods_knowledge/cli304_fleet_snapshot.py"
    )
    names = ("macbook", "rpi-a", "rpi-b")
    assert actual["host_labels"] == list(names)
    payload = {}
    pub = {}
    for h in names:
        signed = SIGNED / "receipts" / f"{h}.json"
        key = SIGNED / "public" / f"{h}.pem"
        assert sha(signed) == actual["original_signed_envelope_sha256"][h]
        assert sha(key) == actual["host_public_key_sha256"][h]
        payload[h] = report(signed)
        pub[h] = key
    challenge = payload["macbook"]["payload"]["challenge"]
    verified = audit_fleet(
        payload,
        pub,
        openssl=Path(openssl).resolve(),
        challenge=challenge,
        now=actual["verification_epoch"],
    )
    assert verified["observed_native_process_candidates"] == 14
    assert verified["fresh_host_signatures_verified"] == 3
    assert verified["host_receipt_sha256"] == actual["host_receipt_sha256"]
    assert verified["all_native_host_sessions_protected"] is False
    assert actual["historical_time_override_used"] is True
    assert actual["host_signatures_cannot_prove_running_sessions_are_current"] is True
    assert actual["evidence_expiry_epoch"] < actual["verification_epoch"] + 181


def test_original_fleet_snapshot_must_not_be_used_as_current_readiness():
    actual = report(FLEET)
    assert actual["observed_native_process_candidates"] == 14
    assert actual["expected_host_count"] == 3
    assert actual["hosts_with_managed_policy_file"] == 0
    assert actual["all_expected_observers_fresh_at_verification_time"] is True
    assert actual["this_does_not_establish_future_freshness"] is True
    assert actual["all_native_host_sessions_protected"] is False
    assert actual["complete_global_session_inventory"] is False
    assert actual["cross_machine_quiescence_authorized"] is False
    assert actual["production_security_gate"] == "HOLD"
    assert actual["stable_release_authorized"] is False


def test_same_pinned_receipts_reject_missing_host_and_expired_replay():
    from mods_knowledge.cli304_fleet_snapshot import verify

    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("OpenSSL unavailable: cannot claim Ed25519 verification")
    names = ("macbook", "rpi-a", "rpi-b")
    data = {h: report(SIGNED / "receipts" / f"{h}.json") for h in names}
    keys = {h: SIGNED / "public" / f"{h}.pem" for h in names}
    at = report(FLEET)["verification_epoch"]
    challenge = data["macbook"]["payload"]["challenge"]
    with pytest.raises(FleetBlocked, match="MISSING_OR_UNEXPECTED_FLEET_HOST"):
        audit_fleet(
            {"macbook": data["macbook"], "rpi-a": data["rpi-a"]},
            keys,
            openssl=Path(openssl).resolve(),
            challenge=challenge,
            now=at,
        )
    with pytest.raises(FleetBlocked, match="EXPIRED_OR_FUTURE"):
        verify(
            data["rpi-b"],
            public=keys["rpi-b"],
            openssl=Path(openssl).resolve(),
            expected_host="rpi-b",
            expected_challenge=challenge,
            now=data["rpi-b"]["payload"]["expires_at"] + 1,
        )


def test_public_artifacts_contain_no_user_credentials_or_private_process_arguments():
    for file in [MANAGED, FLEET, *SIGNED.glob("receipts/*.json")]:
        source = file.read_text()
        for secret in (
            "/home/",
            "/Users/",
            "Authorization:",
            "Cookie:",
            "access_token",
            "--sdk-url",
            "--mcp-config=",
            "session_id",
            "tool_use_id",
            "cse_",
        ):
            assert secret not in source
    registry = load_registry(ROOT / "sources/registry.json")
    claims = load_claims(
        ROOT / "claims",
        registry,
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    assert approved_claims(claims, "2.1.304", "cli") == []


def test_native_managed_auditor_does_not_fabricate_original_model_wires(tmp_path: Path):
    with pytest.raises((_module.MissingNativePolicyEvidence, OSError, ValueError)):
        _module.audit(tmp_path, tmp_path / "nonexistent-native-cli304")
