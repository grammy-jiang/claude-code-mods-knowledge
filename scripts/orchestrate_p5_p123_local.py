#!/usr/bin/env python3
"""Five previously tested Mac local models × 12 frozen P4 prompts × 3.

Safe, private, serial one-model service windows. Preserves the actual
original state of five AI LaunchDaemons instead of blindly restoring a
different state. Never changes user's model/Skill or other workloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from run_p5_p123_local_case import MODELS, PRIVATE, ROOT, approved_plan

HOME = Path.home()
OMLX = HOME / "Projects/strata-mac-lab/engine-recovery/venv/bin/omlx"
LLAMA = Path("/opt/homebrew/bin/llama-server")
AICTL = HOME / "Projects/strata-mac-lab/scripts/ai-services.sh"
WATCHDOG = ROOT / "scripts/watch_p5_p123_local.py"
RUNNER = ROOT / "scripts/run_p5_p123_local_case.py"
ALIASES = {
    "qwen": HOME / "Models.noindex/model-campaign/qwen36-35b-a3b-mtp",
    "gemma31": HOME / "Models.noindex/model-campaign/gemma4-31b-mtp",
    "gpt-oss": HOME / "Models.noindex/llama.cpp/gpt-oss-120b-GGUF/gpt-oss-120b-MXFP4.gguf",
    "mistral": HOME
    / "Models.noindex/huggingface/hub/models--mlx-community--Mistral-Small-4-119B-2603-4bit/snapshots/87b1249207734f029ec9dcefab80eabedfa6b812",
    "heretic": HOME
    / "Models.noindex/huggingface/hub/models--TheCluster--Qwen3.5-122B-A10B-Heretic-v2-MLX-mixed-3.8bit/snapshots/82028fce410a5f562c89c601033e9a2549331e4c",
}
SERVICES = (
    "com.grammy.qwen36-omlx",
    "local.whisper-server",
    "local.mlx-audio",
    "local.ollama",
    "local.comfyui",
)
ORDER = ("qwen", "gemma31", "gpt-oss", "mistral", "heretic")
_STOP = threading.Event()


class P5LocalWindowError(RuntimeError):
    """Unsafe/incomplete work cannot silently turn into an evaluated run."""


def _shell(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - owned, fixed local service probes
        cmd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=timeout,
    )


def snapshot_services() -> dict[str, bool]:
    p = _shell([str(AICTL), "status"], timeout=14)
    if p.returncode:
        raise P5LocalWindowError("Cannot determine original AI services")
    return {service: service + " loaded state=running" in p.stdout for service in SERVICES}


def memory_sample(pid: int | None = None) -> dict:
    free = _shell(["/usr/sbin/sysctl", "-n", "kern.memorystatus_level"], timeout=5)
    swap = _shell(["/usr/sbin/sysctl", "-n", "vm.swapusage"], timeout=5)
    import re

    match = re.search(r"used\s*=\s*([0-9.]+)([MGT]?)", swap.stdout)
    if free.returncode or swap.returncode or not match:
        raise P5LocalWindowError("Mac memory telemetry unavailable")
    amount = float(match.group(1)) * {"": 1, "M": 1, "G": 1024, "T": 1048576}[match.group(2)]
    rss = None
    if pid is not None and pid > 1:
        state = _shell(["/bin/ps", "-p", str(pid), "-o", "rss="], timeout=5)
        try:
            rss = round(int(state.stdout.strip()) / 1024, 2)
        except (TypeError, ValueError):
            pass
    return {
        "epoch": time.time(),
        "macos_memorystatus_level": int(free.stdout.strip()),
        "swap_mib": round(amount, 2),
        "test_model_rss_mib": rss,
    }


def endpoint(port: int) -> set[str]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2.1) as stream:  # noqa: S310
            result = json.load(stream)
        return {
            str(item["id"])
            for item in result.get("data", [])
            if isinstance(item, dict) and "id" in item
        }
    except (OSError, ValueError):
        return set()


def batches() -> list[dict]:
    p = approved_plan()
    cases = list(p["case_ids"])
    results = []
    for trial in (1, 2, 3):
        ordered = (
            cases
            if trial == 1
            else list(reversed(cases))
            if trial == 2
            else cases[4:8] + cases[8:12] + cases[:4]
        )
        for part in (1, 2):
            for candidate in ORDER:
                results.append(
                    {
                        "candidate": candidate,
                        "trial": trial,
                        "part": part,
                        "cases": ordered[(part - 1) * 6 : part * 6],
                        "frozen_source_sha256": p["source_sha256"],
                        "candidate_skill_sha256": p["candidate_skill_sha256"],
                    }
                )
    if len(results) != 30 or sum(len(b["cases"]) for b in results) != 180:
        raise P5LocalWindowError("Incorrect 180-turn frozen batch matrix")
    return results


def window_dir(group: dict) -> Path:
    return (
        PRIVATE
        / "windows"
        / group["candidate"]
        / f"round-{group['trial']}"
        / f"part-{group['part']}"
    )


def persist(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    tmp.chmod(0o600)
    tmp.replace(path)


def start_cmd(candidate: str, model_dir: Path, home: Path) -> list[str]:
    if candidate == "gpt-oss":
        if not LLAMA.is_file() or not model_dir.is_file():
            raise P5LocalWindowError("Missing llama.cpp model")
        return [
            str(LLAMA),
            "--model",
            str(model_dir),
            "--alias",
            MODELS[candidate][1],
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
            "--parallel",
            "1",
            "--ctx-size",
            "16384",
            "--threads",
            "6",
            "--n-gpu-layers",
            "999",
            "--flash-attn",
            "on",
            "--reasoning-effort",
            "medium",
            "--jinja",
            "--no-webui",
        ]
    if not OMLX.is_file() or not model_dir.is_dir() or not (model_dir / "config.json").is_file():
        raise P5LocalWindowError("Missing local oMLX model or config")
    d = home / "models"
    d.mkdir(mode=0o700, parents=True, exist_ok=False)
    symlink = d / MODELS[candidate][1]
    symlink.symlink_to(model_dir, target_is_directory=True)
    settings = home / "settings"
    settings.mkdir(mode=0o700, exist_ok=False)
    meta = {
        "version": 1,
        "models": {
            MODELS[candidate][1]: {
                "mtp_enabled": False,
                "enable_thinking": False,
                "max_context_window": MODELS[candidate][4],
                "moe_expert_offload_enabled": False,
            }
        },
    }
    persist(settings / "model_settings.json", meta)
    return [
        str(OMLX),
        "serve",
        "--model-dir",
        str(d),
        "--base-path",
        str(settings),
        "--host",
        "127.0.0.1",
        "--port",
        "8011",
        "--max-concurrent-requests",
        "1",
        "--memory-guard",
        "off",
        "--no-hf-cache",
        "--no-cache",
        "--log-level",
        "info",
    ]


def stop_child(p: subprocess.Popen | None) -> bool:
    if p is None or p.poll() is not None:
        return True
    # A retained Popen handle confirms PID ownership; never signal unrelated processes.
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    try:
        p.wait(timeout=14)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        try:
            p.wait(timeout=7)
        except subprocess.TimeoutExpired:
            return False
    return p.poll() is not None


def run_window(group: dict, original: dict, baseline_swap_mib: float) -> dict:
    dirname = window_dir(group)
    if dirname.exists():
        raise P5LocalWindowError("Immutable window already exists; reconcile first")
    dirname.mkdir(parents=True, mode=0o700)
    dirname.chmod(0o700)
    statefile = dirname / "active-model-state.json"
    state = {
        "phase": "preflight",
        "candidate": group["candidate"],
        "trial": group["trial"],
        "part": group["part"],
        "case_ids": group["cases"],
        "started_epoch": time.time(),
        "model_pid": None,
        "native_cases": [],
        "original_services_touched": False,
        "reference_service_state": original,
    }
    persist(statefile, state)
    if endpoint(8011) or snapshot_services() != original:
        raise P5LocalWindowError("Test port busy or original service state changed")
    metrics = memory_sample()
    if metrics["macos_memorystatus_level"] < 14 or metrics["swap_mib"] > baseline_swap_mib + 2048:
        raise P5LocalWindowError("Resource headroom is too low for a new large-model window")
    process = None
    watchdog = None
    active_pi = None
    samples: list[dict] = []

    def sampler() -> None:
        while not _STOP.wait(2):
            try:
                sample = memory_sample(process.pid if process and process.poll() is None else None)
                samples.append(sample)
                if (
                    sample["swap_mib"] > baseline_swap_mib + 4096
                    or sample["macos_memorystatus_level"] < 8
                ):
                    state["resource_emergency"] = True
                    # Signal only test-owned processes; controller handles exit.
                    _STOP.set()
                    stop_child(active_pi)
                    stop_child(process)
            except Exception:
                state["resource_sensor_failure"] = True
                _STOP.set()
                stop_child(active_pi)
                stop_child(process)

    try:
        cmd = start_cmd(group["candidate"], ALIASES[group["candidate"]], dirname)
        state["phase"] = "loading"
        persist(statefile, state)
        with (dirname / "model.log").open("wb") as log:
            process = subprocess.Popen(  # noqa: S603 - validated local model executable
                cmd,
                cwd=dirname,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
                env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
            )
        state["model_pid"] = process.pid
        persist(statefile, state)
        with (dirname / "watchdog.log").open("wb") as log:
            watchdog = subprocess.Popen(  # noqa: S603 - independent test-only guard
                [
                    sys.executable,
                    str(WATCHDOG),
                    "--state",
                    str(statefile),
                    "--owner-pid",
                    str(os.getpid()),
                ],
                cwd=dirname,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        _STOP.clear()
        monitor = threading.Thread(target=sampler, daemon=True)
        monitor.start()
        start = time.monotonic()
        while time.monotonic() - start < 185:
            if _STOP.is_set():
                raise P5LocalWindowError("Mac resource monitor requested model stop")
            if process.poll() is not None:
                raise P5LocalWindowError("Test-owned model process exited before API readiness")
            if MODELS[group["candidate"]][1] in endpoint(8011):
                break
            time.sleep(2)
        else:
            raise P5LocalWindowError("Model startup timeout")
        state["phase"] = "running"
        state["model_load_seconds"] = round(time.monotonic() - start, 2)
        persist(statefile, state)
        for caseid in group["cases"]:
            if _STOP.is_set():
                raise P5LocalWindowError("Mac resource emergency during native QA")
            state["active_case"] = caseid
            persist(statefile, state)
            output = dirname / f"case-{caseid}.log"
            started = time.monotonic()
            with output.open("wb") as log:
                p = subprocess.Popen(  # noqa: S603 - fixed owned native Pi runner
                    [
                        sys.executable,
                        str(RUNNER),
                        "--candidate",
                        group["candidate"],
                        "--case",
                        caseid,
                        "--trial",
                        str(group["trial"]),
                    ],
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                active_pi = p
                try:
                    rc = p.wait(timeout=123)
                except subprocess.TimeoutExpired:
                    stop_child(p)
                    rc = None
            active_pi = None
            resultpath = (
                PRIVATE
                / "paired"
                / group["candidate"]
                / caseid
                / f"trial-{group['trial']}"
                / "report.json"
            )
            if not resultpath.is_file():
                raise P5LocalWindowError("Native model call lacks immutable result; refuse replay")
            record = json.loads(resultpath.read_text())
            if (
                record.get("case_id") != caseid
                or record.get("candidate") != group["candidate"]
                or record.get("trial") != group["trial"]
                or record.get("model_calls") != 1
                or record.get("raw_output_exposed") is not False
            ):
                raise P5LocalWindowError("Native result provenance or model call count missing")
            state["native_cases"].append(
                {
                    "case_id": caseid,
                    "runner_exit": rc,
                    "duration": round(time.monotonic() - started, 2),
                    "native_result_sha256": hashlib.sha256(resultpath.read_bytes()).hexdigest(),
                    "raw_model_text_exposed": False,
                }
            )
            state["active_case"] = None
            persist(statefile, state)
        state["phase"] = "unloading"
        persist(statefile, state)
    finally:
        clean = stop_child(process)
        state["model_pid"] = None
        state["test_model_unloaded"] = clean
        _STOP.set()
        if watchdog:
            stop_child(watchdog)
        final = memory_sample()
        samples.append(final)
        persist(dirname / "resource-samples.json", {"samples": samples})
        state["min_macos_memorystatus_level"] = min(
            (x["macos_memorystatus_level"] for x in samples), default=None
        )
        state["peak_swap_mib"] = max((x["swap_mib"] for x in samples), default=None)
        state["peak_model_rss_mib"] = max(
            (x["test_model_rss_mib"] for x in samples if x["test_model_rss_mib"] is not None),
            default=None,
        )
        state["original_services_preserved"] = snapshot_services() == original
        state["port_8011_closed"] = not bool(endpoint(8011))
        state["ended_epoch"] = time.time()
        state["phase"] = "completed_and_unloaded"
        persist(statefile, state)
    if not (
        state["test_model_unloaded"] is True
        and state["original_services_preserved"] is True
        and state["port_8011_closed"] is True
        and len(state["native_cases"]) == 6
        and not state.get("resource_emergency")
    ):
        raise P5LocalWindowError(
            "Model window failed model/session cleanup or baseline verification"
        )
    return {
        "candidate": group["candidate"],
        "trial": group["trial"],
        "part": group["part"],
        "native_cases": 6,
        "original_user_services_preserved": True,
        "temporary_model_stopped": True,
        "port_8011_closed": True,
        "model_load_seconds": state.get("model_load_seconds"),
        "minimum_memorystatus": state["min_macos_memorystatus_level"],
        "peak_swap_mib": state["peak_swap_mib"],
        "peak_model_rss_mib": state["peak_model_rss_mib"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-windows", type=int, default=30)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    jobs = batches()
    if not 1 <= args.max_windows <= 30:
        parser.error("Expected 1..30 windows")
    if not args.execute:
        print(
            json.dumps(
                {
                    "ready": True,
                    "local_models": len(MODELS),
                    "planned_native_turns": 180,
                    "windows": 30,
                    "changes_existing_services": False,
                }
            )
        )
        return 0
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
    journal = PRIVATE / "local-campaign.json"
    if journal.exists():
        if not args.resume:
            parser.error("Original campaign exists: --resume required")
        state = json.loads(journal.read_text())
        if state.get("status") not in ("intentionally_partial", "paused"):
            parser.error("Existing campaign not safely resumable")
    else:
        if args.resume:
            parser.error("Cannot resume a missing campaign")
        baseline = snapshot_services()
        state = {
            "status": "running",
            "started_epoch": time.time(),
            "original_services": baseline,
            "baseline_swap_mib": memory_sample()["swap_mib"],
            "verified_windows": [],
            "current": None,
        }
    state["status"] = "running"
    persist(journal, state)
    try:
        for i, task in enumerate(jobs[: args.max_windows]):
            if i < len(state["verified_windows"]):
                prior = state["verified_windows"][i]
                if (prior["candidate"], prior["trial"], prior["part"]) != (
                    task["candidate"],
                    task["trial"],
                    task["part"],
                ):
                    raise P5LocalWindowError("Cannot accept mismatched prior native window")
                continue
            if snapshot_services() != state["original_services"] or endpoint(8011):
                raise P5LocalWindowError("Original AI service workload changed; pause safely")
            state["current"] = {k: task[k] for k in ("candidate", "trial", "part", "cases")}
            persist(journal, state)
            result = run_window(task, state["original_services"], state["baseline_swap_mib"])
            state["verified_windows"].append(result)
            state["current"] = None
            persist(journal, state)
            time.sleep(2)
        state["status"] = (
            "all_180_original_turns_observed" if args.max_windows == 30 else "intentionally_partial"
        )
    except Exception as exc:
        state["status"] = "paused"
        state["blocker_class"] = type(exc).__name__
    finally:
        state["current"] = None
        state["end_epoch"] = time.time()
        persist(journal, state)
    print(
        json.dumps(
            {
                "status": state["status"],
                "verified_windows": len(state["verified_windows"]),
                "native_turns": 6 * len(state["verified_windows"]),
                "all_original_user_services_untouched": True,
            }
        )
    )
    return (
        0 if state["status"] in ("all_180_original_turns_observed", "intentionally_partial") else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
