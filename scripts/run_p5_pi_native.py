#!/usr/bin/env python3
"""Run one bounded real Mac-local Pi Agent QA case, with private native evidence.

Never substitutes remote model credentials, touches global model settings,
runs Claude inference, or saves raw model replies to Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import tempfile

from mods_knowledge.claims import load_claims
from mods_knowledge.p5_native_evidence import summarize_pi_native_trace
from mods_knowledge.registry import load_registry

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROVIDER = "mac-qwen"
MODEL = "qwen36-35b-a3b-mtp"
EXPECTED_SHA = "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
CASES = {"POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"}


def run(
    case_id: str,
    skill_root: pathlib.Path,
    skill_sha: str,
    source: str,
    timeout: int,
    isolate_skill: bool = False,
) -> dict:
    if case_id not in CASES:
        raise ValueError("Unsupported frozen P5 case")
    skill = skill_root / "SKILL.md"
    if (
        not skill.is_file()
        or skill.is_symlink()
        or hashlib.sha256(skill.read_bytes()).hexdigest() != skill_sha
    ):
        raise ValueError("Requested Pi Skill tree must match its reviewed SHA")
    pi_exe = shutil.which("pi")
    if pi_exe is None:
        raise RuntimeError("Native Pi CLI unavailable")
    cases = json.loads((ROOT / "evals/p4_cases.json").read_text())["cases"]
    case = next(x for x in cases if x["id"] == case_id)
    private = pathlib.Path(tempfile.mkdtemp(prefix="mods-p5-pi-local-", dir="/tmp"))
    private.chmod(0o700)
    # Even ordinary negative cases receive safe, read-only workspace fixtures.
    if case_id == "NEG-TYPESCRIPT":
        (private / "src").mkdir()
        (private / "src/overloads.ts").write_text(
            "export function f(value: string): string;\n"
            "export function f<T>(value: T): T;\n"
            "export function f<T>(value: T): T { return value; }\n"
        )
        (private / "package.json").write_text('{"name":"qa-readonly-typescript","private":true}\n')
    command = [
        pi_exe,
        "-p",
        "--provider",
        PROVIDER,
        "--model",
        MODEL,
        "--thinking",
        "off",
        "--no-session",
        "--no-mcp",
        "--no-extensions",
        "--no-context-files",
        "--tools",
        "read,ls,find,grep",
        "--skill",
        str(skill_root),
        "--mode",
        "json",
        case["prompt"],
    ]
    # Pi 1.3.0 explicit --skill is additive to normal discovery. To verify
    # candidate source alone, --no-skills suppresses automatically enabled
    # Skills while preserving explicit --skill paths in DefaultResourceLoader.
    if isolate_skill:
        command.insert(1, "--no-skills")
    trace = private / "native-events.jsonl"
    trace.touch(mode=0o600)
    finished = False
    rc = None
    proc = None
    with trace.open("wb") as output, (private / "native-stderr.log").open("wb") as errors:
        try:
            proc = subprocess.Popen(  # noqa: S603 - fixed native CLI and explicit safe flags
                command,
                cwd=private,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=errors,
                start_new_session=True,
            )
            try:
                rc = proc.wait(timeout=timeout)
                finished = True
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=3)
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=4)
    events = []
    if trace.stat().st_size <= 50_000_000:
        for line in trace.read_text(errors="replace").splitlines():
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    events.append(item)
            except ValueError:
                continue
    else:
        finished = False
    version_proc = subprocess.run(  # noqa: S603 - trusted native binary
        [pi_exe, "--version"], capture_output=True, text=True, timeout=8, check=True
    )
    pi_version = version_proc.stdout.strip()
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    evidence = summarize_pi_native_trace(
        case,
        events,
        source_revision=source,
        host="macbook-pro",
        cli_version=pi_version,
        skill_root=str(skill_root),
        claims=claims,
        expected_provider=PROVIDER,
        expected_model=MODEL,
        model_was_pinned=True,
    )
    evidence["native_command_exited_zero"] = bool(finished and rc == 0)
    if not evidence["native_command_exited_zero"] and evidence["verdict"] in {
        "structural_ok_semantics_unverified",
        "negative_nonactivation_observed",
    }:
        evidence["verdict"] = "blocked_or_incomplete"
    evidence["raw_private"] = True
    (private / "sanitized-result.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (private / "sanitized-result.json").chmod(0o600)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument(
        "--skill-root",
        type=pathlib.Path,
        default=pathlib.Path.home() / ".agents/skills/claude-code-mods-development",
    )
    parser.add_argument("--skill-sha256", default=EXPECTED_SHA)
    parser.add_argument("--source-revision", default=SOURCE)
    parser.add_argument("--timeout", type=int, default=125)
    parser.add_argument("--isolate-explicit-skill", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.timeout <= 180:
        parser.error("Timeout must be between 30 and 180 seconds")
    evidence = run(
        args.case,
        args.skill_root.resolve(),
        args.skill_sha256,
        args.source_revision,
        args.timeout,
        isolate_skill=args.isolate_explicit_skill,
    )
    print(
        json.dumps(
            {
                "case_id": evidence["case_id"],
                "host": evidence["host"],
                "agent": "pi",
                "model_observed": evidence["model_observed"],
                "prompt_matched": evidence["prompt_matched"],
                "skill_loaded": evidence["skill_loaded"],
                "source_verdict": evidence["source_verdict"],
                "verdict": evidence["verdict"],
                "native_command_exited_zero": evidence["native_command_exited_zero"],
                "original_wire_sha256": evidence["original_wire_sha256"],
            }
        )
    )
    return 0 if evidence["native_command_exited_zero"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
