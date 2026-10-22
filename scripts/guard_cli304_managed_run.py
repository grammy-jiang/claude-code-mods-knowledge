#!/usr/bin/env python3
"""External POSIX gate for opt-in *managed* tasks during Claude Mods updates.

This intentionally cannot control Claude Code built-in tools or a process
launched without this wrapper. Run only known single-process, bounded jobs;
no daemonizing children. Never use it to claim production-wide protection.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import stat
import subprocess
import sys
from pathlib import Path

from mods_knowledge.guarded_rollout import GuardedRollout, UpdateBlocked


def _read_secret(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise UpdateBlocked("SECRET_FILE_REQUIRED")
    meta = path.stat()
    if meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o600:
        raise UpdateBlocked("UNSAFE_SECRET_FILE_PERMISSIONS")
    if meta.st_size > 256:
        raise UpdateBlocked("INVALID_SECRET_LENGTH")
    value = path.read_text().strip()
    if len(value) < 32 or any(c.isspace() for c in value):
        raise UpdateBlocked("INVALID_SESSION_SECRET")
    return value


def _controlled_run(
    gate: GuardedRollout, session: str, secret: str, args: list[str], timeout: int
) -> int:
    if not args or not args[0] or args[0].startswith("-"):
        raise UpdateBlocked("EXPLICIT_SUBPROCESS_EXECUTABLE_REQUIRED")
    permit = gate.enter(session, secret)
    process = None
    try:
        process = subprocess.Popen(args, start_new_session=True)  # noqa: S603 - explicit opt-in argv
        try:
            rc = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            # Unknown descendants must never be assumed terminated simply
            # because the direct child was killed.
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            gate.fail_closed("MANAGED_COMMAND_TIMEOUT_DESCENDANTS_UNVERIFIED")
            raise UpdateBlocked("MANAGED_COMMAND_TIMEOUT_COHORT_BLOCKED") from exc
    except (OSError, subprocess.SubprocessError):
        gate.fail_closed("MANAGED_COMMAND_EXIT_UNVERIFIED")
        raise
    else:
        gate.leave(session, secret, permit)
        return rc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    for name in ("heartbeat", "ack", "run"):
        target = sub.add_parser(name)
        target.add_argument("--session-id", required=True)
        target.add_argument("--secret-file", type=Path, required=True)
        if name == "run":
            target.add_argument("--timeout-seconds", type=int, default=120)
            target.add_argument("command", nargs=argparse.REMAINDER)
    p = parser.parse_args()
    gate = GuardedRollout(p.state_root)
    try:
        if p.action == "status":
            print(json.dumps(gate.status(), sort_keys=True))
            return 0
        secret = _read_secret(p.secret_file)
        if p.action == "heartbeat":
            gate.heartbeat(p.session_id, secret)
        elif p.action == "ack":
            gate.acknowledge(p.session_id, secret)
        else:
            if not 1 <= p.timeout_seconds <= 3600:
                raise UpdateBlocked("INVALID_MANAGED_COMMAND_TIMEOUT")
            args = p.command[1:] if p.command and p.command[0] == "--" else p.command
            return _controlled_run(gate, p.session_id, secret, args, timeout=p.timeout_seconds)
    except (UpdateBlocked, OSError, subprocess.SubprocessError) as exc:
        print("BLOCKED: " + type(exc).__name__, file=sys.stderr)
        return 77
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
