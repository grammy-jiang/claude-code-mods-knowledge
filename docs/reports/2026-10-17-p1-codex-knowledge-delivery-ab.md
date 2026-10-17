# P1 scoped knowledge delivery — 24 native Codex A/B turns

Date: 2026-10-17 (Australia/Sydney). Archived, SHA-verified original native turns; no synthetic or replay-substituted model results.

## Treatment and controls

The two arms share *byte-identical original task prompts*, the same frozen Skill (SHA-256 pinned), optional task-selected evidence files, reviewed Claims, hosted model and medium effort. The only treatment is sending that same selected SSOT evidence as thread-scoped `developerInstructions` at native Codex App Server `thread/start`. Web search is disabled. Negative controls never receive a Mods payload.

| Metric | File only | Preloaded evidence |
| --- | ---: | ---: |
| Real native turns | 12 | 12 |
| Completed native turns | 12 | 12 |
| Positive exact Claim/URL structural pass (of 8) | 5 | 7 |
| Positive actual Skill reads (of 8) | 8 | 8 |
| Positive optional selected-file reads (of 8) | 0 | 1 |
| Positive preload accepted by App Server (of 8) | 0 | 8 |
| Negative completed without Mods Skill (of 4) | 4 | 4 |
| Negative Mods payloads wrongly injected (of 4) | 0 | 0 |
| Completed-turn median wall time (s) | 17.62 | 16.54 |

## Interpretation

The pre-inference delivery transport demonstrably worked: each treatment thread-start was accepted, with a SHA-pinned evidence payload selected from reviewed SSOT, without changing the user prompt or installing a Skill. However, *transport acceptance is not model knowledge utilization*; some outputs still fail exact source structure even with the payload available. The positive structural pass-rate difference is exploratory, not causal proof of a reliable/general improvement. No target CLI generated-code semantic review, local Pi native inference, or ChatGPT ordinary Chat-mode Plugin activation was performed during this P1 pilot.

## Release decision

**No Stable promotion or production installation.** Retain the approved Claude Code CLI 2.1.296 boundary; the Mac's newer installed CLI is not qualified by this SSOT. Keep P5 semantic/Chat-mode gates open. The Pi file-backed `--append-system-prompt` transport is implemented and unit tested, but still requires a dedicated native Pi model acceptance run.
