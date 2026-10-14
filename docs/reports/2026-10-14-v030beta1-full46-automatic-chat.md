# ChatGPT ordinary Chat mode: experimental v0.3.0-beta.1, full 46-case automatic-selection QA

Date: **2026-10-14 (Australia/Sydney)**. Source: `158acdc7c785df6aa9fbecb11187e29ac400392b`, approved knowledge targeted to **Claude Code CLI 2.1.296**. Plugin **`0.3.0-beta.1` was experimental and account-installed for this test, not a GitHub release**. The last published release remains `v0.2.0-beta.1`.

## Complete observed result — FAILED acceptance

| Original P4 cases | Real final replies collected | Actual canonical Plugin Skill resource reads | Strict structural passes | Qualification |
| --- | ---: | ---: | ---: | --- |
| Positive in-scope Mods development | 30/30 | **3/30** | **0/30** | **FAIL** — 27 routing misses; all 30 fail structural gates |
| Unrelated negative controls | 8/8 | **0/8** | **8/8** | Correct nonactivation (not a model-semantic proof) |
| Version, source and safety boundary | 8/8 | **0/8** | **0/8** | **FAIL** — no Plugin Skill resource read in any in-scope boundary case |
| **Total** | **46/46** | **3/46** | **8/46** | **`STABLE_RELEASE_BLOCKED`** |

All **46** prompts were submitted as *separate, new* standard Chat-mode conversations with automatic invocation (no `@Plugin` selection); all **46** real final replies were collected. Their **46 unique, content-addressed conversation fingerprints**, category-specific activation checks, redacted resource URIs, source version, reply SHA-256 and structure flags appear in the companion [sanitized 46-case JSON](2026-10-14-v030beta1-full46-automatic-chat.json). None of the raw conversation IDs, prompts, replies, browser credentials or session state is in this public report.

- The three positive cases with real Plugin resource reads still failed strict structure checks (missing directly usable first-party Mods URL and/or required reviewed Claim IDs). The structural verdict is not an exhaustive, independent semantic code audit.
- Known-risk answer scanning flagged **four** positive cases: three references to historical Early Access `claude-code.d.ts` and one unsupported `export default function register({ on })` declaration. A separate disposable Claude Code CLI 2.1.296 strict-validation check rejects that declaration and accepts the reviewed named `export function register(on)`. These are risk signals and corroborating native checks, not evidence that all other generated code is correct.
- A normal ChatGPT answer to an unverified version or a malicious-source prompt does **not** count as a Plugin pass without an actual canonical Skill `read_resource` trace. All eight boundary cases lacked it.
- The report uses `PARTIAL_LIVE_CHAT_MODE_EVALUATION` because **independent semantic review and full acceptance remain incomplete**, *not* because any of the 46 replies are missing. The separate real 6-case focused pilot is not pooled into this 46-case automatic suite.

## Uploaded/downloaded Plugin integrity and follow-up

The private account was checked as installed/enabled with the canonical Skill enabled before and during the experiment. The exact candidate source upload ZIP SHA-256 was `f368435d5ea6a7523c2d4c1103e557be4c2974726fea067437b9bd35e67a727f`; the server-normalized account ZIP SHA-256 was `dc2d59f7c1023d65ad7db0b4ddcd2e1444a2de6e97153e2ed15d587226d26b4a`. Every one of the **ten approved Plugin/Skill files** and the known server-side sidecar was checked by the fail-closed archive-content comparator; the canonical content SHA-256 was `7f458934643a984a97137d53aef7608383a078c24d7e87496a66700690abd2de`.

**After all 46 replies were collected**, a fresh read-only account check found `0.2.0-beta.1` installed and enabled with the Mods Skill enabled. Its server-downloaded normalized ZIP was independently checked against the genuine published `v0.2.0-beta.1` GitHub Release ZIP: source SHA-256 `6803c69841db79e3c913f9febc79e848856936cafbdcd621bd6ce9589b1c2ba3`, downloaded SHA-256 `56b53fce64a2471a3653288ded3b616d5b07c8b964838b8485b1dc8da2d6417c`, **10/10 approved files matching**, sidecar verified. This is a point-in-time account read-back and content equivalence result, not proof of live model-host acceptance or an authenticated historical rollback audit.

## Release decision and limits

**Reject the experimental `0.3.0-beta.1` for publication or stable promotion.** It is substantially worse in this full candidate run than the previous Beta.1 run's 27/30 observed positive Skill reads. These runs were not a randomized contemporaneous A/B trial; no causal explanation for routing variance is established. Do not publish a stable tag, weaken the gate, silently substitute generic model answers for Plugin reads, or make another unsolicited account change.

Keep [P4 auto-routing #1](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/1), [P4 semantic correctness #2](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/2), [P5 real Claude/Codex/Pi inference #3](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/3) and [P6 stable release #4](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/4) open. The persistent [P4–P6 closeout checklist](../operations/p4-p6-closeout-checklist.md) records the remaining acceptance tasks. Public GitHub evidence is sanitized; primary private Chat traces stay in the QA runner's dedicated Raspberry Pi `/tmp` location and must not be uploaded.
