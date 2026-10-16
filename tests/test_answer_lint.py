"""Detect clearly unsafe/unverified Claude Mods snippets without judging all semantics."""

from __future__ import annotations

import pytest

from mods_knowledge.answer_lint import lint_mods_answer


def get_flags(content: str, *, case_id: str = "POS-E-02") -> set[str]:
    result = lint_mods_answer(content, case_id=case_id)
    assert result["semantic_review_complete"] is False
    return set(result["risk_flags"])


def test_invalid_default_registration_detected_in_executable_code() -> None:
    response = """
Follow this implementation:
```ts
export default function register({ on }) {
  on('tool.call', async ($, e, next) => next(e))
}
```
"""
    assert "unsupported-default-register-destructuring" in get_flags(response)


def test_invalid_registration_in_an_explicit_negative_example_is_not_auto_failed() -> None:
    response = """
Incorrect example (do not use):
```typescript
export default function register({ on }) {}
```
Correct:
```ts
export function register(on) { on('tool.call', async ($, e, next) => next(e)) }
```
"""
    report = lint_mods_answer(response, case_id="POS-E-02")
    assert "unsupported-default-register-destructuring" not in report["risk_flags"]
    assert "register-export-example-needs-manual-review" in report["requires_manual_review"]


def test_single_file_plugin_test_invocation_is_rejected() -> None:
    for command in (
        "claude plugin test ./tests/example.test.ts",
        "claude plugin test tests/example.test.tsx",
        "claude plugin test ./tests/*.test.ts",
    ):
        assert "plugin-test-expects-mod-directory" in get_flags(
            "Run:\n```bash\n" + command + "\n```",
            case_id="POS-Q-01",
        )


def test_valid_plugin_directory_test_command_remains_clean() -> None:
    body = """
Use a directory argument.
```bash
claude plugin test ./my-mod
```
Verified on Claude Code CLI 2.1.296.
"""
    assert "plugin-test-expects-mod-directory" not in get_flags(body, case_id="POS-Q-01")


def test_current_api_reference_to_historical_dts_is_flagged() -> None:
    answer = """
Use https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts
as authoritative current types.
"""
    assert "historical-early-access-types-reference" in get_flags(answer, case_id="POS-T-03")


def test_conditional_historical_warning_is_not_a_false_definitive_claim() -> None:
    answer = """
Do not use https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts
as current version types. Use local generated declarations.
"""
    assert "historical-early-access-types-reference" not in get_flags(answer, case_id="POS-T-03")


def test_critical_middlewares_missing_first_callback_parameter_is_flagged() -> None:
    body = """
A transparent observer:
```ts
on('tool.call', async (e, next) => { return next(e) })
```
"""
    assert "missing-hook-api-argument" in get_flags(body, case_id="POS-E-01")


def test_correct_three_argument_callback_is_not_flagged() -> None:
    body = """
```ts
export function register(on) {
  on('tool.call', async ($, e, next) => { return next(e) })
}
```
"""
    assert "missing-hook-api-argument" not in get_flags(body, case_id="POS-E-01")


def test_unverified_command_input_is_review_required_not_proven_wrong() -> None:
    body = """
```ts
export function register(on) {
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const command = e.command;
    return next(e)
  })
}
```
"""
    assert (
        "event-field-shape-needs-local-types"
        in lint_mods_answer(body, case_id="POS-E-04")["requires_manual_review"]
    )


def test_response_flags_never_include_original_content() -> None:
    private = "PASSWORD=super-secret-do-not-copy"
    data = lint_mods_answer("Example code:\n```\n" + private + "\n```", case_id="POS-P-01")
    assert private not in str(data)
    assert "answer_sha256" in data and len(data["answer_sha256"]) == 64
    assert data["case_id"] == "POS-P-01"
    assert data["semantic_review_complete"] is False


@pytest.mark.parametrize("case_id", ["", "arbitrary/../../", "lowercase", "PRIVATE_🚫"])
def test_invalid_case_ids_rejected(case_id: str) -> None:
    with pytest.raises(ValueError):
        lint_mods_answer("Hello", case_id=case_id)


def test_wrong_signature_in_code_comment_labeled_error_is_not_flagged_as_bad_advice() -> None:
    code = """
The three-argument callback is required.

Do not write this:
§§§typescript
// 错误：参数发生错位
on('tool.call', async (e, next) => { return next(e) })
§§§
""".replace("§", chr(96))
    result = lint_mods_answer(code, case_id="POS-E-01")
    assert "missing-hook-api-argument" not in result["risk_flags"]
    assert "callback-arity-negative-example-needs-manual-review" in result["requires_manual_review"]


