#!/usr/bin/env python3
"""Independent host-level PreToolUse/PostToolUse QA guard for enrolled CLI304.

No module from the reloadable Plugin is imported. Every ordinary tool other
than a reviewed workspace-confined Read is denied. The actual native tool ID
is held as a durable permit across execution until an authenticated Post hook.
Only a session launched with these settings is covered. Do not attach to the
user's existing production sessions or claim global protection.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

# This script lives in the repository; a standalone frozen QA copy preserves
# the same package layout. Never import from a hot-reloadable Mod.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mods_knowledge.guarded_rollout import GuardedRollout, UpdateBlocked  # noqa: E402

MAX_EVENT = 65_536
EVENT_PHASE = {
    "pre": "PreToolUse",
    "post": "PostToolUse",
    "failure": "PostToolUseFailure",
}


def _secret(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise UpdateBlocked("HOST_GATE_SECRET_MISSING")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise UpdateBlocked("HOST_GATE_SECRET_UNSAFE")
    raw = path.read_bytes()
    if len(raw) > 256:
        raise UpdateBlocked("HOST_GATE_SECRET_OVERSIZE")
    token = raw.decode().strip()
    if len(token) < 32 or any(x.isspace() for x in token):
        raise UpdateBlocked("HOST_GATE_SECRET_INVALID")
    return token


def _read_event() -> dict:
    body = sys.stdin.buffer.read(MAX_EVENT + 1)
    if not body or len(body) > MAX_EVENT:
        raise UpdateBlocked("HOST_GATE_INPUT_LENGTH")
    try:
        event = json.loads(body)
    except (UnicodeError, ValueError) as exc:
        raise UpdateBlocked("HOST_GATE_INPUT_NOT_JSON") from exc
    if not isinstance(event, dict):
        raise UpdateBlocked("HOST_GATE_INPUT_NOT_OBJECT")
    return event


def _allowed_read(event: dict, workspace: Path) -> None:
    if event.get("tool_name") != "Read":
        raise UpdateBlocked("HOST_GATE_DENIES_UNREVIEWED_TOOL")
    content = event.get("tool_input")
    if not isinstance(content, dict) or not isinstance(content.get("file_path"), str):
        raise UpdateBlocked("HOST_GATE_UNKNOWN_READ_PARAMETERS")
    target = Path(content["file_path"])
    if not target.is_absolute():
        cwd = event.get("cwd")
        if not isinstance(cwd, str):
            raise UpdateBlocked("HOST_GATE_UNKNOWN_WORKSPACE")
        target = Path(cwd) / target
    try:
        resolved_workspace = workspace.resolve(strict=True)
        resolved_target = target.resolve(strict=True)
    except OSError as exc:
        raise UpdateBlocked("HOST_GATE_READ_PATH_NOT_EXISTING") from exc
    if not resolved_target.is_relative_to(resolved_workspace) or not resolved_target.is_file():
        raise UpdateBlocked("HOST_GATE_READ_OUTSIDE_PRIVATE_WORKSPACE")


def handle(gate: GuardedRollout, secret: str, event: dict, *, phase: str, workspace: Path) -> None:
    if event.get("hook_event_name") != EVENT_PHASE[phase]:
        raise UpdateBlocked("HOST_GATE_WRONG_EVENT")
    session = event.get("session_id")
    tool_id = event.get("tool_use_id")
    if not isinstance(session, str) or not isinstance(tool_id, str):
        raise UpdateBlocked("HOST_GATE_MISSING_NATIVE_IDENTITY")
    if phase == "pre":
        _allowed_read(event, workspace)
        gate.native_tool_pre(session, secret, tool_id, event["tool_name"])
        return
    if event.get("tool_name") != "Read":
        raise UpdateBlocked("HOST_GATE_UNEXPECTED_TOOL_COMPLETION")
    gate.native_tool_post(session, secret, tool_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=tuple(EVENT_PHASE), required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--secret-file", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        event = _read_event()
        gate = GuardedRollout(args.state_root)
        handle(
            gate,
            _secret(args.secret_file),
            event,
            phase=args.phase,
            workspace=args.workspace,
        )
        return 0
    except (UpdateBlocked, OSError, ValueError, TypeError):
        # Exit 2 blocks PreToolUse, and onFailure:block covers missing/failed
        # hooks. Completion-hook failure cannot retroactively block a tool,
        # but its ledger permit remains held so an update cannot begin.
        print("HOST_GATE_REFUSED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
