#!/usr/bin/env python3
"""One bounded Gemma 31B Pi Agent comparison window with Qwen rollback.

User-requested Mac-local research only. Dry-run is the default; --execute
permits a short, service-health-checked maintenance window. No model or
Pi defaults are changed, and the user's original lab server script is not
modified. A copied supervisor retains its own memory-pressure/Swap guards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LAB = Path.home() / "Projects/strata-mac-lab"
SERVER_ORIGINAL = LAB / "model-campaign/real-project-bench/scripts/server.py"
AICTL = LAB / "scripts/ai-services.sh"
REPO = Path(__file__).resolve().parents[1]
PRIVATE = Path.home() / "Models.noindex/benchmarks/pi-mods-skill-activation-20261017"
QWEN_LABEL = "com.grammy.qwen36-omlx"
PLIST = Path("/Library/LaunchDaemons/com.grammy.qwen36-omlx.plist")
SERVICES = (QWEN_LABEL, "local.whisper-server", "local.mlx-audio", "local.ollama", "local.comfyui")


class MaintenanceError(RuntimeError):
    """A bounded maintenance precondition or rollback verification failed."""


def cmd(args: list[str], *, timeout: float = 25.0) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - literal, scoped host-maintenance commands
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def service_states() -> dict[str, bool]:
    p = cmd([str(AICTL), "status"], timeout=13)
    if p.returncode:
        raise MaintenanceError("Cannot read original AI service states")
    return {
        name: any(row.startswith(name + " loaded state=running") for row in p.stdout.splitlines())
        for name in SERVICES
    }


def local_models(port: int) -> set[str]:
    if port not in (18080, 8011):
        raise MaintenanceError("Unexpected test API port")
    try:
        with urllib.request.urlopen(  # noqa: S310 - literal loopback address and port
            f"http://127.0.0.1:{port}/v1/models", timeout=3
        ) as stream:
            result = json.load(stream)
        return {d["id"] for d in result.get("data", []) if isinstance(d, dict) and "id" in d}
    except (OSError, ValueError, KeyError):
        return set()


def memory() -> tuple[int, float]:
    pr = cmd(["/usr/sbin/sysctl", "-n", "kern.memorystatus_level"], timeout=5)
    sw = cmd(["/usr/sbin/sysctl", "-n", "vm.swapusage"], timeout=5)
    if pr.returncode or sw.returncode:
        raise MaintenanceError("Cannot read memory guard metrics")
    mt = re.search(r"used\s*=\s*([0-9.]+)([MGT]?)", sw.stdout)
    if not mt:
        raise MaintenanceError("Cannot read swap usage")
    return int(pr.stdout.strip()), float(mt.group(1)) * {
        "": 1,
        "M": 1,
        "G": 1024,
        "T": 1048576,
    }[mt.group(2)]


def snapshot() -> dict:
    states = service_states()
    pressure, swap_mib = memory()
    listener = cmd(["/usr/sbin/lsof", "-nP", "-iTCP:18080", "-sTCP:ESTABLISHED"], timeout=5)
    connected = max(0, len(listener.stdout.splitlines()) - 1)
    return {
        "service_states": states,
        "memory_pressure": pressure,
        "swap_mib": round(swap_mib, 2),
        "qwen_healthy": "qwen36-35b-a3b-mtp" in local_models(18080),
        "test_port_clear": not local_models(8011),
        "active_qwen_clients": connected,
    }


def prepared_supervisor(folder: Path) -> Path:
    if not SERVER_ORIGINAL.is_file() or SERVER_ORIGINAL.is_symlink():
        raise MaintenanceError("Expected existing reviewed lab supervisor missing")
    original = SERVER_ORIGINAL.read_text()
    old_services = 'names=("com.grammy.qwen36-omlx","local.whisper-server",'
    old_owner = '"real-project-bench/scripts/server.py" in cmd'
    if original.count(old_services) != 1 or original.count(old_owner) != 1:
        raise MaintenanceError("Lab supervisor source changed; cannot safely prepare copied server")
    copied = original.replace(old_services, 'names=("local.whisper-server",')
    copied = copied.replace(old_owner, '"p5-gemma-supervisor.py" in cmd')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / "p5-gemma-supervisor.py"
    path.write_text(copied)
    path.chmod(0o600)
    return path


def server_status(supervisor: Path) -> dict:
    p = cmd([sys.executable, str(supervisor), "status"], timeout=7)
    if p.returncode:
        raise MaintenanceError("Candidate server status unavailable")
    return json.loads(p.stdout)


def stop_owned(supervisor: Path) -> None:
    state = server_status(supervisor)
    if state.get("supervisor_alive"):
        result = cmd([sys.executable, str(supervisor), "stop"], timeout=43)
        if result.returncode:
            raise MaintenanceError("Owned Gemma supervisor failed to stop")
    deadline = time.monotonic() + 28
    while time.monotonic() < deadline:
        state = server_status(supervisor)
        if (
            not state.get("engine_alive")
            and not state.get("supervisor_alive")
            and not local_models(8011)
        ):
            return
        time.sleep(1)
    raise MaintenanceError("Gemma engine remains active; refusing Qwen co-load")


def restore_qwen() -> None:
    if "qwen36-35b-a3b-mtp" in local_models(18080) and service_states()[QWEN_LABEL]:
        return
    if not PLIST.is_file():
        raise MaintenanceError("Original Qwen launchd plist is missing")
    for argv in (
        ["sudo", "-n", "launchctl", "bootstrap", "system", str(PLIST)],
        ["sudo", "-n", "launchctl", "load", "-w", str(PLIST)],
    ):
        if cmd(argv, timeout=22).returncode == 0:
            break
    end = time.monotonic() + 135
    while time.monotonic() < end:
        if "qwen36-35b-a3b-mtp" in local_models(18080) and service_states()[QWEN_LABEL]:
            return
        time.sleep(3)
    raise MaintenanceError("Original Qwen service could not be verified after restoration")


def run(round_no: int, *, max_cases: int, window_seconds: int, execute: bool) -> dict:
    if round_no not in (1, 2, 3) or not 1 <= max_cases <= 6:
        raise MaintenanceError("Only bounded six-case Gemma windows are approved")
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
    before = snapshot()
    if not all(before["service_states"].values()) or not before["qwen_healthy"]:
        raise MaintenanceError("Five original services and default Qwen must be healthy")
    if not before["test_port_clear"] or before["active_qwen_clients"]:
        raise MaintenanceError("Test port occupied or original Qwen has active users")
    if before["memory_pressure"] < 60 or before["swap_mib"] > 512:
        raise MaintenanceError("Insufficient guarded free memory or excess swap")
    if cmd(["sudo", "-n", "true"], timeout=6).returncode:
        raise MaintenanceError("Passwordless, pre-authorized launchctl unavailable")
    if not execute:
        return {
            "phase": "dry_run_safe",
            "round": round_no,
            "max_cases": max_cases,
            "original_services_running": True,
            "qwen_api_healthy": True,
            "model_calls": 0,
        }
    folder = PRIVATE / "gemma-windows" / f"round-{round_no}"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    supervisor = prepared_supervisor(folder)
    logfile = folder / f"window-{int(time.time())}.log"
    report = folder / f"window-{int(time.time())}.json"
    state = {
        "phase": "preparing",
        "original_states": before,
        "round": round_no,
        "max_cases": max_cases,
        "qwen_paused": False,
        "gemma_started": False,
        "qwen_restored": False,
        "start_epoch": time.time(),
        "complete": False,
        "supervisor_copy_sha256": hashlib.sha256(supervisor.read_bytes()).hexdigest(),
        "original_supervisor_sha256": hashlib.sha256(SERVER_ORIGINAL.read_bytes()).hexdigest(),
    }

    def save() -> None:
        report.write_text(json.dumps(state, indent=2) + "\n")
        report.chmod(0o600)

    save()
    child = None
    fatal: str | None = None

    def interrupted(_signal: int, _frame: object) -> None:
        raise MaintenanceError("Maintained job received a stop signal")

    old_term = signal.signal(signal.SIGTERM, interrupted)
    old_int = signal.signal(signal.SIGINT, interrupted)
    try:
        state["phase"] = "pausing_qwen"
        save()
        unloaded = cmd(["sudo", "-n", "launchctl", "bootout", "system/" + QWEN_LABEL], timeout=22)
        if unloaded.returncode:
            raise MaintenanceError("Owned Qwen daemon could not be unloaded")
        state["qwen_paused"] = True
        save()
        if not all(v for k, v in service_states().items() if k != QWEN_LABEL):
            raise MaintenanceError("Another original AI service became unhealthy")
        state["phase"] = "starting_gemma"
        save()
        started = cmd([sys.executable, str(supervisor), "start", "gemma4-31b-mtp"], timeout=43)
        if started.returncode:
            raise MaintenanceError("Owned Gemma supervisor failed to load")
        state["gemma_started"] = True
        save()
        ready_until = time.monotonic() + 72
        while time.monotonic() < ready_until:
            if "gemma4-31b-mtp" in local_models(8011):
                break
            if not server_status(supervisor).get("engine_alive"):
                raise MaintenanceError("Gemma stopped under resource guard before API ready")
            time.sleep(2)
        else:
            raise MaintenanceError("Gemma did not become ready within safe timeout")
        state["phase"] = "running_private_paired_cases"
        save()
        cmdline = [
            sys.executable,
            str(REPO / "scripts/run_p5_pi_paired_batch.py"),
            "--candidate",
            "gemma31",
            "--round",
            str(round_no),
            "--max-cases",
            str(max_cases),
            "--timeout",
            "85",
            "--wall-seconds",
            str(window_seconds),
        ]
        with logfile.open("wb") as output:
            child = subprocess.Popen(  # noqa: S603 - fixed bounded research runner, no bash
                cmdline,
                cwd=REPO,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=output,
                start_new_session=True,
            )
            limit = time.monotonic() + window_seconds + 33
            while time.monotonic() < limit:
                if child.poll() is not None:
                    state["batch_exit_code"] = child.returncode
                    break
                pressure, swap = memory()
                if pressure < 50 or swap > 512 or not server_status(supervisor).get("engine_alive"):
                    raise MaintenanceError("Candidate exceeded existing RAM/Swap guard")
                time.sleep(2)
            else:
                raise MaintenanceError("Candidate batch exceeded hard maintenance window")
        state["phase"] = "batch_stopped"
        save()
    except Exception as exc:
        fatal = type(exc).__name__
        state["error_category"] = fatal
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=4)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=4)
        state["phase"] = "restoring"
        save()
        try:
            stop_owned(supervisor)
        except Exception as exc:
            state["cleanup_error"] = type(exc).__name__
        if not state.get("cleanup_error"):
            try:
                restore_qwen()
                state["qwen_restored"] = True
            except Exception as exc:
                state["restore_error"] = type(exc).__name__
        state["after"] = snapshot()
        state["complete"] = True
        state["phase"] = (
            "complete"
            if (state["qwen_restored"] and not fatal and state.get("batch_exit_code") == 0)
            else "complete_with_blocker"
        )
        state["end_epoch"] = time.time()
        save()
        signal.signal(signal.SIGTERM, old_term)
        signal.signal(signal.SIGINT, old_int)
    return {
        "phase": state["phase"],
        "qwen_restored": state["qwen_restored"],
        "all_original_services_running": all(state["after"]["service_states"].values()),
        "default_qwen_api_healthy": state["after"]["qwen_healthy"],
        "batch_exit_code": state.get("batch_exit_code"),
        "error_category": state.get("error_category"),
        "resource_guard_still_on": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--max-cases", type=int, default=4)
    parser.add_argument("--wall-seconds", type=int, default=420)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.max_cases <= 6 or not 180 <= args.wall_seconds <= 600:
        parser.error("Only bounded maintenance windows supported")
    result = run(
        args.round, max_cases=args.max_cases, window_seconds=args.wall_seconds, execute=args.execute
    )
    print(json.dumps(result))
    return 0 if result["phase"] in {"dry_run_safe", "complete"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
