"""Ephemeral signed host process observations for CLI304 fleet QA.

Independent Ed25519 private keys stay on each observer. A fresh authenticated
snapshot is not proof that every process or tool was inventoried/enforced.
No process arguments, PID values, local paths, account IDs, or session IDs are
included in signed/public snapshots. Linux/macOS only. No background daemon.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

HOST_ID = re.compile(r"[a-z][a-z0-9-]{1,30}\Z")
HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
HEX_128 = re.compile(r"[0-9a-f]{128}\Z")
TTL_SECONDS = 180
MAX_OBSERVATION_SIZE = 8192
SCHEMA_FIELDS = {
    "schema",
    "host_id",
    "challenge",
    "issued_at",
    "expires_at",
    "platform",
    "candidate_native_processes",
    "candidate_with_session_arg",
    "candidate_with_settings_arg",
    "unreadable_process_entries",
    "observed_managed_policy_file",
    "complete_host_session_inventory_attested",
    "all_observed_processes_host_gate_attested",
    "production_coverage_proven",
}
ENVELOPE_FIELDS = {"schema", "payload", "signature"}


class FleetBlocked(ValueError):
    """Unknown, stale, unauthenticated, incomplete or unsupported fleet QA."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise FleetBlocked(reason)


def _regular(path: Path, *, max_bytes: int, private: bool = False) -> None:
    require(path.is_file() and not path.is_symlink(), "MISSING_OR_SYMLINK_EVIDENCE")
    st = path.stat()
    require(st.st_size <= max_bytes and st.st_size > 0, "UNEXPECTED_EVIDENCE_SIZE")
    if private:
        require(
            st.st_uid == os.getuid() and stat.S_IMODE(st.st_mode) == 0o600,
            "UNSAFE_SIGNING_KEY_PERMISSIONS",
        )


def _openssl(binary: Path) -> Path:
    require(
        binary.is_absolute() and binary.is_file() and not binary.is_symlink(),
        "EXPLICIT_OPENSSL_BINARY_REQUIRED",
    )
    return binary


def _canonical(payload: dict) -> bytes:
    require(isinstance(payload, dict) and set(payload) == SCHEMA_FIELDS, "UNKNOWN_SNAPSHOT_SCHEMA")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    require(len(encoded) <= MAX_OBSERVATION_SIZE, "OVERSIZED_SNAPSHOT")
    return encoded


def _candidate(argv: list[str]) -> bool:
    if not argv:
        return False
    name = Path(argv[0]).name.lower()
    full = argv[0].lower()
    return name in {"claude", "claude-code"} or (
        (re.fullmatch(r"2\.1\.\d+", name) or name.startswith("claude-2.1.")) and "claude" in full
    )


def process_counts() -> dict[str, int]:
    """Conservative read-only process candidate scan, not a complete inventory."""
    found = 0
    with_session = 0
    with_settings = 0
    unreadable = 0
    if platform.system() == "Linux":
        for item in Path("/proc").iterdir():
            if not item.name.isdecimal():
                continue
            try:
                raw = (item / "cmdline").read_bytes()
                argv = [x.decode("utf-8", errors="replace") for x in raw.split(b"\0") if x]
            except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
                unreadable += 1
                continue
            if not _candidate(argv):
                continue
            found += 1
            with_session += int(
                "--session-id" in argv or any(x.startswith("--session-id=") for x in argv)
            )
            with_settings += int(
                "--settings" in argv or any(x.startswith("--settings=") for x in argv)
            )
    elif platform.system() == "Darwin":
        result = subprocess.run(  # noqa: S603 - fixed system command, no shell
            ["/bin/ps", "-axo", "pid=,command="],
            capture_output=True,
            text=True,
            check=True,
            timeout=12,
        )
        for line in result.stdout.splitlines():
            fields = line.strip().split(None, 1)
            if len(fields) != 2:
                unreadable += 1
                continue
            try:
                argv = shlex.split(fields[1])
            except ValueError:
                unreadable += 1
                continue
            if not _candidate(argv):
                continue
            found += 1
            with_session += int(
                "--session-id" in argv or any(x.startswith("--session-id=") for x in argv)
            )
            with_settings += int(
                "--settings" in argv or any(x.startswith("--settings=") for x in argv)
            )
    else:
        raise FleetBlocked("UNSUPPORTED_PROCESS_OBSERVER_OS")
    require(
        0 <= with_settings <= found and 0 <= with_session <= found,
        "INVALID_PROCESS_COUNTS",
    )
    return {
        "candidate_native_processes": found,
        "candidate_with_session_arg": with_session,
        "candidate_with_settings_arg": with_settings,
        "unreadable_process_entries": unreadable,
    }


