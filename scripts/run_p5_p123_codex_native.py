#!/usr/bin/env python3
"""One bounded real Codex App Server QA turn with private native wire evidence.

Explicit invocation only. Does not call Claude/ChatGPT Chat Mode, modify user
configuration, or write raw replies to public Git. Run from a trusted checkout.
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
import tempfile
import time
from pathlib import Path

from mods_knowledge.claims import load_claims
from mods_knowledge.p5_native_evidence import summarize_codex_native_trace
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-6.1-sol"
EFFORT = "medium"
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
SKILL_SHA = (
    __import__("hashlib")
    .sha256((ROOT / "dist/common/claude-code-mods-development/SKILL.md").read_bytes())
    .hexdigest()
)
CASES = {"POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}


def _sandbox_root(case_id: str) -> Path:
    base = Path(tempfile.mkdtemp(prefix="mods-p5-codex-", dir="/tmp"))
    base.chmod(0o700)
    if case_id == "NEG-TYPESCRIPT":
        (base / "src").mkdir(mode=0o700)
        (base / "package.json").write_text('{"name":"p5-typescript-control","private":true}\n')
        (base / "tsconfig.json").write_text(
            '{"compilerOptions":{"strict":true,"target":"ES2022"},"include":["src"]}\n'
        )
        (base / "src/overloads.ts").write_text(
            "export function wrap(value: string): {value: string};\n"
            "export function wrap<T>(value: T): {value: T};\n"
            "export function wrap<T>(value: T) { return {value}; }\n"
            "export function first<T>(a: T[]): T | undefined;\n"
            "export function first<T>(a: readonly T[]): T | undefined;\n"
            "export function first<T>(a: readonly T[]) { return a[0]; }\n"
        )
    return base


def _wire_record(fd, record: dict) -> None:
    fd.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    fd.flush()


def run_native_case(
    case_id: str,
    host: str,
    max_seconds: int,
    *,
    private_workspace: Path | None = None,
    approved_case_ids: set[str] | None = None,
    disable_web_search: bool = False,
) -> tuple[Path, dict]:
    if case_id not in (
        approved_case_ids if approved_case_ids is not None else CASES
    ) or host not in {"macbook-pro", "raspberry-pi", "sextant"}:
        raise ValueError("Invalid scoped case/host")
    cases = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    case = next(c for c in cases if c["id"] == case_id)
    if private_workspace is None:
        raise RuntimeError("New Skill benchmark requires isolated owner-only workspace")
    private_agent_home = (
        Path.home()
        / "Models.noindex/benchmarks/p5-p123-seven-stack-20261017"
        / "codex-sandbox-home"
    )
    if not private_agent_home.is_dir() or private_agent_home.is_symlink():
        raise RuntimeError("Private Codex benchmark home missing")
    skill_root = private_workspace / ".agents/skills/claude-code-mods-development"
    skill = skill_root / "SKILL.md"
    if not skill.is_file() or hashlib.sha256(skill.read_bytes()).hexdigest() != SKILL_SHA:
        raise RuntimeError("Installed native Skill digest mismatches approved source")

    if private_workspace is None:
        home = _sandbox_root(case_id)
    else:
        home = private_workspace.resolve()
        if not home.is_dir() or not (home.stat().st_mode & 0o077) == 0:
            raise RuntimeError("Private QA workspace must exist with owner-only mode")
        if (home / "native-wire.jsonl").exists():
            raise RuntimeError("Cannot overwrite an existing native model transcript")
    wire_file = home / "native-wire.jsonl"
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("Codex CLI not installed")
    cmd = [
        executable,
        "app-server",
        "--stdio",
        "-c",
        'model="gpt-6.1-sol"',
        "-c",
        'model_reasoning_effort="medium"',
    ]
    if disable_web_search:
        # Codex read-only shell sandbox does NOT automatically disable
        # the separate native web_search tool. Configure it explicitly.
        cmd += ["-c", 'web_search="disabled"']
    records: list[dict] = []
    skills_provenance_verified = False
    proc = None
    state = "blocked_or_incomplete"
    error_category = None
    try:
        with (
            open(wire_file, "w", encoding="utf-8") as output,
            open(home / "native-stderr.log", "w", encoding="utf-8") as errors,
        ):
            os.chmod(wire_file, 0o600)
            proc = subprocess.Popen(  # noqa: S603 - selected native CLI; args are fixed
                cmd,
                cwd=home,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
                bufsize=0,
                start_new_session=True,
                env={
                    **os.environ,
                    "HOME": str(private_agent_home),
                    "CODEX_HOME": str(private_agent_home),
                },
            )
            assert proc.stdin and proc.stdout
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)

            def send(row: dict) -> None:
                assert proc and proc.stdin
                proc.stdin.write((json.dumps(row, ensure_ascii=False) + "\n").encode())
                proc.stdin.flush()

            send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"clientInfo": {"name": "mods-p5-native-qa", "version": "0.1.0"}},
                }
            )
            send({"jsonrpc": "2.0", "method": "initialized"})
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "skills/extraRoots/set",
                    "params": {"extraRoots": [str(skill_root.parent)]},
                }
            )
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "skills/list",
                    "params": {"cwds": [str(home)], "forceReload": True},
                }
            )
            skills_provenance_verified = False
            thread_id = None
            turn_sent = read_sent = False
            pending = b""
            end = time.monotonic() + max_seconds
            while time.monotonic() < end:
                for _key, _mask in selector.select(0.25):
                    try:
                        chunk = os.read(proc.stdout.fileno(), 65536)
                    except BlockingIOError:
                        chunk = b""
                    if chunk:
                        pending += chunk
                while b"\n" in pending:
                    raw, pending = pending.split(b"\n", 1)
                    try:
                        row = json.loads(raw)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if not isinstance(row, dict):
                        continue
                    records.append(row)
                    _wire_record(output, row)
                    if row.get("id") == 5 and "error" in row:
                        error_category = "isolated_skill_root_unavailable"
                        break
                    if row.get("id") == 6:
                        response = row.get("result")
                        observed = []
                        if isinstance(response, dict):
                            for group in response.get("data", []):
                                if isinstance(group, dict):
                                    observed.extend(
                                        skill
                                        for skill in group.get("skills", [])
                                        if isinstance(skill, dict)
                                    )
                        expected_path = str(skill.resolve() if skill.is_file() else skill)
                        matching = [
                            item
                            for item in observed
                            if item.get("name") == "claude-code-mods-development"
                        ]
                        skills_provenance_verified = (
                            len(matching) == 1 and matching[0].get("path") == expected_path
                        )
                        if not skills_provenance_verified:
                            error_category = "isolated_skill_not_registered"
                            break
                        send(
                            {
                                "jsonrpc": "2.0",
                                "id": 2,
                                "method": "thread/start",
                                "params": {
                                    "cwd": str(home),
                                    "ephemeral": True,
                                    "model": MODEL,
                                    "approvalPolicy": "never",
                                    "sandbox": "read-only",
                                },
                            }
                        )
                    if row.get("id") == 2:
                        if "result" not in row:
                            error_category = "thread_start_failed"
                            break
                        response = row["result"]
                        thread_id = response.get("thread", {}).get("id")
                        if (
                            response.get("model") != MODEL
                            or response.get("modelProvider") != "openai"
                            or response.get("reasoningEffort") != EFFORT
                            or not isinstance(thread_id, str)
                        ):
                            error_category = "resolved_model_or_effort_mismatch"
                            break
                        if not turn_sent:
                            send(
                                {
                                    "jsonrpc": "2.0",
                                    "id": 3,
                                    "method": "turn/start",
                                    "params": {
                                        "threadId": thread_id,
                                        "input": [{"type": "text", "text": case["prompt"]}],
                                        "model": MODEL,
                                        "effort": EFFORT,
                                        "cwd": str(home),
                                        "approvalPolicy": "never",
                                        "sandboxPolicy": {
                                            "type": "readOnly",
                                            "networkAccess": False,
                                        },
                                    },
                                }
                            )
                            turn_sent = True
                    if row.get("id") == 3 and "error" in row:
                        error_category = "turn_start_failed"
                        break
                    if (
                        row.get("method") == "turn/completed"
                        and row.get("params", {}).get("threadId") == thread_id
                        and not read_sent
                    ):
                        send(
                            {
                                "jsonrpc": "2.0",
                                "id": 4,
                                "method": "thread/read",
                                "params": {"threadId": thread_id, "includeTurns": False},
                            }
                        )
                        read_sent = True
                    if row.get("id") == 4:
                        state = "native_turn_recorded"
                        break
                if state == "native_turn_recorded" or error_category:
                    break
                if proc.poll() is not None:
                    error_category = "native_process_exited"
                    break
            if state != "native_turn_recorded" and not error_category:
                error_category = "native_timeout_or_incomplete"
    finally:
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)

    summary: dict = {
        "candidate_skill_sha256": SKILL_SHA,
        "skill_from_isolated_project": True,
        "registered_candidate_skill_before_model": skills_provenance_verified,
        "schema_version": 1,
        "case_id": case_id,
        "host": host,
        "agent": "codex",
        "state": state,
        "blocker": error_category,
        "target_version": "Claude Code CLI 2.1.296",
        "source_revision": SOURCE,
        "model_requested": MODEL,
        "effort_requested": EFFORT,
        "raw_private": True,
        "native_mod_runtime_verified": False,
        "semantic_review_complete": False,
    }
    if state == "native_turn_recorded":
        registry = load_registry(ROOT / "sources/registry.json")
        claims = load_claims(
            ROOT / "claims", registry, ROOT / "sources/snapshots", ROOT / "decisions"
        )
        cli = subprocess.run(  # noqa: S603 - same native executable as the turn
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        ).stdout.strip()
        version = cli.split()[-1]
        evidence = summarize_codex_native_trace(
            case,
            records,
            source_revision=SOURCE,
            host=host,
            cli_version=version,
            skill_root=str(skill_root),
            claims=claims,
            allow_isolated_relative_skills=True,
        )
        summary.update(evidence)
    path = home / "sanitized-report.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    path.chmod(0o600)
    return home, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument("--host", choices=["macbook-pro", "raspberry-pi", "sextant"], required=True)
    parser.add_argument("--timeout", type=int, default=105)
    args = parser.parse_args()
    if not 30 <= args.timeout <= 180:
        parser.error("timeout must be between 30 and 180 seconds")
    _, report = run_native_case(args.case, args.host, args.timeout)
    # Only sanitized fields are printed. Private file path intentionally omitted.
    visible = {
        k: report.get(k)
        for k in (
            "case_id",
            "host",
            "agent",
            "state",
            "blocker",
            "model_server_resolved",
            "effort_server_resolved",
            "prompt_matched",
            "agent_completed",
            "skill_loaded",
            "source_verdict",
            "verdict",
            "original_wire_sha256",
        )
    }
    print(json.dumps(visible, ensure_ascii=False))
    return 0 if report["state"] == "native_turn_recorded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
