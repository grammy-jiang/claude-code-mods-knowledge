"""Signed *live-at-issue-time* QA supervisor witness, NOT global Claude coverage.

Reads real owned root state and original native wire/debug to confirm the
sandboxed Claude 2.1.304 supervisor and its one managed child are alive NOW.
Independent Ed25519 host signatures authenticate the observation origin.
A signature does not freeze, control or discover other active sessions.
The observer deliberately rejects even valid old signatures after a short TTL.
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

from .cli304_supervised_lease import (
    NATIVE_CLI304_SHA,
    SupervisorBlocked,
    boot_id,
    read_lease,
    start_ticks,
)

TTL = 14
FIELDS = {
    "schema",
    "host",
    "challenge",
    "observed_at",
    "expires_at",
    "boot_sha256",
    "supervisor_instance_sha256",
    "native_process_sha256",
    "managed_policy_sha256",
    "native_binary_sha256",
    "native_wire_sha256",
    "same_running_native_session_observed",
    "active_managed_lease_at_issue",
    "complete_host_session_inventory_proven",
    "global_host_protection_proven",
    "stable_release_authorized",
}
HOST = re.compile(r"[a-z][a-z0-9-]{1,25}\Z")
NONCE = re.compile(r"[a-f0-9]{64}\Z")


class LiveWitnessBlocked(ValueError):
    """Untrusted, stale, or incomplete real-host witness."""


def must(condition: bool, reason: str) -> None:
    if not condition:
        raise LiveWitnessBlocked(reason)


def hash_file(path: Path, *, limit: int = 5_000_000) -> str:
    must(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
        "MISSING_PRIVATE_RECORD",
    )
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _canonical(data: dict) -> bytes:
    must(isinstance(data, dict) and set(data) == FIELDS, "INVALID_LIVE_WITNESS_FIELDS")
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    must(len(raw) <= 4096, "OVERSIZED_LIVE_WITNESS")
    return raw


def _alive_child(root: Path, bwrap_pid: int, session: str) -> tuple[int, int]:
    """Require a live bwrap plus a real native Claude 304 process in its group."""
    try:
        ticks = start_ticks(bwrap_pid)
        argv = (Path("/proc") / str(bwrap_pid) / "cmdline").read_bytes().split(b"\0")
    except (OSError, SupervisorBlocked) as exc:
        raise LiveWitnessBlocked("SUPERVISED_BWRAP_NOT_RUNNING") from exc
    joined = b"\0".join(argv)
    must(
        b"bwrap" in argv[0]
        and str(root / "managed").encode() in joined
        and b"/etc/claude-code" in joined,
        "SUPERVISED_HOST_NOT_IN_MANAGED_NAMESPACE",
    )
    matches: list[int] = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        if pid == bwrap_pid:
            continue  # bwrap argv contains the child's flags, but is not Claude
        try:
            args = (path / "cmdline").read_bytes()
            if not args or session.encode() not in args or b"--session-id" not in args:
                continue
            if b"claude-2.1.304" not in args and b"extracted/claude" not in args:
                continue
            if os.getpgid(pid) != os.getpgid(bwrap_pid):
                continue
            matches.append(pid)
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
    must(len(matches) == 1, "NO_UNIQUE_LIVE_NATIVE_CLAUDE_CHILD")
    return ticks, start_ticks(matches[0])


def inspect(root: Path, host: str, challenge: str, *, now: int | None = None) -> dict:
    must(isinstance(host, str) and HOST.fullmatch(host) is not None, "INVALID_WITNESS_HOST")
    must(
        isinstance(challenge, str) and NONCE.fullmatch(challenge) is not None,
        "INVALID_WITNESS_CHALLENGE",
    )
    must(root.is_absolute() and root.is_dir() and not root.is_symlink(), "INVALID_ACTIVE_ROOT")
    private = root / "private"
    must(
        private.is_dir()
        and not private.is_symlink()
        and private.stat().st_uid == os.getuid()
        and stat.S_IMODE(private.stat().st_mode) == 0o700,
        "UNSAFE_ACTIVE_SUPERVISOR_STORAGE",
    )
    state = root / "private/live-status.private.json"
    must(state.is_file() and not state.is_symlink(), "NO_VERIFIED_NATIVE_READ_YET")
    status = json.loads(state.read_text())
    must(
        status["schema"] == 1
        and status["live_native_read_verified"] is True
        and status["global_session_coverage"] is False
        and status["stable_release_authorized"] is False
        and status["phase"] == "ready"
        and status["native_cli_sha256"] == NATIVE_CLI304_SHA,
        "UNVERIFIED_NATIVE_HOST_LIVE_STATUS",
    )
    try:
        lease = read_lease(root / "private/supervisor-lease.json")
    except (SupervisorBlocked, OSError) as exc:
        raise LiveWitnessBlocked("SUPERVISOR_NOT_FRESH_OR_FROZEN") from exc
    must(
        status["parent_supervisor_pid"] == lease["supervisor_pid"]
        and status["parent_supervisor_ticks"] == lease["supervisor_ticks"]
        and status["session_sha256"] == hashlib.sha256(lease["session"].encode()).hexdigest(),
        "MISMATCHED_RUNNING_SUPERVISOR",
    )
    child_ticks, cli_ticks = _alive_child(root, status["child_bwrap_pid"], lease["session"])
    policy = hash_file(root / "managed/managed-settings.json", limit=16_000)
    must(policy == status["policy_sha256"], "MANAGED_POLICY_CHANGED_DURING_SESSION")
    wire = root / "raw/native-wire.private.jsonl"
    debug_path = root / "raw/native-debug.private.log"
    wire_sha = hash_file(wire)
    debug = debug_path.read_text(errors="replace")
    must(
        "managed-settings.json" in debug and "PreToolUse:Read" in debug,
        "REAL_MANAGED_HOOK_NOT_SEEN",
    )
    events = [json.loads(s) for s in wire.read_text().splitlines() if s.strip()]
    must(
        all(x.get("session_id") == lease["session"] for x in events),
        "MIXED_NATIVE_SESSION_EVIDENCE",
    )
    uses = [
        p.get("name")
        for x in events
        if x.get("type") == "assistant"
        for p in (x.get("message") or {}).get("content", [])
        if isinstance(p, dict) and p.get("type") == "tool_use"
    ]
    results = [
        p
        for x in events
        if x.get("type") == "user"
        for p in (x.get("message") or {}).get("content", [])
        if isinstance(p, dict) and p.get("type") == "tool_result"
    ]
    must(
        uses == ["Read"]
        and any("QA_SUPERVISED_READ_OK_20261022" in json.dumps(p) for p in results)
        and any(x.get("type") == "result" and x.get("subtype") == "success" for x in events),
        "NATIVE_MANAGED_READ_NOT_ACTUALLY_COMPLETED",
    )
    instant = int(time.time()) if now is None else now
    must(type(instant) is int and instant > 0, "INVALID_OBSERVER_TIME")
    return {
        "schema": 1,
        "host": host,
        "challenge": challenge,
        "observed_at": instant,
        "expires_at": instant + TTL,
        "boot_sha256": hashlib.sha256(boot_id().encode()).hexdigest(),
        "supervisor_instance_sha256": hashlib.sha256(
            f"{lease['supervisor_pid']}:{lease['supervisor_ticks']}:{lease['generation']}".encode()
        ).hexdigest(),
        "native_process_sha256": hashlib.sha256(
            f"{status['child_bwrap_pid']}:{child_ticks}:{cli_ticks}".encode()
        ).hexdigest(),
        "managed_policy_sha256": policy,
        "native_binary_sha256": NATIVE_CLI304_SHA,
        "native_wire_sha256": wire_sha,
        "same_running_native_session_observed": True,
        "active_managed_lease_at_issue": True,
        "complete_host_session_inventory_proven": False,
        "global_host_protection_proven": False,
        "stable_release_authorized": False,
    }


def _openssl(binary: Path) -> Path:
    must(binary.is_absolute() and binary.is_file(), "INVALID_OPENSSL_EXECUTABLE")
    return binary


def sign(payload: dict, *, private: Path, openssl: Path) -> dict:
    body = _canonical(payload)
    must(
        private.is_file()
        and not private.is_symlink()
        and private.stat().st_uid == os.getuid()
        and stat.S_IMODE(private.stat().st_mode) == 0o600,
        "UNSAFE_HOST_SIGNING_KEY",
    )
    with tempfile.TemporaryDirectory(prefix="cli304-live-sign-") as folder:
        data, sig = Path(folder) / "input", Path(folder) / "signature"
        data.write_bytes(body)
        run = subprocess.run(  # noqa: S603 - exact pinned local openssl argv, no shell
            [
                str(_openssl(openssl)),
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
        must(run.returncode == 0 and sig.is_file(), "LIVE_SIGNING_FAILURE")
        b = sig.read_bytes()
    must(len(b) == 64, "INVALID_ED25519_SIGNATURE_SIZE")
    return {"schema": 1, "payload": payload, "signature": b.hex()}


def verify(envelope: dict, *, pubkey: Path, openssl: Path, host: str, nonce: str, now: int) -> dict:
    must(
        isinstance(envelope, dict)
        and set(envelope) == {"schema", "payload", "signature"}
        and envelope["schema"] == 1,
        "INVALID_ENVELOPE",
    )
    payload = envelope["payload"]
    body = _canonical(payload)
    must(payload["host"] == host and payload["challenge"] == nonce, "WRONG_HOST_OR_NONCE")
    must(
        type(now) is int
        and type(payload["observed_at"]) is int
        and type(payload["expires_at"]) is int
        and payload["expires_at"] - payload["observed_at"] == TTL
        and payload["observed_at"] <= now + 2
        and now < payload["expires_at"],
        "EXPIRED_OR_FUTURE_LIVE_WITNESS",
    )
    must(
        payload["same_running_native_session_observed"] is True
        and payload["active_managed_lease_at_issue"] is True
        and payload["complete_host_session_inventory_proven"] is False
        and payload["global_host_protection_proven"] is False
        and payload["stable_release_authorized"] is False
        and payload["native_binary_sha256"] == NATIVE_CLI304_SHA,
        "UNSUPPORTED_HOST_COVERAGE_ASSERTION",
    )
    for key in (
        "boot_sha256",
        "supervisor_instance_sha256",
        "native_process_sha256",
        "managed_policy_sha256",
        "native_wire_sha256",
    ):
        must(
            re.fullmatch(r"[0-9a-f]{64}", payload[key]) is not None,
            "INVALID_NATIVE_ATTESTED_DIGEST",
        )
    signature = envelope.get("signature")
    must(
        isinstance(signature, str) and re.fullmatch(r"[0-9a-f]{128}", signature),
        "INVALID_SIGNATURE",
    )
    must(pubkey.is_file() and not pubkey.is_symlink(), "MISSING_TRUSTED_PUBLIC_KEY")
    with tempfile.TemporaryDirectory(prefix="cli304-live-verify-") as folder:
        data, sig = Path(folder) / "input", Path(folder) / "sig"
        data.write_bytes(body)
        sig.write_bytes(bytes.fromhex(signature))
        result = subprocess.run(  # noqa: S603 - explicit local OpenSSL, no shell
            [
                str(_openssl(openssl)),
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(pubkey),
                "-rawin",
                "-in",
                str(data),
                "-sigfile",
                str(sig),
            ],
            capture_output=True,
            timeout=12,
            check=False,
        )
    must(result.returncode == 0, "SIGNED_LIVE_WITNESS_VERIFICATION_FAILED")
    return payload


def audit_quorum(
    packets: dict[str, dict],
    keys: dict[str, Path],
    *,
    openssl: Path,
    nonce: str,
    now: int,
) -> dict:
    must(set(keys) == set(packets) and len(keys) >= 2, "MISSING_SIGNED_RUNNING_HOST")
    result = {
        host: verify(
            packets[host], pubkey=keys[host], openssl=openssl, host=host, nonce=nonce, now=now
        )
        for host in sorted(keys)
    }
    must(
        len({x["supervisor_instance_sha256"] for x in result.values()}) == len(result),
        "DUPLICATE_NATIVE_SUPERVISOR_INSTANCE",
    )
    return {
        "schema": 1,
        "actual_signed_live_qa_hosts_at_issue": len(result),
        "host_ids": sorted(result),
        "earliest_witness_expiry": min(x["expires_at"] for x in result.values()),
        "host_witness_sha256": {
            host: hashlib.sha256(_canonical(result[host])).hexdigest() for host in sorted(result)
        },
        "live_witness_is_not_current_after_expiry": True,
        "unmanaged_native_processes_unprotected": True,
        "complete_global_session_inventory_proven": False,
        "production_wide_quiescence_authorized": False,
        "stable_release_authorized": False,
    }
