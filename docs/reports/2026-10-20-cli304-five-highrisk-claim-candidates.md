# Claude Code 2.1.304 — five high-risk new Claim CANDIDATES (no approval)

Date: 2026-10-20, Sydney. **This document and the accompanying new K-Claims are a triage proposal, not new approved guidance.** No CLI304 Skill, account Plugin, or Stable release is authorized.

## Source and review status

The 31 previous approved CLI302 Claims remain unchanged, with range `[2.1.302, 2.1.303)` and original decision ledgers. Seven current first-party HTML observations have been recorded with SHA256 and statuses `not-approved` / `not-assessed`; each raw document is held in a private temporary cache rather than Git. The earlier P1 review confirmed 31 prior Claim identities, 32 matching original official locators (22 distinct anchors) and six synthetic CLI304 permission tests. Nothing in those outcomes certifies full 304 behavior.

The new **K-0070 through K-0074** are entirely fresh Claim IDs to prevent silent version-range widening of old Claims. Each is `lifecycle=candidate`, `authority=guidance`, `verification.source=indexed`, `verification.runtime=not-run`, `decision_record=null`, and limited to CLI `[2.1.304, 2.1.305)`. Their single first-party `official-doc` entry has **role `context`, not `supports`**, using the new unapproved source digest. Therefore **no source has been certified as independently reviewed for a new 304 Claim**.

## Proposed review lanes

| Candidate | Next target | Outstanding evidence before approval |
| --- | --- | --- |
| **K-0070** | `tool.check` `decider: "person"` | Real human-only permission callback, unattended rejection and managed policy precedence. |
| **K-0071** | Optional `e.isReadOnly` | Real host classification and actual tool/agent variants. Mock Read default was `undefined`, explicit true injection worked. |
| **K-0072** | Previous plugin's skipped-Hook transcript diagnostic | Actual two-plugin ordered Hook skip and transcript readback. |
| **K-0073** | Failed Mod reload retaining old version's tools/commands | A real controlled failed reload and state lifetime/rollback check. |
| **K-0074** | `tool.check` `.catch` fail-closed denial | Native mock already rejects unguarded hooks and permissive denial override; real host policy behavior remains unproven. |

Each candidate has a narrow statement that cites actual first-party 2.1.304 release changes and the known mock limitation. No candidate claims that a synthetic mock can make an actual user permission decision.

The original upstream release evidence is pinned at `evidence/upstream/claude_code_v2_1_303_304_release_notes_20261020.json` and the 6/6 native test results at `docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json`. The five candidate source locators were also independently matched to current official HTML `id` attributes and Markdown heading titles; the separate redacted report `docs/reports/2026-10-20-cli304-five-candidate-anchor-evidence.json` fingerprints all five original Claim files and their source bytes. This **does not complete** a substantive first-party Markdown section review or host execution.

## Next release gates

First independently review the precise current official Markdown section revisions, with line-bounded provenance, an attested review date and source revision; then run genuine target-version native tests. For high-risk `tool.check`, do not approve before exercising actual user/host callback, managed precedence and unattended decisions. For skipped Hook and failed-reload cases, obtain real CLI transcript/state evidence. Only then transition each candidate to `reviewed` and, after independent validation, `approved` using new decision records. Regenerate and test a separate CLI304 Skill only when its required approved Claim scope and host tests are complete. Do not treat source HTTP changes or synthetic mock success as automatic approval.

The existing P4 Chat Mode 46-case gate, complete P5 host/model qualification, and Stable eligibility remain **HOLD**. The separate Agent Communication project is excluded.
