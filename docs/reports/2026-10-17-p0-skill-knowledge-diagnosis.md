# P0 system diagnosis — Agent Skills knowledge discovery, routing and use

**Date:** 2026-10-17 (Australia/Sydney)
**Audited revision:** `f8f3312` (fetched `origin/main`; the Mac's primary `main` checkout remained 48 commits behind and was **not** reset).
**Execution:** isolated `audit/p0-skill-knowledge-20261017` worktree; offline code audit, public-report recomputation and private transcript **digest validation only**. No new LLM/ChatGPT turns, installations, active service changes, account changes, published Plugin, or release promotion. **Diagnosis, not remediation.**

## Executive finding

The **largest evidenced bottleneck is not generating task-specific reviewed knowledge; it is ensuring the chosen evidence reaches and is actually consumed by the Agent.** The next bottleneck is using knowledge correctly after reading the main Skill. ChatGPT's automatic Plugin selection is a separate, host-specific bottleneck. These are distinct failures, not one universal problem fixable by a longer `SKILL.md` or a vector database.

## Evidence integrity and frozen population

- The reviewed P5 report `docs/reports/2026-10-17-p5-p123-seven-stack-12x3.json` contains **252 authentic native turns**, from **five Pi/local model stacks plus two Codex configurations**, twelve frozen task cases, three trials per stack/case.
- On Mac, all **252/252** private original event/wire files still exist, and **252/252 SHA-256 hashes match** the report's `raw_events_sha256` fields. No raw prompts, output, account IDs, or private paths have been copied into this report.
- In the **84 positive trials**, **84/84** task-specific `selected-evidence.md` files exist on disk in the individual disposable Skill directories. These have not been installed as a user-wide Skill.
- The public, model-free reporter `scripts/audit_p0_knowledge_funnel.py` recomputes the funnel without reading private transcripts. Private file and digest confirmation was a separate local, read-only check.
- A freshly checked host reports **Claude Code CLI 2.1.301**, **Codex CLI 0.163.0**, and **Pi Agent 1.3.0**. The SSOT currently approves Mods claims only for **Claude Code CLI 2.1.296**. The host is therefore **not** qualified by the reviewed Claim scope.
- An isolated, entirely offline repository regression run yielded **788 passed, 11 skipped**. All 11 skips are Claude Code native validation checks requiring the earlier reviewed **2.1.296** host. `ruff check .` passed. These green unit/package checks are **not** current 2.1.301 native Mods qualification.

| Observable stage | Native positives | Interpretation |
| --- | ---: | --- |
| Task Evidence Pack exists in disposable workspace | **84/84** | Local file delivery/preparation succeeded; manually verified on Mac |
| Main target Skill actually read | **76/84** | Registration/availability and observed read are not the same |
| Original answer passes exact approved Claim/URL **structure** | **39/84** | Structural grounding only; NOT factual or executable correctness |
| Agent actually opened `selected-evidence.md` | **1/84** | Evidence-pack utilization nearly absent; does NOT mean no other reference was read |

Additional descriptive observations: **70/84** native negative trials completed with no Mods Skill, and the evaluator detected **3/84** version/surface boundary violations. A zero detected violation never certifies remaining boundary answers safe. All **84/84 positive turns** were marked native-completed, which alone does not establish substantive, correct answers. Cohorts differ in model settings and tools, so the pooled totals are **diagnostic counts, not causal model rankings**.

## P0-F01 — Task evidence is optional, not an enforced knowledge-delivery stage (high confidence)

- `src/mods_knowledge/task_evidence.py` can deterministically choose up to six version-scoped approved K-Claims and render a concise Evidence Pack. Existing frozen-case selector tests pass.
- `scripts/run_p5_p123_local_case.py` and `scripts/run_p5_p123_codex_case.py` write `references/selected-evidence.md` into **disposable copies** of the candidate Skill before invoking native Agents. The **original user prompts remain unchanged**, and there is **no deterministic injection of this file's contents into the model's initial context**. The Agent must decide to open it.
- `src/mods_knowledge/compiler.py` explicitly says to read the optional file **if an authorized runner generated it**; the normal compiled Skill bundle does **not** include it. A fresh offline build from the audited source produced 31 approved Claims, 53 package artifacts and a 113-line `SKILL.md`, with **no** `selected-evidence.md` in the compiled common package.
- The P3 Pi delivery gate checks required citations in the *original answer*, but does **not** require a successful read of the optional selected file. An exact citation can come from another reference (or be reproduced by the model); a citation check is not proof of selected-file consumption.

**Consequence:** `pack_generated`, `pack_present`, `Skill_read`, `topic_reference_read`, `selected_pack_read` and `answer_structurally_grounded` must be separate measured stages. Making the pack *available* is not a retrieval guarantee.

## P0-F02 — Main Skill reading does not establish knowledge use or semantic correctness (high confidence)

Of 84 positive native turns, 76 showed a real main Skill read, while only 39 answers passed the exact approved Claim/official URL test. Neither number establishes correctness of runnable Mod code. The gate explicitly reports `semantic_correctness_verified: False`, and the existing report refuses stable promotion. An Agent can load a Skill but ignore relevant instructions or cite a familiar reference without applying the verified API semantics.

**Consequence:** retain a native target-version semantic oracle: real CLI 2.1.296 strict checks plus behavioral/mock tests, with downstream result/error preservation as an independent acceptance criterion. Do not relabel `source_verdict: pass` as success.

## P0-F03 — ChatGPT Chat-mode automatic selection is a separate problem (high confidence observation; cause unproven)

The archived six-arm **42-conversation** ChatGPT Chat-mode report (`docs/reports/2026-10-15-six-arm-automatic-routing-observations.json`) contains **0/24 positive automatic Plugin Skill reads** and **6/6 explicit-control Skill reads**. Earlier Chat-mode runs showed different automatic-loading results; there is no demonstrated stable routing improvement. The final arm's 55-second early-to-late interval violated the prescribed 180-second timing protocol, so the full causal experiment was **not** protocol-qualified.

The ChatGPT Plugin is **skills-only**. The project has not proved control over internal Chat-mode automatic routing/eligibility/cache, and a local Pi enforcement layer cannot be assumed to run inside ChatGPT Chat mode. No ChatGPT Work-mode claim is inferred from Chat-mode evidence.

**Consequence:** do not attribute 0/24 to a specific hidden router mechanism; keep automatic and explicit evaluation independent and maintain host-specific acceptance gates.

## P0-F04 — Deterministic task router has observable coverage/scope gaps (reproduced offline)

`route_task()` in `src/mods_knowledge/task_evidence.py` uses regexes over the **entire prompt**, rather than structured Mod-target version and host-surface fields. A small, non-benchmark exploratory probe produced:

| Prompt class | Actual routing | P0 concern |
| --- | --- | --- |
| `How do I create a Mod observer for CLI 2.1.296?` | `unrelated` | False negative: abbreviated in-scope wording |
| `How do I test Mods 2.1.296 offline?` | `unrelated` | False negative: standalone `Mods` |
| `How to test a Claude Code Mod on CLI 2.1.296 with Python 3.14.8?` | `blocked` | Incidental **Python** version mistaken for Mod target version |
| `Build a VS Code pane Claude Code Mods implementation on 2.1.296.` | `mods` | Out-of-scope host not rejected unless surface-related keyword (e.g. `guarantee`) is also present |
| `What is the latest Claude Code Mods API for observer logging?` | `mods`, target `2.1.296` | Unversioned **latest** request silently maps to the historical reviewed target |
| Explicit unreviewed Mod target `2.1.310` | `blocked` | Correct fail-closed behavior, retain it |

These are **deterministic code-level defects/limitations**, not estimates of production failure probability. The small probe is exploratory and was not used to tune/model-rank the original frozen 12-case cohort. Fixing these should preserve conservative refusal for truly unreviewed targets.

## P0-F05 — Knowledge scope and postflight protection are narrower than users may assume

The current SSOT has **91 registered sources** but only **31 approved Claims for Claude Code CLI 2.1.296** in the audited generated package. This is appropriate conservative provenance, not current-version coverage. There is no verified current API guarantee for unreviewed versions/surfaces. The P3 buffered answer gate is an **opt-in local Pi research harness**, not an installed deterministic gate for Codex App Server or ChatGPT Chat mode. No native retrieval Recall@k/semantic relevance baseline exists; the selector is a bounded keyword/regex system, not a general knowledge search index.

## Root-cause confidence

| Assessment | Status |
| --- | --- |
| Task evidence generation/physical file missing | **Ruled out** for the archived 84 positives |
| Selected evidence not normally opened by Agent | **Directly observed** (1/84) |
| Skill registration mistaken for actual Skill read | **Known measurement hazard**; existing native QA differentiates them |
| Heuristic intent/version classifier misses/parses scope wrongly | **Reproduced** by offline input probes |
| Older pretraining knowledge specifically caused any given error | **Unproven** without fact-level answer audits |
| ChatGPT internal router/cache explains 0/24 | **Unknown**; cannot infer a specific backend cause |
| Source citations imply executable behavior | **False inference**; deliberately rejected by current release gates |

## Recommended next stage (P1 proposal; NOT executed in P0)

1. **Evidence delivery A/B:** compare unchanged baseline, explicit Skill instruction, file-based mandatory read with native read receipt, and minimal evidence content pre-injected by a deterministic host adapter. Keep original task text and target model settings fixed; distinguish a successful *delivery* from actual use. For ChatGPT Chat mode, study only capabilities available to skills-only Plugins rather than assuming an intercepting tool/hook exists.
2. **Router hardening:** parse product/version/surface as distinct fields; add abbreviated/paraphrased English and Chinese positives, exclusions, multiple-version questions, incidental version strings, and explicit `latest` requests. Fail closed if latest/current first-party proof is not available.
3. **Quality measurement:** instrument `discovered → skill read → relevant reference/pack delivered → required fact supported → output grounded → target-native semantic test`. Report false activation/negative-case completion separately. Run a semantic human-reviewed sample rather than only URL pattern matching.
4. **Cross-host rollout safety:** retain host-specific evidence gates; no persistent production installation or version bump until a verified acceptance improvement, no increase in unrelated Skill activation, and working semantic native CLI tests. Rate-limit/cap ChatGPT conversation traffic and respect prior HTTP 429 investigations.

**P0 acceptance:** source revision pinned, real archive digests matched, offline baseline reproducible, at least one concrete deterministic routing defect exposed, observed vs inferred failure modes separated, no production changes and no new model traffic. The next implementation decisions belong to P1.
