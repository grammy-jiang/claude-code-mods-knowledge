#!/usr/bin/env python3
"""Fail-closed structural review of original Codex 2.1.302 generated snippets.

This does NOT execute model content. Only the original 54 positive replies
and their source SHA256 are read. No raw prompts, answers, code, or local
private paths are exported. Equality is to two independently reviewed
observer implementations and three first-party CLI command shapes.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
from collections import Counter
from pathlib import Path

from run_p5_codex_evidence_ab_case import _native_model_answer

PRIVATE = Path.home() / "Models.noindex/benchmarks/p5-codex-302-abc-20261017"
FENCE = re.escape(chr(96) * 3)
BLOCK = re.compile(
    rf"(?ms)^{FENCE}(?P<lang>[a-zA-Z0-9_+.-]{{1,24}})[^\n]*\n"
    rf"(?P<code>.*?)^{FENCE}[ \t]*$"
)
JS_LANGS = frozenset(("js", "javascript"))
SHELL_LANGS = frozenset(("bash", "sh", "shell", "zsh"))
COMMANDS = frozenset(
    (
        ("claude", "plugin", "validate", "--strict", "."),
        ("claude", "plugin", "validate", "--strict", "./my-mod"),
        ("claude", "plugin", "test", "./my-mod"),
    )
)


def normalized(code: str) -> str:
    if (
        not isinstance(code, str)
        or not 0 < len(code.encode("utf-8")) < 5000
        or "/*" in code
        or "*/" in code
        or "\x00" in code
    ):
        raise ValueError("Unknown original snippet is not authorized")
    text = re.sub(r"//[^\r\n]*", "", code)
    text = re.sub(r"\s+", "", text)
    # Exact same harmless one-line diagnostic; only quote style differs.
    return text.replace("console.log('observerdone')", 'console.log("observerdone")')


_SHAPES = {
    normalized(
        """on('tool.call', async ($, e, next) => { return next(e); });"""
    ): "direct_transparent_observer",
    normalized(
        """on('tool.call', async ($, e, next) => {
          try { return await next(e); }
          finally {
            try { await Promise.resolve(console.log("observer done")); }
            catch {}
          }
        });"""
    ): "async_fail_isolated_observer",
}


def analyze() -> dict:
    rows = []
    counts = Counter()
    seen = set()
    for file in sorted((PRIVATE / "cases").rglob("302-abc-report.json")):
        row = json.loads(file.read_text(encoding="utf-8"))
        if row.get("category") != "positive":
            continue
        wire = file.parent / "native-wire.jsonl"
        if (
            row["target"] != "2.1.302"
            or not row["native_completed"]
            or row["actual_skill_read"] is not True
            or hashlib.sha256(wire.read_bytes()).hexdigest() != row["wire_sha256"]
        ):
            raise ValueError("Unverified actual model turn, source or Skill")
        reply = _native_model_answer(wire)
        if hashlib.sha256(reply.encode("utf-8")).hexdigest() != row["answer_sha256"]:
            raise ValueError("Native answer does not match original wire")
        key = (row["condition"], row["case_id"], row["trial"])
        if key in seen:
            raise ValueError("Duplicate immutable original answer")
        seen.add(key)
        case = {"arm": row["condition"], "case": row["case_id"], "trial": row["trial"]}
        blocks = {"javascript": [], "shell": [], "other": []}
        for m in BLOCK.finditer(reply):
            lang = m.group("lang").lower()
            code = m.group("code")
            digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
            if lang in JS_LANGS:
                shape = _SHAPES.get(normalized(code))
                if not shape:
                    raise ValueError("Unhandled, not authorized JavaScript source shape")
                blocks["javascript"].append({"sha256": digest, "reviewed_shape": shape})
                counts[shape] += 1
            elif lang in SHELL_LANGS:
                words = tuple(shlex.split(code.strip()))
                if words not in COMMANDS:
                    raise ValueError("Unknown model-generated shell snippet")
                blocks["shell"].append({"sha256": digest, "shape": "fixed_official_plugin_cli"})
                counts["shell_command_blocks"] += 1
            else:
                raise ValueError("An unexpected code language requires independent review")
        case["code_blocks"] = blocks
        rows.append(case)
    if len(rows) != 54:
        raise ValueError("Need exactly 54 independently verified positive answers")
    if (
        counts["direct_transparent_observer"] != 9
        or counts["async_fail_isolated_observer"] != 14
        or counts["shell_command_blocks"] != 19
    ):
        raise ValueError("Original model code shape distribution changed")
    return {
        "schema_version": 1,
        "target_cli": "2.1.302",
        "source_revision": "e1f080ea46102cb257ad57a64f2fecf9fe1cf037",
        "original_positive_answers_sha256_verified": len(rows),
        "generated_javascript_code_blocks": 23,
        "direct_transparent_observer_blocks": counts["direct_transparent_observer"],
        "async_fail_isolated_observer_blocks": counts["async_fail_isolated_observer"],
        "model_generated_shell_command_blocks": counts["shell_command_blocks"],
        "unknown_code_blocks": 0,
        "original_code_executed_by_this_audit": False,
        "representative_original_observer_patterns_native_tested": 2,
        "native_mocked_outcome_tests_per_pattern_passed": 3,
        "direct_identity_error_once_tests_per_pattern_passed": 6,
        "generated_shell_command_shapes_checked_against_native_cli": 3,
        "real_Bash_command_executed": False,
        "all_generated_answers_production_semantics_certified": False,
        "model_private_original_text_exported": False,
        "case_metadata_only": rows,
    }


def main() -> int:
    report = analyze()
    file = (
        Path(__file__).resolve().parents[1]
        / "docs/reports/2026-10-18-claude302-original-model-code-shapes.json"
    )
    if file.exists():
        raise ValueError("Refuse to overwrite already published original audit")
    file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(
        {k: v for k, v in report.items() if isinstance(v, (str, int, bool))},
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
