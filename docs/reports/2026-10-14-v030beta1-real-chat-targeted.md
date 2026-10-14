# v0.3.0-beta.1: targeted real Chat-mode pilot (2026-10-14)

**Verdict: PARTIAL / NOT RELEASE-READY.** Reviewed source revision `158acdc7c785df6aa9fbecb11187e29ac400392b`, target Claude Code CLI **2.1.296**, ChatGPT **ordinary Chat mode**, installed/activated personal candidate **0.3.0-beta.1**. This is an **experimental account installation**, not a published stable release. Source content equality was independently verified by the new offline account archive comparator: all 10 reviewed files and the observed server sidecar matched; the downloaded ZIP and uploaded ZIP have different byte hashes due to normalized layout.

The six-case focused pilot deliberately separates auto and explicit invocation. **Four** real conversations were confirmed sent with final replies collected, while **two** explicit sends timed out waiting for browser-window capacity and remain ambiguous; neither was retried, nor classified as a model error. No raw conversation IDs or replies are published.

| Case | Invocation | Actual Skill read | Qualified verdict |
| --- | --- | --- | --- |
| POS-E-01 | explicit | unknown | Sending ambiguous; no retry |
| POS-Q-01 | explicit | unknown | Sending ambiguous; no retry |
| POS-T-STRICT-AUTHOR | explicit | yes | Structural pass; generated manifest also passed native `claude plugin validate --strict` |
| BOUND-VERSION-NEW | explicit | yes | Structural inconclusive by design; separate scoped manual review confirms safe abstention on unverified 2.1.310 `tool.check` fields and relevant official sources |
| POS-E-01-AUTO | **automatic** | yes | Structural pass; two generated handler variants passed native strict CLI validation and individual `.test.ts` tests; intentionally broken downstream-result mutation made the test fail |
| NEG-TYPESCRIPT | **automatic** | no | Correct nonactivation on unrelated TypeScript task |

No Claude Code model inference was performed. All native validation and mocked Mod tests ran on disposable fixtures using the actual installed **Claude Code CLI 2.1.296**; their SHA-only evidence is in [the sanitized JSON report](2026-10-14-v030beta1-real-chat-targeted.json). The sampled positive and negative automatic-routing results (one each) must **never** be extrapolated into reliability claims. The full 46-case routing and independent multi-host model acceptance gates remain unmet. Existing P4/P5/P6 Issues #1–#4 stay open.

Both original source ZIP and server-downloaded account ZIP remain private; only file and observation hashes are committed. This record does not authorize another release, account change, or closing an issue.