def _managed_location() -> Path:
    if platform.system() == "Linux":
        return Path("/etc/claude-code/managed-settings.json")
    if platform.system() == "Darwin":
        return Path("/Library/Application Support/ClaudeCode/managed-settings.json")
    raise FleetBlocked("UNSUPPORTED_MANAGED_POLICY_OS")


def observe(host_id: str, challenge: str, *, now: int | None = None) -> dict:
    require(
        isinstance(host_id, str) and HOST_ID.fullmatch(host_id) is not None, "INVALID_HOST_LABEL"
    )
    require(
        isinstance(challenge, str) and HEX_64.fullmatch(challenge) is not None,
        "INVALID_FLEET_CHALLENGE",
    )
    stamp = int(time.time()) if now is None else now
    require(isinstance(stamp, int) and stamp > 0, "INVALID_OBSERVATION_TIME")
    counts = process_counts()
    payload = {
        "schema": 1,
        "host_id": host_id,
        "challenge": challenge,
        "issued_at": stamp,
        "expires_at": stamp + TTL_SECONDS,
        "platform": platform.system().lower(),
        **counts,
        "observed_managed_policy_file": _managed_location().is_file(),
        # An argv scan cannot independently validate loaded hooks, all child
        # processes or sessions from other owners. Never auto-upgrade this.
        "complete_host_session_inventory_attested": False,
        "all_observed_processes_host_gate_attested": False,
        "production_coverage_proven": False,
    }
    _canonical(payload)
    return payload


def public_key(private: Path, openssl: Path) -> bytes:
    _regular(private, max_bytes=8192, private=True)
    exe = _openssl(openssl)
    r = subprocess.run(  # noqa: S603 - explicit OpenSSL binary, no shell
        [str(exe), "pkey", "-in", str(private), "-pubout"],
        capture_output=True,
        timeout=12,
        check=False,
    )
    require(r.returncode == 0 and b"BEGIN PUBLIC KEY" in r.stdout, "INVALID_ED25519_PRIVATE_KEY")
    return r.stdout


def sign(payload: dict, *, private: Path, openssl: Path) -> dict:
    message = _canonical(payload)
    _regular(private, max_bytes=8192, private=True)
    exe = _openssl(openssl)
    with tempfile.TemporaryDirectory(prefix="mods-p1-hostsig-") as folder:
        root = Path(folder)
        data = root / "canonical.json"
        sig = root / "signature"
        data.write_bytes(message)
        r = subprocess.run(  # noqa: S603 - explicit OpenSSL binary, no shell
            [
                str(exe),
                "pkeyutl",
                "-sign",
                "-inkey",
                str(private),
                "-rawin",
                "-in",
                str(data),
                "-out",
                str(sig),
            ],
            capture_output=True,
            timeout=12,
            check=False,
        )
        require(r.returncode == 0 and sig.is_file(), "HOST_SNAPSHOT_SIGNATURE_FAILED")
        signature = sig.read_bytes()
    require(len(signature) == 64, "NOT_ED25519_SIGNATURE")
    return {"schema": 1, "payload": payload, "signature": signature.hex()}


