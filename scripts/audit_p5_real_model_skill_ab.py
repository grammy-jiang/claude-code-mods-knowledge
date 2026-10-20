#!/usr/bin/env python3
"""Re-score four genuine saved Sonnet/Codex turns against frozen scoped Skills.

Requires original PRIVATE MacBook host transcripts under /tmp, never uploads
or replays models. Publishes only hashes, source/link coverage, native-code
risk flags, relative Skill version and finite first-party review outcomes.
No original reply, prompt, user home path, raw event, account or tool result
is copied into the public report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mods_knowledge.answer_lint import (
    _cli302_registration_catch_signals,
    _code_spans,
    lint_mods_answer,
)
from mods_knowledge.claim_source_link_coverage import audit_claim_source_links
from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
RISK = "mods-cli302-tool-call-registration-without-catch"
AGENTS = ("sonnet", "codex")
ARMS = ("baseline", "candidate")
TARGET = "2.1.302"
EXPECTED_REVISIONS = {"baseline": "1531e8d", "candidate": "45dcf52"}
EXPECTED_SOURCES = {
    ("sonnet", "baseline"): "476c5bd82c5e6872a46a8b5795f339cc76a2c9b81f7912f8e1d7b885b9aaea25",
    ("sonnet", "candidate"): "6c3c99dd893bf5f1e4a09a66a696932aba923a62057ff1311503ce1133d9fe10",
    ("codex", "baseline"): "9418250d4deda78afdf11ac8cd4a75df60019113e3584f6e3929836bb88632f4",
    ("codex", "candidate"): "e863ad6d85cfcecb1226f4cd29aa2c3e1fbdc633baffba3c42c8465b3e63f8e8",
}


class ModelSkillABBlocked(ValueError):
    """A genuine local A/B turn could not be verified from preserved bytes."""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _private_bytes(path: Path, *, limit: int = 3_000_000) -> bytes:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= limit:
        raise ModelSkillABBlocked("Private model evidence file missing or oversized")
    return path.read_bytes()


def _jsonl(path: Path) -> tuple[list[dict], str]:
    raw = _private_bytes(path)
    try:
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (UnicodeError, ValueError) as exc:
        raise ModelSkillABBlocked("Invalid native model wire JSONL") from exc
    if not events or any(not isinstance(item, dict) for item in events):
        raise ModelSkillABBlocked("Missing complete native model events")
    return events, sha(raw)


def _sonnet(root: Path) -> dict:
    events, wire_sha = _jsonl(root / "sonnet-wire.private.jsonl")
    terminals = [e for e in events if e.get("type") == "result"]
    if len(terminals) != 1 or terminals[0].get("subtype") != "success":
        raise ModelSkillABBlocked("No single genuine completed Sonnet result")
    terminal = terminals[0]
    if set(terminal.get("modelUsage") or {}) != {"claude-sonnet-5-5"}:
        raise ModelSkillABBlocked("Native Sonnet model identity not confirmed")
    reads = []
    error_count = 0
    for event in events:
        for content in (event.get("message") or {}).get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "tool_use" and content.get("name") == "Read":
                location = content.get("input", {}).get("file_path")
                if not isinstance(location, str):
                    raise ModelSkillABBlocked("Read target is missing")
                reads.append(location)
            if content.get("type") == "tool_result" and content.get("is_error"):
                error_count += 1
    suffix = ".claude/skills/claude-code-mods-development/"
    expected = {"SKILL.md", "events.md", "claim-evidence.md"}
    basenames = {Path(location).name for location in reads}
    if (
        len(reads) < 3
        or not expected <= basenames
        or error_count
        or not all(str(root) in location and suffix in location for location in reads)
    ):
        raise ModelSkillABBlocked("Sonnet did not read genuine project-local Skill files")
    text = terminal.get("result")
    if not isinstance(text, str) or not text.strip():
        raise ModelSkillABBlocked("Missing completed Sonnet user-facing response")
    return {
        "answer": text,
        "wire_sha256": wire_sha,
        "model_reported": "claude-sonnet-5-5",
        "model_identity_attested_in_native_wire": True,
        "model_cost_estimate_usd": terminal.get("total_cost_usd"),
        "project_local_reference_read_count": len(reads),
        "all_required_project_references_read": True,
        "tool_errors": error_count,
    }


def _codex(root: Path) -> dict:
    events, wire_sha = _jsonl(root / "codex-wire.private.jsonl")
    terminals = [e for e in events if e.get("type") == "turn.completed"]
    if len(terminals) != 1 or [e for e in events if e.get("type") == "turn.failed"]:
        raise ModelSkillABBlocked("No single completed Codex native turn")
    output = _private_bytes(root / "codex-final.private.txt", limit=200_000).decode()
    commands = []
    for event in events:
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            if item.get("exit_code") != 0:
                raise ModelSkillABBlocked("A required read-only Codex command failed")
            commands.append(item.get("command", ""))
    required = (
        ".agents/skills/claude-code-mods-development/SKILL.md",
        "references/events.md",
        "references/claim-evidence.md",
    )
    if not all(any(value in command for command in commands) for value in required):
        raise ModelSkillABBlocked("Codex did not visibly read its project-local Skill")
    usage = terminals[0].get("usage") or {}
    if not isinstance(output, str) or not output.strip():
        raise ModelSkillABBlocked("Missing completed Codex final reply")
    return {
        "answer": output,
        "wire_sha256": wire_sha,
        "model_reported": "gpt-6.1-sol",
        "model_identity_attested_in_native_wire": False,
        "requested_medium_effort": True,
        "input_tokens_reported": usage.get("input_tokens"),
        "cached_input_tokens_reported": usage.get("cached_input_tokens"),
        "output_tokens_reported": usage.get("output_tokens"),
        "project_local_reference_read_count": len(commands),
        "all_required_project_references_read": True,
        "tool_errors": 0,
    }


def audit(private_root: Path) -> dict:
    if not private_root.is_dir() or private_root.is_symlink():
        raise ModelSkillABBlocked("Private model A/B evidence root does not exist")
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    cases = []
    for arm in ARMS:
        path = private_root / arm
        if not path.is_dir() or path.is_symlink():
            raise ModelSkillABBlocked("Missing original arm directory")
        sonnet_prompt = _private_bytes(path / "prompt.private.txt", limit=10_000).rstrip(b"\n")
        codex_prompt = _private_bytes(path / "codex-prompt.private.txt", limit=10_000)
        active_skill = _private_bytes(
            path / ".claude/skills/claude-code-mods-development/SKILL.md", limit=20_000
        )
        codex_skill = _private_bytes(
            path / ".agents/skills/claude-code-mods-development/SKILL.md", limit=20_000
        )
        if active_skill != codex_skill:
            raise ModelSkillABBlocked("Two native agents were not given identical Skill bytes")
        expected_prompts = {"sonnet": sha(sonnet_prompt), "codex": sha(codex_prompt)}
        for agent in AGENTS:
            original = _sonnet(path) if agent == "sonnet" else _codex(path)
            answer = original.pop("answer")
            lint = lint_mods_answer(answer, case_id="POS-E-01", target_version=TARGET)
            linked = audit_claim_source_links(answer, claims, version=TARGET, surface="cli")
            snippets = [
                source
                for source, _ in _code_spans(answer)
                if "export function register" in source and "tool.call" in source
            ]
            if len(snippets) != 1:
                raise ModelSkillABBlocked("Expected exactly one source-backed Mod example")
            code = snippets[0]
            states = [state for state, _ in _cli302_registration_catch_signals(code)]
            expected_state = "missing" if arm == "baseline" else "attached"
            if states != [expected_state]:
                raise ModelSkillABBlocked("Unexpected hook catch state in original model code")
            if linked["structural_verdict"] != "pass":
                raise ModelSkillABBlocked("Model cited unsupported or incorrectly sourced Claims")
            flags = lint["risk_flags"]
            if arm == "baseline" and RISK not in flags:
                raise ModelSkillABBlocked("Known original registration bug was not detected")
            if arm == "candidate" and (flags or lint["requires_manual_review"]):
                raise ModelSkillABBlocked("New model output failed deterministic risk gate")
            if sha(code.encode()) != EXPECTED_SOURCES[(agent, arm)]:
                raise ModelSkillABBlocked(
                    "Model code snippet differs from original bounded capture"
                )
            cases.append(
                {
                    "agent": agent,
                    "arm": arm,
                    "prompt_sha256": expected_prompts[agent],
                    "skill_sha256": sha(active_skill),
                    "answer_sha256": sha(answer.encode()),
                    "wire_sha256": original["wire_sha256"],
                    "generated_code_sha256": sha(code.encode()),
                    "code_block_count": len(_code_spans(answer)),
                    "generated_registration_catch_state": states[0],
                    "risk_flags": flags,
                    "manual_review_flags": lint["requires_manual_review"],
                    "exact_source_claim_link_verdict": linked["structural_verdict"],
                    "source_claims_cited_count": len(linked["cited_claim_ids"]),
                    "matched_exact_claim_links_count": len(
                        linked["matched_exact_source_claim_ids"]
                    ),
                    "required_source_file_reads_verified": True,
                    "native_model_completion": True,
                    **{k: v for k, v in original.items() if k != "wire_sha256"},
                }
            )
    for agent in AGENTS:
        prompt_hashes = {item["prompt_sha256"] for item in cases if item["agent"] == agent}
        skill_hashes = {item["skill_sha256"] for item in cases if item["agent"] == agent}
        if len(prompt_hashes) != 1 or len(skill_hashes) != 2:
            raise ModelSkillABBlocked("A/B prompt was altered or Skill variants identical")
    return {
        "schema_version": 1,
        "date": "2026-10-20",
        "target_claude_code_cli": TARGET,
        "experiment": "source-pinned project-local Skill content A/B, genuine medium-effort agents",
        "frozen_source_revisions": EXPECTED_REVISIONS,
        "total_valid_genuine_model_turns": 4,
        "same_user_prompt_per_agent_and_two_arms": True,
        "all_four_native_agent_finishes": True,
        "all_four_actual_project_skill_reference_reads": True,
        "baseline_risky_missing_registration_catch": 2,
        "candidate_with_registration_catch": 2,
        "all_four_exact_firstparty_claim_source_structure_pass": True,
        "failed_global_skill_no_read_trial_excluded": True,
        "historical_model_output_bytes_or_prompts_exported": False,
        "user_account_or_credentials_exported": False,
        "all_generated_code_executed_by_model": False,
        "native_code_semantic_quality_approved_by_this_report": False,
        "real_user_permission_host_verified": False,
        "full_model_quality_success_rate_proven": False,
        "full_runtime_generated_tool_types_verified": False,
        "stable_release_authorized": False,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise SystemExit("REFUSED: frozen A/B result already exists")
    try:
        report = audit(args.private_root)
    except (OSError, ValueError, KeyError, TypeError, ModelSkillABBlocked):
        raise SystemExit(
            "BLOCKED: private original model A/B failed evidence verification"
        ) from None
    args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "original_genuine_model_completions": report["total_valid_genuine_model_turns"],
                "baseline_risky": report["baseline_risky_missing_registration_catch"],
                "candidate_fixed": report["candidate_with_registration_catch"],
                "production_quality_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
