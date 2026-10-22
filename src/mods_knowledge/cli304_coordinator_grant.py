"""Mac-issued, short-lived Ed25519 epoch authority for isolated CLI304 QA.

Host-specific grants bind a unique per-launch supervisor generation, session
digest, boot digest, exact policy digest and official CLI binary. The Mac
private signing key NEVER leaves the Mac. Both local supervisor renewal and
the independent managed PreToolUse hook validate the signed grant.

A Mac->Pi delivery gap is intentionally bounded by the short grant TTL.
This is not mTLS, secure remote attestation, a production network service,
or a mandatory organization-wide Claude security policy.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import time
from pathlib import Path

NATIVE_304 = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HOST = re.compile(r"rpi-[ab]\Z")
REQUEST_FIELDS = frozenset(
    {
        "schema",
        "host",
        "cohort",
        "nonce",
        "generation",
        "session_sha256",
        "boot_sha256",
        "policy_sha256",
        "native_binary_sha256",
    }
)
GRANT_FIELDS = REQUEST_FIELDS | {"epoch", "issued_at", "expires_at"}
ENVELOPE_FIELDS = {"schema", "payload", "signature"}
RECEIPT_FIELDS = {"schema", "signed_payload_sha256", "generation", "epoch", "deadline_monotonic"}
MAX_GRANT_SECONDS = 30
MIN_GRANT_SECONDS = 10
MAX_FILE = 8192


class GrantBlocked(ValueError):
    """Invalid source, signature, host, epoch, freshness or local monotonic TTL."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise GrantBlocked(reason)


def _regular(file: Path, *, private: bool = False) -> None:
    require(file.is_file() and not file.is_symlink(), "MISSING_OR_UNSAFE_GRANT_FILE")
    s = file.stat()
    require(0 < s.st_size <= MAX_FILE, "UNEXPECTED_GRANT_FILE_SIZE")
    if private:
        require(
            s.st_uid == os.getuid() and stat.S_IMODE(s.st_mode) == 0o600,
            "UNSAFE_PRIVATE_KEY_OR_RECEIPT",
        )


def canonical(value: dict, *, expected: frozenset[str] | set[str]) -> bytes:
    require(isinstance(value, dict) and set(value) == expected, "INVALID_CANONICAL_FIELDS")
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    require(len(text) <= MAX_FILE, "OVERSIZED_GRANT")
    return text


def validate_request(request: dict) -> bytes:
    body = canonical(request, expected=REQUEST_FIELDS)
    require(
        request["schema"] == 1
        and isinstance(request["host"], str)
        and HOST.fullmatch(request["host"]) is not None,
        "INVALID_HOST_BINDING",
    )
    for name in (
        "cohort",
        "nonce",
        "session_sha256",
        "boot_sha256",
        "policy_sha256",
        "native_binary_sha256",
    ):
        require(
            isinstance(request[name], str) and HEX64.fullmatch(request[name]) is not None,
            "INVALID_REQUEST_DIGEST",
        )
    require(
        isinstance(request["generation"], str)
        and HEX32.fullmatch(request["generation"]) is not None
        and request["native_binary_sha256"] == NATIVE_304,
        "UNREVIEWED_NATIVE_OR_SUPERVISOR_GENERATION",
    )
    return body


def grant_payload(request: dict, *, epoch: int, now: int | None = None, ttl: int = 24) -> dict:
    validate_request(request)
    require(type(epoch) is int and 1 <= epoch <= 100000, "INVALID_AUTHORITY_EPOCH")
    require(
        type(ttl) is int and MIN_GRANT_SECONDS <= ttl <= MAX_GRANT_SECONDS, "INVALID_AUTHORITY_TTL"
    )
    instant = int(time.time()) if now is None else now
    require(type(instant) is int and instant > 0, "INVALID_ISSUANCE_CLOCK")
    payload = {**request, "epoch": epoch, "issued_at": instant, "expires_at": instant + ttl}
    canonical(payload, expected=GRANT_FIELDS)
    return payload


