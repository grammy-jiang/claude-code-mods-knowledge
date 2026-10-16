#!/usr/bin/env python3
"""Bounded, buffered-only Pi Agent Mods Skill activation and delivery QA.

This command never streams candidate model text to the user; only sanitized
gate results leave its private evidence directory. No global user settings,
model services, skill installs or source references are modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import shutil
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.p5_native_evidence import summarize_pi_native_trace
from mods_knowledge.pi_delivery_gate import postflight_mods_case, preflight_mods_case
from mods_knowledge.pi_loop_evidence import NativeRepeatGuard
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path.home() / "Models.noindex/benchmarks/pi-mods-skill-activation-20261017"
SKILL = Path.home() / ".agents/skills/claude-code-mods-development"
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
DIGEST = "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"
PROVIDER = "p5-mac-qwen"
MODEL = "qwen36-35b-a3b-mtp"
API_URL = "http://127.0.0.1:18080/v1"
MODES = {"auto", "explicit", "forced", "explicit-forced"}
CASES = {"POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}
MODEL_CANDIDATES = {
    "qwen": ("p5-mac-qwen", "qwen36-35b-a3b-mtp", "http://127.0.0.1:18080/v1"),
    "gemma31": ("p5-gemma31", "gemma4-31b-mtp", "http://127.0.0.1:8011/v1"),
}
PAIRING_MANIFEST = ROOT / "evals/p5_pi_auto_12x3.json"
MAX_BYTES = 20_000_000


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)


def make_isolated_agent(
    root: Path, *, provider: str = PROVIDER, model: str = MODEL, api_url: str = API_URL
) -> Path:
    d = private_dir(root / "agent")
    model_entry = {
        "id": model,
        "name": "P5 local model in isolated QA",
        "reasoning": False,
        "input": ["text"],
        "contextWindow": 32768,
        "maxTokens": 8192,
    }
    models = {
        "providers": {
            provider: {
                "baseUrl": api_url,
                "api": "openai-completions",
                "apiKey": "P5_ISOLATED_LOOPBACK_ONLY",
                "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
                "models": [model_entry],
            }
        }
    }
    write_json(d / "models.json", models)
    write_json(
        d / "settings.json",
        {
            "defaultProvider": provider,
            "defaultModel": model,
            "defaultThinkingLevel": "off",
        },
    )
    return d


def private_case(case_id: str, mode: str, workspace: Path) -> dict:
    cases = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    case = next(x.copy() for x in cases if x["id"] == case_id)
    if mode in {"explicit", "explicit-forced"} and case["category"] != "negative":
        case["prompt"] = (
            "Use the installed claude-code-mods-development Skill. "
            "First actually read its SKILL.md and task-relevant references, "
            "then cite each relevant K-Claim with its exact official Source URL. "
            "Task: " + case["prompt"]
        )
    if case_id == "NEG-TYPESCRIPT":
        (workspace / "src").mkdir(mode=0o700)
        (workspace / "src/overloads.ts").write_text(
            "export function wrap(value: string): {value: string};\n"
            "export function wrap<T>(value: T): {value: T};\n"
            "export function wrap<T>(value: T) { return {value}; }\n"
            "export function first<T>(items: T[]): T | undefined;\n"
            "export function first<T>(items: readonly T[]): T | undefined;\n"
            "export function first<T>(items: readonly T[]) { return items[0]; }\n"
        )
        (workspace / "package.json").write_text('{"name":"qa-ts-control","private":true}\n')
    elif case_id == "NEG-PYTHON":
        (workspace / "src").mkdir(mode=0o700)
        (workspace / "src/server.py").write_text(
            "import asyncio\n"
            "async def f(lock: asyncio.Lock) -> None:\n"
            "    async with lock:\n"
            "        async with lock:\n"
            "            print('deadlock')\n"
        )
    elif case_id == "NEG-MCP":
        (workspace / "src").mkdir(mode=0o700)
        (workspace / "src/server.py").write_text(
            "import socket\ns = socket.socket()\ns.bind(('127.0.0.1', 9999))\n"
        )
    elif case_id == "NEG-LEGACY-HOOK":
        (workspace / ".claude").mkdir(mode=0o700)
        (workspace / ".claude/settings.json").write_text(
            '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command",'
            '"command":"echo example"}]}]}}\n'
        )
    return case


def runner(
    case_id: str,
    mode: str,
    timeout: int,
    *,
    candidate: str = "qwen",
    trial: int | None = None,
    research_boundary: bool = False,
) -> dict:
    if candidate not in MODEL_CANDIDATES or mode not in MODES:
        raise ValueError("Unsupported model candidate or activation mode")
    if trial is not None:
        plan = json.loads(PAIRING_MANIFEST.read_text())
        case_source = ROOT / "evals/p4_cases.json"
        if hashlib.sha256(case_source.read_bytes()).hexdigest() != plan["source_sha256"]:
            raise ValueError("Frozen paired case source changed")
        approved_models = {(m["id"], m["provider"], m["backend"]) for m in plan["models"]}
        if (
            case_id not in plan["case_ids"]
            or mode != "auto"
            or type(trial) is not int
            or trial not in (1, 2, 3)
            or (
                MODEL_CANDIDATES[candidate][1],
                MODEL_CANDIDATES[candidate][0],
                MODEL_CANDIDATES[candidate][2],
            )
            not in approved_models
        ):
            raise ValueError("Unapproved paired model/manifest trial")
    elif case_id not in CASES:
        raise ValueError("Unsupported frozen case/activation mode")
    provider, model, api_url = MODEL_CANDIDATES[candidate]
    if (
        not (SKILL / "SKILL.md").is_file()
        or hashlib.sha256((SKILL / "SKILL.md").read_bytes()).hexdigest() != DIGEST
    ):
        raise RuntimeError("The reviewed installed Skill checksum did not match")
    executable = shutil.which("pi")
    if executable is None:
        raise RuntimeError("Pi CLI unavailable")
    private_dir(PRIVATE)
    root = private_dir(
        PRIVATE
        / (
            f"paired/{candidate}/{case_id}/trial-{trial}"
            if trial is not None
            else f"runs/{case_id}/{mode}"
        )
    )
    if (root / "report.json").exists():
        raise RuntimeError("Previous evidence exists: refusing to overwrite a completed run")
    agent_dir = make_isolated_agent(
        root if trial is not None else PRIVATE,
        provider=provider,
        model=model,
        api_url=api_url,
    )
    workspace = private_dir(root / "workspace")
    case = private_case(case_id, mode, workspace)
    pre = preflight_mods_case(case)
    if research_boundary and case["category"] != "boundary":
        raise ValueError("Research-only bypass is limited to frozen boundary cases")
    if pre["action"] == "abstain_before_model" and not research_boundary:
        report = {
            "case_id": case_id,
            "mode": mode,
            "action": pre["action"],
            "model_calls": 0,
            "reason": pre["reason"],
            "safe_reply": pre["safe_reply"],
            "source_revision": SOURCE,
            "skill_sha256": DIGEST,
            "raw_output_exposed": False,
            "semantic_correctness_verified": False,
        }
        write_json(root / "report.json", report)
        return report
    argv = [
        executable,
        "-p",
        "--provider",
        provider,
        "--model",
        model,
        "--thinking",
        "off",
        "--no-session",
        "--no-mcp",
        "--no-extensions",
        "--no-context-files",
        "--tools",
        "read,ls,find,grep",
    ]
    if mode in {"forced", "explicit-forced"}:
        argv += ["--no-skills", "--skill", str(SKILL)]
    if trial is not None:
        scope_guard = ROOT / "scripts/p5_pi_scope_guard.mjs"
        if not scope_guard.is_file() or scope_guard.is_symlink():
            raise RuntimeError("Test-only native Pi scope extension unavailable")
        # Pi 1.3.0 explicitly supports -e even when --no-extensions
        # disables automatic extensions. This is never installed globally.
        argv += ["--extension", str(scope_guard)]
    argv += ["--mode", "json", case["prompt"]]
    env = os.environ.copy()
    env["PI_CODING_AGENT_DIR"] = str(agent_dir)
    if trial is not None:
        env["P5_PI_ALLOWED_WORKSPACE"] = str(workspace)
        env["P5_PI_ALLOWED_SKILL_ROOT"] = str(SKILL)
    # This test provider uses the loopback service, not remote AI tokens.
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        env.pop(key, None)

    # Hard fail if the intended local service is not currently healthy.
    try:
        if api_url not in ("http://127.0.0.1:18080/v1", "http://127.0.0.1:8011/v1"):
            raise ValueError("Inference endpoint is not a permitted loopback address")
        with urllib.request.urlopen(api_url + "/models", timeout=4) as response:  # noqa: S310
            advertised = json.load(response)
        if model not in [x.get("id") for x in advertised.get("data", [])]:
            raise RuntimeError("Target local model did not appear in the model catalog")
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError("Selected local inference endpoint is unavailable") from exc

    trace = root / "events.jsonl"
    records = []
    guard = NativeRepeatGuard(repeat_limit=6, total_tool_limit=48)
    timed_out = False
    repeat_terminated = False
    tool_abort_reason = None
    native_exit = None
    proc = None
    started = time.monotonic()
    with trace.open("wb") as events_out, (root / "stderr.log").open("wb") as stderr:
        trace.chmod(0o600)
        proc = subprocess.Popen(  # noqa: S603 - approved CLI with fixed sandbox-only arguments
            argv,
            cwd=workspace,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr,
            bufsize=0,
            start_new_session=True,
        )
        assert proc.stdout
        stream = selectors.DefaultSelector()
        stream.register(proc.stdout, selectors.EVENT_READ)
        pending = b""
        total = 0
        ended = False
        while time.monotonic() - started < timeout:
            for _key, _mask in stream.select(0.25):
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    ended = proc.poll() is not None
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    tool_abort_reason = "trace_size_limit"
                    break
                events_out.write(chunk)
                pending += chunk
            while b"\n" in pending:
                raw, pending = pending.split(b"\n", 1)
                try:
                    event = json.loads(raw)
                except (UnicodeError, ValueError):
                    continue
                if not isinstance(event, dict):
                    continue
                records.append(event)
                if guard.observe(event):
                    repeat_terminated = True
                    tool_abort_reason = guard.reason
                    break
            if repeat_terminated or tool_abort_reason:
                break
            if ended or proc.poll() is not None:
                break
        else:
            timed_out = True
        if proc.poll() is None:
            if repeat_terminated or tool_abort_reason or timed_out:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=3)
            else:
                try:
                    native_exit = proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=3)
        if not (repeat_terminated or tool_abort_reason or timed_out):
            native_exit = proc.returncode

    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    audit = postflight_mods_case(
        case,
        records,
        claims=claims,
        skill_root=str(SKILL),
        source_revision=SOURCE,
        provider=provider,
        model=model,
        pi_version="1.3.0",
        native_exit_code=native_exit,
        timed_out=timed_out,
        terminated_for_repeat=repeat_terminated or bool(tool_abort_reason),
    )
    research_evidence = None
    if research_boundary:
        research_evidence = summarize_pi_native_trace(
            case,
            records,
            source_revision=SOURCE,
            host="macbook-pro",
            cli_version="1.3.0",
            skill_root=str(SKILL),
            claims=claims,
            expected_provider=provider,
            expected_model=model,
            model_was_pinned=True,
        )
        # Never promote a research-only boundary answer to delivery, even if
        # the raw model happened to give a safe-looking refusal.
        audit["action"] = "block_candidate"
        audit["allow_raw_candidate_delivery"] = False
    report = {
        "case_id": case_id,
        "mode": mode,
        "candidate": candidate,
        "trial": trial,
        "research_only": research_boundary,
        "observed_model": research_evidence["model_observed"] if research_evidence else None,
        "research_verdict": research_evidence["verdict"] if research_evidence else None,
        "research_actual_skill_read": research_evidence["skill_loaded"]
        if research_evidence
        else None,
        "model_calls": 1,
        "source_revision": SOURCE,
        "skill_sha256": DIGEST,
        "elapsed_s": round(time.monotonic() - started, 2),
        "response_stream_buffered": True,
        "raw_output_exposed": False,
        "native_exit_code": native_exit,
        "timed_out": timed_out,
        "repeat_abort_reason": tool_abort_reason,
        "event_sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
        "candidate_prompt_sha256": hashlib.sha256(case["prompt"].encode()).hexdigest(),
        "gate": audit,
    }
    write_json(root / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    approved_case_ids = set(json.loads(PAIRING_MANIFEST.read_text())["case_ids"])
    parser.add_argument("--case", required=True, choices=sorted(CASES | approved_case_ids))
    parser.add_argument("--mode", required=True, choices=sorted(MODES))
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--candidate", choices=sorted(MODEL_CANDIDATES), default="qwen")
    parser.add_argument("--trial", type=int, default=None)
    parser.add_argument("--research-boundary", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.timeout <= 150:
        parser.error("bounded timeout must be between 30 and 150 seconds")
    report = runner(
        args.case,
        args.mode,
        args.timeout,
        candidate=args.candidate,
        trial=args.trial,
        research_boundary=args.research_boundary,
    )
    # Only vetted metadata is emitted. Raw events/prompts stay private.
    audit = report.get("gate", {})
    print(
        json.dumps(
            {
                "case": report["case_id"],
                "mode": report["mode"],
                "model_calls": report["model_calls"],
                "candidate": report.get("candidate", args.candidate),
                "trial": report.get("trial"),
                "research_only": report.get("research_only", False),
                "research_verdict": report.get("research_verdict"),
                "preflight": report.get("action"),
                "elapsed_s": report.get("elapsed_s"),
                "skill_read_observed": audit.get("skill_read_observed"),
                "gate_action": audit.get("action"),
                "reason_codes": audit.get("reason_codes"),
                "tool_repeat_abort": report.get("repeat_abort_reason"),
                "raw_output_exposed": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
