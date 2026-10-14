# P6-D: public Git historical private-conversation link exposure

**Date:** 2026-10-15 (Australia/Sydney). Public repository: `grammy-jiang/claude-code-mods-knowledge`. Audited main revision: **`383ef48a9834abe5c1ef3017dc99fd051ee72111`**. This is a **read-only historical ref audit**, not an instruction to rewrite public history or a representation that private conversation links are accessible without account authentication.

## Precisely scoped findings

An isolated temporary clone of the current **public GitHub repository** fetched every advertised branch tip and tag and traversed the reachable Git commit trees. It searched for literal `https://` ChatGPT `/c/` conversation URLs with full UUID-shaped identifiers. Test suites deliberately containing textual *regex patterns* with a `/c/` substring were excluded: these are not conversation links. Matching source was inspected privately and never published in this report.

| Scope | Checked | Git objects with identifiable real-shaped links |
| --- | ---: | ---: |
| Current `main` tree | One current tip | **0** |
| Public remote branch tips | 27 | **20** |
| Public tag tips | 1 | **1** |
| Unique commits reachable from all current refs | 72 | **47** |
| Historical ancestors reachable from `main` | 54 | **35** |
| Distinct UUID-shaped conversation URLs across affected current tips | — | **2** |

The affected files at the older ref tips are historic P4/P5 evidence and release-note Markdown. Current `main` removed those specific links before this audit, but historical commit objects and archived ref trees remain externally retrievable. Cleaning a current file **does not purge Git history**, and deleting only stale branches would not remove the 35 identified historical ancestors already reachable from `main`.

The prior `v0.2.0-beta.1` published Release asset verification found clean ZIP contents, but **release assets were not rechecked in this particular Git ref scan**. This classification recognizes UUID-form links; other shapes, forks, mirrors, cached pages, deleted remote refs and detached Git objects are not comprehensively assessed. The real links' strings, IDs, hashes tied to individuals, account credentials and private ChatGPT transcripts were **never copied into the public evidence**.

## No destructive edits without coordinated migration

Do **not** force-push, rewrite `main` history, move the published tag, or delete legacy branches while other sessions or consumers may rely on their commit SHAs. A complete historical scrub would require: (1) account-owner confirmation of affected public mirrors/forks and intended disclosure response, (2) coordinated stop/freeze for collaborators and release consumers, (3) revised Git history and tag provenance mapping plus verified artifact checksums, (4) cleanup of relevant hosted refs/caches where possible, and (5) a documented post-migration verification and rollback/consumer communication plan. Git-host retention and prior clones mean total erasure cannot be guaranteed.

Meanwhile, test coverage prevents the **current tracked public documentation** from accidentally introducing another direct UUID-shaped ChatGPT conversation link. This is an additional prevention check, not an audit of every historical source or an authorization to rewrite any ref. [Sanitized counted ref inventory](2026-10-15-public-git-ref-privacy-audit.json) preserves exact observed scope. **P6-D stays open**, and stable release qualification remains `STABLE_RELEASE_BLOCKED`.
