# Claude Code 2.1.309 — first-party SSOT source roll-forward

**Observed:** 2026-10-23, Australia/Sydney.
**Status:** source-only research; no current-version Claims approved; Stable HOLD.

## Official release version

The official Anthropic npm package latest dist-tag was **2.1.309** on
2026-10-23 and first-party GitHub agreed:
https://github.com/anthropics/claude-code/releases/tag/v2.1.309

The separate npm stable dist-tag was 2.1.308. The project explicitly
uses npm latest, never the distinct stable or next dist-tag, as its
next intended exact version target. This observation alone does NOT
authorize installing or publishing a current Skill or Plugin.

Five original GitHub releases, v2.1.305 through v2.1.309, were
individually fetched from exact first-party tags and SHA256-bound.
The private original release-note bodies were not committed. Public
SHA256s cover all five original bodies and nine selected release
bullets directly relevant to this project:
[evidence/upstream/claude_code_v2_1_305_309_release_notes_20261023.json](../../evidence/upstream/claude_code_v2_1_305_309_release_notes_20261023.json)

## Scoped observations for subsequent native/agent acceptance

| Exact upstream release | Version-specific observation | Required proof before promotion |
| --- | --- | --- |
| 2.1.305 | Gateway ToolSearch fallback after API rejection | Original provider/host model test |
| 2.1.305 | Mod Image fullscreen rendering and dock width changed | Actual native UI/terminal checks |
| 2.1.307 | HTTP MCP retry safety distinguishes read-only or idempotent calls | Genuine MCP transport/tool outcome |
| 2.1.307 | SDK MCP tools could be stale following background work | Actual SDK and Agent discovery check |
| 2.1.309 | Additional-directory same-name Skills should remain reachable using qualified names | Competing directory Skill discovery/invocation |
| 2.1.309 | Nested package Skills used by verify/code-review have a discovery fix | Native nested project + shell change test |
| 2.1.309 | Mod turn.step model aliases have a resolution fix | Original 309 native callback test |
| 2.1.309 | Cloud-synced Skills/Plugins have a disk-read recovery fix | Isolated sync/recovery test without user profile changes |

These are selective release-note observations, NOT an exhaustive API
changelog, approved user guidance or a passed host-model test. The
v2.1.306 and v2.1.308 releases were also SHA-pinned, though none of
their bullets matched the narrow selectors. Zero selected topics does
not mean those releases contained no change.

The original full upstream texts and private authentication remain
off Git. Deterministic verification and exact release-bullet source
hashes are provided in scripts/audit_cli309_release_window.py.

## Three updated official Source Registry snapshots

Using the existing allowlisted Source Registry collection flow, three
registered first-party sources were fetched on 2026-10-23:

- M003 — Mods reference (L0).
- M004 — Mods events (L0).
- M033 — Claude Code changelog (L2).

All three official raw HTML response SHA256s differed from their prior
recorded observations. The append-only snapshot index and metadata
were updated and the local integrity checker passed. Every new
metadata record explicitly says **approval_status: not-approved** and
**semantic_status: not-assessed**. No upstream text was copied.

Historic original Registry pins for M003/M004 are unchanged. M033
was historically **indexed and unpinned**, so this report does not
invent a former reviewed SHA for the changelog. Raw HTML byte drift
does not itself prove a Mods API semantic change.

## Downstream and release boundary

- Existing 31 approved 2.1.302-scoped Claims remain unchanged.
- **Zero approved 2.1.309 Claims.** Previous Claims are not widened.
- Compiling a current-version 2.1.309 Skill is still fail-closed.
- No current-version agent Skill or ChatGPT Chat Mode Plugin was
  compiled, installed, published or marked tested by this research.
- Native 2.1.309 Mods/Skill host behavior and actual agent use are
  not yet verified; neither is the complete Chat Mode acceptance suite.
- No production Claude CLI, local Agent installation or existing
  ChatGPT Plugin account has been modified.
- Upstream failed-reload behavior remains an in-scope compatibility
  observation (Issue #110); an unrelated distributed security
  supervisor is archived outside main and not a Stable release gate.

**Next in-scope P2/P3 unit:** review authoritative current Skills and
Mods sections for these four 309-relevant items; then run genuine
native Skill name-conflict/nested discovery and harmless Mod alias
tests, retaining exact versions and private-original evidence.
Only independently approved target Claims may feed generation.

Recheck npm latest before any further approval, native QA or release.
See [latest-only roll-forward procedure](../operations/latest-version-rollforward.md).