def verify(
    envelope: dict,
    *,
    public: Path,
    openssl: Path,
    expected_host: str,
    expected_challenge: str,
    now: int | None = None,
) -> dict:
    require(
        isinstance(envelope, dict)
        and set(envelope) == ENVELOPE_FIELDS
        and envelope.get("schema") == 1,
        "INVALID_SIGNED_ENVELOPE",
    )
    payload = envelope.get("payload")
    message = _canonical(payload)
    require(
        payload["schema"] == 1
        and payload["host_id"] == expected_host
        and payload["challenge"] == expected_challenge,
        "WRONG_HOST_OR_FLEET_CHALLENGE",
    )
    stamp = int(time.time()) if now is None else now
    require(isinstance(stamp, int) and stamp > 0, "INVALID_VERIFICATION_TIME")
    require(
        isinstance(payload["issued_at"], int)
        and isinstance(payload["expires_at"], int)
        and payload["expires_at"] - payload["issued_at"] == TTL_SECONDS
        and payload["issued_at"] <= stamp + 20
        and payload["expires_at"] > stamp,
        "EXPIRED_OR_FUTURE_SIGNED_OBSERVATION",
    )
    for key in (
        "candidate_native_processes",
        "candidate_with_session_arg",
        "candidate_with_settings_arg",
        "unreadable_process_entries",
    ):
        require(
            type(payload[key]) is int and 0 <= payload[key] <= 1_000_000, "INVALID_PROCESS_COUNT"
        )
    require(
        payload["candidate_with_session_arg"] <= payload["candidate_native_processes"]
        and payload["candidate_with_settings_arg"] <= payload["candidate_native_processes"],
        "INVALID_PROCESS_COVERAGE",
    )
    require(payload["platform"] in ("linux", "darwin"), "INVALID_HOST_OS")
    require(type(payload["observed_managed_policy_file"]) is bool, "INVALID_MANAGED_OBSERVATION")
    require(
        all(
            payload[k] is False
            for k in (
                "complete_host_session_inventory_attested",
                "all_observed_processes_host_gate_attested",
                "production_coverage_proven",
            )
        ),
        "UNSUPPORTED_PRODUCTION_COVERAGE_ASSERTION",
    )
    sig = envelope.get("signature")
    require(
        isinstance(sig, str) and HEX_128.fullmatch(sig) is not None, "INVALID_ED25519_SIGNATURE"
    )
    _regular(public, max_bytes=8192)
    exe = _openssl(openssl)
    with tempfile.TemporaryDirectory(prefix="mods-p1-verify-") as folder:
        root = Path(folder)
        data, signature = root / "canonical.json", root / "signature"
        data.write_bytes(message)
        signature.write_bytes(bytes.fromhex(sig))
        r = subprocess.run(  # noqa: S603 - explicit OpenSSL binary, no shell
            [
                str(exe),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public),
                "-rawin",
                "-in",
                str(data),
                "-sigfile",
                str(signature),
            ],
            capture_output=True,
            timeout=12,
            check=False,
        )
    require(r.returncode == 0, "SIGNATURE_VERIFICATION_FAILED")
    return payload


def audit_fleet(
    envelopes: dict[str, dict],
    public_keys: dict[str, Path],
    *,
    openssl: Path,
    challenge: str,
    now: int | None = None,
) -> dict[str, Any]:
    require(
        isinstance(envelopes, dict)
        and isinstance(public_keys, dict)
        and len(public_keys) >= 2
        and len(public_keys) <= 8
        and set(envelopes) == set(public_keys),
        "MISSING_OR_UNEXPECTED_FLEET_HOST",
    )
    signed: dict[str, dict] = {}
    for host in sorted(public_keys):
        signed[host] = verify(
            envelopes[host],
            public=public_keys[host],
            openssl=openssl,
            expected_host=host,
            expected_challenge=challenge,
            now=now,
        )
    total = sum(x["candidate_native_processes"] for x in signed.values())
    return {
        "schema": 1,
        "target": "fleet-readonly-qa",
        "expected_host_count": len(public_keys),
        "fresh_host_signatures_verified": len(signed),
        "observed_native_process_candidates": total,
        "hosts_with_managed_policy_file": sum(
            x["observed_managed_policy_file"] for x in signed.values()
        ),
        "all_expected_observers_fresh_at_verification_time": True,
        "this_does_not_establish_future_freshness": True,
        "all_native_host_sessions_protected": False,
        "complete_global_session_inventory": False,
        "cross_machine_quiescence_authorized": False,
        "stable_release_authorized": False,
        "host_receipt_sha256": {
            host: hashlib.sha256(_canonical(payload)).hexdigest()
            for host, payload in signed.items()
        },
        "host_public_key_sha256": {
            host: hashlib.sha256(public_keys[host].read_bytes()).hexdigest() for host in signed
        },
    }
