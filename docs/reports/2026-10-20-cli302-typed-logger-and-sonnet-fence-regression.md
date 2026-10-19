# P5: CLI 2.1.302 native typed logging and indented code-block fix

Date: 2026-10-20 Sydney. Scoped to reviewed Claude Code CLI 2.1.302.

## The original source fact is now single-sourced

The two independently installed CLI 2.1.302 native executable binaries
(Mac and Raspberry Pi) yielded identical first-party, embedded core Mods
type declarations: SHA256
8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e.

The original native Codex/Sonnet model outputs were checked under those
declarations: two of five observer JavaScript bodies typechecked, three
failed TS2584 for console.log inside a Mod hook module. Three private
TEST-ONLY variants using the typed engine
$.ui.log(text, { to: "debug" }) instead passed the core typecheck.
No original model source was silently changed.

Evidence record: evidence/cli302/hook_observer_typed_logging.json,
with approved note text SHA256 and exact link to the public original
type-audit report. The compiler validates the evidence and its core
type digest, failure counts and incomplete-runtime-types status BEFORE
generating the CLI302 Skill. It does NOT create a new unsupported
first-party API Claim out of an informal note.

The new instruction is scoped to CLI302, copied identically to the five
host Skills, kept below the established 9,000-character length bound.
The legacy CLI296 Skill remains unchanged. The Pi's newly installed
CLI303 is explicitly unreviewed by these particular CLI302 facts.

## Second actual regression: indented Markdown code blocks

The previous offline answer linter accepted only an opening fence and
an unindented closing fence, so a REAL Sonnet POS-E-01 answer's THREE
code blocks, each indented by three spaces, went completely unread.

A Red-first test demonstrates the missed source snippet.
The revised deterministic code-span scanner accepts up to three spaces
of CommonMark fence indentation, preserves inline-code nonactivation,
and distinguishes actual dangerous examples from clearly labeled
negative/counterexamples.

Original completed Sonnet 5.5 native answer bytes and wire SHA256s were
verified against the prior immutable real P5 report. Current linter:
- POS-E-01: 3 original code blocks now detected, concrete unsupported
  CLI302 console global flagged as known type risk.
- POS-Q-01: 1 legitimate block, no false console type risk.
This is a read-only historical recheck: NO new model calls, no reply
revisions and no private transcript content in Git.

## Deterministic program and scorer integration

The answer-lint parser accepts an explicit target 2.1.302 flag and
refuses unsupported 2.1.303. P5 real native scorer also forwards its
reviewed target into the same deterministic linter; structural Claim
links alone can no longer erase an actually detected typed-code risk.

The checker is conservative, NOT a full TypeScript language service.
Known patterns must still be validated against exact first-party
target-generated tool schema declarations, which are NOT completely
available offline without authorized interactive plugin loading.

The existing native CLI302 mock and Node behavior testing remain
valid but do not override actual original model type failures.
P5 full live interactive permission semantics, current native Qwen
model quality, original P4 strict 6/8 boundary activation, complete
46-case Chat Mode and Stable release remain HOLD. Do not deploy
unreviewed CLI302 facts to a CLI303 host.

Agent Communication is a separate excluded project.
