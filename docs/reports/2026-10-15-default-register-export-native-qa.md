# P4 technical quality: reject default-only Mod registration exports in model answers

**Observation:** 2026-10-15 (Australia/Sydney). Actual local **MacBook Pro Claude Code CLI 2.1.296**, not an AI model turn. The approved Single Source of Truth already includes named-registration Claim **K-0032**, sourced from [official Mods reference — files](https://code.claude.com/docs/en/plugins/mods/reference#files). This change tightens a **conservative known-risk scanner**; it does not modify approved Claims, released Plugin content, or online ChatGPT routing.

## Native CLI reproduction

Disposable `.claude-plugin/plugin.json` and `hooks/hooks.json` fixtures with otherwise identical, valid Mod callback `on('tool.call', async ($, e, next) => next(e))` were passed to `claude plugin validate --strict`:

| Isolated JavaScript module export | Strict CLI verdict |
| --- | --- |
| `export default function register(on)` | **FAIL**: no export named `register` |
| `export default async function register(on)` | **FAIL**: no export named `register` |
| `export function register(on)` | **PASS** |

The original `mods-knowledge answer-lint` recognized only `export default function register({ on })` (default plus destructured argument); it **missed** the unsupported default-only export even when the argument was `on` and the tool callback order was correct. The new `unsupported-default-register-export` known-risk flag catches the two native-rejected forms. The existing `unsupported-default-register-destructuring` risk key and explicit incorrect-example/manual-review behavior remain unchanged for previously recorded reports.

Red-first regression reproduced **3 failing tests** before the fix; after the fix, `tests/test_answer_lint.py` passed **24/24**. The tests also preserve valid named export and explicit warning/negative examples. No user-provided Mod, third-party hook, untrusted page, or real filesystem-modifying tool call was executed. Sample native fixtures remain private in isolated `/tmp` rather than in a release artifact.

**Limit:** this is a bounded pattern/lint guard, not TypeScript semantic verification, native runtime acceptance of arbitrary generated snippets, or proof the ChatGPT Plugin was invoked. Native CLI 2.1.296 cannot establish behavior for later CLI versions or host surfaces. P4 and P5 remain open and the stable release gate remains blocked.
