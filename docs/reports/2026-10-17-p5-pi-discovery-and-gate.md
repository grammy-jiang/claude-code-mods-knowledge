# P5 local Pi Agent — Skill discovery versus compliance and safe delivery

Date: 2026-10-17 AEDT. Real native Pi Agent 1.3.0 JSONL
with the Mac-hosted unchanged Qwen3.6 35B-A3B model and the installed
byte-pinned Claude Mods Skill. Knowledge remains scoped to CLI 2.1.296.

## P0 — The old negative-case tool loop

The archived, timed-out 2026-10-16 NEG-TYPESCRIPT trace showed
24 tool executions (21 read, three ls) and **zero tool errors**.
Eighteen were identical file reads. The longest adjacent repeated
identical call sequence was fourteen, interrupted by other tools.
No Mods Skill was read and there was no completed final response before
the historical 110.08-second timeout.

This is a tool-progress/termination issue, not false Mods Skill
activation and not filesystem permission failure. The new test-only
repeat guard fingerprints actual native tool name plus arguments
without recording or publishing raw paths. It can abort the entire
private test run after six consecutive identical invocations,
without fabricating tool results or accepting an incomplete answer.

A new matching negative trial was stopped after 20.3 seconds with
reason `repeated_identical_tool_call`. The gate correctly recorded
an incomplete turn and rejected the generated partial response.

## P1 — Native auto, explicit and forced Skill exposure

All prompts are frozen P4 cases. The `auto` mode uses ordinary Pi
discovery, with no explicit Skill mention. The `explicit` mode
adds a direct instruction to read Skill and the task references.
The `forced` mode uses explicit Skill path and disables automatic
discovery using native `--no-skills --skill`.

| Case | Mode | Actual Skill read | Exact source audit | Gate |
| --- | --- | --- | --- | --- |
| POS-Q-01 | auto | yes | FAIL | blocked |
| POS-Q-01 | explicit | yes | PASS | blocked: executable example requires native review |
| POS-Q-01 | forced | no | FAIL | blocked |
| POS-E-01 | auto | yes | FAIL | blocked |
| POS-E-01 | explicit | yes | PASS | blocked: executable code and manual review |
| POS-E-01 | forced | yes | FAIL | blocked |
| NEG-TYPESCRIPT | auto | no | not applicable | blocked: repeated read loop |

These are SINGLE trials, not reliable activation-rate statistics.
Qwen spontaneously discovered and read the Skill on both positive
`auto` trials. Direct instructions improved exact citations but
did not certify runnable Mod semantics. Explicit resource exposure
still did not guarantee that the model read the Skill (1/2).

## Deterministic gate: what it does and does not guarantee

The opt-in `pi_delivery_gate` and buffered runner are NOT installed
as the user's default Pi Agent or any persistent extension.

- An out-of-scope Mods API request receives a deterministic refusal
  BEFORE inference (e.g. unreviewed 2.1.310). BOUND-VERSION-NEW consumed **zero model calls**.
- Eligible test cases are sent to the native model in a disposable
  read-only workspace. All candidate text/events are buffered
  privately, not streamed to the user.
- Only after the model settles do native provider/model identity,
  actual Skill read, exact Claim IDs and first-party `#fragment`
  links, tool progress, code hazards and completion get checked.
- Missing sources, invalid provenance, missing required Skill reads,
  tool loops, incomplete turns and executable code with no
  independent target-native validation are withheld. A post hoc
  audit cannot retract unsafe text already streamed by a normal
  interactive Pi session.
- Even a structural PASS is NOT a guarantee of semantic correctness.
  Model-generated runnable Mod examples need native CLI 2.1.296
  strict and mocked tests, including downstream error identity.

All raw native JSONL, user task text, account materials and private
process logs remain in an access-restricted Mac benchmark location.
Only sanitized case IDs, verdicts, digests and metadata enter Git.

## Next campaign

A frozen twelve-case suite (four positives, four negatives,
four security/version boundaries) with three independent attempts per
model is planned for Qwen3.6 and Gemma 4 31B only. GPT-OSS 120B
remains deferred. Before Gemma inference, verify memory/Swap guards,
save all user service states and restore the default Qwen after each
bounded test campaign. P5 and Stable release gates remain OPEN.