def sign(payload: dict, *, key: Path, openssl: Path) -> dict:
    _regular(key, private=True)
    require(openssl.is_absolute() and openssl.is_file(), "OPENSSL_EXECUTABLE_REQUIRED")
    validate_request({k: payload[k] for k in REQUEST_FIELDS})
    require(set(payload) == GRANT_FIELDS, "BAD_SIGNED_EPOCH_FIELDS")
    with tempfile.TemporaryDirectory(prefix="mods-cli304-authority-") as temp:
        base = Path(temp)
        message, signature = base / "message.json", base / "signature"
        message.write_bytes(canonical(payload, expected=GRANT_FIELDS))
        result = subprocess.run(  # noqa: S603 - explicitly trusted OpenSSL argv
            [
                str(openssl),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(key),
                "-rawin",
                "-in",
                str(message),
                "-out",
                str(signature),
            ],
            check=False,
            capture_output=True,
            timeout=12,
        )
        require(result.returncode == 0 and signature.is_file(), "AUTHORITY_SIGN_FAILED")
        raw = signature.read_bytes()
    require(len(raw) == 64, "NOT_AN_ED25519_SIGNATURE")
    return {"schema": 1, "payload": payload, "signature": raw.hex()}


def verify(
    envelope: dict,
    *,
    request: dict,
    public_key: Path,
    openssl: Path,
    now: int | None = None,
    min_epoch: int = 1,
) -> dict:
    expected_request_bytes = validate_request(request)
    require(
        isinstance(envelope, dict) and set(envelope) == ENVELOPE_FIELDS and envelope["schema"] == 1,
        "INVALID_AUTHORITY_ENVELOPE",
    )
    body = envelope["payload"]
    require(isinstance(body, dict) and set(body) == GRANT_FIELDS, "INVALID_AUTHORITY_PAYLOAD")
    require(
        canonical({k: body[k] for k in REQUEST_FIELDS}, expected=REQUEST_FIELDS)
        == expected_request_bytes,
        "CROSS_HOST_OR_STALE_SUPERVISOR_GRANT",
    )
    current = int(time.time()) if now is None else now
    require(type(current) is int and current > 0, "INVALID_VERIFY_CLOCK")
    require(
        type(body["epoch"]) is int
        and body["epoch"] >= min_epoch
        and type(body["issued_at"]) is int
        and type(body["expires_at"]) is int
        and MIN_GRANT_SECONDS <= body["expires_at"] - body["issued_at"] <= MAX_GRANT_SECONDS
        and body["issued_at"] <= current + 2
        and current < body["expires_at"],
        "GRANT_EXPIRED_FUTURE_OR_EPOCH_REPLAY",
    )
    sig = envelope["signature"]
    require(
        isinstance(sig, str) and re.fullmatch(r"[0-9a-f]{128}", sig) is not None,
        "BAD_SIGNATURE_FORMAT",
    )
    _regular(public_key)
    require(openssl.is_absolute() and openssl.is_file(), "OPENSSL_EXECUTABLE_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="mods-cli304-verify-") as temp:
        base = Path(temp)
        message, signature = base / "message.json", base / "signature"
        message.write_bytes(canonical(body, expected=GRANT_FIELDS))
        signature.write_bytes(bytes.fromhex(sig))
        result = subprocess.run(  # noqa: S603 - explicit local OpenSSL
            [
                str(openssl),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_key),
                "-rawin",
                "-in",
                str(message),
                "-sigfile",
                str(signature),
            ],
            check=False,
            capture_output=True,
            timeout=12,
        )
    require(result.returncode == 0, "MAC_COORDINATOR_SIGNATURE_INVALID")
    return body


