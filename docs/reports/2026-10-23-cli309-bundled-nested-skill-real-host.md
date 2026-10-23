# Claude Code 2.1.309: /verify and /code-review after a nested shell edit

**Date:** 2026-10-23 (Australia/Sydney).
**In scope:** Claude Code Mods P5 original Agent Skill discovery and knowledge use.
**Outcome:** mixed real-host QA; **not** full bundled Skill acceptance, no
new 2.1.309 Claims, no production change, Stable HOLD.

## Exact official target and documented behaviors

This test follows the upstream 2.1.309 release note about /verify and
/code-review finding a nested package's own Skill when its files are
changed from a shell process:

https://github.com/anthropics/claude-code/releases/tag/v2.1.309

First-party references:
- https://code.claude.com/docs/en/skills (monorepo dynamic discovery)
- https://code.claude.com/docs/en/commands (explicit /verify invocation)
- https://code.claude.com/docs/en/code-review-local (foreground -p review,
  diff-target selection, and optional --fix/--comment behavior)

The real, SHA-pinned official 2.1.309 Linux ARM64 CLI binary used on
Raspberry Pi 5 and Sextant has SHA256:
9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b.
Its original official release archive is SHA256:
8ecd1f2d06ccbd3f89c8886e840e42b57a19063f3de9cfe5f7d90fe875ba99ef.

The project never ran /code-review ultra, --fix or --comment and did
not invoke external pull-request or cloud review actions.

## Method: shell mutation within one continuing authenticated native host

A disposable local Git repository was created on each Pi, using the
four fixed files in
evals/fixtures/cli309-bundled-nested-20261023.

It contains a packages/widget/index.js function whose intended result
is a+b, and a package-local, explicitly scoped nested Skill named
mods-qa-widget-check. That Skill states the correct arithmetic invariant
and contains an independent unique marker. It is not a production Mods
Skill or a version-approved Claim.

An original authenticated Sonnet 5.5 CLI 2.1.309 process started at the
**repository root** while the working tree was clean. The same native
session then completed the following ordered sequence:

1. A no-tool baseline prompt (QA_ROOT_ONLY) returned successfully.
2. An **external shell** changed only packages/widget/index.js, replacing
   a+b with a+b+1; the test independently checked the original committed
   source, exact mutated file hash and one-file Git diff.
3. The still-running CLI process received explicit
   /verify packages/widget/index.js.
4. The same CLI process then received explicit
   /code-review low packages/widget/index.js.

The native process continued throughout all three model responses.
Bash permission was narrow: only selected read-only Git inspection,
cat and ls commands, with don't-ask mode. Any attempted Node execution
outside the allowed commands was denied and must not be called a runtime
pass. This is intentional to avoid authorizing broad shell execution
merely for acceptance.

## Actual first-party native results (not model-text inference)

| Tested behavior | Raspberry Pi | Sextant |
| --- | --- | --- |
| Single native session for all three turns | PASS | PASS |
| External shell changed only nested widget file | PASS | PASS |
| Native debug dynamically discovered one nested Skill | PASS | PASS |
| /verify recognized erroneous +1 source change | PASS | PASS |
| /verify actually invoked native Skill(mods-qa-widget-check) | **PASS** | **NO** |
| /verify read or accessed the nested Skill recipe | PASS | PASS, via Bash cat |
| /verify actually executed Node runtime test | **BLOCKED by permissions** | **BLOCKED by permissions** |
| /code-review attempted inspection of changed nested file | PASS | PASS |
| /code-review delivered an off-by-one correctness finding | **PARTIAL PASS**, via Read fallback | **BLOCKED**, composite Git diff denied |
| /code-review actually invoked the nested Skill tool | **NO** | **NO** |

This is important: merely reading SKILL.md, discovering a filename, or
repeating an embedded marker is **not equivalent** to a native Skill
tool invocation. In the original Pi /verify event, the model really
called Skill(mods-qa-widget-check). The Sextant /verify model instead
used a Bash cat on that file. Both cases are retained separately.

For /code-review, the Raspberry Pi model tried a compound Git diff
that was denied, then Read the changed nested source and reported the
off-by-one error. On Sextant, the read-only Git diff command used a
different composite shell form; it was denied and no correct review
finding was produced in that particular turn. These permissions and
model choices matter to acceptance and cannot be flattened into one
"2/2 passed" label.

No production Code, user Skills, Plugin configurations, or account
settings were touched. The only Git modification was the explicitly
controlled QA shell change in the temporary widget repository.

## Original native evidence and independent replay

- Real Claude 2.1.309 assistant stream-json including actual ToolUse
  inputs and user tool_result failures.
- Original private debug log, strict native version, real Sonnet model
  events, one native session ID across all three ordered results.
- Original scratch Git baseline, changed file hash and nested Skill
  source SHA256.
- Independent auditor:
  scripts/audit_cli309_bundled_nested_evidence.py.
- Public digest-linked report:
  docs/reports/2026-10-23-cli309-bundled-nested-native-evidence.json.

Both Pi hosts preserved their originals in separate mode-0700 private
evidence archives **outside Git**. The auditor replayed the archived
source and original wires and produced byte-identical sanitized reports.
Git contains only the safe source fixture, public digests and bounded
conclusions. Private prompts, full model answers, host paths, session
identifiers and credentials were excluded.

CI validates the declared native outcomes, exact source/auditor hashes,
misclassification controls and the prohibition on promoting unreviewed
knowledge. CI does **not** repeat paid model calls or claim that
sanitized public metadata is a substitute for original private wires.

## Release decision / next in-scope work

- Verified native *discovery*: 2/2.
- Verified /verify real Skill invocation: **1/2**.
- Full /verify runtime observation: **0/2** (Node execution was refused).
- /code-review native nested Skill invocation: **0/2**.
- Finished code review finding: Pi partial; Sextant blocked on diff
  command permissions.
- The full generated Claude Code Mods Skill, source-cited answer accuracy,
  Codex/Pi Agent native model behavior and ChatGPT Chat Mode Plugin
  remain distinct pending acceptance stages.
- 2.1.309 has **zero approved SSOT Claims**. None were silently inherited
  from 2.1.302 and no Skill/Plugin was promoted by these source QA runs.
- Stable HOLD. The archived unrelated distributed host-security work is
  out of scope and not required for this release.

Next useful, narrow P5 step: retest /code-review under an explicitly
permissioned read-only diff workflow in a disposable container, then
measure the actual generated Mods Skill's claim/source accuracy with
separate Claude Code/Codex/Pi Agent trials.
