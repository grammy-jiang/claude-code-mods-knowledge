# P5 local-agent P1 — native provenance and multi-host evidence

Date: 2026-10-16, Australia/Sydney. This report records real native
model turns, an independently validated source-limited Skill and remaining
semantic blockers, NOT a full host/runtime release qualification.

## Source and version boundary

- Baseline installed 0.3.4-beta.2 Skill: source Git SHA
  `6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e` and installed
  `SKILL.md` SHA256
  `03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e`.
- Native CLI versions: Codex 0.163.0, Pi Agent 1.3.0,
  Claude Code CLI 2.1.301 on MacBook, Raspberry Pi and sextant.
- The 31 approved Mods SSOT Claims target **Claude Code CLI 2.1.296 only**.
  Native 2.1.301 manifest validation is not complete API requalification.
- Claude Code quota exhausted: **zero Claude Code model calls** in P1.
  ChatGPT Chat Mode P4 deferred due unreliable transport, NOT accepted.

## Engineering outcomes

1. **P1-L07 model provenance:** New App Server QA runner joins native
   `thread/start` and `thread/read` server-resolved model identity with
   the same `turn/start`/`turn/completed`, real tool file reads,
   frozen original prompt, final answer and SHA-only report. Every counted
   Codex turn independently confirmed `openai / gpt-6.1-sol / medium`;
   command flags and `codex exec --json` alone are not proof.
2. **P1-L08 evidence pipeline:** The native Codex/Pi scorers reuse
   approved Claim exact first-party `#fragment` source checks and
   known-risk answer lint. The matrix JSON records 24 cells, 10 observed
   and 14 unobserved, each observed cell with its SHA256 trace evidence.
   Explicit `full_p5_acceptance=false` and all
   `native_mod_runtime_verified=false`. Missing is never a pass.
3. **P1-L09 cross-host:** Actual Codex positive/negative native model
   turns succeeded on MacBook, Raspberry Pi and sextant.
   Every positive read the correct installed Mods Skill and exact source
   links, every unrelated TypeScript control avoided the Mods Skill.
   The local Pi model is hosted only on the MacBook: do not pretend it
   runs on Raspberry Pi/sextant or substitute a remote model.
4. **P1-L06 mitigation and audit:** Strengthened generated Skill's
   unsupported-version STOP language, async diagnostic type advice and
   answer-lint. A false positive for explicitly WRONG callback samples
   was fixed (including `// ❌` comments). The Pi runner now uses
   correct read-only discovery tools and `--no-skills` with explicit
   `--skill` for candidate isolation. No global user settings changed.

## Actual native model evidence matrix

The companion `2026-10-16-p5-local-p1-matrix.json` contains **10 observed
of 24 eligible cells**, and **14 not_observed**. Baseline observations:

| Host | Agent | Actual observed cases | Observation |
| --- | --- | --- | --- |
| MacBook | Codex Sol/medium | POS-Q-01, NEG-TYPESCRIPT | source/Claim structural positive, correct negative nonactivation |
| Raspberry Pi | Codex Sol/medium | POS-E-01, NEG-TYPESCRIPT | source/Claim structural positive, correct negative nonactivation |
| sextant | Codex Sol/medium | POS-E-01, NEG-TYPESCRIPT | source/Claim structural positive, correct negative nonactivation |
| MacBook | Pi local Qwen/off | POS-E-01, POS-Q-01, NEG-TYPESCRIPT, BOUND-VERSION-NEW | two positive exact-source failures, negative correct, boundary pending/unsafe |

Every `structural_ok_semantics_unverified` is **not a true model semantic pass**.
The Codex positive source and mock results do not prove production host events.
Original model-origin POS-E-01 code snippets previously passed actual
target CLI 2.1.296 strict and bounded benign native mock (2 Codex, 2 Pi);
the production downstream-error identity is not fully validated.

## Pi 2.1.310 semantic blocker — confirmed, not fixed

The installed Pi local Qwen `mac-qwen/qwen36-35b-a3b-mtp` produced
incomplete source anchors and a `tool.call` observer example referencing
unverified `e.toolName`. This requires target-type review, not an invented
unsupported-API guarantee. A read-only TypeScript case that initially
looped with a `read`-only QA runner completed using `read,ls,find,grep`
without Mods Skill activation; that runner defect is fixed.

Separate **unpublished, isolated candidate** Skills, compiled from a
working tree, were tested with explicit `--no-skills --skill` to prevent
accidental global-Skill reads. Native Pi `message_end` confirmed the
local model and exact original boundary prompt. The model nonetheless
emitted implementation code and historic 2.1.296 API checklists when
asked for unverified 2.1.310 without checking official docs, including
after stronger STOP rules were positioned before other Skill content.
Deterministic auditing now labels such cases **`boundary_scope_violated`**,
not a safe answer or an ordinary source-structure pass.

These dirty-tree candidate tests are experimental and cannot be
represented as a released, signed or matching published bundle.
**Pi's boundary semantic acceptance remains OPEN despite completion
of P1 guardrail/QA implementation.** There is no basis to promise that
Markdown instructions alone will force the local model to comply.

## Remaining P5 and release boundaries

P1-L07, L08 and representative L09 infrastructure and native QA are
complete. P1-L06 detection/mitigations are implemented but Pi's
model-level safety behavior still fails an observed case. P5 Issue #3
must remain OPEN, as must P4 Issues #1/#2 and stable release Issue #4.
There is no full 24/24 host/model qualification, no fresh allowed Claude
Sonnet inference and no complete production Mod event E2E.

All original model prompts and replies, JSONL native traces, login
artifacts, thread IDs, local absolute paths and private credentials
remain **outside public Git**. This document and the machine JSON
contain only case IDs, immutable hashes, expected model settings,
real observed verdicts and their limitations.
