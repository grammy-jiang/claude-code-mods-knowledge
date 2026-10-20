# P5 CLI302: catch registration warning missed by original model code

Date: 2026-10-20, Sydney. **This is a 2.1.302-scoped Skill QA improvement,
NOT permission to deploy model-generated Mods, promote 2.1.303/304 Claims or
release Stable.** Agent Communication is a different project and excluded.

## Root cause — two independent error-handling layers

The original real Codex/Sonnet `tool.call` Mod examples guarded optional
logging with local JavaScript `try/catch`, but had no error handler attached
to the `on('tool.call', ...)` registration. The native CLI validator reports
`gating hook without .catch: tool.call` even when `plugin validate --strict`
exits 0 and otherwise reports success. Neither a guarded diagnostic logger
nor source citations establish registration-level failure handling.

The first-party official source describes the registration `on(...).catch(...)`
and the special `next.called` / cached downstream result behavior:
https://code.claude.com/docs/en/plugins/mods/events#handle-a-hook-that-fails

The original CLI302 embedded TypeScript core declaration contains both
`on(...).catch` and `next.called`; the separate SHA-verified 302/304 strict
typechecks accepted a synthetic typed observer using this API. This official
source is paired with **target-native** evidence; currently available docs
alone cannot prove full historical version compatibility.

## Original vs corrected isolated native observations

- Five original SHA-preserved Codex/Sonnet source snippets on **2.1.302**:
  **5/5 warning cases**. Original bytes were not modified.
- Three reviewed synthetic hook behaviors: normal transparent observer,
  deliberate pre-`next` failure and deliberate post-`next` failure.
- Official CLI **2.1.302, 2.1.303 and 2.1.304** under Linux Bubblewrap:
  **9/9** native strict validations without the missing-catch warning.
- **18/18** native, mocked Read result and denial assertions passed;
  each verifies that its downstream mock was invoked only once.
- Incorrect recovery that substitutes `{ deny }` after `next`:
  correctly rejected by the native test in **all three** versions.
- Native thrown JavaScript error **object identity**: not proven by this
  mock test kit; direct synthetic mocks that throw are wrapped as
  `HooksError`. Do not make an identity-preservation claim from this result.
- Interactive host/user permission callbacks, dynamically generated tool
  declaration merges and genuine current model inference: not tested here.

See the immutable redacted structured report
`docs/reports/2026-10-20-p5-hook-catch-native-three-version-review.json`,
and its reproducible, SHA-restricted sandbox audit
`scripts/audit_p5_hook_catch_native.py`. The complete synthetic fixtures
are in `evals/fixtures/p5-cli302-hook-catch/`. All models and actual user
tools were excluded from the native replay.

## Corrective source-driven workflow

The existing K-0068 has a separately recorded `console.log` type conflict;
its historical Claim text and decision ledger remain **unchanged**. New
`evidence/cli302/hook_registration_catch_guidance.json` pins the native
report SHA256, first-party locator and bounded guidance. Compiler validates
these inputs before injecting source-attested, **non-normative P5 QA** into
only the CLI302 Skill and its `events.md` and `claim-evidence.md` references.
Existing 296 output remains byte-identical (SHA256
`b831b476463c1b3aac8edc74dd579fc57dfa1c68c802ebfea0d738d73564f416`).
Neither the approved Claim count nor 2.1.302 review interval is widened.

The answer linter now identifies a missing registration `.catch` separately
from logger `try/catch`, including original three-space-indented Sonnet
fences. It scans balanced hook registration calls and deliberately treats
incomplete syntax as requiring manual review; this is a known-risk lexical
signal rather than a full JavaScript parser. All five preserved original
source snippets are newly flagged; harmless unrelated code and explicit
negative examples do not receive the same automatic failure verdict.

## Remaining gated milestones

A genuine saved-prompt model/Skill A/B against medium Codex and Sonnet,
followed by reviewed target real-host acceptance, is required to show
**model output quality improves**. This change alone is a deterministic
checker and better reference guidance, not proof of production behavior.
CLI303/304 are still not approved as new API Claim targets, and P4 Chat Mode
activation, all 46 cases, P5 full native quality and Stable remain HOLD.
