"""The native tool.call registration catch is distinct from local logger catch.

A 3-space indented real Sonnet code example must not evade the scanner.
This bounded lexical scanner is an offline signal, never full JavaScript QA.
"""

from __future__ import annotations

from mods_knowledge.answer_lint import lint_mods_answer

F = chr(96) * 3
RISK = "mods-cli302-tool-call-registration-without-catch"


def fenced(js: str, indent: str = "") -> str:
    return (
        "Use this Claude Code Mod:\n"
        + indent
        + F
        + "js\n"
        + "\n".join(indent + line for line in js.splitlines())
        + "\n"
        + indent
        + F
    )


def risk(js: str, *, version: str = "2.1.302", indent: str = "") -> dict:
    return lint_mods_answer(fenced(js, indent), case_id="POS-E-01", target_version=version)


def test_incomplete_original_tool_call_registration_is_risky():
    js = "export function register(on) { on('tool.call', async ($, e, next) => next(e)); }"
    assert RISK in risk(js)["risk_flags"]
    assert RISK in risk(js, indent="   ")["risk_flags"]


def test_local_try_catch_does_not_resolve_missing_registration_catch():
    js = """export function register(on) {
      on('tool.call', async ($, e, next) => {
        try { return await next(e) }
        finally { try { await Promise.resolve($.ui.log('log', {to:'debug'})) } catch {} }
      });
    }"""
    assert RISK in risk(js)["risk_flags"]


def test_safe_native_tested_registration_catch_does_not_trigger_missing_flag():
    js = """export function register(on) {
      on('tool.call', async ($,e,next)=>{
        try { return await next(e) }
        finally { try { $.ui.log('QA', {to:'debug'}) } catch {} }
      }).catch(async ($, e, next) => next(e));
    }"""
    assert RISK not in risk(js)["risk_flags"]


def test_catch_on_unrelated_promise_does_not_mask_registration_warning():
    js = """export function register(on) {
      on('tool.call', async ($, e, next) => {
        await Promise.resolve('ignore').catch(() => {});
        return next(e);
      });
    }"""
    assert RISK in risk(js)["risk_flags"]


def test_wrong_example_is_manual_not_a_recommended_bad_hook():
    js = "export function register(on) { on('tool.call', ($,e,next)=>next(e)); }"
    output = lint_mods_answer(
        "❌ Incorrect Mod example:\n" + F + "js\n" + js + "\n" + F,
        case_id="POS-E-01",
        target_version="2.1.302",
    )
    assert RISK not in output["risk_flags"]
    assert (
        "cli302-tool-call-catch-negative-example-requires-review"
        in output["requires_manual_review"]
    )


def test_incomplete_fenced_registration_is_not_silently_safe():
    js = "export function register(on) { on('tool.call', async ($, e, next) => { return next(e) "
    output = risk(js)
    assert "cli302-tool-call-registration-catch-unverified" in output["requires_manual_review"]


def test_legacy_296_cannot_borrow_302_registration_warning():
    js = "export function register(on) { on('tool.call', ($,e,next)=>next(e)); }"
    assert RISK not in risk(js, version="2.1.296")["risk_flags"]


def test_unrelated_javascript_and_inline_code_do_not_trigger():
    example = "Plain JS: " + F + "js\nconsole.log('other program');\n" + F
    report = lint_mods_answer(example, case_id="NEG-TYPESCRIPT", target_version="2.1.302")
    assert RISK not in report["risk_flags"]
    inline = "Mention `on('tool.call', handler)` only as inline text."
    report = lint_mods_answer(inline, case_id="POS-E-01", target_version="2.1.302")
    assert RISK not in report["risk_flags"]


def test_all_five_original_source_hashed_codex_sonnet_modules_are_now_detected():
    from pathlib import Path

    from mods_knowledge.answer_lint import lint_mods_answer

    base = Path(__file__).resolve().parents[1] / "evals/fixtures/p5-native-model-code-302"
    paths = sorted((base / "codex").glob("*.mjs")) + sorted((base / "sonnet").glob("*.js"))
    assert len(paths) == 5
    detected = 0
    for source in paths:
        answer = fenced(source.read_text(), indent="   " if source.parent.name == "sonnet" else "")
        flags = lint_mods_answer(answer, case_id="POS-E-01", target_version="2.1.302")["risk_flags"]
        detected += RISK in flags
    assert detected == 5
