# K-0035 — central, approved CLI validation-directory rule

**Date:** 2026-10-16. **Scope:** Claude Code CLI **2.1.296 only**; not Desktop, later versions, model routing or live ChatGPT account acceptance.

## Why this Claim was required

In one Mac Codex -> Agent Communication -> ordinary ChatGPT Chat Mode test, the installed `claude-code-mods-knowledge` Plugin actually loaded its expected Skill and three relevant reference files (read_resource tool metadata). The model produced supported K-Claim IDs and first-party URLs, but recommended a **pathless `claude plugin validate`** command. Running it on the real target CLI 2.1.296 returned **exit 1, `missing required argument 'path'`**; validating a safe synthetic Mod with an explicit directory passed.

PR #39 first added a known-risk linter and a target-scoped source-backed Skill guardrail. However, the compiler itself contained a second literal copy of the CLI requirement, contrary to our **Single Source of Truth** rule. The fix is an atomic Claim, not another source-of-truth string in the compiler.

## Approval and evidence

New **K-0035** (`mods.types.plugin-validate-directory-required`): approved guidance, bounded to `[2.1.296, 2.1.297)` and the **CLI** host; primary area Types, secondary area Testing. Its text specifies the required directory path, valid `claude plugin validate --strict .`, the native missing-path error and how `claude plugin test` differs. It explicitly withholds all-version or real interactive runtime guarantees.

It cites reviewed first-party **M002**: [Check what Claude Code reads from your mod](https://code.claude.com/docs/en/plugins/mods/create#check-what-claude-code-reads-from-your-mod), whose pinned source digest is carried in the Claim. The exact missing-path and success exit statuses are independently grounded in local CLI 2.1.296 execution; the official document link alone does not claim to have certified all runtime behavior. For the real Chat Mode and CLI evidence boundary, see [the original native command report](2026-10-16-chat-mode-native-plugin-validate-path.md).

Two explicit source-review lifecycle events, `candidate -> reviewed -> approved`, were recorded by the repository's native `mods-knowledge claims transition` command. Its SHA-linked decision ledger is `decisions/K-0035.json`; this is an attributed AI review backed by first-party source + locally reproducible CLI results, **not** an independently certified human review or another model acceptance test. The Claim passes schema, pinned source and decision-ledger validation.

## Distribution contract

The portable compiler now selects K-0035 by **approved Claim subject**, along with existing K-0032/0033/0034 guardrails. It renders K-0035's own `statement`, first-party `M002` URL and ID into the `SKILL.md` generated for all four hosts from the same input. K-0035 also appears under `references/types.md`. No path-required API rule is maintained as a second literal assertion inside `_skill_main`.

There are now **30** approved target-matched Claims and **5** unchanged unapproved candidates in the SSOT. The earlier installed account release `0.2.0-beta.1` remains unchanged with its historical 26-Claim contents. Source synchronization, packaging and offline tests are **not** evidence that ChatGPT read the newly generated Skill; an actual account install/readback and new genuine Chat Mode conversation with independent semantic code review would still be required to qualify a future release.

**Stable release remains blocked** on real model behavior, semantic answer correctness and remaining host/privacy gates. No source tag was changed, no user account Plugin was installed/updated, and no private ChatGPT identifiers or content are disclosed.
