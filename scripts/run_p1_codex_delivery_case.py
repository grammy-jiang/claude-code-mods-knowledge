#!/usr/bin/env python3
"""P1 one-case native Codex delivery A/B; owner-only isolated benchmark.

A/B treatment = pre-inference native developerInstructions with a typed,
SHA-256-pinned SSOT evidence payload. Both arms already have the same optional
selected-evidence file. Real native model turns are opt-in, never automatic.
No local weight loading, no published Plugin, no skill/user installation,
and no ChatGPT Chat/Work interaction. The report stores no raw user/model text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

import run_p5_p123_codex_case as trial_runner
import run_p5_p123_codex_native as native

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evals/p1_codex_delivery_ab.json"
OLD_ARCHIVE = (
    Path.home()
    / "Models.noindex/benchmarks/p5-p123-seven-stack-20261017"
    / "paired/qwen/POS-E-01/trial-1/agent/skills/claude-code-mods-development"
)
PRIVATE = Path.home() / "Models.noindex/benchmarks/p1-skill-delivery-20261017"
COPY = PRIVATE / "frozen-candidate-skill"
LOCK = PRIVATE / "experiment.lock"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def plan() -> dict:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        doc["arms"] != ["file_only", "preload"]
        or doc["planned_trials"] != 24
        or doc["positive_repetitions"] != 2
        or doc["negative_repetitions"] != 1
        or doc["model"] != native.MODEL
        or doc["effort"] != native.EFFORT
        or _sha((ROOT / doc["source_file"]).read_bytes()) != doc["source_sha256"]
    ):
        raise ValueError("Frozen P1 plan does not match the original benchmark")
    expected = json.loads((ROOT / "evals/p5_p123_seven_stack_12x3.json").read_text())
    if doc["frozen_skill_sha256"] != expected["candidate_skill_sha256"]:
        raise ValueError("P1 Skill source differs from approved original candidate")
    return doc


def prepare_isolated_source(expected_sha: str) -> Path:
    if not PRIVATE.is_dir():
        PRIVATE.mkdir(mode=0o700, parents=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077:
        raise ValueError("P1 private campaign dir must be real and owner-only")
    if COPY.exists() and (COPY.is_symlink() or not COPY.is_dir()):
        raise ValueError("Invalid existing frozen Skill copy")
    if not COPY.exists():
        if not OLD_ARCHIVE.is_dir() or OLD_ARCHIVE.is_symlink():
            raise FileNotFoundError("Historical original Skill source not accessible")
        if _sha((OLD_ARCHIVE / "SKILL.md").read_bytes()) != expected_sha:
            raise ValueError("Historical source Skill changed")
        # The source archived case already contains its task-specific pack.
        # Never let that old case's evidence contaminate another frozen case.
        shutil.copytree(
            OLD_ARCHIVE,
            COPY,
            ignore=shutil.ignore_patterns("selected-evidence.md"),
        )
        for item in COPY.rglob("*"):
            if item.is_file():
                item.chmod(0o600)
            elif item.is_dir():
                item.chmod(0o700)
    if _sha((COPY / "SKILL.md").read_bytes()) != expected_sha:
        raise ValueError("Frozen copied Skill changed")
    if (COPY / "references/selected-evidence.md").exists():
        raise ValueError("Stale, cross-case selected evidence in frozen source")
    return COPY


def run(case_id: str, trial: int, arm: str) -> dict:
    approved = plan()
    if arm not in approved["arms"]:
        raise ValueError("Unknown delivery experiment arm")
    if case_id in approved["positive_cases"]:
        if trial not in (1, 2):
            raise ValueError("Trial outside planned positive repetitions")
    elif case_id in approved["negative_cases"]:
        if trial != 1:
            raise ValueError("Trial outside planned negative repetitions")
    else:
        raise ValueError("Case not in frozen P1 experiment")
    source = prepare_isolated_source(approved["frozen_skill_sha256"])
    # Isolated in-process overrides: do not write to /usr/local, ~/.codex,
    # ~/.agents or any production Skill directory.
    trial_runner.PRIVATE = PRIVATE
    trial_runner.SOURCE = source
    native.SKILL_SHA = approved["frozen_skill_sha256"]
    # Lock prevents simultaneous hosted turns and rate-limit bursts.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(LOCK, flags, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("P1 benchmark already running or has a stale lock") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writable:
            writable.write("P1 research: one native trial at a time\n")
        result = trial_runner.run(
            case_id,
            trial,
            no_web=True,
            delivery_mode=arm,
            p1_experiment=True,
        )
        accepted = result.get("P1_native_thread_accepted_delivery")
        if arm == "preload" and case_id in approved["positive_cases"] and accepted is not True:
            # Report remains saved; a transport failure is an experiment failure.
            raise RuntimeError("Native App Server did not confirm thread-scoped evidence")
        return {
            "case_id": case_id,
            "category": "positive" if case_id in approved["positive_cases"] else "negative",
            "trial": trial,
            "arm": arm,
            "native_completed": result["native_case_completed"],
            "Skill_read_observed": result["actual_candidate_skill_read"],
            "exact_claim_source_structural_verdict": result["source_verdict"],
            "thread_accepted_evidence": accepted,
            "payload_sha256": result.get("P1_payload_sha256"),
            "time_seconds": result["elapsed_s"],
            "raw_model_text_private": True,
            "semantic_mod_code_verified": False,
        }
    finally:
        LOCK.unlink(missing_ok=True)


def main() -> int:
    data = plan()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=data["arms"], required=True)
    parser.add_argument("--case", choices=data["positive_cases"] + data["negative_cases"], required=True)
    parser.add_argument("--trial", type=int, required=True)
    opts = parser.parse_args()
    summary = run(opts.case, opts.trial, opts.arm)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["native_completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