def _read_json(path: Path, *, private: bool = False) -> dict:
    _regular(path, private=private)
    try:
        data = json.loads(path.read_bytes())
    except (UnicodeError, ValueError) as exc:
        raise GrantBlocked("INVALID_JSON_AUTHORITY_STATE") from exc
    require(isinstance(data, dict), "INVALID_JSON_OBJECT")
    return data


def _write_private(path: Path, value: dict, *, replace: bool = False) -> None:
    raw = canonical(value, expected=set(value))
    require(
        path.is_absolute() and path.parent.is_dir() and not path.parent.is_symlink(),
        "UNSAFE_AUTHORITY_OUTPUT_PATH",
    )
    require(
        stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        and path.parent.stat().st_uid == os.getuid(),
        "AUTHORITY_OUTPUT_DIRECTORY_NOT_PRIVATE",
    )
    if not replace:
        require(
            not path.exists() and not path.is_symlink(), "IMMUTABLE_AUTHORITY_STATE_ALREADY_EXISTS"
        )
    with tempfile.TemporaryDirectory(prefix=".auth-tmp-", dir=path.parent) as temp:
        new = Path(temp) / "state.json"
        new.write_bytes(raw + b"\n")
        new.chmod(0o600)
        os.replace(new, path)


def accept(
    request_file: Path,
    grant_file: Path,
    public_key: Path,
    openssl: Path,
    receipt_file: Path,
    *,
    now: int | None = None,
    monotonic: float | None = None,
) -> dict:
    """One-time bootstrap acceptance, binds wall expiry also to monotonic age."""
    request = _read_json(request_file, private=True)
    envelope = _read_json(grant_file, private=True)
    body = verify(envelope, request=request, public_key=public_key, openssl=openssl, now=now)
    current = int(time.time()) if now is None else now
    mono = time.monotonic() if monotonic is None else monotonic
    # max 30 seconds even if wall clock jumps backwards after bootstrap
    remaining = max(0, min(MAX_GRANT_SECONDS, body["expires_at"] - current))
    require(remaining >= 1, "GRANT_TOO_CLOSE_TO_EXPIRY")
    receipt = {
        "schema": 1,
        "signed_payload_sha256": hashlib.sha256(
            canonical(envelope, expected=ENVELOPE_FIELDS)
        ).hexdigest(),
        "generation": request["generation"],
        "epoch": body["epoch"],
        "deadline_monotonic": mono + remaining,
    }
    _write_private(receipt_file, receipt)
    return receipt


def authorized(
    request_file: Path,
    grant_file: Path,
    public_key: Path,
    openssl: Path,
    receipt_file: Path,
    *,
    now: int | None = None,
    monotonic: float | None = None,
) -> dict:
    """Fail closed on *every tool call*, even if local renewal thread survives."""
    request = _read_json(request_file, private=True)
    envelope = _read_json(grant_file, private=True)
    receipt = _read_json(receipt_file, private=True)
    require(
        set(receipt) == RECEIPT_FIELDS and receipt["schema"] == 1, "INVALID_LOCAL_AUTHORITY_RECEIPT"
    )
    mono = time.monotonic() if monotonic is None else monotonic
    require(
        type(receipt["deadline_monotonic"]) in (int, float)
        and 0 < receipt["deadline_monotonic"] - mono <= MAX_GRANT_SECONDS + 0.1,
        "MAC_AUTHORITY_MONOTONIC_LEASE_EXPIRED",
    )
    require(
        hashlib.sha256(canonical(envelope, expected=ENVELOPE_FIELDS)).hexdigest()
        == receipt["signed_payload_sha256"]
        and receipt["generation"] == request["generation"],
        "AUTHORITY_RECEIPT_REPLAY_OR_MUTATION",
    )
    body = verify(
        envelope,
        request=request,
        public_key=public_key,
        openssl=openssl,
        now=now,
        min_epoch=receipt["epoch"],
    )
    require(body["epoch"] == receipt["epoch"], "EPOCH_CHANGED_WITHOUT_NEW_RECEIPT")
    return body
