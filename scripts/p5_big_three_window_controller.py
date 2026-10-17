# ruff: noqa: S603
#!/usr/bin/env python3
"""Three large Mac models, bounded offline-only Pi Agent 4-case research.

Stop ONLY five user-authorized AI inference LaunchDaemons. Samples unified
memory-pressure/swap and model RSS; no percent-pressure kill switch;
only a 4 GiB swap emergency ceiling and native OS safety constraints remain. No model
downloads, no global Pi model or installed Skill changes.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
PRIVATE = pathlib.Path.home() / "Models.noindex/benchmarks/p5-big-three-native-108-20261017"
AICTL = pathlib.Path.home() / "Projects/strata-mac-lab/scripts/ai-services.sh"
OMLX = pathlib.Path.home() / "Projects/strata-mac-lab/engine-recovery/venv/bin/omlx"
LLAMA = pathlib.Path("/opt/homebrew/bin/llama-server")
HUB = pathlib.Path.home() / "Models.noindex/huggingface/hub"
PROJ = pathlib.Path.home() / "Projects/claude-code-mods-knowledge-p5-big-three-108-20261017"
SKILL = pathlib.Path.home() / ".agents/skills/claude-code-mods-development"
SCOPE = PROJ / "scripts/p5_pi_scope_guard.mjs"
STATE = BASE / "live_state.json"
LABELS = (
    "com.grammy.qwen36-omlx",
    "local.whisper-server",
    "local.mlx-audio",
    "local.ollama",
    "local.comfyui",
)
MODELS = (
    (
        "gpt-oss-120b",
        "llama",
        pathlib.Path.home() / "Models.noindex/llama.cpp/gpt-oss-120b-GGUF/gpt-oss-120b-MXFP4.gguf",
        True,
    ),
    (
        "mistral-small-4-119b",
        "omlx",
        HUB
        / "models--mlx-community--Mistral-Small-4-119B-2603-4bit/snapshots/87b1249207734f029ec9dcefab80eabedfa6b812",
        False,
    ),
    (
        "qwen35-122b-heretic",
        "omlx",
        HUB
        / "models--TheCluster--Qwen3.5-122B-A10B-Heretic-v2-MLX-mixed-3.8bit/snapshots/82028fce410a5f562c89c601033e9a2549331e4c",
        False,
    ),
)
WINDOW = (
    json.loads((BASE / "window_config.json").read_text())
    if (BASE / "window_config.json").exists()
    else {}
)
CANDIDATE = WINDOW.get("candidate")
TRIAL = WINDOW.get("trial")
CASES = tuple(WINDOW.get("case_ids", []))
MODEL_KEYS = {
    "gpt-oss": "gpt-oss-120b",
    "mistral": "mistral-small-4-119b",
    "heretic": "qwen35-122b-heretic",
}
SKILL_SHA = "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"
ENVIRON = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "NO_PROXY": "127.0.0.1,localhost",
}
state = {
    "phase": "preflight",
    "controller_pid": os.getpid(),
    "started_epoch": time.time(),
    "experiment": "big-three-108-frozen-window",
    "candidate": CANDIDATE,
    "trial": TRIAL,
    "window_part": WINDOW.get("part"),
    "frozen_case_ids": list(CASES),
    "source_sha256": WINDOW.get("source_sha256"),
    "context_window": 16384,
    "per_turn_output_token_cap": 6144,
    "custom_memory_percent_abort_disabled": True,
    "isolated_omlx_memory_guard": "off",
    "emergency_swap_limit_mib": 4096,
    "original_state": None,
    "services_stopped": False,
    "active_model": None,
    "model_pid": None,
    "models": [],
    "restore_confirmed": False,
}
stop_signal = threading.Event()
danger = threading.Event()
samples = []
model_proc = None
pi_proc = None
monitor_thread = None
state_lock = threading.Lock()


def write_state() -> None:
    with state_lock:
        temp = STATE.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2) + "\n")
        os.replace(temp, STATE)


def run(argv: list[str], timeout: int = 12) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL
    )


def service_states() -> dict:
    r = run([str(AICTL), "status"], timeout=14)
    if r.returncode != 0:
        raise RuntimeError("AI_SERVICE_STATUS_FAILED")
    return {name: (name + " loaded state=running" in r.stdout) for name in LABELS}


def endpoint(port: int) -> set[str]:
    if port not in (18080, 8011):
        raise RuntimeError("INVALID_LOCAL_PORT")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2.3) as r:
            j = json.load(r)
        return {str(d["id"]) for d in j.get("data", []) if isinstance(d, dict) and "id" in d}
    except (OSError, ValueError):
        return set()


def metrics() -> dict:
    a = run(["/usr/sbin/sysctl", "-n", "kern.memorystatus_level"], timeout=5)
    b = run(["/usr/sbin/sysctl", "-n", "vm.swapusage"], timeout=5)
    if a.returncode or b.returncode:
        raise RuntimeError("RESOURCE_SENSOR_FAILED")
    match = re.search(r"used\s*=\s*([0-9.]+)([MGT]?)", b.stdout)
    if not match:
        raise RuntimeError("INVALID_SWAP_REPORT")
    swap = float(match.group(1)) * {"M": 1, "G": 1024, "T": 1048576, "": 1}[match.group(2)]
    rss = None
    if model_proc and model_proc.poll() is None:
        p = run(["/bin/ps", "-p", str(model_proc.pid), "-o", "rss="], timeout=5)
        try:
            rss = round(int(p.stdout.strip()) / 1024, 1)
        except (ValueError, TypeError):
            pass
    return {
        "epoch": time.time(),
        "memory_pressure_pct": int(a.stdout.strip()),
        "swap_mib": round(swap, 2),
        "model_rss_mib": rss,
    }


def process_stop(p: subprocess.Popen | None, expected: str) -> bool:
    if p is None or p.poll() is not None:
        return True
    # A currently live direct subprocess.Popen handle is sufficient to
    # prove ownership: no numeric PID can be reused while this child lives.
    # The separate watchdog has no Popen handle, so it DOES verify ps owner.
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    try:
        p.wait(timeout=13)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        try:
            p.wait(timeout=6)
        except subprocess.TimeoutExpired:
            return False
    return p.poll() is not None


def resource_monitor() -> None:
    while not stop_signal.is_set():
        try:
            item = metrics()
            item["model"] = state.get("active_model")
            samples.append(item)
            # User explicitly disabled the artificial 50% memory-free gate.
            # Record system pressure without terminating for any percent.
            # Emergency fallback only if actual disk swap exceeds 4 GiB.
            if item["swap_mib"] > 4096:
                danger.set()
                state["resource_guard_triggered"] = True
                # Stop just our owned research processes, not any user service.
                if pi_proc:
                    process_stop(pi_proc, "/pi")
                if model_proc:
                    process_stop(
                        model_proc,
                        "llama-server" if state.get("active_model") == "gpt-oss-120b" else "/omlx",
                    )
        except Exception:
            state["resource_sensor_error"] = True
            danger.set()
            if pi_proc:
                process_stop(pi_proc, "/pi")
            if model_proc:
                process_stop(
                    model_proc,
                    "llama-server" if state.get("active_model") == "gpt-oss-120b" else "/omlx",
                )
        stop_signal.wait(2)


def prepare_model(alias: str, engine: str, weights: pathlib.Path, reasoning: bool) -> list[str]:
    if engine == "llama":
        assert LLAMA.is_file() and weights.is_file()
        return [
            str(LLAMA),
            "--model",
            str(weights),
            "--alias",
            alias,
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
    assert OMLX.is_file() and weights.is_dir() and (weights / "config.json").is_file()
    root = PRIVATE / "server" / alias
    modelset = root / "modelset"
    prefs = root / "settings"
    modelset.mkdir(parents=True, exist_ok=True)
    prefs.mkdir(parents=True, exist_ok=True)
    pointer = modelset / alias
    if pointer.exists() or pointer.is_symlink():
        pointer.unlink()
    pointer.symlink_to(weights, target_is_directory=True)
    conf = {
        "version": 1,
        "models": {
            alias: {
                "mtp_enabled": False,
                "enable_thinking": False,
                "max_context_window": 16384,
                "moe_expert_offload_enabled": False,
            }
        },
    }
    (prefs / "model_settings.json").write_text(json.dumps(conf, indent=2) + "\n")
    return [
        str(OMLX),
        "serve",
        "--model-dir",
        str(modelset),
        "--base-path",
        str(prefs),
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


def agent_config(alias: str, reasoning: bool) -> pathlib.Path:
    root = PRIVATE / "agents" / alias
    root.mkdir(parents=True, exist_ok=True)
    info = {
        "providers": {
            "p5-large": {
                "baseUrl": "http://127.0.0.1:8011/v1",
                "api": "openai-completions",
                "apiKey": "PRIVATE_LOCAL_LOOPBACK_ONLY",
                "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": reasoning},
                "models": [
                    {
                        "id": alias,
                        "name": "P5 local big model " + alias,
                        "reasoning": reasoning,
                        "input": ["text"],
                        "contextWindow": 16384,
                        "maxTokens": 6144,
                    }
                ],
            }
        }
    }
    (root / "models.json").write_text(json.dumps(info, indent=2) + "\n")
    (root / "settings.json").write_text(
        json.dumps(
            {
                "defaultProvider": "p5-large",
                "defaultModel": alias,
                "defaultThinkingLevel": "medium" if reasoning else "off",
            },
            indent=2,
        )
        + "\n"
    )
    for f in root.iterdir():
        f.chmod(0o600)
    return root


def smoke_case(alias: str, reasoning: bool, case: dict, agent_dir: pathlib.Path) -> dict:
    global pi_proc
    cid = case["id"]
    dest = PRIVATE / "paired" / CANDIDATE / cid / f"trial-{TRIAL}"
    existing = dest / "report.json"
    if existing.is_file():
        old = json.loads(existing.read_text())
        if (
            old.get("candidate") != CANDIDATE
            or old.get("case_id") != cid
            or old.get("trial") != TRIAL
        ):
            raise RuntimeError("CONFLICTING_OLD_FROZEN_EVIDENCE")
        return {
            "case_id": cid,
            "trial": TRIAL,
            "status": "already_observed_no_replay",
            "substantive_completed": old.get("substantive_completed_answer"),
            "sha": old.get("event_sha256"),
            "raw_private": True,
        }
    if (dest / "events.jsonl").exists():
        raise RuntimeError("UNFINISHED_NATIVE_EVIDENCE_DO_NOT_REPLAY")
    runner = PROJ / "scripts/run_p5_big_three_case.py"
    python = PROJ / ".venv/bin/python"
    if not python.is_file() or not runner.is_file():
        raise RuntimeError("OWNED_EVAL_RUNNER_MISSING")
    argv = [
        str(python),
        str(runner),
        "--case",
        cid,
        "--mode",
        "auto",
        "--candidate",
        CANDIDATE,
        "--trial",
        str(TRIAL),
        "--timeout",
        "95",
    ]
    start = time.monotonic()
    with (BASE / f"case-{cid}.log").open("wb") as out:
        pi_proc = subprocess.Popen(
            argv,
            cwd=PROJ,
            stdout=out,
            stderr=out,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, **ENVIRON},
        )
        try:
            rc = pi_proc.wait(timeout=119)
        except subprocess.TimeoutExpired:
            process_stop(pi_proc, "/python")
            rc = None
        finally:
            pi_proc = None
    if existing.is_file():
        row = json.loads(existing.read_text())
        if (
            row.get("candidate") != CANDIDATE
            or row.get("case_id") != cid
            or row.get("trial") != TRIAL
            or row.get("raw_output_exposed") is not False
        ):
            raise RuntimeError("NATIVE_EVIDENCE_ATTRIBUTION_FAILED")
        return {
            "case_id": cid,
            "trial": TRIAL,
            "status": "observed",
            "runner_exit": rc,
            "native_exit": row.get("native_exit_code"),
            "substantive_completed": row.get("substantive_completed_answer"),
            "final_stop": row.get("final_stop_reason"),
            "source_verdict": row.get("gate", {}).get("source_verdict"),
            "skill_read": row.get("gate", {}).get("skill_read_observed"),
            "boundary_verdict": row.get("research_verdict"),
            "repeat_abort": row.get("repeat_abort_reason"),
            "sha": row.get("event_sha256"),
            "elapsed_s": row.get("elapsed_s"),
            "raw_private": True,
        }
    failure = {
        "case_id": cid,
        "trial": TRIAL,
        "status": "runner_failed_or_incomplete",
        "exit": rc,
        "elapsed_s": round(time.monotonic() - start, 2),
    }
    (BASE / f"case-{cid}-failure.json").write_text(json.dumps(failure) + "\n")
    return failure


def check_ready(alias: str, proc: subprocess.Popen) -> tuple[bool, str]:
    deadline = time.monotonic() + 185
    while time.monotonic() < deadline:
        if danger.is_set():
            return False, "resource_guard"
        if proc.poll() is not None:
            return False, "model_process_exited_" + str(proc.returncode)
        if alias in endpoint(8011):
            return True, "ready"
        time.sleep(2)
    return False, "model_api_timeout"


def restore_originals() -> dict:
    state["phase"] = "restoring_original_services"
    write_state()
    p = run([str(AICTL), "restore"], timeout=85)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        ss = service_states()
        if all(ss.values()) and "qwen36-35b-a3b-mtp" in endpoint(18080):
            return {
                "restore_exit": p.returncode,
                "all_five_running": True,
                "qwen_api_healthy": True,
            }
        time.sleep(3)
    return {
        "restore_exit": p.returncode,
        "all_five_running": all(service_states().values()),
        "qwen_api_healthy": "qwen36-35b-a3b-mtp" in endpoint(18080),
    }


def handle_signal(sig, frame) -> None:
    danger.set()
    state["signal"] = sig


def main() -> None:
    global model_proc, monitor_thread
    os.umask(0o077)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    PRIVATE.chmod(0o700)
    write_state()
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    try:
        assert CANDIDATE in MODEL_KEYS and type(TRIAL) is int and TRIAL in (1, 2, 3)
        assert 1 <= len(CASES) <= 6 and len(CASES) == len(set(CASES))
        plan = json.loads((PROJ / "evals/p5_big_three_auto_12x3.json").read_text())
        if (
            hashlib.sha256((PROJ / plan["source_file"]).read_bytes()).hexdigest()
            != plan["source_sha256"]
            or WINDOW["source_sha256"] != plan["source_sha256"]
            or any(cid not in plan["case_ids"] for cid in CASES)
        ):
            raise RuntimeError("FROZEN_CASE_OR_SOURCE_CHANGED")
        first = metrics()
        services = service_states()
        qwen = "qwen36-35b-a3b-mtp" in endpoint(18080)
        busy = run(["/usr/sbin/lsof", "-nP", "-iTCP:18080", "-sTCP:ESTABLISHED"], timeout=6)
        active = max(0, len(busy.stdout.splitlines()) - 1)
        state["original_state"] = {
            "services": services,
            "qwen_api_healthy": qwen,
            "qwen_client_connections": active,
            "resources": first,
        }
        write_state()
        if not all(services.values()) or not qwen or active:
            raise RuntimeError("AI_SERVICE_OR_EXISTING_USER_PRECHECK_FAILED")
        if first["swap_mib"] > 4096 or endpoint(8011):
            raise RuntimeError("EXCESS_SWAP_OR_TEST_PORT_BUSY")
        if (
            not SKILL.is_dir()
            or hashlib.sha256((SKILL / "SKILL.md").read_bytes()).hexdigest() != SKILL_SHA
        ):
            raise RuntimeError("INSTALLED_SKILL_SOURCE_MISMATCH")
        if not SCOPE.is_file():
            raise RuntimeError("SCOPED_PI_NATIVE_EXTENSION_NOT_FOUND")
        catalog = json.loads((PROJ / "evals/p4_cases.json").read_text())["cases"]
        lookup = {x["id"]: x for x in catalog}
        state["phase"] = "stopping_five_original_services"
        # Before changing anything, flag restoration required.
        state["restore_needed"] = True
        write_state()
        stopped = run([str(AICTL), "stop"], timeout=90)
        state["stop_return_code"] = stopped.returncode
        state["services_stopped"] = all(not v for v in service_states().values())
        write_state()
        if stopped.returncode or not state["services_stopped"]:
            raise RuntimeError("FAILED_TO_STOP_ALL_ORIGINAL_SERVICES")
        after = metrics()
        state["after_shutdown"] = after
        if after["swap_mib"] > 4096:
            raise RuntimeError("EXCESSIVE_SWAP_AFTER_SHUTDOWN")
        write_state()
        monitor_thread = threading.Thread(target=resource_monitor, daemon=True)
        monitor_thread.start()
        for alias, engine, weights, reasoning in MODELS:
            if alias != MODEL_KEYS[CANDIDATE]:
                continue
            row = {
                "model": alias,
                "engine": engine,
                "weights_bytes": (
                    weights.stat().st_size
                    if weights.is_file()
                    else sum(
                        p.stat().st_size
                        for p in weights.iterdir()
                        if p.name.endswith(".safetensors")
                    )
                ),
                "start_epoch": time.time(),
                "loading": True,
                "ready": False,
                "cases": [],
                "startup_failure": None,
            }
            state["models"].append(row)
            state["phase"] = "loading_model"
            state["active_model"] = alias
            state["resource_guard_triggered"] = False
            danger.clear()
            write_state()
            if metrics()["swap_mib"] > 4096:
                row["startup_failure"] = "emergency_swap_limit_before_model"
                row["loading"] = False
                write_state()
                continue
            argv = prepare_model(alias, engine, weights, reasoning)
            log = BASE / "server.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            start = time.monotonic()
            try:
                with log.open("wb") as out:
                    model_proc = subprocess.Popen(
                        argv,
                        stdin=subprocess.DEVNULL,
                        stdout=out,
                        stderr=out,
                        start_new_session=True,
                        env={**os.environ, **ENVIRON},
                    )
                state["model_pid"] = model_proc.pid
                write_state()
                ok, reason = check_ready(alias, model_proc)
                row["startup_s"] = round(time.monotonic() - start, 2)
                row["ready"] = ok
                row["loading"] = False
                if not ok:
                    row["startup_failure"] = reason
                write_state()
                if ok:
                    agent = agent_config(alias, reasoning)
                    for caseid in CASES:
                        if danger.is_set():
                            break
                        state["phase"] = "native_pi_testing"
                        state["active_case"] = caseid
                        write_state()
                        try:
                            res = smoke_case(alias, reasoning, lookup[caseid], agent)
                        except Exception as e:
                            res = {
                                "case_id": caseid,
                                "blocked_by": type(e).__name__,
                                "agent_completed": False,
                                "raw_private": True,
                            }
                        row["cases"].append(res)
                        write_state()
                    state.pop("active_case", None)
            finally:
                if model_proc:
                    row["stop_success"] = process_stop(
                        model_proc, "llama-server" if engine == "llama" else "/omlx"
                    )
                    model_proc = None
                state["model_pid"] = None
                row["end_epoch"] = time.time()
                own = [x for x in samples if x.get("model") == alias]
                row["min_memory_free_pct"] = min(
                    (x["memory_pressure_pct"] for x in own), default=None
                )
                row["max_swap_mib"] = max((x["swap_mib"] for x in own), default=None)
                row["max_model_rss_mib"] = max(
                    (x["model_rss_mib"] for x in own if x.get("model_rss_mib") is not None),
                    default=None,
                )
                row["loading"] = False
                write_state()
            if danger.is_set():
                row["resource_guard_triggered"] = True
                # Avoid launching another model before memory has recovered.
                until = time.monotonic() + 80
                while time.monotonic() < until:
                    s = metrics()
                    if s["swap_mib"] <= 1024:
                        break
                    time.sleep(3)
                else:
                    state["remaining_models_skipped"] = "memory_did_not_recover"
                    write_state()
                    break
        state["phase"] = "model_tests_completed"
        write_state()
    except Exception as exc:
        state["fatal_error"] = type(exc).__name__ + ": " + str(exc)[:200]
        write_state()
    finally:
        stop_signal.set()
        if pi_proc:
            process_stop(pi_proc, "/pi")
        if model_proc:
            process_stop(
                model_proc,
                "llama-server" if state.get("active_model") == "gpt-oss-120b" else "/omlx",
            )
            model_proc = None
        if monitor_thread:
            monitor_thread.join(timeout=8)
        try:
            state["restore"] = (
                restore_originals()
                if state.get("restore_needed")
                else {
                    "all_five_running": all(service_states().values()),
                    "qwen_api_healthy": "qwen36-35b-a3b-mtp" in endpoint(18080),
                }
            )
        except Exception as exc:
            state["restore"] = {
                "all_five_running": False,
                "qwen_api_healthy": False,
                "restore_error": type(exc).__name__,
            }
        state["restore_confirmed"] = bool(
            state["restore"]["all_five_running"] and state["restore"]["qwen_api_healthy"]
        )
        state["end_epoch"] = time.time()
        state["last_resource_sample"] = samples[-1] if samples else None
        state["min_pressure"] = min([x["memory_pressure_pct"] for x in samples], default=None)
        state["max_swap_mib"] = max([x["swap_mib"] for x in samples], default=None)
        state["max_model_rss_mib"] = max(
            [x["model_rss_mib"] for x in samples if x.get("model_rss_mib") is not None],
            default=None,
        )
        state["phase"] = (
            "complete"
            if state["restore_confirmed"] and not state.get("fatal_error")
            else "complete_with_issues"
        )
        write_state()
        samples_file = BASE / "resource-samples.json"
        samples_file.write_text(json.dumps(samples, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        print(
            json.dumps(
                {
                    "ready": CANDIDATE in MODEL_KEYS
                    and TRIAL in (1, 2, 3)
                    and 1 <= len(CASES) <= 6,
                    "candidate": CANDIDATE,
                    "trial": TRIAL,
                    "case_ids": CASES,
                    "would_shutdown_services": False,
                }
            )
        )
    else:
        main()
