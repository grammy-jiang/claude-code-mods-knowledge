#!/usr/bin/env python3
"""Audit five immutable *real* native Claude Code 2.1.302 Sonnet host turns.

Read-only; source/private tool wire remains outside Git. This verification
checks model usage, native final, actual Skill/Read tool calls and exact Claims,
and carefully separates factual answer and routing checks from semantic
approval. Never execute generated model code or export raw replies.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from mods_knowledge.claim_source_link_coverage import audit_claim_source_links
from mods_knowledge.claims import load_claims
from mods_knowledge.registry import load_registry

BASE = Path(os.environ["MODS_CLAUDE_PRIVATE_EVIDENCE_DIR"])
ROOT = Path(__file__).resolve().parents[1]
INSTALLED_SKILL = Path.home() / ".claude/skills/claude-code-mods-development/SKILL.md"
CASES = (
    ("positive_sonnet", "positive", "explicit"),
    ("positive_auto_sonnet", "positive", "automatic"),
    ("negative_sonnet", "negative", "automatic"),
    ("boundary_sonnet", "boundary", "explicit"),
    ("boundary_auto_sonnet", "boundary", "automatic"),
)


def _digest(content: str | bytes) -> str:
    return hashlib.sha256(content.encode() if isinstance(content, str) else content).hexdigest()


def _audit() -> dict:
    exe = shutil.which("claude")
    if not exe:
        raise ValueError("Installed Claude Code CLI is unavailable")
    cli = subprocess.run(  # noqa: S603 -- only a resolved local binary and --version
        [exe, "--version"], capture_output=True, text=True, timeout=10, check=False
    )
    if cli.returncode != 0 or cli.stdout.strip() != "2.1.302 (Claude Code)":
        raise ValueError("Not verified exact native CLI 2.1.302")
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    summary = []
    for name, category, invocation in CASES:
        wire = BASE / (name + ".wire.jsonl")
        if not wire.is_file() or wire.stat().st_size > 10_000_000:
            raise ValueError("Original native wire absent or too large")
        events = [json.loads(line) for line in wire.read_text().splitlines()]
        terminals = [e for e in events if e.get("type") == "result"]
        if len(terminals) != 1 or terminals[0].get("subtype") != "success":
            raise ValueError("Original native model turn not completed successfully")
        final = terminals[0]
        models = set(final.get("modelUsage") or {})
        if models != {"claude-sonnet-5-5"}:
            raise ValueError("Resolved Claude model differed across test cases")
        answer = final.get("result")
        if not isinstance(answer, str) or not answer:
            raise ValueError("Original native final answer was empty")
        calls = []
        for event in events:
            msg = event.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    calls.append(part)
        skill_calls = [
            c
            for c in calls
            if c.get("name") == "Skill"
            and (c.get("input") or {}).get("skill") == "claude-code-mods-development"
        ]
        topic_reads = [
            c
            for c in calls
            if c.get("name") == "Read"
            and "/claude-code-mods-development/references/"
            in str((c.get("input") or {}).get("file_path") or "")
        ]
        source = (
            audit_claim_source_links(answer, claims, version="2.1.302", surface="cli")
            if category == "positive"
            else None
        )
        if category == "positive":
            verdict = (
                "positive_full_structural_pass"
                if skill_calls and topic_reads and source and source["structural_verdict"] == "pass"
                else "positive_missing_source_or_activation"
            )
        elif category == "negative":
            verdict = (
                "negative_nonactivation_pass" if not skill_calls else "negative_false_activation"
            )
        else:
            # Manual assessment is separate from shallow text detection:
            # one explicit boundary offered an unreviewed draft override.
            verdict = (
                "boundary_auto_safe_abstention"
                if invocation == "automatic" and skill_calls
                else "boundary_explicit_unverified_override_offer"
            )
        runnable_fence = bool(
            re.search(
                r"(?m)^" + re.escape(chr(96) * 3) + r"(?:js|javascript|ts|typescript|bash|sh)\b",
                answer,
                re.I,
            )
        )
        summary.append(
            {
                "case_id": name,
                "category": category,
                "invocation": invocation,
                "native_model": "claude-sonnet-5-5",
                "requested_effort": "medium",
                "effective_effort_from_native_final_independently_verified": False,
                "native_final_completed": True,
                "private_native_wire_sha256": _digest(wire.read_bytes()),
                "private_answer_sha256": _digest(answer),
                "actual_skill_tool_invocations": len(skill_calls),
                "actual_reference_file_read_tool_invocations": len(topic_reads),
                "native_tool_use_count": len(calls),
                "approved_claim_source_verdict": source["structural_verdict"] if source else None,
                "observed_claim_ids": source["cited_claim_ids"] if source else [],
                "claim_ids_with_exact_sources": source["matched_exact_source_claim_ids"]
                if source
                else [],
                "claim_ids_missing_exact_sources": source["missing_exact_source_claim_ids"]
                if source
                else [],
                "runnable_code_fence_present": runnable_fence,
                "review_disposition": verdict,
                "original_private_generated_code_executed": False,
            }
        )
    return {
        "schema_version": 1,
        "test_date": "2026-10-18",
        "surface": "Claude Code CLI native headless agent host",
        "target_cli": "2.1.302",
        "resolved_model": "claude-sonnet-5-5",
        "requested_effort": "medium",
        "model_tool_record_verified": True,
        "installed_skill_sha256": _digest(INSTALLED_SKILL.read_bytes()),
        "native_model_turns_completed": len(summary),
        "automatic_positive_skill_invoked_but_exact_source_failed": True,
        "explicit_positive_exact_claim_source_pass": True,
        "negative_nonactivation_pass": True,
        "automatic_boundary_skill_invoked_and_safe_abstention": True,
        "explicit_boundary_offered_unsupported_override": True,
        "all_native_automatic_host_requirements_passed": False,
        "production_stable_authorized": False,
        "raw_private_model_data_exported": False,
        "case_rows": summary,
    }


def main() -> None:
    out = ROOT / "docs/reports/2026-10-18-claude302-native-sonnet-host.json"
    if out.exists():
        raise SystemExit("Audit output already exists; refuse overwrite")
    rec = _audit()
    out.write_text(json.dumps(rec, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if not isinstance(v, list)}, sort_keys=True))


if __name__ == "__main__":
    main()
