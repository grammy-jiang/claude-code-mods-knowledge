# Claude Code CLI304: K-0074 source-REVIEWED, NOT approved, with explicit host-integration release gate

Date: 2026-10-21 (AEDT). **This is a source-review lifecycle milestone, not a release authorization.** The existing K-0074 `tool.check` registration `.catch` / fail-closed denial guidance is now `reviewed` against an exact, SHA-addressed first-party Claude Code CLI 2.1.304 Events section. All other new version claims remain candidates and **no CLI304 Claim is approved**.

## Provenance

- Earlier K-0074 was a `candidate` with a *context-only* new official HTML observation from PR #106. Its immutable public initial candidate SHA256 remains recorded in the original evidence.
- PR #107 independently inspected the current official Events `#handle-a-hook-that-fails` Markdown section using SHA-pinned HTML and Markdown captures, a full bounded section line range, the section SHA256 and a reviewer-labelled, timestamped version-specific source revision record. This shows that the official documentation explicitly supports the **narrow recommendation** to deny a failed `tool.check` via a registration `.catch` handler, including the `next.called` distinction.
- The target-native CLI304 Bubblewrap testing had already established **6/6 synthetic permission test results**, correct denial preservation and a deliberately missing-catch warning being rejected; synthetic tests are **not real user permission dialogs**.
- K-0074's source evidence role has changed from `context` to `supports`, and `verification.source` from `indexed` to `reviewed`, with no change to the original normative statement, target scope `[2.1.304, 2.1.305)`, or the previous K-0043/K-0058/K-0068 histories.
- The official `mods-knowledge claims transition` workflow recorded **one audited `candidate → reviewed`** event with the actor label, UTC timestamp, rationale and chained Claim SHA256 in `decisions/K-0074.json`. This label is **not** cryptographic proof of a human signer's identity. Neither previous approved Claim bytes nor any previous decision ledger was altered.

The immutable redacted audit is at `docs/reports/2026-10-21-cli304-k0074-source-reviewed-only.json`, with `scripts/audit_cli304_k0074_review_transition.py` validating its SHA and lifecycle boundaries.

## Important newly fixed policy defect

The old SSOT validator's *approved guidance* branch did not universally require successful runtime evidence. Thus an already reviewed but high-risk permission-security recommendation for a NEW CLI could otherwise be approved on its source evidence alone, misleading a model into assuming actual host permission behavior had been verified.

The updated release gate now requires **`verification.runtime = integration-pass`** and validated, hash-pinned target-version runtime reports before any **CLI 2.1.304+ security/permission guidance** with primary domain `P` can be formally approved. Earlier 2.1.296/2.1.302 approvals remain valid; source-only K-0074 remains `reviewed`, not approved. This is intentionally stricter than a synthetic `claude plugin test` success or a `smoke-pass` report. A genuine host run and independent review remain required to establish the semantic truth of the evidence; a recorded test report is not itself proof of the actor's honesty.

A destructive-in-isolation negative test copies the SSOT into a private temporary directory, attempts `K-0074: reviewed → approved` with **runtime not-run**, verifies the new gate rejects the transition, then confirms both Claim and decision ledger bytes are unchanged. The real working tree is never used for the attempted approval. Existing CLI296/302 source approvals and compiler outputs are separately checked for regressions.

## Current state and remaining work

74 total Claim records: **62 approved for their respective earlier versions**, **9 candidates**, **1 reviewed but unapproved** (K-0074), and **2 deprecated**. CLI304 remains **0 approved Claims**. Its Skill is not compilable under the existing fail-closed version gate; no installed Skill, real plugin or production CLI was touched.

K-0070 (`decider: person`), K-0071 (`e.isReadOnly`), K-0072 (skipped-Hook transcript) and K-0073 (failed Mod reload) still require direct version-specific release-source evidence plus real host permissions/order/reload tests. K-0074 itself needs an actual target-host integrated permission test and separate approval decision before being used as a production safety guarantee. Other original CLI302 Claims, Chat Mode 46-case P4/P5 and Stable remain HOLD. Agent Communication is out of scope.
