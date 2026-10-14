# Claude Code Mods: Chat-mode two-Skill routing A/B — 2026-10-14

**Exploratory only; not a release and not proof of deterministic auto-activation.**

All **48** comparisons came from authenticated, real ChatGPT **ordinary Chat mode**, not Work. Four sequential non-randomized rounds used the same twelve P4 prompts and standard effort, each in a newly created Chat. The single-Skill control was the published Beta.1. The ephemeral two-Skill variant kept the **entire canonical Beta.1 Skill and root Plugin description unchanged**, adding only one narrow compatibility/security Skill and changing the manifest version.

| Observed read_resource activation | Single Skill, two rounds | Two Skills, two rounds |
|---|---:|---:|
| Boundary/versions/security | **3/16** | **7/16** |
| Ordinary Mods development | **1/4** | **3/4** |
| Irrelevant-task false loads | **0/4** | **0/4** |
| Completed real replies | **24/24** | **24/24** |

Per-round boundary counts: control 3/8 and 0/8; two-Skill 3/8 and 4/8. Fisher's exact two-sided p for the pooled boundary counts is **0.25241**, not conventionally statistically significant. **Small sample, sequential non-randomized design and changing server-side model routing prohibit a causal or deterministic success claim.** Some loaded answers still supplied unverified cross-version tool.check and UI field details; no full independent semantic correctness review of the 48 responses was done.

The exact case IDs, original P4 prompt SHA-256, per-round loaded Skill names and anonymized tool resource-read observations are in [the public sanitized A/B JSON](2026-10-14-multiskill-routing-a-b.json). It does NOT contain raw prompts, responses, cookies, Plugin instance IDs or conversation IDs. Complete transcripts and authentication remain locally on Raspberry Pi under /tmp, not in GitHub.

The account was restored to **published 0.2.0-beta.1, enabled**. The tested prototype ZIP was assembled ephemerally in /tmp; it is **not byte-identical** to the separately implemented SSOT-generated opt-in routing preview. That new compiler requires its own model/host testing before publication or account installation.

Next: repeat with a larger, preferably randomized sample and the **exact generated preview ZIP**, validate negative non-activation, independent technical correctness and rollback. Issue #1 remains OPEN and no stable/Beta release should be inferred from these counts.
