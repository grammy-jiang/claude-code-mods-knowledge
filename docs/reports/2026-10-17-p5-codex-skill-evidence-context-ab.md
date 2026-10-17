# Codex Sol medium — task-scoped Skill evidence A/B/C native comparison

Date: 2026-10-17 (Sydney). **144 genuine native Codex App Server
turns**: 108 old frozen 12-case × 3-condition × 3-repeat turns and
36 independent heldout 4-case × 3-condition × 3-repeat turns.

All conditions used the same approved V3 Skill bytes, GPT-6.1 Sol
medium, web search disabled, read-only sandbox, single-turn ephemeral
native App Server process and identical original user prompt bytes.
There was NO fine-tuning, model setting/weight adjustment or global
Skill/ChatGPT Plugin installation.

## Exact frozen twelve-case comparison

| Metric | A: historical V3 Skill | B: V3 + verified Evidence Pack | C: B + buffered P3 gate |
| --- | ---: | ---: | ---: |
| Raw exact approved Claim + official URL (positive) | 8/12 | 12/12 | 12/12 |
| Exact source plus actual new V3 Skill read | 8/12 | 12/12 | 12/12 |
| Normal unrelated no-Skill completion | 12/12 | 12/12 | 12/12 |
| Original native turn completed | 36/36 | 36/36 | 36/36 |
| Selected SSOT context submitted (positive only) | 0/12 | 12/12 | 12/12 |
| Boundary cases flagged for manual review | 12/12 | 12/12 | 12/12 |

**Raw model scores are measured on actual assistant messages,**
not on postfilled citations. B/C developer context receipts confirm
delivery to the native Codex thread, not that the model internally
used every cited Claim. C's gate executes AFTER generation and
therefore cannot improve the model's underlying raw accuracy.

## Separately frozen heldout four-case comparison

| Metric | A: historical V3 Skill | B: V3 + verified Evidence Pack | C: B + buffered P3 gate |
| --- | ---: | ---: | ---: |
| Raw exact approved Claim + official URL (positive) | 6/6 | 6/6 | 6/6 |
| Exact source with actual new V3 Skill read | 6/6 | 6/6 | 6/6 |
| Unrelated no-Skill completion | 3/3 | 3/3 | 3/3 |
| Native completed turns | 12/12 | 12/12 | 12/12 |
| Task-selected developer context submitted | 0/6 | 6/6 | 6/6 |
| Boundary cases flagged for manual review | 3/3 | 3/3 | 3/3 |

Heldout prompts were frozen independently of the original P4 source,
covering transparent observers, strict validation path, unrelated
asyncio reentry and a genuinely unreviewed CLI target. There is
no historical external holdout baseline.

## Paired evidence of impact

### Frozen cases
- A_v3_vs_B_context: improved 4, regressed 0, both-pass 8, both-fail 0 (n=12)
- B_context_vs_C_context_gate: improved 0, regressed 0, both-pass 12, both-fail 0 (n=12)

### Heldout
- A_v3_vs_B_context: improved 0, regressed 0, both-pass 6, both-fail 0 (n=6)
- B_context_vs_C_context_gate: improved 0, regressed 0, both-pass 6, both-fail 0 (n=6)

## P3 postflight buffer and release safety

C used a deterministic, privately buffered gate. For an approved
positive case, it checks model/Skill provenance, actual Claim/URL
links, target version and executable Mod code risks. No unknown
API version code is released. A result with copyable Mod code
still needs independent reviewed CLI native runtime verification.

- Frozen C condition: 18/36 structural-only candidate outcomes passed the gate.
- Heldout C condition: 3/12 structural-only candidate outcomes passed the gate.
- Frozen C positive answers: 6/12 passed the buffer. Six other positives were withheld because executable
Mod code lacked reviewed native runtime semantic validation.
- Heldout C positive answers: 0/6 passed the buffer; all six were withheld, including three with
additional selected-Claim/URL mismatches under the stricter P3 gate.
- Frozen boundary answers: 0/12 passed the gate; heldout
boundary answers: 0/3 passed, despite manual-review-only native scoring.
- The remaining gate approvals are unrelated negative controls
(12 frozen and 3 heldout), not approved executable Mod outputs.

Neither result is production semantic approval; the experiment
withheld all raw model text from end users.

## Limitations and next decision

- Historical previous Codex no-web exact-source baselines were 12/12
  and 6/12 under different Skill/agent environments. This A/B/C
  uses a newly fixed frozen V3 and one isolated Codex App Server
  environment, which is the cleaner causal comparison.
- Independent runs, changing service conditions and small samples
  can produce sampling noise. Results are a workflow comparison,
  not a proof that model weights or any Agent are inherently poor.
- Developer context delivery is explicit and recorded, but there
  is no verifiable internal model-consumption signal.
- A structural Claim/URL match does NOT verify target-native
  Mods tool values, exceptions or runnable code.
- Full ChatGPT Chat-mode Plugin activation and production P3
  delivery controls remain outside this Codex-only experiment.

**Do not install/promote the Skill or close P5 Issue #3 on this
experiment alone.** All original private model text, thread IDs,
account details and host paths remain on Mac.