def test_strict_validation_requires_author_metadata_for_supplied_mod_example() -> None:
    answer = """
A complete Claude Code Mod is below.

**.claude-plugin/plugin.json**
```json
{"name":"transparent-observer","version":"0.1.0","description":"Mod observer"}
```

**hooks/observer.ts**
```ts
export function register(on) {
  on("tool.call", async ($, e, next) => next(e))
}
```

Run:
```bash
claude plugin validate ./transparent-observer --strict
```
""".replace("`", chr(96))
    flags = get_flags(answer, case_id="POS-E-02")
    assert "strict-validate-manifest-author-warning" in flags


def test_manifest_author_object_resolves_strict_validation_warning_risk() -> None:
    answer = """
**.claude-plugin/plugin.json**
```json
{"name":"mod","version":"0.1.0","author":{"name":"QA"}}
```
```bash
claude plugin validate --strict ./mod
```
""".replace("`", chr(96))
    assert "strict-validate-manifest-author-warning" not in get_flags(answer)


def test_absence_of_strict_flag_does_not_create_a_fatal_risk() -> None:
    answer = """
**.claude-plugin/plugin.json**
```json
{"name":"mod","version":"0.1.0"}
```

```bash
claude plugin validate ./mod
```
""".replace("`", chr(96))
    assert "strict-validate-manifest-author-warning" not in get_flags(answer)


def test_non_manifest_json_is_not_incorrectly_reported_as_plugin_manifest() -> None:
    answer = """
Project settings:
```json
{"name":"mod","version":"0.1.0"}
```
Run: claude plugin validate --strict ./mod
""".replace("`", chr(96))
    assert "strict-validate-manifest-author-warning" not in get_flags(answer)


def test_explicitly_invalid_authorless_manifest_is_review_flag_not_bad_advice() -> None:
    answer = """
Incorrect example (strict mode will fail):
**.claude-plugin/plugin.json**
```json
{"name":"mod","version":"0.1.0"}
```
```bash
claude plugin validate --strict ./mod
```
""".replace("`", chr(96))
    result = lint_mods_answer(answer, case_id="POS-E-02")
    assert "strict-validate-manifest-author-warning" not in result["risk_flags"]
    assert "strict-author-example-needs-manual-review" in result["requires_manual_review"]


@pytest.mark.parametrize(
    "declaration",
    [
        "export default function register(on) { on('tool.call', async ($, e, next) => next(e)) }",
        "export default async function register(on) { on('tool.call', async ($, e, next) => next(e)) }",
    ],
)
def test_default_registered_function_with_normal_callback_is_still_invalid(
    declaration: str,
) -> None:
    # Independently reproduced with claude plugin validate --strict, CLI 2.1.296:
    # a correctly ordered callback does not repair a missing named register export.
    response = "Use this Mod:\n```ts\n" + declaration + "\n```"
    assert "unsupported-default-register-export" in get_flags(response)


def test_incorrect_default_function_syntax_as_negative_example_requires_review() -> None:
    response = """
Wrong example — do not use:
```ts
export default function register(on) { on('tool.call', async ($, e, next) => next(e)) }
```
Correct named export:
```ts
export function register(on) { on('tool.call', async ($, e, next) => next(e)) }
```
"""
    report = lint_mods_answer(response, case_id="POS-E-02")
    assert "unsupported-default-register-export" not in report["risk_flags"]
    assert "register-export-example-needs-manual-review" in report["requires_manual_review"]


def test_named_registration_with_correct_callback_is_not_default_export() -> None:
    response = """
```typescript
export function register(on) {
  on('tool.call', async ($, e, next) => next(e));
}
```
"""
    assert "unsupported-default-register-export" not in get_flags(response)


@pytest.mark.parametrize(
    "handler",
    [
        "on('tool.call', { tool: 'Bash' }, async (e, next) => next(e))",
        'on("tool.call", { tool: "Read", when: "before" }, async (e,next) => next(e))',
        "on('tool.call', {tool: 'Bash'}, async ( e, next ) => {return next(e)})",
    ],
)
def test_filtered_tool_call_callback_missing_api_argument_is_flagged(handler: str) -> None:
    reply = "Use this in your Mod:\n```ts\nexport function register(on) {\n" + handler + "\n}\n```"
    assert "missing-hook-api-argument" in get_flags(reply)


