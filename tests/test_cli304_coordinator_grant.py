"""Mac epoch authorization is host-scoped, signed and independently expires."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from mods_knowledge.cli304_coordinator_grant import (
    NATIVE_304,
    GrantBlocked,
    _write_private,
    accept,
    authorized,
    grant_payload,
    sign,
    verify,
)

WALL = 1_000_000
MONO = 13_000.0
COHORT = "a" * 64


@pytest.fixture
def keys(tmp_path: Path):
    binary = shutil.which("openssl")
    if not binary:
        pytest.skip("Ed25519 OpenSSL executable not available")
    openssl = Path(binary).resolve()
    private = tmp_path / "coordinator-key.pem"
    subprocess.run(  # noqa: S603 - only fixed test-only OpenSSL
        [str(openssl), "genpkey", "-algorithm", "ED25519", "-out", str(private)],
        timeout=15,
        check=True,
        capture_output=True,
    )
    private.chmod(0o600)
    public = tmp_path / "coordinator-public.pem"
    subprocess.run(  # noqa: S603 - fixed QA argv
        [str(openssl), "pkey", "-in", str(private), "-pubout", "-out", str(public)],
        timeout=15,
        check=True,
        capture_output=True,
    )
    return openssl, private, public


@pytest.fixture
def state(tmp_path: Path, keys):
    openssl, private, public = keys
    folder = tmp_path / "host"
    folder.mkdir(mode=0o700)
    folder.chmod(0o700)
    request = {
        "schema": 1,
        "host": "rpi-a",
        "cohort": COHORT,
        "nonce": "b" * 64,
        "generation": "c" * 32,
        "session_sha256": "d" * 64,
        "boot_sha256": "e" * 64,
        "policy_sha256": "f" * 64,
        "native_binary_sha256": NATIVE_304,
    }
    payload = grant_payload(request, epoch=11, now=WALL)
    envelope = sign(payload, key=private, openssl=openssl)
    rp, gp, receipt = folder / "request.json", folder / "grant.json", folder / "receipt.json"
    _write_private(rp, request)
    _write_private(gp, envelope)
    return {
        "openssl": openssl,
        "private": private,
        "public": public,
        "request": request,
        "payload": payload,
        "envelope": envelope,
        "reqpath": rp,
        "grantpath": gp,
        "receipt": receipt,
    }


def _accept(s, *, now=WALL, monotonic=MONO):
    return accept(
        s["reqpath"],
        s["grantpath"],
        s["public"],
        s["openssl"],
        s["receipt"],
        now=now,
        monotonic=monotonic,
    )


def _authorized(s, *, now=WALL + 4, monotonic=MONO + 4):
    return authorized(
        s["reqpath"],
        s["grantpath"],
        s["public"],
        s["openssl"],
        s["receipt"],
        now=now,
        monotonic=monotonic,
    )


def test_mac_signed_grant_bootstrap_and_each_read_is_cryptographically_verified(state):
    accepted = _accept(state)
    assert accepted["epoch"] == 11
    assert accepted["generation"] == state["request"]["generation"]
    assert _authorized(state)["epoch"] == 11
    assert os.stat(state["receipt"]).st_mode & 0o777 == 0o600
    assert all(
        str(state["private"].resolve()) not in path.read_text()
        for path in (state["reqpath"], state["grantpath"], state["receipt"])
    )


def test_no_signature_or_grant_fails_closed_before_any_protected_operation(state):
    with pytest.raises(GrantBlocked, match="MISSING_OR_UNSAFE_GRANT_FILE"):
        _authorized(state)
    _accept(state)
    state["grantpath"].unlink()
    with pytest.raises(GrantBlocked, match="MISSING_OR_UNSAFE_GRANT_FILE"):
        _authorized(state)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("host", "rpi-b"),
        ("cohort", "0" * 64),
        ("nonce", "0" * 64),
        ("generation", "0" * 32),
        ("session_sha256", "0" * 64),
        ("policy_sha256", "0" * 64),
        ("boot_sha256", "0" * 64),
    ],
)
def test_token_for_other_host_policy_session_or_generation_never_replays(state, field, replacement):
    _accept(state)
    fake = copy.deepcopy(state["request"])
    fake[field] = replacement
    state["reqpath"].write_text(json.dumps(fake))
    with pytest.raises(
        GrantBlocked,
        match="CROSS_HOST_OR_STALE_SUPERVISOR_GRANT|AUTHORITY_RECEIPT_REPLAY_OR_MUTATION",
    ):
        _authorized(state)


def test_expired_mac_grant_denied_even_if_local_heartbeat_continues(state):
    _accept(state)
    with pytest.raises(GrantBlocked, match="MAC_AUTHORITY_MONOTONIC_LEASE_EXPIRED"):
        _authorized(state, now=WALL + 5, monotonic=MONO + 25)
    with pytest.raises(GrantBlocked, match="GRANT_EXPIRED_FUTURE_OR_EPOCH_REPLAY"):
        _authorized(state, now=WALL + 25, monotonic=MONO + 5)


def test_wall_clock_rollback_does_not_extend_monotonic_lease(state):
    _accept(state)
    with pytest.raises(GrantBlocked, match="MAC_AUTHORITY_MONOTONIC_LEASE_EXPIRED"):
        _authorized(state, now=WALL - 5, monotonic=MONO + 30)


def test_tampered_payload_rejected_even_if_receipt_is_rewritten(state):
    _accept(state)
    fake = copy.deepcopy(state["envelope"])
    fake["payload"]["epoch"] = 12
    state["grantpath"].write_text(json.dumps(fake))
    with pytest.raises(GrantBlocked, match="AUTHORITY_RECEIPT_REPLAY_OR_MUTATION"):
        _authorized(state)


def test_unsigned_new_epoch_or_replaced_key_never_accepted(state, tmp_path):
    _accept(state)
    payload = copy.deepcopy(state["payload"])
    payload["epoch"] += 1
    fake = {"schema": 1, "payload": payload, "signature": state["envelope"]["signature"]}
    state["grantpath"].write_text(json.dumps(fake))
    with pytest.raises(GrantBlocked):
        _authorized(state)


def test_wrong_coordinator_public_key_is_refused(state, tmp_path):
    _accept(state)
    wrong = tmp_path / "another.pem"
    wrongpriv = tmp_path / "anotherpriv.pem"
    subprocess.run(  # noqa: S603 - test-only local OpenSSL
        [str(state["openssl"]), "genpkey", "-algorithm", "ED25519", "-out", str(wrongpriv)],
        capture_output=True,
        check=True,
        timeout=12,
    )
    subprocess.run(  # noqa: S603 - test-only OpenSSL
        [str(state["openssl"]), "pkey", "-in", str(wrongpriv), "-pubout", "-out", str(wrong)],
        capture_output=True,
        check=True,
        timeout=12,
    )
    with pytest.raises(GrantBlocked, match="MAC_COORDINATOR_SIGNATURE_INVALID"):
        authorized(
            state["reqpath"],
            state["grantpath"],
            wrong,
            state["openssl"],
            state["receipt"],
            now=WALL + 1,
            monotonic=MONO + 1,
        )


def test_corrupt_private_receipt_unsafe_permissions_denied(state):
    _accept(state)
    state["receipt"].chmod(0o644)
    with pytest.raises(GrantBlocked, match="UNSAFE_PRIVATE_KEY_OR_RECEIPT"):
        _authorized(state)


@pytest.mark.parametrize("ttl", [0, 3, 31, 300])
def test_mac_cannot_sign_unreviewed_long_lived_grants(state, ttl):
    with pytest.raises(GrantBlocked, match="INVALID_AUTHORITY_TTL"):
        grant_payload(state["request"], epoch=11, now=WALL, ttl=ttl)


def test_forged_status_flags_cannot_be_added_to_signed_grant(state):
    altered = copy.deepcopy(state["envelope"])
    altered["payload"]["production_ready"] = True
    with pytest.raises(GrantBlocked, match="INVALID_AUTHORITY_PAYLOAD"):
        verify(
            altered,
            request=state["request"],
            public_key=state["public"],
            openssl=state["openssl"],
            now=WALL,
        )


def test_epoch_replay_is_rejected_after_epoch_advance(state):
    envelope = state["envelope"]
    with pytest.raises(GrantBlocked, match="GRANT_EXPIRED_FUTURE_OR_EPOCH_REPLAY"):
        verify(
            envelope,
            request=state["request"],
            public_key=state["public"],
            openssl=state["openssl"],
            now=WALL + 1,
            min_epoch=12,
        )


def test_unknown_native_binary_or_unsupported_host_rejected(state):
    request = dict(state["request"], host="untrusted-host")
    with pytest.raises(GrantBlocked, match="INVALID_HOST_BINDING"):
        grant_payload(request, epoch=1, now=WALL)
    request = dict(state["request"], native_binary_sha256=hashlib.sha256(b"unreviewed").hexdigest())
    with pytest.raises(GrantBlocked, match="UNREVIEWED_NATIVE_OR_SUPERVISOR_GENERATION"):
        grant_payload(request, epoch=1, now=WALL)
