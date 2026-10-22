"""Ed25519 fleet receipt controls; verifies signatures, NOT complete session safety."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mods_knowledge.cli304_fleet_snapshot import (
    FleetBlocked,
    audit_fleet,
    observe,
    process_counts,
    public_key,
    sign,
    verify,
)

STAMP = 1234567
CHALLENGE = "a" * 64
HOSTS = ("macbook", "rpi-a", "rpi-b")


@pytest.fixture
def fleet(tmp_path: Path):
    exe = shutil.which("openssl")
    if not exe:
        pytest.skip("OpenSSL CLI not installed; cannot claim cryptographic proof")
    openssl = Path(exe).resolve(strict=True)
    all_public, envelopes = {}, {}
    for i, host in enumerate(HOSTS):
        folder = tmp_path / host
        folder.mkdir()
        private = folder / "private-key.pem"
        created = subprocess.run(  # noqa: S603 - exact QA OpenSSL path
            [str(openssl), "genpkey", "-algorithm", "ED25519", "-out", str(private)],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        assert created.returncode == 0
        private.chmod(0o600)
        pubfile = folder / "public-key.pem"
        pubfile.write_bytes(public_key(private, openssl))
        payload = {
            "schema": 1,
            "host_id": host,
            "challenge": CHALLENGE,
            "issued_at": STAMP,
            "expires_at": STAMP + 180,
            "platform": "linux" if i else "darwin",
            "candidate_native_processes": i + 2,
            "candidate_with_session_arg": i,
            "candidate_with_settings_arg": 0,
            "unreadable_process_entries": 0,
            "observed_managed_policy_file": False,
            "complete_host_session_inventory_attested": False,
            "all_observed_processes_host_gate_attested": False,
            "production_coverage_proven": False,
        }
        envelopes[host] = sign(payload, private=private, openssl=openssl)
        all_public[host] = pubfile
        assert private.read_text() not in json.dumps(envelopes[host])
    return {"keys": all_public, "envelopes": envelopes, "openssl": openssl, "root": tmp_path}


def test_three_distinct_hosts_signed_present_but_global_protection_not_proven(fleet):
    r = audit_fleet(
        fleet["envelopes"],
        fleet["keys"],
        openssl=fleet["openssl"],
        challenge=CHALLENGE,
        now=STAMP + 1,
    )
    assert r["expected_host_count"] == 3
    assert r["fresh_host_signatures_verified"] == 3
    assert r["observed_native_process_candidates"] == 9
    assert r["all_native_host_sessions_protected"] is False
    assert r["cross_machine_quiescence_authorized"] is False
    assert r["stable_release_authorized"] is False
    assert sorted(r["host_public_key_sha256"]) == sorted(HOSTS)


def test_missing_or_extra_fleet_host_never_succeeds(fleet):
    envelopes, keys = fleet["envelopes"], fleet["keys"]
    with pytest.raises(FleetBlocked, match="MISSING_OR_UNEXPECTED"):
        audit_fleet(
            dict(list(envelopes.items())[:2]),
            keys,
            openssl=fleet["openssl"],
            challenge=CHALLENGE,
            now=STAMP,
        )
    with pytest.raises(FleetBlocked, match="MISSING_OR_UNEXPECTED"):
        audit_fleet(
            {**envelopes, "rogue": envelopes["rpi-b"]},
            keys,
            openssl=fleet["openssl"],
            challenge=CHALLENGE,
            now=STAMP,
        )


def test_signing_identity_must_match_approved_host_and_challenge(fleet):
    current = fleet["envelopes"]["macbook"]
    with pytest.raises(FleetBlocked, match="WRONG_HOST_OR_FLEET_CHALLENGE"):
        verify(
            current,
            public=fleet["keys"]["macbook"],
            openssl=fleet["openssl"],
            expected_host="rpi-a",
            expected_challenge=CHALLENGE,
            now=STAMP,
        )
    with pytest.raises(FleetBlocked, match="WRONG_HOST_OR_FLEET_CHALLENGE"):
        verify(
            current,
            public=fleet["keys"]["macbook"],
            openssl=fleet["openssl"],
            expected_host="macbook",
            expected_challenge="c" * 64,
            now=STAMP,
        )
    with pytest.raises(FleetBlocked, match="SIGNATURE_VERIFICATION_FAILED"):
        verify(
            current,
            public=fleet["keys"]["rpi-a"],
            openssl=fleet["openssl"],
            expected_host="macbook",
            expected_challenge=CHALLENGE,
            now=STAMP,
        )


def test_tampered_data_rejected_even_if_counts_look_plausible(fleet):
    changed = copy.deepcopy(fleet["envelopes"]["rpi-a"])
    changed["payload"]["candidate_native_processes"] += 1
    with pytest.raises(FleetBlocked, match="SIGNATURE_VERIFICATION_FAILED"):
        verify(
            changed,
            public=fleet["keys"]["rpi-a"],
            openssl=fleet["openssl"],
            expected_host="rpi-a",
            expected_challenge=CHALLENGE,
            now=STAMP,
        )


@pytest.mark.parametrize("now", [STAMP - 40, STAMP + 180, STAMP + 200])
def test_future_or_expired_snapshot_is_not_fresh_fleet_approval(fleet, now):
    with pytest.raises(FleetBlocked, match="EXPIRED_OR_FUTURE"):
        verify(
            fleet["envelopes"]["rpi-b"],
            public=fleet["keys"]["rpi-b"],
            openssl=fleet["openssl"],
            expected_host="rpi-b",
            expected_challenge=CHALLENGE,
            now=now,
        )


def test_forged_global_success_is_refused_even_with_valid_private_signature(fleet):
    private = fleet["root"] / "rpi-a/private-key.pem"
    fake = copy.deepcopy(fleet["envelopes"]["rpi-a"]["payload"])
    fake["production_coverage_proven"] = True
    signed = sign(fake, private=private, openssl=fleet["openssl"])
    with pytest.raises(FleetBlocked, match="UNSUPPORTED_PRODUCTION_COVERAGE_ASSERTION"):
        verify(
            signed,
            public=fleet["keys"]["rpi-a"],
            openssl=fleet["openssl"],
            expected_host="rpi-a",
            expected_challenge=CHALLENGE,
            now=STAMP,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_native_processes", -1),
        ("candidate_with_session_arg", 100),
        ("candidate_with_settings_arg", "one"),
        ("unreadable_process_entries", True),
        ("platform", "windows"),
    ],
)
def test_bad_signed_fields_still_refuse(fleet, field, value):
    p = copy.deepcopy(fleet["envelopes"]["rpi-b"]["payload"])
    p[field] = value
    signed = sign(p, private=fleet["root"] / "rpi-b/private-key.pem", openssl=fleet["openssl"])
    with pytest.raises(FleetBlocked):
        verify(
            signed,
            public=fleet["keys"]["rpi-b"],
            openssl=fleet["openssl"],
            expected_host="rpi-b",
            expected_challenge=CHALLENGE,
            now=STAMP,
        )


def test_key_permissions_are_checked(fleet):
    private = fleet["root"] / "macbook/private-key.pem"
    private.chmod(0o644)
    with pytest.raises(FleetBlocked, match="UNSAFE_SIGNING_KEY_PERMISSIONS"):
        sign(
            fleet["envelopes"]["macbook"]["payload"],
            private=private,
            openssl=fleet["openssl"],
        )


def test_process_snapshot_does_not_export_raw_command_arguments():
    counts = process_counts()
    assert set(counts) == {
        "candidate_native_processes",
        "candidate_with_session_arg",
        "candidate_with_settings_arg",
        "unreadable_process_entries",
    }
    assert all(type(v) is int and v >= 0 for v in counts.values())
    sample = observe("qa-observer", "e" * 64, now=STAMP)
    assert sample["production_coverage_proven"] is False
    assert sample["complete_host_session_inventory_attested"] is False
    assert sample["all_observed_processes_host_gate_attested"] is False
    assert all(
        not any(s in json.dumps(sample) for s in ("/home/", "--sdk-url", "ANTHROPIC_API_KEY"))
        for _ in range(1)
    )
