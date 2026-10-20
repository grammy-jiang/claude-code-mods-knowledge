# Claude Code 2.1.304 P1 — 31-Claim fresh first-party review and high-risk permission mock

**Review date:** 2026-10-20, Sydney. **Status: UNDER REVIEW; no 2.1.304 Claim or release is approved.**

The existing reviewed Claude Code CLI 2.1.302 Claims **K-0039 through K-0069** remain immutable and version-bounded to `[2.1.302, 2.1.303)`. In particular, the previously approved K-0068 includes an illustrative `console.log` call that failed real CLI302 native core typing. Its historical decision and text were **not** modified or promoted to CLI304.

## 1. Fresh independent first-party document pass

Seven first-party documentation pages were freshly fetched in both **HTML and Markdown** form from `https://code.claude.com/docs/en/plugins/mods/`: `admin`, `create`, `events`, `interface`, `overview`, `reference` and `test`. The raw pages remain **private** on Raspberry Pi; their exact independent SHA256 and byte counts appear in the redacted JSON report.

- Prior Claim/decision identity checked: **31/31** SHA-pinned originals unchanged.
- Official source references: **32/32** original locator occurrences resolve to exactly one current HTML `h2`/`h3`/`h4` heading ID, each with a matching title in the independently retrieved Markdown.
- Unique official headings: **22**; pages covered: **7**.
- All seven current HTML byte digests differ from the previous registry snapshots. Different HTML bytes **do not prove a changed API**: unrelated site markup or formatting can also change. New, independently reviewed first-party version-specific source revisions and approval decisions are still required before CLI304 publication.
- Every row in the refreshed matrix remains `ANCHORS_VERIFIED_ONLY`, with `api_semantics_verified_for_304=false` and `new_304_claim_approved=false`.

Reproducible, redacted report: `docs/reports/2026-10-20-cli304-p1-all31-fresh-primary-anchor-matrix.json`.

Offline audit implementation: `scripts/audit_cli304_fresh_firstparty_claim_matrix.py`. It cross-checks existing 31 original Claim SHA256, approval decision SHA256, precise official locator, current HTML headings, Markdown headings, official 304 release evidence, target-native core-type diff and the additional native permission test. It does **not** fetch pages while running.

To reproduce on an authorized development workstation, first save the seven `.html` and `.md` official pages into a private working folder, then run:

```sh
uv run --offline --group dev python scripts/audit_cli304_fresh_firstparty_claim_matrix.py \
  --private-official-pages /tmp/mods-cli304-firstparty-31claim-20261020 \
  --out /tmp/mods-cli304-firstparty-31claim-20261020/new-reviewed-matrix.json
```

A changed/missing heading, wrong source hash for an existing approved Claim, 304 approval appearing without a new decision, wrong native evidence or source mismatch is a **blocking** audit outcome.

## 2. Target-native 304 permission and failure mock (separate evidence)

The SHA-pinned first-party 2.1.304 ARM64 binary ran solely inside **Linux Bubblewrap** with an unshared network namespace, disposable Home, reviewed fixture, no model, and **synthetic** Read/Write permission test objects. No actual user tool, permission dialog, credential or account data was mounted.

- First-party target strict Mod validation: **pass, with registration `.catch` and no uncaught-gating warning**.
- Native permission test kit: **6/6 pass**, including Write `ask` delegated to `decider: 'person'`, preserving `deny` and `allow`, injected exception denied via `.catch`, event/input freezing, and intentionally injected read-only metadata.
- A synthetic `Read` check **without explicitly supplied metadata** yielded `e.isReadOnly === undefined`. An expressly injected `isReadOnly: true` was readable. This proves a limited API/test fixture branch, **not that the real host automatically tags every Read**.
- Deliberately omitting the registration catch: native validator returned exit zero **with a gating warning**; independent fail-closed acceptance correctly rejected it.
- Deliberately replacing a `deny` verdict with `allow`: native mock tests detected the attempted permission relaxation and failed.

SHA-bound report: `docs/reports/2026-10-20-cli304-p1-toolcheck-six-native-safety.json`. Reviewed fixture: `evals/fixtures/cli304-toolcheck-p1-boundaries/`. Reproducer: `scripts/audit_cli304_toolcheck_p1_sandbox.py`.

The previously pinned first-party 304 core TypeScript declarations demonstrate optional `e.isReadOnly` and `decider: 'person'` typing differences relative to 302; **merged runtime-generated built-in tool types remain unverified**. None of these synthetic outcomes substitute for a genuine interactive permission dialog or organization-managed policy precedence test.

## 3. Prioritized high-risk semantic review queue

| Original Claim | Proven now | Remaining mandatory evidence |
| --- | --- | --- |
| K-0041 — immutable event rewrite | Native 304 synthetic `tool.check` event and input are frozen | Verify actual event rewrite and `isReadOnly` behavior in a host path. |
| K-0042 — Hook ordering | Exact current official source heading exists | Two-plugin ordering, skip propagation and transcript line from a real 304 host. |
| K-0043 — tool-call outcomes | Native synthetic `allow`, `ask`, `deny` pass | Real permission decision/side-effect behavior, including human-only approval. |
| K-0045 — session/reset lifecycle | Current official state section located | Real failure/reload recovery across sessions; release explicitly fixed the old reload state bug. |
| K-0048 — generated API types | Official 304 core `.d.ts` SHA pinned; changed permission types | Obtain complete host-generated built-in tool/MCP declarations from authorized native load. |
| K-0049 — static Hook inspection | Native 304 validator and independent warning gate exercised | Verify other loaded Hook error/warning cases; exit zero alone is inadequate. |
| K-0058 — permissions precedence | Native synthetic person/deny/catch behavior checked | Genuine host callback, no-person case, managed `deny`/`ask` priority and agent distinctions. |
| K-0063 — transcript diagnostics | First-party 304 release note explicitly covers skipped Hooks | Genuine two-plugin skip event and full transcript readback in the real CLI. |
| K-0068 — observer diagnostic conflict | Original 302 `console` type failure independently confirmed | New 304 source-scoped Claim with a type-correct, fail-isolated diagnostic recipe. |

The remaining 22 previous Claims each have a source/section and target review question in the complete JSON queue. Their current documentation anchors are verified, **not their normative or runtime semantics**.

## 4. Release boundary and next sequence

1. Add a version-specific official source-review revision **without overwriting** old 302 pins, then create separately identified CLI304 candidate Claims with complete provenance.
2. Run genuine user/host permission behavior and cross-plugin ordering tests in an explicitly approved safe environment. Do not fabricate an interactive permission result from test stubs.
3. Validate lifetime/reload errors, all registered features and generated runtime types; complete scoped natural-model/Skill acceptance before proposing a 304 Skill.
4. Only after target-specific Claim approvals and independent gates, compile a *separate* CLI304 candidate and verify install/readback with safe rollback. P4 Chat Mode 46-case acceptance and Stable remain HOLD.

**No installed 302/303 CLI, deployed local Skill or ChatGPT account Plugin was changed during this review.** Agent Communication is an excluded, separate project.
