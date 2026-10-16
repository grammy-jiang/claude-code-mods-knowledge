"""Conservative, offline lint for Claude Code Mods answer-code hazards.

This is a risk-signal scanner, *not* full semantic verification. It returns
only flags, a response checksum and a case ID, never source text or secrets.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex

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
# A named `register` export with a destructured `on` parameter also fails
# the actual CLI 2.1.296 strict Hook loader: it requires a plain name.
_BAD_NAMED_DESTRUCTURED_REGISTER = re.compile(
    r"\bexport\s+(?:async\s+)?function\s+register\s*\(\s*\{\s*on\b",
    re.I,
)
# Actual CLI 2.1.296 also requires the first parameter of a direct named
# const/function-expression register entry to be a *plain identifier*.
# Named const destructuring, including a separately exported local register,
# failed native strict validation and the offline mocked test loader.
# Limit this to source-backed direct forms, not general JavaScript parsing.
_BAD_CONST_DESTRUCTURED_REGISTER = re.compile(
    r"(?m)^[ \t]*(?P<export>export[ \t]+)?const[ \t]+register\s*=\s*"
    r"(?:async\s+)?(?:\(\s*\{|function\s*\(\s*\{)",
    re.I,
)
_LOCAL_REGISTER_EXPORTED = re.compile(r"\bexport\s*\{\s*register\s*(?:[,}])", re.I)
# A simple named `register` function declaration or const function value is
# statically recognized by the target CLI 2.1.296. A factory invocation or
# an exported assignment to a separately named variable is NOT equivalent:
# native strict validation and its offline mock loader rejected both.
# These patterns intentionally match only source-backed known-bad shapes;
# they do not claim to parse general JavaScript or certify other exports.
_INDIRECT_REGISTER_FACTORY = re.compile(
    r"(?m)^[ \t]*export\s+const\s+register\s*=\s*"
    r"(?!function\b|async\b)(?:[$A-Za-z_][$\w]*\.)*[$A-Za-z_][$\w]*\s*\(",
    re.I,
)
_INDIRECT_REGISTER_ALIAS = re.compile(
    r"(?m)^[ \t]*export\s+const\s+register\s*=\s*"
    r"(?!function\b|async\b)[$A-Za-z_][$\w]*[ \t]*(?:;|$)",
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
# A path is REQUIRED by native `claude plugin validate` in CLI 2.1.296.
# `claude plugin test` differs: its directory argument is optional.
# Only inspect line-leading shell commands in executable examples; a plain
# explanation mentioning the command is not a runnable instruction.
_VALIDATE_LINE = re.compile(
    r"(?m)^[ \t]*(?:\$[ \t]+)?claude[ \t]+plugin[ \t]+validate\b(?P<args>[^\n]*)",
    re.I,
)
_DTS = "https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts"
_ECOMMAND = re.compile(r"\be\.command\b")
# Native-bounded observer safety: a diagnostic can throw/reject. If a
# handler calls an unprotected logger AFTER awaiting next(e), a successful
# tool result can be replaced by the logger failure; an unprotected log in
# catch(error) can also mask the ORIGINAL downstream rejection. Pure regex is
# intentionally narrow: scan only bounded snippets without an inner try {}.
# These signals never by themselves constitute full runnable-code QA.
_DIAGNOSTIC_CALL = r"(?:console\.(?:log|warn|info|error)|\$\s*\.\s*ui\s*\.\s*log)"
_UNGUARDED_POST_NEXT_LOG = re.compile(
    r"\b(?:const|let|var)\s+[$A-Za-z_][$\w]*\s*=\s*await\s+next\s*\(\s*e\s*\)\s*;"
    r"(?:(?!\btry\s*\{|\bfinally\s*\{|\bcatch\s*(?:\(|\{))[\s\S]){0,500}?"
    + _DIAGNOSTIC_CALL
    + r"\s*\(",
    re.I,
)
_UNGUARDED_CATCH_LOG = re.compile(
    r"\bcatch\s*\(\s*[$A-Za-z_][$\w]*\s*\)\s*\{"
    r"(?:(?!\btry\s*\{|\bfinally\s*\{)[\s\S]){0,300}?" + _DIAGNOSTIC_CALL + r"\s*\(",
    re.I,
)
# Narrow additional cases: an unprotected diagnostic in a finally block
# *still* replaces the downstream result/error when it throws, including the
# `try { return await next(e) } finally { console.log(...) }` form. Only
# match bounded simple block openings; this is a risk signal, not a JS parser.
_UNGUARDED_FINALLY_LOG = re.compile(
    r"\bfinally\s*\{(?:(?!\btry\s*\{)[\s\S]){0,320}?" + _DIAGNOSTIC_CALL + r"\s*\(",
    re.I,
)
# A synchronous try/catch does not catch a diagnostic Promise that rejects
# later. The return type might be unknown, so issue a manual review flag
# rather than assuming every console logger is asynchronous.
_PROTECTED_FINALLY_DIAGNOSTIC = re.compile(
    r"\bfinally\s*\{\s*try\s*\{(?P<body>[\s\S]{0,320}?)\}\s*catch"
    r"\s*(?:\([^)]{0,80}\))?\s*\{",
    re.I,
)
_AWAITED_DIAGNOSTIC = re.compile(
    r"\bawait\s+(?:Promise\s*\.\s*resolve\s*\(\s*)?" + _DIAGNOSTIC_CALL + r"\s*\(",
    re.I,
)
_NEGATIVE = re.compile(
    r"(?:incorrect|wrong|bad example|do not use|never use|"
    r"不正确|错误示例|不要|不能这么写|以下是错)[^.!?\n]{0,90}$",
    re.I,
)


# A visible answer may intentionally show an *unsafe* code block as a
# counterexample under a two-line heading. The old anchored _NEGATIVE regex
# missed that context. Last explicit heading wins, so a later heading saying
# "correct / recommended" must not conceal risky runnable code.
_WRONG_LABEL = re.compile(
    r"(?:❌|错误|不正确|反例|不安全|wrong\b|incorrect\b|"
    r"do not use|don't use|unsafe\b|avoid\b)",
    re.I,
)
_RIGHT_LABEL = re.compile(
    r"(?:✅|正确|推荐|correct\b|recommended\b|\bsafe pattern\b|\buse this\b)",
    re.I,
)


def _clearly_negative_code_preface(preface: str) -> bool:
    lines = [line.strip() for line in preface.splitlines() if line.strip()]
    last_marker = None
    for line in lines[-3:]:
        if len(line) > 120:
            continue
        wrong = list(_WRONG_LABEL.finditer(line))
        right = list(_RIGHT_LABEL.finditer(line))
        if wrong or right:
            latest_wrong = max((m.start() for m in wrong), default=-1)
            latest_right = max((m.start() for m in right), default=-1)
            last_marker = "wrong" if latest_wrong > latest_right else "right"
    return last_marker == "wrong" or bool(_NEGATIVE.search(preface.rstrip()))


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
        negated = _clearly_negative_code_preface(intro)

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
        bad_named = _BAD_NAMED_DESTRUCTURED_REGISTER.search(code)
        if bad_named:
            if is_negated(bad_named):
                review.add("register-export-example-needs-manual-review")
            else:
                hard.add("unsupported-named-register-destructuring")
        bad_const = _BAD_CONST_DESTRUCTURED_REGISTER.search(code)
        if bad_const and (bad_const.group("export") or _LOCAL_REGISTER_EXPORTED.search(code)):
            if is_negated(bad_const):
                review.add("register-export-example-needs-manual-review")
            else:
                hard.add("unsupported-named-register-destructuring")
        for bad_form, risk in (
            (_INDIRECT_REGISTER_FACTORY, "register-indirect-factory-export"),
            (_INDIRECT_REGISTER_ALIAS, "register-indirect-alias-export"),
        ):
            found = bad_form.search(code)
            if found:
                if is_negated(found):
                    review.add("register-indirect-export-negative-example-needs-manual-review")
                else:
                    hard.add(risk)
        bad_hook = _BAD_HOOK.search(code)
        if bad_hook:
            if is_negated(bad_hook):
                review.add("callback-arity-negative-example-needs-manual-review")
            else:
                hard.add("missing-hook-api-argument")
        if _SINGLE_FILE.search(code) and not negated:
            hard.add("plugin-test-expects-mod-directory")
        for validation in _VALIDATE_LINE.finditer(code):
            raw_args = validation.group("args").split("#", 1)[0].strip()
            # A shell line continued with a backslash may have the actual
            # path on the following line; do not fabricate a missing argument.
            if raw_args.endswith("\\"):
                review.add("plugin-validate-multiline-command-needs-manual-review")
                continue
            try:
                args = shlex.split(raw_args)
            except ValueError:
                review.add("plugin-validate-arguments-needs-manual-review")
                continue
            if "--help" in args or "-h" in args:
                continue
            has_directory = any(arg != "--" and not arg.startswith("-") for arg in args)
            if not has_directory:
                if is_negated(validation):
                    review.add("plugin-validate-missing-path-negative-example-needs-manual-review")
                else:
                    hard.add("plugin-validate-missing-path")
        if "tool.call" in code and re.search(r"\bnext\s*\(\s*e\s*\)", code):
            for regex, risk_name in (
                (_UNGUARDED_POST_NEXT_LOG, "observer-post-next-diagnostics-not-isolated"),
                (_UNGUARDED_CATCH_LOG, "observer-catch-diagnostics-can-mask-error"),
                (_UNGUARDED_FINALLY_LOG, "observer-finally-diagnostics-not-isolated"),
            ):
                unsafe = regex.search(code)
                if unsafe:
                    if is_negated(unsafe):
                        review.add("observer-diagnostic-negative-example-needs-manual-review")
                    else:
                        hard.add(risk_name)
            # This only identifies uncertain async behavior, never claims a
            # full semantic verdict. The guarded logging operation must be
            # awaited (or have an equivalent Promise rejection handler).
            protected = _PROTECTED_FINALLY_DIAGNOSTIC.search(code)
            if protected and re.search(_DIAGNOSTIC_CALL + r"\s*\(", protected.group("body"), re.I):
                if not _AWAITED_DIAGNOSTIC.search(protected.group("body")):
                    review.add("observer-async-diagnostic-unawaited-needs-manual-review")
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
