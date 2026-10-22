"""Ephemeral per-process Ed25519 witness authentication; never global ready."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from mods_knowledge.cli304_supervised_attestation import (
    TTL,
    LiveWitnessBlocked,
    audit_quorum,
    sign,
    verify,
)
from mods_knowledge.cli304_supervised_lease import NATIVE_CLI304_SHA

NONCE = "a" * 64
START = 1_234_567


@pytest.fixture
def signed(tmp_path: Path):
    openssl_path = shutil.which("openssl")
    if openssl_path is None:
        pytest.skip("OpenSSL required for real Ed25519 verification")
    openssl = Path(openssl_path).resolve()
    pubs = {}
    packets = {}
    for i, name in enumerate(("rpi-a", "rpi-b")):
        root = tmp_path / name
        root.mkdir()
        priv = root / "secret.pem"
        subprocess.run(  # noqa: S603 - explicit fixed test-only OpenSSL argv
            [str(openssl), "genpkey", "-algorithm", "ED25519", "-out", str(priv)],
            capture_output=True,
            check=True,
            timeout=15,
        )
        priv.chmod(0o600)
        public = root / "pub.pem"
        subprocess.run(  # noqa: S603 - explicit fixed test-only OpenSSL argv
            [str(openssl), "pkey", "-in", str(priv), "-pubout", "-out", str(public)],
            capture_output=True,
            check=True,
            timeout=15,
        )
        payload = {
            "schema": 1,
            "host": name,
            "challenge": NONCE,
            "observed_at": START,
            "expires_at": START + TTL,
            "boot_sha256": hashlib.sha256(f"boot-{i}".encode()).hexdigest(),
            "supervisor_instance_sha256": hashlib.sha256(f"supervisor-{i}".encode()).hexdigest(),
            "native_process_sha256": hashlib.sha256(f"native-{i}".encode()).hexdigest(),
            "managed_policy_sha256": "e" * 64,
            "native_binary_sha256": NATIVE_CLI304_SHA,
            "native_wire_sha256": "f" * 64,
            "same_running_native_session_observed": True,
            "active_managed_lease_at_issue": True,
            "complete_host_session_inventory_proven": False,
            "global_host_protection_proven": False,
            "stable_release_authorized": False,
        }
        packets[name] = sign(payload, private=priv, openssl=openssl)
        pubs[name] = public
    return packets, pubs, openssl


def test_two_valid_signed_active_at_issue_hosts_still_not_global(signed):
    packets, pubs, openssl = signed
    state = audit_quorum(packets, pubs, openssl=openssl, nonce=NONCE, now=START + 1)
    assert state["actual_signed_live_qa_hosts_at_issue"] == 2
    assert state["host_ids"] == ["rpi-a", "rpi-b"]
    assert state["complete_global_session_inventory_proven"] is False
    assert state["production_wide_quiescence_authorized"] is False
    assert state["stable_release_authorized"] is False


def test_missing_host_and_mismatched_keys_fail_closed(signed):
    packets, pubs, openssl = signed
    with pytest.raises(LiveWitnessBlocked, match="MISSING_SIGNED_RUNNING_HOST"):
        audit_quorum({"rpi-a": packets["rpi-a"]}, pubs, openssl=openssl, nonce=NONCE, now=START)
    with pytest.raises(LiveWitnessBlocked, match="SIGNED_LIVE_WITNESS_VERIFICATION_FAILED"):
        verify(
            packets["rpi-a"],
            pubkey=pubs["rpi-b"],
            openssl=openssl,
            host="rpi-a",
            nonce=NONCE,
            now=START,
        )


@pytest.mark.parametrize("instant", [START - 9, START + TTL, START + TTL + 1])
def test_expired_or_future_live_proof_rejected(signed, instant):
    packets, pubs, openssl = signed
    with pytest.raises(LiveWitnessBlocked, match="EXPIRED_OR_FUTURE"):
        verify(
            packets["rpi-a"],
            pubkey=pubs["rpi-a"],
            openssl=openssl,
            host="rpi-a",
            nonce=NONCE,
            now=instant,
        )


def test_altered_payload_cannot_keep_same_signature(signed):
    packets, pubs, openssl = signed
    changed = copy.deepcopy(packets["rpi-b"])
    changed["payload"]["managed_policy_sha256"] = "b" * 64
    with pytest.raises(LiveWitnessBlocked, match="SIGNED_LIVE_WITNESS_VERIFICATION_FAILED"):
        verify(
            changed,
            pubkey=pubs["rpi-b"],
            openssl=openssl,
            host="rpi-b",
            nonce=NONCE,
            now=START,
        )


def test_even_valid_signer_cannot_assert_global_protection(signed, tmp_path):
    packets, pubs, openssl = signed
    tamper = dict(packets["rpi-a"]["payload"], global_host_protection_proven=True)
    key = tmp_path / "new-secret.pem"
    subprocess.run(  # noqa: S603 - explicit test OpenSSL
        [str(openssl), "genpkey", "-algorithm", "ED25519", "-out", str(key)],
        check=True,
        capture_output=True,
    )
    key.chmod(0o600)
    rogue = sign(tamper, private=key, openssl=openssl)
    with pytest.raises(LiveWitnessBlocked, match="UNSUPPORTED_HOST_COVERAGE_ASSERTION"):
        verify(
            rogue,
            pubkey=pubs["rpi-a"],
            openssl=openssl,
            host="rpi-a",
            nonce=NONCE,
            now=START,
        )


def test_wrong_challenge_refused(signed):
    packets, pubs, openssl = signed
    with pytest.raises(LiveWitnessBlocked, match="WRONG_HOST_OR_NONCE"):
        audit_quorum(packets, pubs, openssl=openssl, nonce="b" * 64, now=START)


def test_private_supervisor_digests_are_not_raw_pids_or_session_ids(signed):
    packets, _, _ = signed
    text = json.dumps(packets, sort_keys=True)
    assert "session_id" not in text
    assert "supervisor_pid" not in text
    assert "child_bwrap_pid" not in text
    assert "private_key" not in text