def test_filtered_tool_call_correct_three_arg_callback_is_not_flagged() -> None:
    reply = """
```ts
export function register(on) {
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => next(e));
}
```
"""
    assert "missing-hook-api-argument" not in get_flags(reply)


def test_filtered_bad_handler_explained_as_negative_example_is_manual_only() -> None:
    reply = """
Incorrect example (do not use):
```ts
on('tool.call', { tool: 'Bash' }, async (e, next) => next(e))
```
Correct:
```ts
on('tool.call', { tool: 'Bash' }, async ($, e, next) => next(e))
```
"""
    report = lint_mods_answer(reply, case_id="POS-E-01")
    assert "missing-hook-api-argument" not in report["risk_flags"]
    assert "callback-arity-negative-example-needs-manual-review" in report["requires_manual_review"]


@pytest.mark.parametrize(
    "declaration",
    [
        "export function register({ on }) { on('tool.call', async ($, e, next) => next(e)) }",
        "export async function register({on}) { on('tool.call', async ($, e, next) => next(e)) }",
    ],
)
def test_named_register_destructuring_is_invalid_even_when_callback_arity_correct(
    declaration: str,
) -> None:
    # Native Claude Code CLI 2.1.296 --strict rejected the plain named form.
    # A named *export* alone is insufficient: on must be a plain parameter.
    response = "Suggested runnable Mod:\n```ts\n" + declaration + "\n```"
    assert "unsupported-named-register-destructuring" in get_flags(response)


def test_explicitly_wrong_named_register_example_is_manual_review_not_advice() -> None:
    response = """
Wrong example — do not use:
```js
export function register({ on }) {
  on('tool.call', async ($, e, next) => next(e));
}
```
Correct:
```js
export function register(on) {
  on('tool.call', async ($, e, next) => next(e));
}
```
"""
    findings = lint_mods_answer(response, case_id="POS-E-01")
    assert "unsupported-named-register-destructuring" not in findings["risk_flags"]
    assert "register-export-example-needs-manual-review" in findings["requires_manual_review"]


@pytest.mark.parametrize(
    "invalid",
    [
        "claude plugin validate",
        "claude plugin validate --strict",
        "claude plugin validate --json --strict",
        "claude plugin validate --strict --json",
        "$ claude plugin validate --strict",
    ],
)
def test_cli_validate_requires_path_and_flags_bare_commands(invalid: str) -> None:
    # On native Claude Code CLI 2.1.296 these commands return code 1:
    # error: missing required argument 'path'.
    response = f"Run to check your Mod:\n```bash\n{invalid}\n```"
    assert "plugin-validate-missing-path" in get_flags(response, case_id="POS-E-01")


@pytest.mark.parametrize(
    "valid",
    [
        "claude plugin validate .",
        "claude plugin validate --strict .",
        "claude plugin validate --json --strict ./your-mod",
        "claude plugin validate './some mod' --strict",
        "claude plugin validate --help",
        "claude plugin test .",
    ],
)
def test_cli_validate_with_path_or_help_is_not_flagged(valid: str) -> None:
    body = f"Run:\n```bash\n{valid}\n```"
    assert "plugin-validate-missing-path" not in get_flags(body, case_id="POS-E-01")


def test_textual_description_of_invalid_command_is_not_executable_advice() -> None:
    answer = "Running `claude plugin validate` without a path will fail."
    assert "plugin-validate-missing-path" not in get_flags(answer, case_id="POS-E-01")


def test_negated_bare_validation_command_is_manual_review_only() -> None:
    answer = """
Wrong example — do not use:
```bash
claude plugin validate --strict
```
Correct:
```bash
claude plugin validate --strict .
```
"""
    result = lint_mods_answer(answer, case_id="POS-E-01")
    assert "plugin-validate-missing-path" not in result["risk_flags"]
    assert (
        "plugin-validate-missing-path-negative-example-needs-manual-review"
        in result["requires_manual_review"]
    )


def test_codeblock_cli_validate_missing_path_is_detected() -> None:
    text = '<CodeBlock language="bash">claude plugin validate --strict</CodeBlock>'
    assert "plugin-validate-missing-path" in get_flags(text, case_id="POS-Q-01")


def test_multiline_shell_validate_path_is_not_false_positive() -> None:
    sample = """Check it:
```bash
claude plugin validate --strict \\
  ./my-mod
```
"""
    assert "plugin-validate-missing-path" not in get_flags(sample, case_id="POS-E-01")


