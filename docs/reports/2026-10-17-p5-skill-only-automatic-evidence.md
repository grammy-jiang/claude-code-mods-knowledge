# P5 Skill-only Qwen3.6 experiment: automatic Claim/source evidence

Date: 2026-10-17 (Sydney). These are authentic native Pi Agent 1.3.0
auto-discovery turns on the **unchanged local Qwen3.6 35B-A3B**
provider. There was no fine-tuning, model-weight swap, decoding
configuration change, new inference server, or global Skill install.

## What changed

The SSOT compiler generates one citation contract for **both**
automatic and explicit Mods Skill activation. Each topic reference
begins with copy-ready approved K-Claim/first-party URL fragment
pairs; a 31-Claim evidence index also derives from the reviewed
single source of truth. No new or unapproved API fact was added.

## Matched 12-case × 3-turn source and routing results

| Metric | Historical Qwen Skill | Revised Skill candidate |
| --- | ---: | ---: |
| Positive exact approved Claim+official URL structure | 2/12 | 9/12 |
| Unrelated tasks completed without Mods Skill | 10/12 | 8/12 |
| Rule-detected unreviewed version implementation violations | 3/12 | 0/12 |

Lower is better for version violations. Zero rule-detected violations
is **NOT** proof of full safety; every other boundary response still
requires code/version review.

## Frozen original case observations

| Case | Category | Exact source / correct negative / detected boundary | Skill reads |
| --- | --- | ---: | ---: |
| BOUND-HISTORY | boundary | 0/3 | 2/3 |
| BOUND-SURFACE | boundary | 0/3 | 3/3 |
| BOUND-VERSION-NEW | boundary | 0/3 | 2/3 |
| BOUND-VERSION-OLD | boundary | 0/3 | 1/3 |
| NEG-LEGACY-HOOK | negative | 0/3 | 2/3 |
| NEG-MCP | negative | 3/3 | 0/3 |
| NEG-PYTHON | negative | 3/3 | 0/3 |
| NEG-TYPESCRIPT | negative | 2/3 | 0/3 |
| POS-E-01 | positive | 3/3 | 3/3 |
| POS-P-01 | positive | 2/3 | 3/3 |
| POS-Q-01 | positive | 1/3 | 3/3 |
| POS-S-02 | positive | 3/3 | 3/3 |

For a boundary row, the value counts **detected failures**, not safety
passes. The table is descriptive of native source/text evidence only.

## Historical observations and limitations

- In an initial two-positive native A/B, both the installed Skill
  and an early revised candidate scored 0/2 exact Claim/source passes.
- A follow-up candidate with evidence lines near the bottom of a
  topic reference also failed. The strongest candidate moved
  copy-ready citation pairs to the beginning of topic references
  and placed the source contract in the Skill discovery description.
- The strongest candidate was independently tested with four
  positive cases repeated three times, plus four unrelated
  negatives and four source/version boundaries repeated three times.
- The old Qwen benchmark and this revised Skill pilot share
  frozen prompt SHA/model identity but are **not an interleaved
  randomized A/B** and were executed on separate occasions.
- Exact citations establish evidence **structure**, not
  independent factual correctness or executable Mod semantics.
- The research version scope remains Claude Code CLI 2.1.296.
  This result does not authorize newer API code or stable release.

## Safety and delivery

All generated Claude Code, Codex, Pi Agent and ChatGPT Skill/Plugin
files are deterministic copies of the same reviewed source.
A passing package verification is not real ChatGPT Chat-mode
Plugin activation verification. Original native model replies,
tool-event JSONL and personal paths remain in a private Mac
directory; only bounded verdicts, case IDs, timings and SHA256
are published. No production user Skill or Plugin is updated
by this experiment. Keep P5 and stable release gates open.
