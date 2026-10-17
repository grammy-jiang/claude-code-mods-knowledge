# ruff: noqa: S603
#!/usr/bin/env python3
"""Independent bounded rollback if the owner-controlled test worker exits.

Does not stop any user process; only a verified child model from the
maintenance state, then restores the exact five originally loaded AI
LaunchDaemons. Intended to run in its own session.
"""

from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import time
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
STATE = BASE / "live_state.json"
CTL = pathlib.Path.home() / "Projects/strata-mac-lab/scripts/ai-services.sh"
LABELS = (
    "com.grammy.qwen36-omlx",
    "local.whisper-server",
    "local.mlx-audio",
    "local.ollama",
    "local.comfyui",
)


def read() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid < 2:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def owner_confirmed(pid: object, expected_cmd: str) -> bool:
    if not alive(pid):
        return False
    x = subprocess.run(
        ["/bin/ps", "-ww", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        timeout=5,
    )
    cmd = x.stdout.strip()
    return (
        bool(cmd)
        and any(word in cmd for word in ("llama-server", "/omlx serve"))
        and (expected_cmd in cmd if expected_cmd else True)
    )


def stop_child(state: dict) -> bool:
    pid = state.get("model_pid")
    alias = state.get("active_model")
    expected = "gpt-oss-120b-MXFP4.gguf" if alias == "gpt-oss-120b" else "modelset" if alias else ""
    if not owner_confirmed(pid, expected):
        return not alive(pid)
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + 14
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.4)
    if owner_confirmed(pid, expected):
        os.killpg(pid, signal.SIGKILL)
    return not alive(pid)


def health() -> bool:
    x = subprocess.run([str(CTL), "status"], capture_output=True, text=True, timeout=12)
    return x.returncode == 0 and all(n + " loaded state=running" in x.stdout for n in LABELS)


def qwen() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:18080/v1/models", timeout=3) as r:
            j = json.load(r)
        return any(x.get("id") == "qwen36-35b-a3b-mtp" for x in j.get("data", []))
    except (OSError, ValueError):
        return False


def restore() -> tuple[bool, str]:
    try:
        subprocess.run(
            [str(CTL), "restore"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=65
        )
        until = time.monotonic() + 170
        while time.monotonic() < until:
            if health() and qwen():
                return True, "all_five_healthy"
            time.sleep(3)
        return False, "restore_health_deadline"
    except Exception as e:
        return False, type(e).__name__


def main() -> int:
    until = time.monotonic() + 1800
    while time.monotonic() < until:
        data = read()
        if data.get("phase") in ("complete", "complete_with_issues") and data.get(
            "restore_confirmed"
        ):
            return 0
        owner = data.get("controller_pid")
        if owner and not alive(owner):
            reason = "controller_exited_early"
            break
        time.sleep(3)
    else:
        reason = "hard_maintenance_time_limit"
    details = read()
    success_stop = stop_child(details)
    success_restore, restore_code = restore()
    outcome = {
        "reason": reason,
        "model_owned_process_stopped": success_stop,
        "restored_all_five": success_restore,
        "restore_code": restore_code,
        "epoch": time.time(),
    }
    (BASE / "watchdog_recovery.json").write_text(json.dumps(outcome, indent=2) + "\n")
    return 0 if success_restore else 4


if __name__ == "__main__":
    raise SystemExit(main())
