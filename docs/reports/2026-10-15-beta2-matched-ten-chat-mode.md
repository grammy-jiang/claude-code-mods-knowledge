# P4: rejected v0.3.0-beta.2 routing experiment and verified return to published Beta.1

**Test performed:** 2026-10-14, Sydney local time; evidence archived 2026-10-15. Target knowledge: Claude Code **CLI 2.1.296 only**. The experimental candidate was compiled at Git `582279c9531edc39d4f22ac73bdd497b5e3bab6c` from current SSOT; it changed the portable Plugin metadata and early Skill answer instructions. These source changes remain on a separate experimental local branch, **not** `main` and **not** a published GitHub release.

## Ten-case, real ordinary ChatGPT Chat-mode replays

The two cohorts replayed the **exact same ten unchanged prompts** from `evals/p4_cases.json`, each in a new ordinary Chat-mode conversation without `@Plugin`. All twenty sends resolved to distinct actual conversations and all twenty final replies were independently read. Every reply's own metadata reports `gpt-6-thinking` and `standard` effort. The installed version and exact package contents were checked separately; source and server-normalized ZIP files differ in raw hashes, but decompressed reviewed contents match. The private raw replies/account identifiers are not included here.

| Cases | Published `0.2.0-beta.1` | Experimental `0.3.0-beta.2` | Verdict |
| --- | --- | --- | --- |
| Six Mods-positive tasks: canonical Skill resource loads | **3/6** | **0/6** | Candidate visibly regressed; both fail acceptance |
| Six Mods-positive tasks: strict structural passes | **1/6** | **0/6** | Neither is a semantic QA pass |
| Two version/security boundaries: canonical Skill reads | **0/2** | **0/2** | Both fail activation |
| Two unrelated controls: unwanted Skill reads | **0/2** | **0/2** | Correct nonactivation in both samples |

The baseline generated two known-risk flags (unsupported default `register` destructuring and an outdated historical TypeScript reference). Candidate replies generated two historical TypeScript reference flags even though none of the in-scope Skill resources were read. Neither model's generic response is credited as an in-scope Plugin success.

**These are serial, nonrandomized observations**, not a controlled, contemporaneous A/B. The sample is not large enough to assign causality to Plugin descriptions alone or to claim a stable triggering percentage. However, there is **no evidence supporting promotion** of the candidate, so it is rejected. In particular, the 431 passing offline Python tests validated the package/compiler, **not** ChatGPT model routing.

## Account recovery, integrity and other Plugins

The account was read back before/during/after the candidate test and found installed/enabled on `0.2.0-beta.1`, then `0.3.0-beta.2`, then **restored `0.2.0-beta.1`**. Both experimental candidate and restored baseline were downloaded from ChatGPT and each passed the strict 10-file normalized-archive comparator and observed server sidecar verifier. The account's other **ten** personal Plugins had identical recorded name, installed flag, status, version and disabled-Skill-name state before versus after the test. This is a concrete before/after state comparison, not a claim that all external identity or historical audit controls are complete.

The published baseline ZIP SHA-256 is `6803c69841db79e3c913f9febc79e848856936cafbdcd621bd6ce9589b1c2ba3`. The experimental package ZIP SHA-256 is `9a5992897c2b58d2f111cf33ee4a04b018cdd0d04f199f7c2190ce101b52d0d6`. The companion [case-level sanitized evidence](2026-10-15-beta2-matched-ten-chat-mode.json) records per-cohort hashes, Claim-ID detection and source-read URIs, but not private conversation information.

## Release decision and remaining work

Reject `0.3.0-beta.2`; do not merge its routing/answer-contract source changes as a validated improvement, do not cut another release, and keep stable readiness **blocked**. Continue P4 repeatability and actual source/semantic checks, P5 three-host model inference and P6 proof-based release qualification. Open issues remain [#1 routing](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/1), [#2 semantic QA](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/2), [#3 agent hosts](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/3) and [#4 stable gate](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/4).
