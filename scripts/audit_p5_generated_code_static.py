#!/usr/bin/env python3
"""Audit PRIVATE Codex P5 answers without executing or publishing model-origin code.

This checks frozen native provenance, observed answer hashes, Markdown code fences
and JavaScript *syntax*. It never runs model code, invokes a Mod loader with model
code, modifies original trial artifacts or grants semantic approval.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from run_p5_codex_evidence_ab_case import PRIVATE, _native_model_answer
from score_p5_codex_evidence_ab import frozen, row

# Single-line language labels only. Ignore any non-fenced prose.
_FENCE = re.escape(chr(96) * 3)
_BLOCK = re.compile(
    rf"(?ms)^{_FENCE}(?P<lang>[a-zA-Z0-9_+.-]{{0,24}})[ \t]*\n"
    rf"(?P<content>.*?)^{_FENCE}[ \t]*$"
)
_JS = frozenset(("js", "javascript", "mjs", "cjs"))
_SHELL = frozenset(("sh", "bash", "shell", "zsh"))
_MAX_ANSWER = 200_000
_MAX_CODE = 65_536


class StaticAuditBlocked(ValueError):
    """Never publish a result when provenance, bounds or static tools fail."""


def code_blocks(answer: str) -> list[tuple[str, str]]:
    if not isinstance(answer, str) or not answer or len(answer) > _MAX_ANSWER:
        raise StaticAuditBlocked("Absent or unbounded private model answer")
    blocks: list[tuple[str, str]] = []
    for match in _BLOCK.finditer(answer):
        language = match.group("lang").lower()
        code = match.group("content")
        if len(code.encode("utf-8")) > _MAX_CODE:
            raise StaticAuditBlocked("Code block exceeds syntax-only review limit")
        blocks.append((language, code))
    return blocks


def javascript_syntax_ok(code: str, *, node: str | None = None) -> bool:
    """Node --check parses stdin but does NOT execute model-provided content."""
    if not isinstance(code, str) or not code or len(code.encode("utf-8")) > _MAX_CODE:
        raise StaticAuditBlocked("Invalid or unbounded static syntax input")
    exe = node or shutil.which("node")
    if not exe or not Path(exe).is_file():
        raise StaticAuditBlocked("No resolved local Node syntax checker")
    try:
        # Owner-only disposable working directory; no user HOME/module hooks.
        with tempfile.TemporaryDirectory(prefix="mods-static-syntax-") as isolated:
            result = subprocess.run(  # noqa: S603 -- syntax-only stdin, no shell
                [exe, "--check", "--input-type=module"],
                input=code,
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
                cwd=isolated,
                env={"NODE_OPTIONS": "", "HOME": isolated, "PATH": os.defpath},
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StaticAuditBlocked("Isolated syntax-only subprocess unavailable") from exc
    # Do not include stderr: it may quote PRIVATE model content.
    return result.returncode == 0


def audit() -> dict:
    manifest, all_cases, claims = frozen()
    records = []
    for case_id in manifest["case_ids"]:
        case = all_cases[case_id]
        if case["category"] != "positive":
            continue
        for trial in (1, 2, 3):
            native = row("C_context_gate", trial, case, claims)
            if (
                native["status"] != "observed"
                or native["native_completed"] is not True
                or native["actual_v3_skill_read"] is not True
                or native["semantic_mod_runtime_verified"] is not False
            ):
                raise StaticAuditBlocked("Unverified frozen positive native case")
            home = PRIVATE / "cases" / "C_context_gate" / case_id / f"trial-{trial}"
            answer = _native_model_answer(home / "native-wire.jsonl")
            if hashlib.sha256(answer.encode()).hexdigest() != native["original_answer_sha256"]:
                raise StaticAuditBlocked("Native model answer SHA mismatch")
            blocks = code_blocks(answer)
            javascript = [content for lang, content in blocks if lang in _JS]
            parsed = [javascript_syntax_ok(content) for content in javascript]
            records.append(
                {
                    "case_id": case_id,
                    "trial": trial,
                    "answer_sha256_verified": True,
                    "code_fence_count": len(blocks),
                    "javascript_fence_count": len(javascript),
                    "javascript_syntax_pass": sum(parsed),
                    "javascript_syntax_fail": len(parsed) - sum(parsed),
                    "shell_fence_count": sum(lang in _SHELL for lang, _ in blocks),
                    "postflight_code_reason_present": (
                        "runnable_mod_code_needs_native_target_semantic_test"
                        in (native["P3_gate_reasons"] or [])
                    ),
                }
            )
    if len(records) != 12:
        raise StaticAuditBlocked("Expected exactly twelve C-condition positive native replies")
    result = {
        "schema_version": 1,
        "purpose": "static syntax triage ONLY; not native Mods code semantics",
        "cohort": "Codex native frozen C_context_gate positive 4 cases x 3 repeats",
        "observed_verified_native_answers": len(records),
        "original_answer_sha256_verified": sum(item["answer_sha256_verified"] for item in records),
        "answers_with_fences": sum(item["code_fence_count"] > 0 for item in records),
        "javascript_code_blocks": sum(item["javascript_fence_count"] for item in records),
        "javascript_syntax_pass": sum(item["javascript_syntax_pass"] for item in records),
        "javascript_syntax_fail": sum(item["javascript_syntax_fail"] for item in records),
        "shell_code_blocks_not_executed": sum(item["shell_fence_count"] for item in records),
        "P3_blocked_code_reason": sum(item["postflight_code_reason_present"] for item in records),
        "all_model_origin_code_executed": False,
        "native_mod_semantics_verified": False,
        "promote_production_skill_or_gate": False,
        "model_text_or_private_path_exported": False,
        "per_case_metadata": records,
    }
    return result


def main() -> None:
    try:
        output = audit()
    except (OSError, ValueError) as exc:
        # Fail closed without leaking exceptions containing private file paths.
        raise SystemExit(f"P5 static audit BLOCKED: {type(exc).__name__}") from None
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
