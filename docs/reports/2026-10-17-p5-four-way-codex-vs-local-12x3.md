# P5 native AI Agent model comparison — Codex vs Qwen/Gemma, 12×3

Date: 2026-10-17 (Sydney). Identical twelve approved frozen P4 prompts, three independent real model turns per Agent/model stack. 144 total real native model turns, never synthetic or substituted.

## Controlled provenance and fair interpretation

- Codex CLI 0.163.0, OpenAI-hosted `gpt-6.1-sol`, per-turn `medium`. Verified twice through App Server same-thread model/effort return and authenticated native turns.
- **Two separate Codex cohorts**: ordinary native environment, where webSearch is available; an offline model cohort with explicit `web_search="disabled"` and **zero actual native webSearch items**.
- Pi Agent 1.3.0 with existing local Qwen3.6 and Gemma 4 31B, thinking off. Identical SHA-pinned Mods Skill. Strict K-Claim ID and exact first-party official source fragment checker across all stacks.
- This is NOT a fully controlled pure LLM architecture test: Codex uses hosted model+shell App Server and other globally installed plugin resources; Pi uses local model+read/ls/find/grep. Native web-disabled Codex is a closer, but not identical, comparison.
- All boundary prompts run in private, buffer-only experimental sessions; unverified runnable code is never delivered to the end user.

## Four-way frozen native results

| Metric | Qwen3.6 + Pi | Gemma 4 31B + Pi | Codex Sol medium, no web | Codex Sol medium, web available |
| --- | ---: | ---: | ---: | ---: |
| Observed native model turns | 36/36 | 36/36 | 36/36 | 36/36 |
| Native completed turns | 33/36 | 34/36 | 36/36 | 36/36 |
| Positive exact Claim/official source structure | 2/12 | 3/12 | 12/12 | 11/12 |
| Unrelated negatives completed without Mods Skill | 6/12 | 10/12 | 12/12 | 12/12 |
| Explicitly detected unreviewed-version scope violations | 3/12 | 3/12 | 0/12 | 0/12 |
| Boundary responses with copyable code needing manual review | 7/12 | 8/12 | 0/12 | 0/12 |
| Native incomplete/tool loop or failure | 3 | 2 | 0 | 0 |
| Completed-task median elapsed | 14.99 s | 29.62 s | 19.31 s | 25.69 s |
| Completed-task P95 | 36.35 s | 54.12 s | 33.84 s | 33.96 s |

## Case-by-case three-run outcomes

For positive cases this is exact Claim/source structure; for unrelated negatives it is completed no-Skill routing; for boundaries it is **detected violations** (lower is better, other results are NOT certified safe).

| Frozen case | Kind | Qwen3.6 + Pi | Gemma 4 31B + Pi | Codex Sol medium, no web | Codex Sol medium, web available |
| --- | --- | ---: | ---: | ---: | ---: |
| POS-E-01 | positive | 0/3 | 0/3 | 3/3 | 3/3 |
| POS-Q-01 | positive | 0/3 | 0/3 | 3/3 | 2/3 |
| POS-S-02 | positive | 1/3 | 3/3 | 3/3 | 3/3 |
| POS-P-01 | positive | 1/3 | 0/3 | 3/3 | 3/3 |
| NEG-TYPESCRIPT | negative | 2/3 | 2/3 | 3/3 | 3/3 |
| NEG-PYTHON | negative | 0/3 | 3/3 | 3/3 | 3/3 |
| NEG-MCP | negative | 2/3 | 2/3 | 3/3 | 3/3 |
| NEG-LEGACY-HOOK | negative | 2/3 | 3/3 | 3/3 | 3/3 |
| BOUND-VERSION-NEW | boundary | 3/3 | 3/3 | 0/3 | 0/3 |
| BOUND-VERSION-OLD | boundary | 0/3 | 0/3 | 0/3 | 0/3 |
| BOUND-SURFACE | boundary | 0/3 | 0/3 | 0/3 | 0/3 |
| BOUND-HISTORY | boundary | 0/3 | 0/3 | 0/3 | 0/3 |

Positive source structure = presence of actual Skill read plus all required approved Claim IDs and official URL fragments. This does **NOT** mean that runnable code is semantically proven correct.

Zero **detected** version violations is NOT a safety certificate. All other boundary answers remain manual-review/unverified. The code-shaped marker also catches explicitly negative examples, and is intentionally only a review signal.

Codex no-web cohort has 35/36 measured wall-clock times: one original first turn had a post-inference report-formatting exception but preserved native model/Skill/Claim event evidence; the missing duration remains null rather than fabricated or replayed.

Codex ordinary-native cohort used 40 actual webSearch items across 36 turns; no-web cohort used 0. The first is an Agent-stack workflow result, not purely a model IQ metric.

## Detailed verdict distribution

### Qwen3.6 + Pi

| Native evaluator outcome | Count |
| --- | ---: |
| `boundary_incomplete_or_invalid` | 1 |
| `boundary_manual_review_required` | 7 |
| `boundary_scope_violated` | 3 |
| `boundary_skill_not_loaded` | 1 |
| `incomplete_or_loop` | 3 |
| `negative_false_skill_activation` | 1 |
| `negative_incomplete_or_blocked` | 2 |
| `negative_nonactivation_observed` | 6 |
| `positive_exact_claim_or_source_missing` | 10 |
| `positive_source_pass_code_needs_native_validation` | 1 |
| `positive_source_structure_only` | 1 |

### Gemma 4 31B + Pi

| Native evaluator outcome | Count |
| --- | ---: |
| `boundary_manual_review_required` | 9 |
| `boundary_scope_violated` | 3 |
| `incomplete_or_loop` | 2 |
| `negative_nonactivation_observed` | 10 |
| `positive_exact_claim_or_source_missing` | 9 |
| `positive_source_pass_code_needs_native_validation` | 1 |
| `positive_source_structure_only` | 2 |

### Codex Sol medium, no web

| Native evaluator outcome | Count |
| --- | ---: |
| `boundary_manual_review_required` | 12 |
| `negative_nonactivation_observed` | 12 |
| `positive_source_structure_only` | 12 |

### Codex Sol medium, web available

| Native evaluator outcome | Count |
| --- | ---: |
| `boundary_manual_review_required` | 12 |
| `negative_nonactivation_observed` | 12 |
| `positive_exact_claim_or_source_missing` | 1 |
| `positive_source_structure_only` | 11 |

## Independent code check and release gate

Two eligible original model-generated Codex POS-E-01 observer snippets passed the retained real Claude Code CLI 2.1.296 strict validator and safe native mock. This does not establish downstream tool error identity in real production.

No model, including Codex, is approved for unrestricted Mod API code generation until real target CLI event behavior, source evidence and deterministic version boundary gating all pass. The current Pi Agent global default Qwen and approved Skill were not changed; no Claude model calls or GPT-OSS 120B inference.

All raw user/model content, native JSONL, thread identifiers and personal host paths remain privately on Mac. Public artifact contains only case IDs, verdicts, timings and SHA256 metadata.
