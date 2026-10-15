# Real ChatGPT Chat Mode QA: `0.3.3-beta.2`, five-case controlled trial

**2026-10-16, Australia/Sydney. Outcome: five real Chat replies verified; model-selection/source checks improved, but semantic code acceptance still FAILED. The candidate was NOT published or promoted.**

## Version, account and actual Chat Mode provenance

- The experiment used MacBook Pro Codex 0.162.1, the installed **Agent Communication** Skill, and a task-owned isolated ChatGPT Project. All sends used the ordinary authenticated Chrome Chat Mode composer, **not ChatGPT Work Mode**, with a unique never-before-used `TASK_ID` per prompt. Effective model/effort in every actual final was **GPT-6 Thinking / Standard**. The five exact new Chat conversations each had an independently matched canonical `FINAL_VERIFIED` receipt. Ambiguous sends were not retried, and 401/403/429 or Cloudflare blocks were not bypassed.
- Source revision: `9c0b7b8213b9edda3a52130239b180ff0202c266` (`main` after PR #41). The candidate was a **private, unpublished** Plugin ZIP `0.3.3-beta.2`, knowledge revision `0.1.2`, target Claude Code CLI **2.1.296**, 30 approved version-matched Claims and five remaining candidates. Pi and Mac independent package build SHA-256: `77f1ee38e1258341895f9cb617d07c482a428bdb4fbc0d22b01ae21418c8eb96`. Temporary installed account contents matched the reviewed package's **10/10 canonical files plus server sidecar**.
- Before installation, the genuine GitHub-published `v0.2.0-beta.1` ZIP was downloaded and its published `SHA256SUMS` verified; an independently downloaded active account copy matched ten files plus sidecar. The account baseline contained exactly ten other personal Plugins. After this five-case run, the outer owner restored published **`0.2.0-beta.1`**, verified the account download's **10/10 canonical files and sidecar**, and recorded **identical state for the other ten personal Plugins**. The owner job completed successfully. No personal Plugin account changes remain from this experiment.

## Real case results (not inferred from model self-reports)

| Exact P4 case, intentionally ordered | Actual canonical scoped Mods Skill read | Independently checked source/technical results | Conservative disposition |
| --- | --- | --- | --- |
| **NEG-HVAC** — unrelated HVAC question, no Plugin requested | **0**, as required | Actual GPT-6 Thinking normal answer, no Mods read_resource, no explicit Plugin system hint | **PASS negative nonactivation** |
| **BOUND-VERSION-NEW** — unverified CLI `2.1.310` API request explicitly naming Plugin | **5** reads: Skill + source-index/types/events/testing | **6/6** cited approved Claim URLs used correct exact official `Source:` `#anchor`. Does not guarantee unsupported newer-version API, no generated runnable code | **PASS scoped version-boundary guidance**, not a future-version API guarantee |
| **POS-U-01** — Pane/AbovePrompt UI matcher | **4** reads: Skill + relevant references | **3/3** cited approved Claims including expected K-0027 have exact source locators. The previous candidate's unrelated K-0035 source-anchor omission did **not** recur | **REVIEW NEEDED** — actual UI session/Panes were not executed |
| **POS-Q-01** — offline `.test.ts` testing command | **4** scoped reads | **5/5** Claim sources exact, correct `claude plugin test .` directory pattern; no known linter risk | **REVIEW NEEDED** — model-origin test code was not run end to end |
| **POS-E-01** — transparent `tool.call` observer | **5** scoped reads | **9/9** Claim sources exact; correct named `register(on)`, `($,e,next)` and path-bearing static validation, yet **unsafe unprotected observer logging** can alter tool result/error semantics | **SEMANTIC FAIL**, despite source and basic lint pass |

**Counts:** five sends, five `FINAL_VERIFIED` final replies, **4/4 relevant** requests read the expected Skill, **0/1 unrelated** request falsely activated, all cited Claim/source URLs correctly matched under independently validated SSOT, and the unverified-version boundary safely abstained. **Two bounded passes** (negative, version safety), **two further-runtime-review cases**, **one independent semantic failure**. This sample does **not** prove 100% future text routing, universal safe code generation, or stable eligibility. Because of the E01 failure, the candidate is **REJECTED** for release promotion.

## Failure to preserve downstream success/error when logging throws

The original POS-E-01 user request specifically asked how to make a `tool.call` *transparent observer* that does not change the original tool result. The generated answer included a correct simplest handler `return next(e)` but also recommended an **extended logging example** with the following control-flow shape:

```ts
const result = await next(e);
console.log('tool.call completed', { elapsedMs: 2 });
return result;
// catch(error) includes console.error(...) before rethrowing error
```

If `console.log` throws after `next(e)` succeeded, this handler rejects rather than returning the original success. If `next(e)` rejected and the unguarded `console.error` in the handler's catch block also throws, the logging error masks the original rejection. This contradicts the approved transparent-observer invariant [K-0007 / official M004](https://code.claude.com/docs/en/plugins/mods/events#observe-an-event), even though the basic callback signature is correct and the old known-risk lint did not flag it.

This semantic problem was **independently reproduced using assistant-authored synthetic JavaScript hooks**, not by executing actual model-output code: Mac Node v24.21.0 showed both wrong result/error paths from the unsafe control flow, then a fail-isolated `try/finally`-with-nested-logger-`try/catch` synthetic hook preserved the exact downstream result and original exception object under both synchronous logging exceptions. Native Claude Code CLI **2.1.296** `claude plugin validate --strict <disposable-Mod-directory>` passed the safe named `register(on)` hook. This still does **not** establish that arbitrary model-generated Mods code works in a real Claude host, or that `$.ui.log` itself is a supported API without version-specific verification.

## Remediation and remaining release blockers

- Add approved version-bound **K-0036** to the SSOT: transparent observer diagnostic failures must be fail-isolated so that `next(e)` result and exception semantics are preserved. Its first-party M004 evidence is tied to the existing approved K-0007; JavaScript error-isolation behavior has separately reproducible native synthetic evidence, not full real-host acceptance.
- Add bounded offline known-risk detection for unprotected diagnostics after `await next(e)` or inside `catch(error)`. Clearly labeled negative examples are manual review, and protecting diagnostics in nested `try/catch` must not be misclassified as unsafe. Include network-free Node synthetic success/error identity tests, plus local target CLI2.1.296 strict synthetic validation proof. Absence of flags **never** certifies all code semantics.
- Compile the new K-0036 fact and exact M004 URL into every portable host Skill from the **Single Source of Truth**, not a duplicate literal API fact in the generator. Qualify a **new** candidate against genuinely independent Chat Mode sends before replacing installed Beta.1. P4 automatic routing, P4 full semantic QA, P5 host-specific inference and P6 stable release remain open; **STABLE_RELEASE_BLOCKED**.

Public evidence deliberately omits personal ChatGPT conversations, account/Plugin/project IDs, exact private request IDs, raw replies, cookies, credentials, and private downloaded ZIP bodies. Read-only originals/receipts remain on the authorized Mac task-owned directory.
