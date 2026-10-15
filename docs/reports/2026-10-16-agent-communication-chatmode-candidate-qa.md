# Real ordinary Chat Mode QA: source-matched 0.3.3-beta.1 candidate

**2026-10-16, Australia/Sydney. Verdict: `STOPPED_ON_QA_FAILURE`; full source/semantic qualification NOT achieved.** The MacBook Pro used its real Codex 0.162.1 CLI and the installed Agent Communication Skill to submit normal browser-mediated ChatGPT **Chat Mode** messages. No Work Mode was involved. Model/effective thinking in all finished turns was **GPT-6 Thinking / Standard**.

## Reproducible package and private-account rollback

- From approved SSOT `main` commit `966cec4176edf9b2a5035c541fa134ac53855c2a`, the MacBook Pro and Raspberry Pi independently built the same **unpublished** `0.3.3-beta.1` Plugin ZIP (knowledge revision `0.1.1`, Claude Code CLI **2.1.296**, **30 approved Claims**, five still candidate). ZIP SHA-256: `5ad6b115f11eea55844387df30fae1629a0db7a46f62ffa55471038b657f2725`; all ten canonical Plugin files and the server sidecar passed account download read-back matching after temporary installation.
- Before installation, Mac's standard authenticated Chat Mode checks and the Agent Communication send preflight were `GO`/`READY`. The account had the published `0.2.0-beta.1` installed and enabled, and exactly ten other personal Plugins. The originally published GitHub Beta.1 ZIP matched a private account-downloaded backup (ten canonical files and sidecar), with checksum verified against the published release's `SHA256SUMS`.
- The task was single-owner, contained within a dedicated new test Project and five frozen case prompts, and each sent turn was reconciled against its **exact** TASK_ID, Project, user prompt, requested model/effort, Chat ID and canonical assistant final. No uncertain send was retried.
- After the candidate test stopped, the outer owner restored the **published `0.2.0-beta.1`**, downloaded and checked the restored 10/10 canonical files plus server sidecar, and compared the unrelated ten personal Plugin states before and after: **identical**. Account source/rollback verification passed; this proves the state of this controlled experiment, not closure of all historical P6 account provenance requirements.

## Three actual source-read Chat conversations

| Original P4 case | Normal Chat final | Canonical scoped Skill resource reads | Claim/source result | Independent semantic status |
| --- | --- | --- | --- | --- |
| **POS-E-01** — transparent `tool.call` observer | `FINAL_VERIFIED` | **5**: Skill + events/types/testing/security references | 11 cited approved Claims, expected sources included; K-0035 used with the correct path-bearing validation command | **Review needed.** Known-risk lint clean and safe synthetic static Mod strict validation passed, but original generated code was not executed; no full semantic acceptance |
| **POS-Q-01** — offline `.test.ts` testing | `FINAL_VERIFIED` | **4**: Skill + testing/types/events references | 8 cited approved Claims, expected source URLs including the versioned test-directory/path rules | **Bounded accept.** `claude plugin test .` and related command semantics matched the target CLI; not full end-to-end generated-code validation |
| **POS-U-01** — Pane/AbovePrompt UI matching | `FINAL_VERIFIED` | **6**: Skill + interface/types/events/source-index/official-examples references | K-0015, K-0027 and K-0028 had their approved exact source locators; **K-0035 did not** | **Failed source coverage.** K-0035 was cited, but the supplied M002 link pointed to the **other** `#get-the-types-for-your-build` section instead of the required `#check-what-claude-code-reads-from-your-mod` anchor |
| **BOUND-VERSION-NEW** — unsupported target API | **Not sent** | — | — | Not tested due to preceding fail-stop |
| **NEG-HVAC** — unrelated negative | **Not sent** | — | — | Not tested due to preceding fail-stop |

Total: **3/5 attempted, 3/3 canonical finals, 3/3 real Skill loads, 1 bounded semantic acceptance, 1 further-review requirement, 1 independent source-citation failure.** There were no observed auth/Cloudflare/HTTP429 blockers in the three successful Chat turns. The two unattempted prompts are **not** passed or failed results. The five-case suite as a whole **failed its eligibility gate**.

The missing K-0035 citation is specifically grounded in the approved SSOT Claim `claims/K-0035.json`, tied to pinned official Mods source [M002, validation section](https://code.claude.com/docs/en/plugins/mods/create#check-what-claude-code-reads-from-your-mod). Another URL on the same first-party page is not interchangeable when the user explicitly asks for **per-Claim direct official source locators**.

## Corrective action, evidence limits and disposition

The existing structural Chat-mode source check detects the presence of *any* first-party Mods URL, but that is insufficient when the answer cites several different Claims. An offline, version- and host-scoped **per-Claim direct official locator audit** is now available in `mods_knowledge.claim_source_link_coverage`; it accepts only each cited approved K-Claim's own exact pinned first-party `Source:` URL, **including the fragment anchor**, and flags unknown/out-of-scope Claims or missing expected IDs. The source contract in the generated portable Skill now asks for this exact per-Claim check **after actual Skill loading**. This cannot force model activation, judge all semantic correctness, or certify an unseen real Chat turn.

**Do not promote** `0.3.3-beta.1` or release a stable Plugin on this evidence. Keep P4-B automatic routing, P4-C semantic QA, P4-D unrun boundaries, P5 host QA, P6 stable-readiness and historical public Git privacy coordination open. Continue with a separately reviewed, properly source-matched version candidate after healthy preflight; preserve test-owned private Chat receipts and replies only on the host. Public records exclude all private conversation URLs/UUIDs, account identifiers, actual Plugin instance IDs, raw model answers, credentials and browser state.
