"""Conservative, offline lint for Claude Code Mods answer-code hazards.

This is a risk-signal scanner, *not* full semantic verification. It returns
only flags, a response checksum and a case ID, never source text or secrets.
"""

from __future__ import annotations

import hashlib
import json
import re

_CASE = re.compile(r"[A-Z][A-Z0-9_-]{3,60}\Z")
_BLOCK = re.compile(
    r"```[A-Za-z0-9_-]*[^\n]*\n(?P<fenced>[\s\S]*?)\n```"
    r"|<CodeBlock\b[^>]*>(?P<component>[\s\S]*?)</CodeBlock>",
    re.IGNORECASE,
)
# A default export does not satisfy the named `register` export required by
# Claude Code CLI 2.1.296, even when the callback args themselves are correct.
_BAD_EXPORT = re.compile(r"\bexport\s+default\s+(?:async\s+)?function\s+register\s*\(", re.I)
_BAD_DESTRUCTURED_REGISTER = re.compile(
    r"\bexport\s+default\s+(?:async\s+)?function\s+register\s*\(\s*\{\s*on\s*\}",
    re.I,
)
# In Mods a tool.call filter object (e.g. { tool: 'Bash' }) may occur
# between the event name and the callback. An (e, next) callback is wrong
# with or without this filter because the first parameter is the Mods $ API.
# Bounded, simple filters only: no attempt to parse arbitrary TypeScript.
_BAD_HOOK = re.compile(
    r"\bon\s*\(\s*['\"]tool\.call['\"]\s*,\s*"
    r"(?:\{[^{}]{1,512}\}\s*,\s*)?"
    r"async\s*\(\s*e\s*,\s*next\s*\)",
    re.I,
)
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
    strict_command = bool(
        re.search(r"\bclaude\s+plugin\s+validate\b[^\n]{0,160}--strict\b", answer, re.I)
    )
    for code, intro in _code_spans(answer):
        # The manifest's author field is optional for non-strict validation,
        # but its absence produces a warning that fails --strict on CLI 2.1.296.
        # Only flag actual .claude-plugin/plugin.json examples paired with a
        # recommended strict validation command, not unrelated JSON snippets.
        if strict_command and re.search(r"\.claude-plugin/plugin\.json", intro, re.I):
            try:
                document = json.loads(code)
            except ValueError:
                document = None
            if (
                isinstance(document, dict)
                and {"name", "version"} <= set(document)
                and not document.get("author")
            ):
                if re.search(
                    r"incorrect|wrong|will fail|fails strict|do not use|错误示例|不正确|错误",
                    intro,
                    re.I,
                ):
                    review.add("strict-author-example-needs-manual-review")
                else:
                    hard.add("strict-validate-manifest-author-warning")
        negated = bool(_NEGATIVE.search(intro.rstrip()))

        def is_negated(match: re.Match[str], snippet: str = code, preface: bool = negated) -> bool:
            before = snippet[: match.start()].rstrip()
            comment = before.splitlines()[-1] if before else ""
            negative_comment = bool(
                re.match(
                    r"\s*(?://|#|/\*)\s*(?:错误|不正确|wrong|incorrect|do not|don't)",
                    comment,
                    re.I,
                )
            )
            return preface or negative_comment

        bad_export = _BAD_EXPORT.search(code)
        if bad_export:
            if is_negated(bad_export):
                review.add("register-export-example-needs-manual-review")
            elif _BAD_DESTRUCTURED_REGISTER.search(code):
                # Keep the original risk key stable for existing saved reports.
                hard.add("unsupported-default-register-destructuring")
            else:
                hard.add("unsupported-default-register-export")
        bad_hook = _BAD_HOOK.search(code)
        if bad_hook:
            if is_negated(bad_hook):
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
            r"(do not use|do not write|not.*current|historical|outdated|obsolete|"
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
