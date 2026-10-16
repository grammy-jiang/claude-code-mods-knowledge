#!/usr/bin/env python3
"""Run remaining Gemma research windows sequentially, never concurrently.

Will resume only after any existing owned maintenance window has completed
with Qwen verified restored. Each individual window still enforces the
original memory/Swap thresholds and restoration checks.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from run_p5_gemma_window import MaintenanceError, snapshot

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path.home() / "Models.noindex/benchmarks/pi-mods-skill-activation-20261017"
SUITE = ROOT / "evals/p5_pi_auto_12x3.json"


def pending(round_number: int) -> list[str]:
    data = json.loads(SUITE.read_text())
    cases = data["case_ids"]
    missing = []
    for name in cases:
        file = PRIVATE / "paired/gemma31" / name / f"trial-{round_number}/report.json"
        if not file.is_file():
            missing.append(name)
    return missing


def previous_window_safe() -> bool:
    all_windows = sorted(
        (PRIVATE / "gemma-windows").glob("round-*/window-*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not all_windows:
        return True
    recent = json.loads(all_windows[-1].read_text())
    return (
        recent.get("complete") is True
        and recent.get("qwen_restored") is True
        and recent.get("phase") == "complete"
    )


def healthy_to_switch() -> bool:
    try:
        s = snapshot()
    except (MaintenanceError, OSError, subprocess.TimeoutExpired):
        return False
    return (
        all(s["service_states"].values())
        and s["qwen_healthy"]
        and s["test_port_clear"]
        and s["active_qwen_clients"] == 0
        and s["memory_pressure"] >= 60
        and s["swap_mib"] <= 512
    )


def run_window(round_number: int, max_cases: int, wall_seconds: int) -> dict:
    script = ROOT / "scripts/run_p5_gemma_window.py"
    call = [
        sys.executable,
        str(script),
        "--round",
        str(round_number),
        "--max-cases",
        str(max_cases),
        "--wall-seconds",
        str(wall_seconds),
        "--execute",
    ]
    result = subprocess.run(  # noqa: S603 - exact pinned local maintenance script
        call,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=wall_seconds + 220,
    )
    try:
        data = json.loads(result.stdout.strip())
    except ValueError as exc:
        raise MaintenanceError("Maintenance window did not return sanitized JSON") from exc
    if (
        result.returncode
        or data.get("phase") != "complete"
        or data.get("qwen_restored") is not True
        or data.get("default_qwen_api_healthy") is not True
        or data.get("all_original_services_running") is not True
    ):
        raise MaintenanceError("Controlled window did not verify all original AI services")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=720)
    parser.add_argument("--max-windows", type=int, default=6)
    args = parser.parse_args()
    if not 30 <= args.wait_seconds <= 900 or not 1 <= args.max_windows <= 6:
        parser.error("Out-of-scope wait or maintenance window count")
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    file = PRIVATE / "gemma-sequential-status.json"
    s = {
        "state": "waiting_for_safe_window",
        "completed_windows": [],
        "remaining": {str(k): len(pending(k)) for k in (1, 2, 3)},
        "real_model_turns_planned": 36,
    }

    def save() -> None:
        tmp = file.with_suffix(".tmp")
        tmp.write_text(json.dumps(s, indent=2) + "\n")
        tmp.replace(file)
        file.chmod(0o600)

    save()
    if not args.execute:
        s["state"] = "dry_run"
        save()
        print(json.dumps(s))
        return 0

    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        if previous_window_safe() and healthy_to_switch():
            break
        time.sleep(3)
    else:
        s["state"] = "wait_timed_out_without_touching_services"
        save()
        print(json.dumps({"state": s["state"], "windows": 0}))
        return 2

    try:
        for round_number in (1, 2, 3):
            while pending(round_number):
                if len(s["completed_windows"]) >= args.max_windows:
                    s["state"] = "stopped_at_window_limit"
                    save()
                    print(json.dumps({"state": s["state"], "windows": len(s["completed_windows"])}))
                    return 2
                if not previous_window_safe() or not healthy_to_switch():
                    raise MaintenanceError("Original services or memory not healthy before window")
                before = len(pending(round_number))
                s["active_round"] = round_number
                s["state"] = "testing"
                save()
                result = run_window(round_number, min(6, before), 540)
                after = len(pending(round_number))
                s["remaining"] = {str(k): len(pending(k)) for k in (1, 2, 3)}
                s["completed_windows"].append(
                    {
                        "round": round_number,
                        "observed_new": before - after,
                        "rollback_verified": result["qwen_restored"],
                    }
                )
                if after >= before:
                    raise MaintenanceError(
                        "Maintenance produced no new real native model observations"
                    )
                s["state"] = "window_complete"
                s.pop("active_round", None)
                save()
        s["state"] = "all_36_observed"
        save()
        print(
            json.dumps(
                {
                    "state": s["state"],
                    "windows": len(s["completed_windows"]),
                    "remaining": s["remaining"],
                }
            )
        )
        return 0
    except (MaintenanceError, subprocess.TimeoutExpired) as exc:
        s["state"] = "paused_on_guard_or_restoration_issue"
        s["error_category"] = type(exc).__name__
        s.pop("active_round", None)
        save()
        print(
            json.dumps(
                {
                    "state": s["state"],
                    "windows": len(s["completed_windows"]),
                    "error_category": type(exc).__name__,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
