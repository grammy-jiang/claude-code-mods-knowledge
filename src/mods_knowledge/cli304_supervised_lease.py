"""Fail-closed, supervised native host QA lease, never a global Claude policy.

The Linux supervisor owns and writes one 0600 lease in a 0700 directory.
An independently installed managed PreToolUse command hook checks the
supervisor's PID+start time+boot identity AND short monotonic lease expiry.
Only sandbox-started QA hosts loading the managed hook are covered. A user
with the same UID can forge these files: this is not a system privilege boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

NATIVE_CLI304_SHA = "c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3"
SCHEMA = 1
TTL_MIN = 0.5
TTL_MAX = 6.0
MAX_BYTES = 4096
PHASES = frozenset({"ready", "frozen", "blocked"})
SESSION_PATTERN = re.compile(r"[a-zA-Z0-9-]{10,80}\Z")


class SupervisorBlocked(ValueError):
    """Missing, stale, unauthenticated or contradictory supervised QA state."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SupervisorBlocked(reason)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def boot_id() -> str:
    """Linux-only namespace process origin; no fallbacks to unsafe defaults."""
    text = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    require(len(text) == 36, "MISSING_LINUX_BOOT_ID")
    return text


def start_ticks(pid: int) -> int:
    """Read Linux proc stat field 22, distinguishing same-PID replacements."""
    require(type(pid) is int and pid > 0, "INVALID_SUPERVISOR_PID")
    try:
        contents = (Path("/proc") / str(pid) / "stat").read_text()
        # The executable name inside parentheses can contain spaces and ')'.
        tail = contents[contents.rfind(")") + 2 :].split()
        require(tail[0] not in ("Z", "X", "x"), "SUPERVISOR_ZOMBIE_OR_EXITED")
        ticks = int(tail[19])  # stat tail begins with field 3
    except (OSError, ValueError, IndexError) as exc:
        raise SupervisorBlocked("SUPERVISOR_PROCESS_NOT_ALIVE") from exc
    require(ticks > 0, "INVALID_SUPERVISOR_START_TICKS")
    return ticks


def _private_path(file: Path, *, creating: bool = False) -> None:
    require(file.is_absolute(), "ABSOLUTE_PRIVATE_LEASE_REQUIRED")
    folder = file.parent
    require(folder.is_dir() and not folder.is_symlink(), "INVALID_LEASE_DIRECTORY")
    s = folder.stat()
    require(
        s.st_uid == os.getuid() and stat.S_IMODE(s.st_mode) == 0o700,
        "INVALID_LEASE_DIRECTORY_PERMISSIONS",
    )
    if not creating:
        require(file.is_file() and not file.is_symlink(), "MISSING_PRIVATE_LEASE")
        st = file.stat()
        require(
            st.st_uid == os.getuid()
            and stat.S_IMODE(st.st_mode) == 0o600
            and 0 < st.st_size <= MAX_BYTES,
            "INVALID_LEASE_FILE_PERMISSIONS",
        )


def atomic_lease(file: Path, value: dict[str, Any]) -> str:
    """Replace one verified private state atomically, fsync file and directory."""
    _private_path(file, creating=True)
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    require(len(raw) <= MAX_BYTES, "OVERSIZED_LEASE")
    fd, path = tempfile.mkstemp(dir=file.parent, prefix=".lease-")
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        os.replace(path, file)
        dfd = os.open(file.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(path):
            os.unlink(path)
    return digest(raw)


def read_lease(file: Path, *, now: float | None = None) -> dict[str, Any]:
    """Always re-read state at each guarded tool, refuse stale/alien PID."""
    _private_path(file)
    try:
        value = json.loads(file.read_bytes())
    except (OSError, ValueError) as exc:
        raise SupervisorBlocked("CORRUPTED_PRIVATE_LEASE") from exc
    require(
        isinstance(value, dict)
        and set(value)
        == {
            "schema",
            "session",
            "phase",
            "generation",
            "deadline_monotonic",
            "supervisor_pid",
            "supervisor_ticks",
            "boot_id",
        }
        and value["schema"] == SCHEMA,
        "INVALID_LEASE_SCHEMA",
    )
    require(
        isinstance(value["session"], str)
        and SESSION_PATTERN.fullmatch(value["session"]) is not None,
        "INVALID_LEASE_SESSION",
    )
    require(
        value["phase"] in PHASES
        and isinstance(value["generation"], str)
        and re.fullmatch(r"[a-f0-9]{32}", value["generation"]),
        "INVALID_LEASE_PHASE",
    )
    require(
        type(value["deadline_monotonic"]) in (float, int)
        and value["deadline_monotonic"] > 0
        and type(value["supervisor_pid"]) is int
        and type(value["supervisor_ticks"]) is int,
        "INVALID_LEASE_CLOCK_OR_PROCESS",
    )
    # Reject leases from a previous machine boot or a different process
    # that acquired the same PID after the real supervisor died.
    require(value["boot_id"] == boot_id(), "STALE_LINUX_BOOT")
    require(
        start_ticks(value["supervisor_pid"]) == value["supervisor_ticks"],
        "SUPERVISOR_PID_REUSED_OR_GONE",
    )
    instant = time.monotonic() if now is None else now
    require(
        0 < value["deadline_monotonic"] - instant <= TTL_MAX + 0.2,
        "SUPERVISOR_LEASE_EXPIRED_OR_FUTURE",
    )
    require(value["phase"] == "ready", "SUPERVISED_HOST_FROZEN")
    return value


class PrivateLease:
    """Owned by the actual launcher; immutable child identity in one cohort."""

    def __init__(self, path: Path, *, session: str, ttl: float = 2.0):
        require(
            SESSION_PATTERN.fullmatch(session) is not None,
            "INVALID_SESSION_ID",
        )
        require(TTL_MIN <= ttl <= TTL_MAX, "INVALID_SHORT_HEARTBEAT_TTL")
        _private_path(path, creating=True)
        require(not path.exists(), "EXISTING_PRIVATE_LEASE")
        self.path = path
        self.session = session
        self.ttl = ttl
        self.pid = os.getpid()
        self.ticks = start_ticks(self.pid)
        self.machine_boot = boot_id()
        self.generation = secrets.token_hex(16)
        self.phase = "blocked"
        self._initial_health_verification_pending = True
        self._write_lock = threading.RLock()
        self.refresh("blocked")

    def refresh(self, phase: str | None = None) -> str:
        with self._write_lock:
            if phase is not None:
                require(phase in PHASES, "INVALID_PHASE_TRANSITION")
                # Allow only the initial bootstrap to transition from
                # blocked to ready; never silently thaw a frozen or blocked
                # host after a failure without a fresh supervisor generation.
                if phase == "ready" and self.phase != "ready":
                    require(
                        self.phase == "blocked" and self._initial_health_verification_pending,
                        "BLOCKED_SUPERVISOR_CANNOT_REOPEN",
                    )
                    self._initial_health_verification_pending = False
                self.phase = phase
            state = {
                "schema": SCHEMA,
                "session": self.session,
                "phase": self.phase,
                "generation": self.generation,
                "deadline_monotonic": time.monotonic() + self.ttl,
                "supervisor_pid": self.pid,
                "supervisor_ticks": self.ticks,
                "boot_id": self.machine_boot,
            }
            return atomic_lease(self.path, state)
