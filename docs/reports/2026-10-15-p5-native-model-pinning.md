# P5 native Agent-model QA — model identity drift and pinned replay

**Date:** 2026-10-15 (Australia/Sydney). Target knowledge: **Claude Code CLI 2.1.296**, not all versions or surfaces. Portable approved Skill source Git SHA `81fdf78656238f8383cbeed54ed3420bdc480231`, `SKILL.md` SHA-256 `8cf14b9cd072d6ca7b8796cc863b6168694f663a4246d3fbb7da51480cb391b8` (matching project-local Pi and Codex Skill copies). All source claims remain read-only and unchanged. Raw local native events, model responses and account information remain private.

## Root cause discovered: Pi Agent's implicit model differed

A set of 14 **exact original P4 prompts** was replayed through real Pi Agent 1.1.0 with a project-local approved Skill exposed by `--skill` and the native `read` tool. The run **omitted `--provider` and `--model`**. The actual `message_end` metadata consistently recorded **`mac-qwen/qwen36-35b-a3b-mtp` in all 14 attempts** — *not* the `openai-codex/gpt-5.5` model used in earlier Pi Agent QA. These were not comparable same-model runs. Twelve attempts reached `agent_end`; eleven had a usable final response; two timed out and one ended with a native model error. Actual Skill reads occurred for 6/6 Mods-positive and 4/4 boundary tasks; there were no observed false Skill reads for the four unrelated controls, but one unrelated control had no usable reply and another timed out. No P5 acceptance can be inferred for that unpinned cohort.

The native Qwen answers also exhibited known-risk patterns: an unsupported two-argument `tool.call` callback and a default/destructured `register` export. Their detection does not prove the remainder of generated code is correct. Critically, recording a `--skill` path means Skill *metadata was exposed*, **not** that every model turn automatically read the Skill; only actual `read` tool events count.

## Four original P4 prompts replayed with an explicit provider/model

A second independent run used the actual Pi CLI options **`--provider openai-codex --model gpt-5.5`** without modifying any global settings. The returned assistant events independently confirmed **`openai-codex/gpt-5.5` in 4/4**. Each event stream also contained exactly the original P4 user prompt. All four produced usable final replies.

| Exact P4 case | Native Skill `read` | Source/answer quality finding |
| --- | --- | --- |
| `POS-E-01` transparent `tool.call` observer | Yes; `SKILL.md` and events reference | Missing required K-Claims and direct first-party source link: **structural fail** |
| `POS-Q-01` Mod `.test.ts` test command | Yes; `SKILL.md` | Missing expected test Claim/direct source; offered invalid test-file invocation: **structural fail** |
| `NEG-TYPESCRIPT` unrelated TypeScript overloads | No | Correct **negative nonactivation**; ordinary answer semantics not scored for this Plugin |
| `BOUND-VERSION-NEW` unverified newer Mods API | Yes; `SKILL.md` | **Requires independent boundary semantic review**; a Skill read alone is not acceptance |

Thus correct model pinning fixed the **measurement provenance**, not Pi's technical answer reliability. A named, checked source revision and an actual model-specific trace are required separately from mere CLI command arguments.

## Other hosts, and strict separation of evidence kinds

- **Codex CLI 0.162.1 on Raspberry Pi:** three original P4 real model turns completed. `POS-E-01` read the actual Skill and references, with approved K-Claim IDs and direct first-party Mods links. `NEG-TYPESCRIPT` did not read the Skill. `BOUND-VERSION-NEW` read the Skill but its final answer omitted direct Mods documentation and Claim IDs. Codex JSONL in this run did **not** expose an independently verified resolved model identifier; model pinning was also absent, so this is **partial host evidence**, not an unconditional P5-B pass.
- **Claude Code CLI 2.1.296 on MacBook Pro:** a real model attempt produced `authentication_failed`; neither this nor a separate Pi CLI 2.1.299 authentication failure is a Mod inference verdict. The Mac's independent `claude plugin validate --strict` and safe mocked `.test.ts` checks test syntax, **not** model activation.
- **Version mismatch:** Raspberry Pi Claude Code was **2.1.299** and sextant Claude Code **2.1.289** during these checks. Neither is accepted as native 2.1.296 runtime proof; sextant had no Pi Agent installation in the preceding model-free host survey.

## New fail-closed verification control

`mods_knowledge.pi_model_evidence.summarize_pi_model_trace` accepts private real Pi Agent JSONL *events in memory*, the exact original case, explicit model-flag provenance, source SHA and Skill directory. It only returns hashes, sanitized Skill-relative paths, observed model/provider, matched-prompt/model booleans and categorized evidence verdicts. It **never emits original prompt/response text, outside-workspace file paths, credentials or native error messages**. Model metadata mismatches or omitted pin flags receive `invalid_provenance`; incomplete/error turns remain `blocked_or_incomplete`; unrelated file-read errors do not wrongly become Mods Skill activation failures. A structural pass expressly remains `structural_ok_semantics_unverified` until independent technical review.

The [companion sanitized evidence](2026-10-15-p5-native-model-pinning.json) stores 18 Pi model attempts across the **two distinct cohorts**, three real Codex case hashes and the actual limitations. It is **not** a 46-case ChatGPT Plugin auto-routing evaluation or a complete three-host P5 acceptance. P4, P5 and P6 stable-readiness gates remain open and blocked.
