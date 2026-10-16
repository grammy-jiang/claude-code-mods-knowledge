# P5 local-agent-first medium-model development plan

Date: 2026-10-16, Australia/Sydney. Owner prioritizes **native local Agent
development and testing** while ChatGPT ordinary Chat-mode 429/transport is
unreliable. P4 and stable-release gates remain OPEN; they are merely paused.
Claude Code quota is exhausted: **never run Claude model inference yet**.

## Reviewed baseline

- PR #49 merged, Git main d3db512; reviewed installed Skill source
  6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e; package 0.3.4-beta.2.
- Installed SKILL.md SHA256:
  03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e.
- Current CLI versions across MacBook Pro, Raspberry Pi and sextant:
  Claude Code 2.1.301, Codex 0.163.0, Pi Agent 1.3.0.
- 31 active approved knowledge Claims remain scoped to **Claude CLI
  2.1.296**; 2.1.301 installation does not certify full Mods API support.
- Fresh native CLI auth check on all three machines: **six of six logged
  in**. Mac Claude initially loggedIn=false; owner completed private
  iPhone OAuth; login process exited 0; independent auth status now true.
  This does NOT establish model quota or successful inference.
- Existing Mac Codex global default is gpt-6-astra/max. Native
  Codex model/list confirmed **gpt-6.1-sol / medium** is supported;
  select it per-run without changing global config.
- Existing Mac Pi defaults to **mac-qwen/qwen36-35b-a3b-mtp** and thinking
  off. Native model catalog says it has NO thinking capability. Preserve
  this default, rather than substituting remote GPT models or a fictional
  Pi medium effort.
- Claude future model preference: **Sonnet / medium**, supported by the
  installed CLI arguments; NO Claude model requests until quota returns.

## First native model cohort (Mac only)

Eight real bounded native commands used four frozen case prompts from
evals/p4_cases.json. Codex was ephemeral, read-only, specified
gpt-6.1-sol/medium. Pi used the local mac-qwen provider, thinking off,
ephemeral session, read-only tool, no extensions/MCP/context. All raw
model output and JSONL event traces are PRIVATE, not checked into Git.

| Original case | Codex first observations | Pi local first observations |
| --- | --- | --- |
| POS-E-01 | Actual Mods SKILL, events, types reads; named register with three-argument callback and isolated diagnostic, not native-tested | Actual Mods SKILL and events read; weak diagnostic/async example requires independent semantic review |
| POS-Q-01 | Mods SKILL and testing reference read; directory-oriented offline Mod test command and source | Mods SKILL read; directory-oriented Mod test command and source |
| NEG-TYPESCRIPT | No Mods SKILL read; answered about lack of project in initially empty test directory | No Mods SKILL read; 58 irrelevant read-tool calls, model error and no usable final reply; incomplete, not a Plugin false activation |
| BOUND-VERSION-NEW | Mods SKILL read and cautious unsupported 2.1.310 warning | Mods SKILL read, warns 2.1.310 unverified but repeats scoped 2.1.296 facts under target-newer question |

Native 2.1.301 CLI help independently confirms the Mod test directory
parameter is optional (current directory default) while Mod validate
requires a path. Historical target-native 2.1.296 proof must remain
separately version-matched.

Pi event metadata independently shows its actual local Qwen provider and
model for all four cases. This first Codex exec JSONL did not expose a
verified resolved model identity; only command-selected model and actual
native catalog support are known. The command exits do NOT constitute
a semantic PASS, and no new model-generated Mod artifact was yet
independently strict-validated / natively tested.

The initial negative fixtures had NO TypeScript project. A separate
negative-case replay with a safe normal TypeScript mini-project was
started to avoid scoring environment confusion as Skill failure; preserve
both cohorts independently, not overwrite initial observations.

## Updated task checklist and acceptance

- [x] P0-L01: Verify Claude Code + Codex CLI auth on all three machines;
  fix Mac Claude with private iPhone OAuth and recheck fresh status.
- [x] P0-L02: Confirm selected non-maximal models and efforts;
  choose Codex gpt-6.1-sol/medium, Pi existing local Qwen/off;
  defer all Claude Sonnet/medium inference for quota.
- [x] P0-L03: Execute first four exact P4 positive/negative/boundary
  cases for Codex and Pi in private read-only workspaces; record native events
  and distinctions between exposed, read, replied, and verified semantics.
- [x] P0-L04: Complete and grade negative TypeScript fixture replay.
  Pi first ran 58 reads and ended in error with no project; a real TypeScript fixture still timed out after 74 reads when only the read tool was available. Supplying read/ls/find/grep made Pi complete in 21 seconds, with no Mods Skill read. This is a QA tool-permission design defect, not observed false Skill activation.
- [ ] P0-L05: Independent structural + semantic review of original
  model replies/code and exact official source/Claim anchors, then
  run model-origin artifact strict validation and native offline tests
  only for exact reviewed Claude CLI 2.1.296 (four real model-origin snippets already passed target-native strict validation and harmless mock); keep failures separate
  from missing artifacts or wrong target versions.
- [ ] P1-L06: Repair remaining Pi answer-semantic issues: async logging
  and downstream-result transparency, Claim/source precision and
  unsupported-version framing. The 58/74 read-loop cases were caused by
  the QA runner omitting the normal read-only discovery tools; do not
  misclassify this harness defect as a persistent model failure.
- [ ] P1-L07: Improve observed-model provenance for Codex (not only
  per-invocation flags); retain actual Pi message_end identity checks.
- [ ] P1-L08: Reuse native discovery, Pi evidence summarizer, answer
  lint, source verifier, .test.ts native fixtures and frozen cases
  in one per-Agent/per-host matrix. Do not implement parallel divergent
  versions of the SSOT.
- [ ] P1-L09: Extend native behavior tests on Pi/sextant as appropriate;
  do NOT assume Mac-hosted local Qwen is available on the other machines.
- [ ] P2-L10: Resume Claude Code Sonnet/medium P5 real-model tests
  only when quota and owner authorization permit; require actual
  model inference, reference reads and end-to-end safe CLI event.
- [ ] P2-L11: Implement documented SSOT/Skill corrections from
  confirmed failures, rebuild and check matching hashes on all hosts.
- [ ] P2-L12: Update Issue #3 with only sanitized per-case evidence and
  remain OPEN until real model/host acceptance is complete. P4 Chat-mode
  Issue #1/#2 and Stable P6 Issue #4 stay blocked.

## Privacy and operational constraints

Use an isolated Git worktree; preserve unrelated active Agents, credentials,
private account/login data, browser state and unrelated Plugin installations.
No global model config changes, no Claude model calls, no chat 429 retries,
no public raw prompts, model responses, JSONL, local file paths, OAuth
authorization URL or code. Record only case IDs, hashes, coarse verdicts
and source/CLI/model versions in GitHub.

References: docs/reports/2026-10-16-p5-local-cli-and-skill-upgrade.md,
docs/reports/2026-10-15-p5-native-model-pinning.md,
docs/operations/p5-native-skill-discovery.md,
docs/operations/p4-p6-closeout-checklist.md and GitHub Issue #3.

The sanitized first-cohort evidence report is at
docs/reports/2026-10-16-p5-medium-local-agent-qa.md.
