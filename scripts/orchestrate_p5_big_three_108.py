#!/usr/bin/env python3
"""Guarded real Mac M5 Max 3×12×3 Pi Agent native model evaluation.

Run in a detached macOS process, not as a shell background child. Each
independent six-turn local inference window has a second watchdog,
immediately restores the five previously loaded AI services and
independently verifies Qwen's original API before any next window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "evals/p5_big_three_auto_12x3.json"
PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-big-three-native-108-20261017"
AICTL = Path.home() / "Projects/strata-mac-lab/scripts/ai-services.sh"
SERVICES = (
    "com.grammy.qwen36-omlx",
    "local.whisper-server",
    "local.mlx-audio",
    "local.ollama",
    "local.comfyui",
)
MODELS = ("gpt-oss", "mistral", "heretic")
MODEL_IDS = {
    "gpt-oss": "gpt-oss-120b",
    "mistral": "mistral-small-4-119b",
    "heretic": "qwen35-122b-heretic",
}
CONTROLLER = ROOT / "scripts/p5_big_three_window_controller.py"
WATCHDOG = ROOT / "scripts/p5_big_three_window_watchdog.py"


class BigModelWindowError(RuntimeError):
    """Refuse unsafe service changes or mismatched immutable evidence."""


def manifest() -> dict:
    j = json.loads(PLAN.read_text())
    expected = hashlib.sha256((ROOT / j["source_file"]).read_bytes()).hexdigest()
    if (
        expected != j["source_sha256"]
        or j["repetitions"] != 3
        or len(j["case_ids"]) != len(set(j["case_ids"])) != 12
        or j["expected_total_model_trials"] != 108
        or {x["id"] for x in j["models"]} != set(MODEL_IDS.values())
    ):
        raise BigModelWindowError("Frozen original 12-case source or model identities changed")
    return j


def ordered_case_ids(round_no: int, ids: list[str]) -> list[str]:
    if round_no == 1:
        return ids
    if round_no == 2:
        return list(reversed(ids))
    if round_no == 3:
        return ids[4:8] + ids[8:12] + ids[:4]
    raise BigModelWindowError("Unexpected independent repetition index")


def windows() -> list[dict]:
    j = manifest()
    result = []
    for round_no in (1, 2, 3):
        ordered = ordered_case_ids(round_no, j["case_ids"])
        for part in (1, 2):
            for candidate in MODELS:
                result.append(
                    {
                        "candidate": candidate,
                        "trial": round_no,
                        "part": part,
                        "case_ids": ordered[(part - 1) * 6 : part * 6],
                        "source_sha256": j["source_sha256"],
                        "manifest_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
                    }
                )
    if len(result) != 18 or sum(len(w["case_ids"]) for w in result) != 108:
        raise BigModelWindowError("Window assignment does not cover 108 frozen attempts")
    return result


def window_dir(window: dict) -> Path:
    return (
        PRIVATE
        / "windows"
        / window["candidate"]
        / f"round-{window['trial']}"
        / f"part-{window['part']}"
    )


def _run(argv: list[str], *, timeout: int = 14) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - literal pre-validated local host commands
        argv,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
    )


def service_state() -> dict:
    p = _run([str(AICTL), "status"], timeout=14)
    if p.returncode:
        raise BigModelWindowError("Could not determine current five AI service states")
    return {name: name + " loaded state=running" in p.stdout for name in SERVICES}


def qwen_endpoint_healthy() -> bool:
    try:
        with urllib.request.urlopen(  # noqa: S310 - fixed loopback
            "http://127.0.0.1:18080/v1/models",
            timeout=4,
        ) as stream:
            response = json.load(stream)
        return any(x.get("id") == "qwen36-35b-a3b-mtp" for x in response.get("data", []))
    except (OSError, ValueError):
        return False


def test_endpoint_vacant() -> bool:
    try:
        with urllib.request.urlopen(  # noqa: S310 - fixed loopback
            "http://127.0.0.1:8011/v1/models",
            timeout=2,
        ):
            return False
    except (OSError, ValueError):
        return True


def swap_used_mib() -> float:
    p = _run(["/usr/sbin/sysctl", "-n", "vm.swapusage"], timeout=5)
    if p.returncode:
        raise BigModelWindowError("Swap telemetry not available")
    import re

    m = re.search(r"used\s*=\s*([0-9.]+)([MGT]?)", p.stdout)
    if not m:
        raise BigModelWindowError("Swap telemetry format not parseable")
    return float(m.group(1)) * {"": 1, "M": 1, "G": 1024, "T": 1048576}[m.group(2)]


def readiness() -> bool:
    states = service_state()
    if not all(states.values()) or not qwen_endpoint_healthy() or not test_endpoint_vacant():
        return False
    if swap_used_mib() > 1024:
        return False
    check = _run(
        ["/usr/sbin/lsof", "-nP", "-iTCP:18080", "-sTCP:ESTABLISHED"],
        timeout=6,
    )
    if len(check.stdout.splitlines()) > 1:
        return False
    return True


def safe_prior_state(window: dict) -> dict | None:
    directory = window_dir(window)
    file = directory / "live_state.json"
    if not file.is_file():
        if directory.exists():
            raise BigModelWindowError("Prior incomplete window directory exists")
        return None
    value = json.loads(file.read_text())
    if (
        value.get("candidate") != window["candidate"]
        or value.get("trial") != window["trial"]
        or value.get("window_part") != window["part"]
    ):
        raise BigModelWindowError("Inconsistent old model/round window identity")
    if not (
        value.get("phase") == "complete"
        and value.get("restore_confirmed") is True
        and value.get("fatal_error") is None
        and value.get("restore", {}).get("all_five_running") is True
        and value.get("restore", {}).get("qwen_api_healthy") is True
    ):
        raise BigModelWindowError("Unclean previous run, do not redo or replace it")
    models = value.get("models", [])
    if len(models) != 1 or models[0].get("model") != MODEL_IDS[window["candidate"]]:
        raise BigModelWindowError("Old model ID missing or wrong")
    if not models[0].get("ready") or models[0].get("stop_success") is not True:
        raise BigModelWindowError("Previous model did not load/stop properly")
    if len(models[0].get("cases", [])) != 6:
        raise BigModelWindowError("Incomplete old window; no automatic replay")
    return value


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def window_run(window: dict) -> dict:
    directory = window_dir(window)
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    directory.chmod(0o700)
    _write(directory / "window_config.json", window)
    for name, source in (
        ("maintenance_runner.py", CONTROLLER),
        ("restore_watchdog.py", WATCHDOG),
    ):
        if not source.is_file():
            raise BigModelWindowError("Native service watchdog/controller source missing")
        target = directory / name
        shutil.copyfile(source, target)
        target.chmod(0o600)
    dry = _run([sys.executable, str(directory / "maintenance_runner.py"), "--dry-run"])
    if dry.returncode:
        raise BigModelWindowError("Per-window configuration preflight failed")
    verified = json.loads(dry.stdout)
    if not verified.get("ready") or verified["case_ids"] != window["case_ids"]:
        raise BigModelWindowError("Per-window frozen prompt set diverged")
    with (directory / "controller.log").open("wb") as out:
        p = subprocess.Popen(  # noqa: S603 - dedicated, owned test-only Python file
            [sys.executable, str(directory / "maintenance_runner.py")],
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    try:
        with (directory / "watchdog.log").open("wb") as out:
            wd = subprocess.Popen(  # noqa: S603 - owned, separate watchdog session
                [sys.executable, str(directory / "restore_watchdog.py")],
                cwd=directory,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except Exception:
        # The model owner has a fully-populated restoration finally block.
        # Do not start another test window if watchdog fails.
        p.terminate()
        p.wait(timeout=180)
        raise
    try:
        rc = p.wait(timeout=1180)
    except subprocess.TimeoutExpired as e:
        p.terminate()
        try:
            rc = p.wait(timeout=180)
        except subprocess.TimeoutExpired:
            rc = None
        raise BigModelWindowError("Owned test window timed out; watchdog restores services") from e
    wd.wait(timeout=30)
    state = safe_prior_state(window)
    if state is None or rc != 0:
        raise BigModelWindowError("Actual window did not preserve trusted native QA result")
    return {
        "candidate": window["candidate"],
        "trial": window["trial"],
        "part": window["part"],
        "source_sha256": window["source_sha256"],
        "six_native_turns": len(state["models"][0]["cases"]),
        "model_ready": bool(state["models"][0]["ready"]),
        "model_stop_verified": state["models"][0]["stop_success"] is True,
        "all_five_original_services_restored": state["restore_confirmed"] is True,
        "load_seconds": state["models"][0].get("startup_s"),
        "raw_model_text_private": True,
    }


def campaign(max_windows: int) -> dict:
    PRIVATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    journal = PRIVATE / "campaign-progress.json"
    if journal.exists():
        raise BigModelWindowError("Existing campaign progress requires reconciliation")
    state = {
        "campaign": "P5-BIG-THREE-108-AUTO-SKILL",
        "status": "running",
        "started_epoch": time.time(),
        "expected_turns": 108,
        "observed_windows": [],
        "current_window": None,
        "original_service_rollbacks_verified": 0,
    }
    _write(journal, state)
    try:
        for w in windows()[:max_windows]:
            prev = safe_prior_state(w)
            if prev is not None:
                state["observed_windows"].append(
                    {
                        "candidate": w["candidate"],
                        "trial": w["trial"],
                        "part": w["part"],
                        "resume": "existing_original_evidence_verified",
                        "all_five_original_services_restored": True,
                    }
                )
                _write(journal, state)
                continue
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and not readiness():
                time.sleep(4)
            if not readiness():
                raise BigModelWindowError("Original Mac services busy or resource headroom unsafe")
            state["current_window"] = {k: w[k] for k in ("candidate", "trial", "part", "case_ids")}
            _write(journal, state)
            result = window_run(w)
            state["observed_windows"].append(result)
            state["original_service_rollbacks_verified"] += 1
            state["current_window"] = None
            _write(journal, state)
            time.sleep(3)
        state["status"] = "all_windows_complete" if max_windows == 18 else "intentionally_partial"
    except Exception as exc:
        state["status"] = "paused_on_unsafe_or_incomplete_window"
        state["blocker_category"] = type(exc).__name__
    finally:
        state["end_epoch"] = time.time()
        state["current_window"] = None if state["status"] != "running" else state["current_window"]
        _write(journal, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-windows", type=int, default=18)
    args = parser.parse_args()
    if not 1 <= args.max_windows <= 18:
        parser.error("Only 1..18 windows approved")
    planned = windows()
    if not args.execute:
        print(
            json.dumps(
                {
                    "ready": True,
                    "would_stop_services": False,
                    "model_windows": len(planned),
                    "frozen_turns": 108,
                    "window_size": 6,
                    "candidate_models": list(MODELS),
                    "rounds": 3,
                }
            )
        )
        return 0
    final = campaign(args.max_windows)
    print(
        json.dumps(
            {
                "status": final["status"],
                "completed_windows": len(final["observed_windows"]),
                "last_blocker": final.get("blocker_category"),
                "raw_user_model_text_exposed": False,
            }
        )
    )
    return 0 if final["status"] == "all_windows_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
