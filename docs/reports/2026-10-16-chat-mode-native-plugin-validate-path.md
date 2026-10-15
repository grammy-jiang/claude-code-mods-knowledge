# Chat Mode generated CLI validation command — native-scope correctness fix

**2026-10-16 | Claude Code CLI 2.1.296 only | ChatGPT ordinary Chat Mode evidence.**

## Actual observed failure

A real ChatGPT Chat Mode conversation was submitted once through the MacBook Pro Codex agent's installed **Agent Communication** Skill. The message explicitly requested the installed `claude-code-mods-knowledge` Plugin, its Skill, and the `events.md`, `types.md`, and `testing.md` resources, and asked how to build a transparent `tool.call` observer. The unique original conversation was independently recovered through read-only receipt-based verification after an initial `HTTP 429` on the canonical read path; **no new Chat message was sent for recovery**.

The canonical conversation trace had **four** tool-resource reads: its actual scoped `skill.md`, and the requested `references/events.md`, `references/types.md`, and `references/testing.md`. They shared the correct Plugin identity and finished status; this establishes resource *read metadata*, **not** a byte-for-byte copy of the returned resource bodies. Full user-visible answer review found 12 approved scoped K-Claim IDs and 10 distinct first-party official Mods anchor URLs.

**Failure:** The generated runnable-command section included `claude plugin validate` **without any path**. The installed actual target **Claude Code CLI 2.1.296** returned **exit code 1** and `error: missing required argument 'path'`. A separately created safe synthetic Mod validated correctly when given an explicit directory (`claude plugin validate --strict /path/to/disposable-mod`: exit code 0); it does not prove the response's original entire program is runnable. The similarly named `claude plugin test` command is different: its plugin-directory argument defaults to the current working directory when absent. A single `.test.ts` file path is **not** a valid Mod-directory argument for that test command.

This is a **semantic correctness failure** even though real Plugin resource reads, target version, K-ID citations, and official URLs were verified. The verdict remains **PARTIAL**, not 100% code correctness. No private conversation URL, Plugin/account ID, prompt, raw reply, credential, or project-specific identity is published here. Raw task receipt and test-specific results stay within Mac's task-owned private directory.

## Evidence anchors and bounded repair

- **Approved Claim K-0016 / first-party M002:** [Check what Claude Code reads from your mod](https://code.claude.com/docs/en/plugins/mods/create#check-what-claude-code-reads-from-your-mod) — static discovery/validation on the target CLI.
- **Approved Claim K-0034 / first-party M002:** [Create a mod](https://code.claude.com/docs/en/plugins/mods/create) — strict validation of example manifests and version-specific warnings.
- Target's `claude plugin validate --help` explicitly shows a required `<path>` argument. `claude plugin test --help` shows optional `[dir]`. Both commands and one correct synthetic validation were executed on the real target Mac CLI 2.1.296; no network login, third-party Mod or real user data was used in those synthetic checks.

Correct validation from a Mod root:

```bash
claude plugin validate --strict .
claude plugin test .
```

`src/mods_knowledge.answer_lint` now identifies *recommended pathless executable shell command examples* including a bare validate invocation with `--strict` and/or `--json`, while leaving valid directory arguments, `--help`, prose mentions and clearly negative examples unfailed (the latter still require manual review). The deterministic compiler's generated portable Skill now includes this CLI `2.1.296` guardrail after direct-use source-check guidance. Both fixes are tested offline; **they cannot force ChatGPT to read the Skill, cannot prevent every model error, and are not a live model acceptance pass**.

The currently installed personal account Plugin is still the published **`0.2.0-beta.1`** package (only 26 approved Claims); repo-side fixes do **not** silently update installed account contents. A new version may be qualified only after a separate user-account installation/rollback-control test and actual Chat Mode QA, with native checks for executable examples.
