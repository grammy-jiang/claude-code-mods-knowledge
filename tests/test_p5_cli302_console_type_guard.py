"""Real native CLI302 core typing: no unsupported Mod hook console globals.

Three of five genuine original Codex/Sonnet Mod examples failed TS2584.
Keep the old 2.1.296 Skill untouched and never certify future 2.1.303.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mods_knowledge.answer_lint import lint_mods_answer
from mods_knowledge.claims import load_claims
from mods_knowledge.compiler import (
    compile_knowledge,
)
from mods_knowledge.p5_native_evidence import _source_and_lint
from mods_knowledge.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/reports/2026-10-19-p5-cli302-original-code-core-type-audit.json"
RISK = "mods-cli302-unsupported-console-global"
FENCE = chr(96) * 3


def test_cli302_skill_teaches_first_party_typed_diagnostics_on_all_five_hosts():
    evidence = json.loads(EVIDENCE.read_text())
    assert (
        evidence["core_declarations_sha256"]
        == "8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e"
    )
    assert evidence["original_fail"] == 3
    assert evidence["test_only_ui_log_remediation_typecheck_pass"] == 5
    result = compile_knowledge(
        ROOT, api_version="2.1.302", surface="cli", source_revision="p5-typed302"
    )
    skills = [v.decode() for k, v in result.items() if k.endswith("/SKILL.md")]
    assert len(skills) == 5 and len(set(skills)) == 1
    for content in skills:
        assert "console.log" in content
        assert '$.ui.log(text, { to: "debug" })' in content
        assert "No Node/DOM" in content
        assert "next(e)" in content
        assert "mock" in content.lower()
        assert len(content) < 9000


def test_old_compiled_cli296_remains_unchanged():
    m = compile_knowledge(ROOT, api_version="2.1.296", surface="cli", source_revision="p5-typed302")
    s = m["common/claude-code-mods-development/SKILL.md"].decode()
    assert "CLI 2.1.302 hook types" not in s
    assert '$.ui.log(text, { to: "debug" })' not in s


@pytest.mark.parametrize(
    "code",
    (
        'export function register(on) { on("tool.call", async ($, e, next) => '
        "{ try { return await next(e) } finally {"
        'try { await Promise.resolve(console.log("observer done")) } catch {} } }) }',
        'export function register(on) { on("tool.call", async ($, e, next) => '
        '{ console.info("diagnostic"); return next(e) }) }',
    ),
)
def test_original_console_based_mod_code_is_known_type_risk(code: str):
    answer = "Claude Code CLI 2.1.302 Mod:\n" + FENCE + "js\n" + code + "\n" + FENCE
    report = lint_mods_answer(answer, case_id="POS-E-01", target_version="2.1.302")
    assert RISK in report["risk_flags"]
    assert report["semantic_review_complete"] is False
    assert report["verdict"] == "known_risk"


def test_non_mod_and_historical_version_not_falsely_flagged():
    generic = "Ordinary TypeScript:\n" + FENCE + "js\nconsole.log('hi')\n" + FENCE
    r = lint_mods_answer(generic, case_id="NEG-TYPESCRIPT", target_version="2.1.302")
    assert RISK not in r["risk_flags"]
    old = (
        "Mods code:\n"
        + FENCE
        + 'js\non("tool.call", async ($,e,next)=>{console.log("x");return next(e)})\n'
        + FENCE
    )
    r2 = lint_mods_answer(old, case_id="POS-E-01", target_version="2.1.296")
    assert RISK not in r2["risk_flags"]


def test_first_party_ui_logger_is_not_the_bad_console_global():
    code = (
        'export function register(on) { on("tool.call", async ($, e, next) => {'
        " try { return await next(e) } finally { "
        'try { $.ui.log("observer done", { to: "debug" }) } catch {} } }) }'
    )
    r = lint_mods_answer(
        FENCE + "js\n" + code + "\n" + FENCE, case_id="POS-E-01", target_version="2.1.302"
    )
    assert RISK not in r["risk_flags"]


def test_deliberately_bad_example_needs_review_not_a_source_pass():
    code = 'on("tool.call", async ($,e,next)=>{console.log("x");return next(e)})'
    answer = "❌ Incorrect Mod example:\n" + FENCE + "js\n" + code + "\n" + FENCE
    r = lint_mods_answer(answer, case_id="POS-E-01", target_version="2.1.302")
    assert RISK not in r["risk_flags"]
    assert "cli302-console-negative-example-requires-review" in r["requires_manual_review"]


def test_unreviewed_future_cli_is_never_assumed_compatible():
    with pytest.raises(ValueError):
        lint_mods_answer("Hello", case_id="POS-E-01", target_version="2.1.303")


def test_p5_actual_native_scorer_propagates_explicit_target_version():
    claims = load_claims(
        ROOT / "claims",
        load_registry(ROOT / "sources/registry.json"),
        ROOT / "sources/snapshots",
        ROOT / "decisions",
    )
    case = {"id": "POS-E-01", "category": "positive", "expected_claim_ids": []}
    snippet = (
        "Claude Code CLI 2.1.302 Mod code:\n"
        + FENCE
        + "js\n"
        + 'export function register(on) { on("tool.call", async ($,e,next)=>{'
        " try { return await next(e) } finally {"
        ' try { await Promise.resolve(console.log("done")) } catch {} } }) }' + "\n" + FENCE
    )
    result = _source_and_lint(case, snippet, claims, target_version="2.1.302")
    assert RISK in result["risk_flags"]
    old = _source_and_lint(case, snippet, claims, target_version="2.1.296")
    assert RISK not in old["risk_flags"]


def test_cli_answer_lint_public_interface_accepts_only_reviewed_version(tmp_path: Path):
    from mods_knowledge.cli import main

    src = tmp_path / "original-reply.private.txt"
    src.write_text(
        FENCE + "js\n" + 'export function register(on) {on("tool.call", ($,e,next)=>{'
        ' console.log("diagnostic");return next(e)})}' + "\n" + FENCE
    )
    out = tmp_path / "redacted-evidence.json"
    rc = main(
        [
            "answer-lint",
            "--answer-file",
            str(src),
            "--case-id",
            "POS-E-01",
            "--target-version",
            "2.1.302",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    obj = json.loads(out.read_text())
    assert RISK in obj["risk_flags"]
    assert "console.log" not in out.read_text()
