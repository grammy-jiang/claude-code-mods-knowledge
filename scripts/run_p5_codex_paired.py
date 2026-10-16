#!/usr/bin/env python3
"""Native Codex gpt-6.1-sol / medium, frozen P5 12×3 paired model QA.

Preserves original Pi research prompts and exact approved Skill bytes.
No Claude model or ChatGPT Chat-mode calls. Full Codex native messages
remain owner-only on Mac; emits case IDs, hashes, statuses and safe metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from run_p5_codex_native import run_native_case

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "evals/p5_pi_auto_12x3.json"
CASES = ROOT / "evals/p4_cases.json"
PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-codex-sol-medium-20261017"
MODEL = "gpt-6.1-sol"
EFFORT = "medium"
SKILL_SHA = "03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e"
SOURCE = "6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e"
FIXTURES = {
    "NEG-TYPESCRIPT": {
        "src/overloads.ts": (
            "export function wrap(value: string): {value: string};\n"
            "export function wrap<T>(value: T): {value: T};\n"
            "export function wrap<T>(value: T) { return {value}; }\n"
            "export function first<T>(items: T[]): T | undefined;\n"
            "export function first<T>(items: readonly T[]): T | undefined;\n"
            "export function first<T>(items: readonly T[]) { return items[0]; }\n"
        ),
        "package.json": '{"name":"p5-typescript-control","private":true}\n',
    },
    "NEG-PYTHON": {
        "src/server.py": (
            "import asyncio\nasync def f(lock: asyncio.Lock) -> None:\n"
            "    async with lock:\n        async with lock:\n            print('deadlock')\n"
        ),
    },
    "NEG-MCP": {
        "src/server.py": ("import socket\ns = socket.socket()\ns.bind(('127.0.0.1', 9999))\n"),
    },
    "NEG-LEGACY-HOOK": {
        ".claude/settings.json": (
            '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command",'
            '"command":"echo example"}]}]}}\n'
        ),
    },
}


class NativeCohortError(ValueError):
    """Invalid or mismatched frozen/observed Codex test evidence."""


def frozen() -> dict:
    manifest = json.loads(PLAN.read_text())
    if (
        hashlib.sha256(CASES.read_bytes()).hexdigest() != manifest["source_sha256"]
        or len(manifest["case_ids"]) != 12
        or len(set(manifest["case_ids"])) != 12
        or manifest["repetitions"] != 3
    ):
        raise NativeCohortError("Frozen source manifest changed")
    index = {c["id"]: c for c in json.loads(CASES.read_text())["cases"]}
    if any(c not in index for c in manifest["case_ids"]):
        raise NativeCohortError("Unknown frozen test case")
    return manifest


def case_root(case_id: str, trial: int, *, web_disabled: bool = False) -> Path:
    if case_id not in frozen()["case_ids"] or trial not in (1, 2, 3):
        raise NativeCohortError("Invalid selected case/round")
    return (
        PRIVATE
        / ("no-web/paired" if web_disabled else "paired")
        / MODEL
        / case_id
        / f"trial-{trial}"
    )


def prepare_fixture(case_id: str, folder: Path) -> None:
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.chmod(0o700)
    for rel, data in FIXTURES.get(case_id, {}).items():
        file = folder / rel
        file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        file.write_text(data)
        file.chmod(0o600)


def run(case_id: str, trial: int, timeout: int, *, no_web: bool = False) -> dict:
    if not 30 <= timeout <= 180:
        raise NativeCohortError("Trial timeout out of bounds")
    manifest = frozen()
    if case_id not in manifest["case_ids"] or trial not in (1, 2, 3):
        raise NativeCohortError("Trial outside approved manifest")
    skill = Path.home() / ".agents/skills/claude-code-mods-development/SKILL.md"
    if not skill.is_file() or hashlib.sha256(skill.read_bytes()).hexdigest() != SKILL_SHA:
        raise NativeCohortError("Installed Skill bytes differ from approved baseline")
    folder = case_root(case_id, trial, web_disabled=no_web)
    if (folder / "report.json").exists() or (folder / "native-wire.jsonl").exists():
        raise NativeCohortError("Cannot overwrite previous native evidence")
    prepare_fixture(case_id, folder)
    started = time.monotonic()
    try:
        _, evidence = run_native_case(
            case_id,
            "macbook-pro",
            timeout,
            private_workspace=folder,
            approved_case_ids=set(manifest["case_ids"]),
            disable_web_search=no_web,
        )
    except Exception as exc:
        # Preserve original failure event files rather than pretending a pass.
        issue = type(exc).__name__
        evidence = {
            "state": "native_exception",
            "blocker": issue,
            "case_id": case_id,
            "model_provenance": "unknown",
            "source_verdict": "not_observed",
            "verdict": "blocked_or_incomplete",
            "agent_completed": False,
            "skill_loaded": False,
        }
    raw = folder / "native-wire.jsonl"
    digest = hashlib.sha256(raw.read_bytes()).hexdigest() if raw.is_file() else None
    web_search_count = 0
    if raw.is_file():
        for line in raw.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("method") == "item/completed" and isinstance(
                event.get("params", {}).get("item"), dict
            ):
                web_search_count += event["params"]["item"].get("type") == "webSearch"
    report = {
        "schema_version": 1,
        "candidate": "codex",
        "case_id": case_id,
        "trial": trial,
        "model_requested": MODEL,
        "effort_requested": EFFORT,
        "source_revision": SOURCE,
        "skill_sha256": SKILL_SHA,
        "original_case_file_sha256": manifest["source_sha256"],
        "elapsed_s": round(time.monotonic() - started, 2),
        "native_wire_sha256": digest,
        "web_search_disabled_requested": no_web,
        "native_web_search_count": web_search_count,
        "raw_transcript_private": True,
        "raw_output_exposed": False,
        "native_mod_runtime_verified": False,
        "semantic_review_complete": False,
        "evidence": evidence,
    }
    path = folder / "report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=frozen()["case_ids"], required=True)
    parser.add_argument("--trial", type=int, choices=[1, 2, 3], required=True)
    parser.add_argument("--timeout", type=int, default=95)
    parser.add_argument("--no-web", action="store_true")
    args = parser.parse_args()
    report = run(args.case, args.trial, args.timeout, no_web=args.no_web)
    evidence = report["evidence"]
    print(
        json.dumps(
            {
                "case_id": report["case_id"],
                "trial": report["trial"],
                "elapsed_s": report["elapsed_s"],
                "state": evidence.get("state"),
                "blocker": evidence.get("blocker"),
                "model_server_resolved": evidence.get("model_server_resolved"),
                "effort_server_resolved": evidence.get("effort_server_resolved"),
                "model_provenance": evidence.get("model_provenance"),
                "skill_loaded": evidence.get("skill_loaded"),
                "source_verdict": evidence.get("source_verdict"),
                "verdict": evidence.get("verdict"),
                "raw_output_exposed": False,
                "web_disabled": report["web_search_disabled_requested"],
                "native_web_search_count": report["native_web_search_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
