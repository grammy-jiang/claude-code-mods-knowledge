#!/usr/bin/env python3
"""Native Pi 1.3 / Claude CLI 2.1.302 P5 preflight only; never starts a model.

This *is not* host-model acceptance or a real completion. It checks the
same reviewed Skill installed on the target and atomically records whether
the case is blocked before inference or needs a separate controlled Pi
model call. No MCP, extensions, Qwen server, secrets or user config edits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from mods_knowledge.pi_delivery_gate import preflight_mods_case
from mods_knowledge.release_validation import (
    validate_dist,
    validate_skill_frontmatter,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = frozenset(("POS-E-01", "POS-Q-01", "NEG-TYPESCRIPT", "BOUND-VERSION-NEW"))
# Source identity comes from the complete reviewed build manifest AND exact
# local Git HEAD, not from a stale version-specific hardcoded checksum.


class NativePreflight302Error(ValueError):
    """Native model inference is not authorized by this invalid host scope."""


def plan(
    case: dict,
    *,
    skill_bytes: bytes,
    reviewed_skill_sha256: str,
    reviewed_source_revision: str,
    observed_claude_version: str,
    observed_pi_version: str,
) -> dict:
    if (
        not isinstance(case, dict)
        or case.get("id") not in CASES
        or observed_claude_version != "2.1.302 (Claude Code)"
        or observed_pi_version != "1.3.0"
        or not isinstance(reviewed_skill_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", reviewed_skill_sha256)
        or not isinstance(reviewed_source_revision, str)
        or not re.fullmatch(r"[0-9a-f]{40}", reviewed_source_revision)
        or hashlib.sha256(skill_bytes).hexdigest() != reviewed_skill_sha256
    ):
        raise NativePreflight302Error("P5 native installed CLI/Skill/version mismatch")
    metadata = validate_skill_frontmatter(skill_bytes)
    if metadata["name"] != "claude-code-mods-development":
        raise NativePreflight302Error("Wrong native Skill")
    result = preflight_mods_case(case, target_version="2.1.302")
    if result["source_target"] != "Claude Code CLI 2.1.302":
        raise NativePreflight302Error("Unknown case/target scope")
    blocked = result["action"] == "abstain_before_model"
    if not blocked and result["action"] != "run_scoped_model":
        raise NativePreflight302Error("Ambiguous Pi preflight decision")
    return {
        "schema_version": 1,
        "source_revision": reviewed_source_revision,
        "skill_sha256": reviewed_skill_sha256,
        "native_pi_version": observed_pi_version,
        "installed_claude_code_version": observed_claude_version,
        "target": "2.1.302",
        "case_id": case["id"],
        "category": case["category"],
        "original_prompt_sha256": hashlib.sha256(case["prompt"].encode()).hexdigest(),
        "action": "abstain_before_model" if blocked else "model_backend_required_after_preflight",
        "original_gate_reason": result["reason"],
        "safe_refusal_sha256": (
            hashlib.sha256(result["safe_reply"].encode()).hexdigest() if blocked else None
        ),
        "model_requests_authorized_by_gate": result["model_requests_needed"],
        "model_requests_performed": 0,
        "native_model_inference_completed": False,
        "full_native_host_acceptance": False,
        "raw_prompt_or_local_account_data_exported": False,
        "stable_release_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=sorted(CASES), required=True)
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path.home() / ".agents/skills/claude-code-mods-development",
    )
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: immutable previous Pi P5 case output exists")
    if not args.skill_root.is_dir() or args.skill_root.is_symlink():
        raise SystemExit("BLOCKED: installed local native Pi Skill missing")
    skill = args.skill_root / "SKILL.md"
    if not skill.is_file() or skill.is_symlink():
        raise SystemExit("BLOCKED: untrusted native Pi Skill path")
    # Model-free, fail-closed attestation of the exact on-host compiled
    # candidate and the checked-out source that produced it. Do not trust
    # a caller-supplied SHA to bless an arbitrary installed file.
    built = validate_dist(args.dist)
    if built.get("target") != {"api_version": "2.1.302", "surface": "cli"}:
        raise SystemExit("BLOCKED: build target is not the reviewed CLI 2.1.302")
    manifest = json.loads((args.dist / "manifests/build-manifest.json").read_text())
    reviewed_rev = manifest.get("source_revision")
    git_exe = shutil.which("git")
    if not git_exe or not isinstance(reviewed_rev, str):
        raise SystemExit("BLOCKED: reviewed source revision missing")
    checked_out = subprocess.run(  # noqa: S603 - local pinned git read-only
        [git_exe, "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    ).stdout.strip()
    if checked_out != reviewed_rev or not re.fullmatch(r"[0-9a-f]{40}", reviewed_rev):
        raise SystemExit("BLOCKED: compiled manifest and Git source drift")
    canonical = args.dist / "common/claude-code-mods-development/SKILL.md"
    reviewed_sha = hashlib.sha256(canonical.read_bytes()).hexdigest()
    data = json.loads((ROOT / "evals/p4_cases_cli_2_1_302.json").read_text())
    case = next(row for row in data["cases"] if row["id"] == args.case)
    claude_executable = shutil.which("claude")
    pi_executable = shutil.which("pi")
    if not claude_executable or not pi_executable:
        raise SystemExit("BLOCKED: reviewed native CLIs not installed")
    version = subprocess.run(  # noqa: S603 - reviewed native CLI, no shell
        [claude_executable, "--version"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    ).stdout.strip()
    pi = subprocess.run(  # noqa: S603 - reviewed native Pi CLI, no shell
        [pi_executable, "--version"],
        capture_output=True,
        text=True,
        timeout=8,
        check=True,
    ).stdout.strip()
    result = plan(
        case,
        skill_bytes=skill.read_bytes(),
        reviewed_skill_sha256=reviewed_sha,
        reviewed_source_revision=reviewed_rev,
        observed_claude_version=version,
        observed_pi_version=pi,
    )
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    args.out.chmod(0o600)
    print(
        json.dumps(
            {
                "case_id": result["case_id"],
                "action": result["action"],
                "model_requests_performed": 0,
                "safe_refusal_sha256": result["safe_refusal_sha256"],
                "native_model_inference_completed": False,
                "stable_release_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
