#!/usr/bin/env python3
"""Build a private command-line --settings JSON with an external fail-closed hook.

QA only: the invoking operator must independently verify that the target
native CLI loaded this immutable setting before any protected tools run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


def _absolute_regular(file: Path) -> None:
    if not file.is_absolute() or not file.is_file() or file.is_symlink():
        raise ValueError("EXACT_ABSOLUTE_HOOK_EXECUTABLE_REQUIRED")


def build_settings(
    *,
    python: Path,
    script: Path,
    state_root: Path,
    secret_file: Path,
    workspace: Path,
) -> dict:
    _absolute_regular(python)
    _absolute_regular(script)
    if not state_root.is_absolute() or not state_root.is_dir():
        raise ValueError("EXISTING_PRIVATE_STATE_ROOT_REQUIRED")
    if not workspace.is_absolute() or not workspace.is_dir():
        raise ValueError("PRIVATE_WORKSPACE_REQUIRED")
    if not secret_file.is_file() or secret_file.is_symlink():
        raise ValueError("PRIVATE_SECRET_REQUIRED")
    info = secret_file.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError("UNSAFE_PRIVATE_SECRET")
    hooks = {}
    for phase, event in (
        ("pre", "PreToolUse"),
        ("post", "PostToolUse"),
        ("failure", "PostToolUseFailure"),
    ):
        hook = {
            "type": "command",
            "command": str(python),
            "args": [
                str(script),
                "--phase",
                phase,
                "--state-root",
                str(state_root),
                "--secret-file",
                str(secret_file),
                "--workspace",
                str(workspace),
            ],
            "timeout": 12,
            "onFailure": "block",
        }
        hooks[event] = [{"matcher": "", "hooks": [hook]}]
    return {"hooks": hooks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("python", "script", "state-root", "secret-file", "workspace", "out"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    output = args.out
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise SystemExit("REFUSED: unexpected settings output path")
    content = (
        json.dumps(
            build_settings(
                python=args.python,
                script=args.script,
                state_root=args.state_root,
                secret_file=args.secret_file,
                workspace=args.workspace,
            ),
            sort_keys=True,
            indent=2,
        ).encode()
        + b"\n"
    )
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    print(
        json.dumps({"settings_sha256": hashlib.sha256(content).hexdigest(), "on_failure": "block"})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