@pytest.mark.parametrize(
    "unsafe_code",
    [
        """export function register(on) {
  on("tool.call", async ($, e, next) => {
    const result = await next(e);
    console.log("tool.call completed", {elapsedMs: 2});
    return result;
  });
}""",
        """export function register(on) {
  on('tool.call', async ($, e, next) => {
    const result = await next(e);
    await $.ui.log('observer summary');
    return result;
  });
}""",
    ],
)
def test_unisolated_post_next_diagnostics_can_replace_downstream_result(unsafe_code: str) -> None:
    report = lint_mods_answer("Run this:\n```ts\n" + unsafe_code + "\n```", case_id="POS-E-01")
    assert "observer-post-next-diagnostics-not-isolated" in report["risk_flags"]
    assert report["semantic_review_complete"] is False


def test_unisolated_catch_diagnostics_can_mask_original_next_rejection() -> None:
    # A real 2026-10-16 Chat Mode reply passed K-ID/URL/callback-lint checks
    # but a second `console.error()` failure would mask the `next(e)` error.
    code = """export function register(on) {
  on("tool.call", async ($, e, next) => {
    try {
      const result = await next(e);
      console.log("tool.call completed", {elapsedMs: 2});
      return result;
    } catch (error) {
      console.error("tool.call failed");
      throw error;
    }
  });
}"""
    report = lint_mods_answer("Example:\n```ts\n" + code + "\n```", case_id="POS-E-01")
    assert "observer-post-next-diagnostics-not-isolated" in report["risk_flags"]
    assert "observer-catch-diagnostics-can-mask-error" in report["risk_flags"]


def test_fail_isolated_try_finally_observer_does_not_trigger_known_diagnostic_risks() -> None:
    text = """Correct transparent observer:
```ts
export function register(on) {
  on('tool.call', async ($, e, next) => {
    try { return await next(e); }
    finally {
      try { console.log('tool.call completed'); }
      catch { /* ignore only diagnostic failure */ }
    }
  });
}
```"""
    report = lint_mods_answer(text, case_id="POS-E-01")
    assert not any("diagnostic" in x for x in report["risk_flags"])


def test_minimal_direct_next_observer_remains_clean() -> None:
    text = """```ts
export function register(on) {
  on('tool.call', async ($, e, next) => next(e));
}
```"""
    report = lint_mods_answer(text, case_id="POS-E-01")
    assert not report["risk_flags"]


def test_negated_unsafe_observer_is_review_only_not_a_recommended_hard_risk() -> None:
    text = """Wrong example (do not use):
```ts
on('tool.call', async ($, e, next) => {
  const result = await next(e);
  console.log('diagnostic');
  return result;
});
```
Correct is a locally protected diagnostic or simple return next(e)."""
    result = lint_mods_answer(text, case_id="POS-E-01")
    assert "observer-post-next-diagnostics-not-isolated" not in result["risk_flags"]
    assert (
        "observer-diagnostic-negative-example-needs-manual-review"
        in result["requires_manual_review"]
    )


@pytest.mark.parametrize(
    "unsafe_finally",
    [
        """export function register(on) {
  on('tool.call', async ($, e, next) => {
    try { return await next(e); }
    finally { console.log('done'); }
  });
}""",
        """export function register(on) {
  on('tool.call', async ($, e, next) => {
    try { return await next(e); }
    finally { await $.ui.log('done'); }
  });
}""",
    ],
)
def test_unguarded_finally_logger_can_mask_original_downstream_outcome(unsafe_finally: str) -> None:
    result = lint_mods_answer("Proposed:\n```ts\n" + unsafe_finally + "\n```", case_id="POS-E-01")
    assert "observer-finally-diagnostics-not-isolated" in result["risk_flags"]
    assert result["semantic_review_complete"] is False


def test_unguarded_finally_logging_example_marked_wrong_is_not_hard_block() -> None:
    answer = """Wrong example (do not use):
```ts
on('tool.call', async ($, e, next) => {
  try { return await next(e); }
  finally { console.log('done'); }
});
```"""
    result = lint_mods_answer(answer, case_id="POS-E-01")
    assert "observer-finally-diagnostics-not-isolated" not in result["risk_flags"]
    assert (
        "observer-diagnostic-negative-example-needs-manual-review"
        in result["requires_manual_review"]
    )


