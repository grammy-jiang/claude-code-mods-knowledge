#!/usr/bin/env python3
"""Isolated, native managed PreToolUse gate for supervised CLI304 QA only.

It is loaded from the OS managed settings namespace, not from a reloadable
Mod or an opt-in lower-priority --settings file. On unexpected input, missing
lease or crashed parent it exits 2, rejecting tools. Only a QA workspace Read
is eligible. The private lease is user-writable: not a privileged policy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mods_knowledge.cli304_supervised_lease import SupervisorBlocked, read_lease


def check(event: object, *, lease: Path, workspace: Path) -> None:
    if not isinstance(event, dict):
        raise SupervisorBlocked("INVALID_NATIVE_HOOK_INPUT")
    if event.get("hook_event_name") != "PreToolUse":
        raise SupervisorBlocked("UNKNOWN_HOOK_EVENT")
    status = read_lease(lease)
    if event.get("session_id") != status["session"]:
        raise SupervisorBlocked("UNREGISTERED_NATIVE_SESSION")
    if event.get("tool_name") != "Read":
        raise SupervisorBlocked("QA_READ_ONLY_MANAGED_POLICY")
    call = event.get("tool_input")
    if not isinstance(call, dict) or not isinstance(call.get("file_path"), str):
        raise SupervisorBlocked("UNKNOWN_READ_TARGET")
    target = Path(call["file_path"])
    if not target.is_absolute():
        cwd = event.get("cwd")
        if not isinstance(cwd, str):
            raise SupervisorBlocked("MISSING_NATIVE_WORKING_DIRECTORY")
        target = Path(cwd) / target
    if (
        not target.resolve(strict=True).is_relative_to(workspace.resolve(strict=True))
        or not target.resolve(strict=True).is_file()
    ):
        raise SupervisorBlocked("READ_TARGET_OUTSIDE_QA_WORKSPACE")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lease", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(65537)
        if not raw or len(raw) > 65536:
            raise SupervisorBlocked("INVALID_HOOK_STDIN_LENGTH")
        check(json.loads(raw), lease=arguments.lease, workspace=arguments.workspace)
        return 0
    except (SupervisorBlocked, OSError, UnicodeError, ValueError, TypeError):
        print("SUPERVISOR_QA_DENIED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
