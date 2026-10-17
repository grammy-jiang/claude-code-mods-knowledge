# Exact Claude CLI2.1.302 Codex native A/B/C — candidate 0.4.8-beta.1

The rebuilt SSOT Skill from immutable source commit
12a5bf492faa8778a4bc411e0150cbbe8d780c66 and its exact current
candidate Skill SHA were used in a second, independent 144-turn native Codex
App Server experiment. The previous baseline's original 144 native events,
wires, answers and scores were left untouched.

All turns were real and independent, with resolved model
gpt-6.1-sol, medium thinking, disabled Web search, read-only tools.
One wire and one assistant answer hash per turn were checked against
a single completed native turn, with unique ledger hashes and per-cell
installed Skill digest verified independently before publication.

| Actual condition | Completed | Required positive Claim+exact official source | Unrelated negative Skill absent |
| --- | ---: | ---: | ---: |
| A: candidate Skill only | 48/48 | 18/18 | 15/15 |
| B: candidate Skill + task-selected evidence | 48/48 | 18/18 | 15/15 |
| C: B + deterministic buffered structural gate | 48/48 | 18/18 | 15/15 |

The source and negative metrics are identical to the prior CLI2.1.302
baseline; adding contextual Claim delivery therefore offered no measurable
benefit for these already-saturated structural metrics.

C's structural gate admitted six of 18 positive answers for *further*
code-level review, while 12 positive answers and all 15 boundary cases
were held for further review. It did not prove native semantic correctness
or run original model-produced Mod code. A positive source link by itself
cannot demonstrate the safety of executable code, permission policy,
UI focus, model's actual attention, or host behavior.

The private original model prompts, answers, wire payloads, account IDs
and workspace paths were not exported. All publicly recorded per-cell
evidence is aggregate-only, SHA-based and strictly limited to Claude CLI
2.1.302. The ChatGPT Chat Mode beta0.4.8 full 46-case experiment is
separately pending and remains the primary P4 production gate. HOLD.
