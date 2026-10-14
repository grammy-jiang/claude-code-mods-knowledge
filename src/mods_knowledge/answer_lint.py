"""Conservative, offline lint for Claude Code Mods answer-code hazards.

This is a risk-signal scanner, *not* full semantic verification. It returns
only flags, a response checksum and a case ID, never source text or secrets.
"""

from __future__ import annotations

import hashlib
import re

_CASE = re.compile(r"[A-Z][A-Z0-9_-]{3,60}\Z")
_BLOCK = re.compile(
    r"```[A-Za-z0-9_-]*[^\n]*\n(?P<fenced>[\s\S]*?)\n```"
    r"|<CodeBlock\b[^>]*>(?P<component>[\s\S]*?)</CodeBlock>",
    re.IGNORECASE,
)
_BAD_EXPORT = re.compile(r"export\s+default\s+function\s+register\s*\(\s*\{\s*on\s*\}", re.I)
_BAD_HOOK = re.compile(r"\bon\s*\(\s*['\"]tool\.call['\"]\s*,\s*async\s*\(\s*e\s*,\s*next\s*\)")
_SINGLE_FILE = re.compile(r"\bclaude\s+plugin\s+test\s+(?:\S+/)?\S*\.test\.tsx?(?:\s|$)", re.I)
_DTS = "https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts"
_ECOMMAND = re.compile(r"\be\.command\b")
_NEGATIVE = re.compile(
    r"(?:incorrect|wrong|bad example|do not use|never use|"
    r"不正确|错误示例|不要|不能这么写|以下是错)[^.!?\n]{0,90}$",
    re.I,
)


def _code_spans(answer: str) -> list[tuple[str, str]]:
    result = []
    for match in _BLOCK.finditer(answer):
        code = match.group("fenced") or match.group("component") or ""
        intro = answer[max(0, match.start() - 140) : match.start()]
        result.append((code, intro))
    return result


def lint_mods_answer(answer: str, *, case_id: str) -> dict:
    """Flag known high-risk constructs without inferring an unobserved model pass."""
    if not isinstance(case_id, str) or not _CASE.fullmatch(case_id):
        raise ValueError("Case ID must be a bounded P4-like identifier")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("A nonempty observed model reply is required")
    hard: set[str] = set()
    review: set[str] = set()
    for code, intro in _code_spans(answer):
        negated = bool(_NEGATIVE.search(intro.rstrip()))
        if _BAD_EXPORT.search(code):
            if negated:
                review.add("register-export-example-needs-manual-review")
            else:
                hard.add("unsupported-default-register-destructuring")
        if _BAD_HOOK.search(code):
            if negated:
                review.add("callback-arity-negative-example-needs-manual-review")
            else:
                hard.add("missing-hook-api-argument")
        if _SINGLE_FILE.search(code) and not negated:
            hard.add("plugin-test-expects-mod-directory")
        if _ECOMMAND.search(code) and "tool.call" in code:
            review.add("event-field-shape-needs-local-types")
    if _DTS in answer:
        window_start = answer.index(_DTS)
        preceding = answer[max(0, window_start - 110) : window_start].lower()
        if not re.search(
            r"(do not use|not.*current|historical|outdated|obsolete|"
            r"不要用|不是当前|已过时|历史)",
            preceding,
        ):
            hard.add("historical-early-access-types-reference")
    return {
        "schema_version": 1,
        "case_id": case_id,
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        "risk_flags": sorted(hard),
        "requires_manual_review": sorted(review),
        "semantic_review_complete": False,
        "verdict": "known_risk" if hard else "unverified",
        "scope": "Known hazards only; absence of flags never establishes API correctness",
    }
