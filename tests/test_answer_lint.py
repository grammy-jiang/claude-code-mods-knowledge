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
