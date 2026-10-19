"""Real Sonnet CLI302 generated Markdown fenced code indented three spaces.

The old answer linter only matched an unindented closing fence, missing
every actual code example in an authentic POS-E-01 Sonnet reply.
"""

from __future__ import annotations

from mods_knowledge.answer_lint import _code_spans, lint_mods_answer

FENCE = chr(96) * 3
RISK = "mods-cli302-unsupported-console-global"


def example(indent: str) -> str:
    code = (
        "export function register(on) {\n"
        '  on("tool.call", async ($,e,next) => {\n'
        "    try { return await next(e) }\n"
        '    finally { try { console.log("diagnostic") } catch {} }\n'
        "  });\n"
        "}\n"
    )
    lines = code.rstrip().splitlines()
    return "Claude Code Mods example:\n" + (
        indent
        + FENCE
        + "js\n"
        + "\n".join(indent + line for line in lines)
        + "\n"
        + indent
        + FENCE
        + "\n"
    )


def test_three_space_indented_sonnet_code_fence_is_real_mod_code():
    answer = example("   ")
    assert len(_code_spans(answer)) == 1
    result = lint_mods_answer(answer, case_id="POS-E-01", target_version="2.1.302")
    assert RISK in result["risk_flags"]


def test_unindented_and_one_space_fences_both_keep_risk_detection():
    for indent in ("", " "):
        answer = example(indent)
        assert len(_code_spans(answer)) == 1
        result = lint_mods_answer(answer, case_id="POS-E-01", target_version="2.1.302")
        assert RISK in result["risk_flags"]


def test_inline_formatting_does_not_create_a_fake_runnable_code_block():
    inline = (
        "Mention the inline string "
        + chr(96)
        + 'console.log("hello")'
        + chr(96)
        + " for regular JavaScript and do not propose a Mods hook."
    )
    assert _code_spans(inline) == []
    result = lint_mods_answer(inline, case_id="NEG-TYPESCRIPT", target_version="2.1.302")
    assert RISK not in result["risk_flags"]


def test_three_space_bad_example_is_only_manual_negative_warning():
    answer = "❌ Incorrect Mod snippet:\n" + example("   ").split("\n", 1)[1]
    result = lint_mods_answer(answer, case_id="POS-E-01", target_version="2.1.302")
    assert RISK not in result["risk_flags"]
    assert "cli302-console-negative-example-requires-review" in result["requires_manual_review"]