def test_logger_promise_not_awaited_inside_finally_guard_requires_manual_review() -> None:
    text = """```ts
export function register(on) {
  on('tool.call', async ($, e, next) => {
    try { return await next(e); }
    finally { try { console.log('diagnostic'); } catch { /* ignored */ } }
  });
}
```"""
    result = lint_mods_answer(text, case_id="POS-E-01")
    assert "observer-finally-diagnostics-not-isolated" not in result["risk_flags"]
    assert (
        "observer-async-diagnostic-unawaited-needs-manual-review"
        in result["requires_manual_review"]
    )


def test_awaited_fail_isolated_finally_logger_and_direct_next_remain_clean() -> None:
    code = """export function register(on) {
  on('tool.call', async ($, e, next) => {
    try { return await next(e); }
    finally { try { await Promise.resolve(console.log('diagnostic')); } catch { /* ignored */ } }
  });
}"""
    result = lint_mods_answer("```ts\n" + code + "\n```", case_id="POS-E-01")
    assert not any("diagnostic" in s for s in result["risk_flags"])
    assert not any("diagnostic" in s for s in result["requires_manual_review"])


@pytest.mark.parametrize(
    "preface",
    [
        "下面是**错误写法**（不能照搬）：\n### 演示：",
        "Incorrect example, do not copy:\nDemonstration:",
        "❌ 不安全的反例（仅说明问题）：\n### 错误模式：",
    ],
)
def test_unprotected_logger_explicit_negative_comparison_is_manual_review_not_hard_risk(
    preface: str,
) -> None:
    unsafe = """```ts
on('tool.call', async ($, e, next) => {
  try { return await next(e); }
  finally { console.log('unsafe diagnostic'); }
})
```"""
    result = lint_mods_answer(preface + "\n" + unsafe, case_id="POS-E-01")
    assert "observer-finally-diagnostics-not-isolated" not in result["risk_flags"]
    assert (
        "observer-diagnostic-negative-example-needs-manual-review"
        in result["requires_manual_review"]
    )


def test_latest_positive_recommendation_overrides_old_negative_context() -> None:
    unsafe = """```ts
on('tool.call', async ($, e, next) => {
  try { return await next(e); }
  finally { console.log('throws'); }
})
```"""
    answer = (
        "以上的一个错误模式提醒我们避免日志抛出。\n"
        "接下来是推荐给用户直接复制的正确实现：\n" + unsafe
    )
    flags = lint_mods_answer(answer, case_id="POS-E-01")
    assert "observer-finally-diagnostics-not-isolated" in flags["risk_flags"]


def test_uncertain_unlabeled_unsafe_observer_remains_hard_risk() -> None:
    code = """Example:
```ts
on('tool.call', async ($, e, next) => {
  try { return await next(e); }
  finally { console.log('log'); }
})
```"""
    flags = lint_mods_answer(code, case_id="POS-E-01")
    assert "observer-finally-diagnostics-not-isolated" in flags["risk_flags"]


@pytest.mark.parametrize(
    "factory_export",
    [
        "export const register = createRegister()",
        "export const register=createRegister(on)",
        "export const register = buildHookModule()",
    ],
)
def test_factory_assigned_register_export_is_known_native_rejected(factory_export: str) -> None:
    # Confirmed real Claude Code CLI 2.1.296 (Mac) strict validation failed
    # even though createRegister() returned an actual callable function.
    reply = "Copyable Mod:\n```js\n" + factory_export + "\n```"
    output = lint_mods_answer(reply, case_id="POS-E-01")
    assert "unsupported-factory-register-export" in output["risk_flags"]
    assert output["semantic_review_complete"] is False


def test_factory_register_as_explicitly_wrong_example_is_manual_review() -> None:
    reply = """错误示例（不要照搬）：
```js
export const register = createRegister()
```
正确实现：
```js
export function register(on) { on('tool.call', async ($, e, next) => next(e)) }
```"""
    report = lint_mods_answer(reply, case_id="POS-E-01")
    assert "unsupported-factory-register-export" not in report["risk_flags"]
    assert "register-export-example-needs-manual-review" in report["requires_manual_review"]


def test_correct_named_function_register_does_not_trigger_factory_export_risk() -> None:
    sample = """```js
export function register(on) { on('tool.call', async ($, e, next) => next(e)) }
```"""
    report = lint_mods_answer(sample, case_id="POS-E-01")
    assert "unsupported-factory-register-export" not in report["risk_flags"]
