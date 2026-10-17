#!/usr/bin/env python3
"""Mac-only owned model process watchdog for a scoped P5 QA batch.

Never starts, stops, or otherwise touches the user's original AI services,
Android emulators or Chrome. Stops only a verified test-owned child when
its controller dies; records a small private audit, not model content.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def process_alive(pid: object) -> bool:
    if type(pid) is not int or pid < 2:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def owned_model_command(pid: int, candidate: str) -> bool:
    probe = subprocess.run(  # noqa: S603 - literal read-only ps
        ["/bin/ps", "-ww", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        timeout=7,
    )
    cmd = probe.stdout.strip()
    return probe.returncode == 0 and (
        ("llama-server" in cmd and "gpt-oss-120b-MXFP4.gguf" in cmd)
        if candidate == "gpt-oss"
        else ("/omlx serve" in cmd and "--port 8011" in cmd)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--owner-pid", type=int, required=True)
    args = parser.parse_args()
    statefile = args.state.resolve()
    if statefile.name != "active-model-state.json" or not statefile.is_file():
        raise ValueError("Owned active-model state file required")
    # Supports 20-minute maximum model+six-turn windows, one at a time.
    until = time.monotonic() + 1300
    reason = None
    while time.monotonic() < until:
        try:
            s = json.loads(statefile.read_text())
        except (OSError, ValueError):
            s = {}
        if s.get("phase") == "completed_and_unloaded":
            return 0
        if not process_alive(args.owner_pid):
            reason = "controller_no_longer_running"
            break
        time.sleep(2)
    else:
        reason = "window_hard_deadline_exceeded"
    try:
        s = json.loads(statefile.read_text())
    except (OSError, ValueError):
        s = {}
    candidate, pid = s.get("candidate"), s.get("model_pid")
    stopped = not process_alive(pid)
    if not stopped and candidate in {"qwen", "gemma31", "gpt-oss", "mistral", "heretic"}:
        if owned_model_command(pid, candidate):
            os.killpg(pid, signal.SIGTERM)
            time.sleep(4)
            if process_alive(pid) and owned_model_command(pid, candidate):
                os.killpg(pid, signal.SIGKILL)
            stopped = not process_alive(pid)
    result = {
        "reason": reason,
        "verified_test_model_stopped": stopped,
        "original_user_services_touched": False,
        "timestamp_epoch": time.time(),
    }
    out = statefile.parent / "watchdog-recovery.json"
    with out.open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    out.chmod(0o600)
    return 0 if stopped else 3


if __name__ == "__main__":
    raise SystemExit(main())
