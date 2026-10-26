# Latest-only Claude Code SSOT roll-forward

This is the mandatory procedure for new Skills and ChatGPT Chat Mode
Plugin releases. Latest means the first-party npm latest dist-tag, not
the separately tagged stable or next channel. The actual release
version is a three-part version, never the word latest in a versioned
Claim, Plugin manifest, or build API target.

## Stages and immutable history

1. Run the version preflight with the proposed exact version:
   uv run python scripts/check_latest_claude_code.py
   --target-version 2.1.302 --require-installed.
   These lines form one CLI invocation. Stop if the online official
   latest tag differs. Re-run this after long test campaigns.
2. Use native official installer on every intended host:
   claude install latest. Verify the real binary, its version, and
   any existing long-running sessions before restarting them. Avoid
   silently disrupting work on an earlier loaded process.
3. Append a NEW host profile ID for each version/host observation;
   never rewrite a prior profile identity. Probe separately on Mac,
   Raspberry Pi and sextant. The current version audit for 2026-10-17
   is in docs/reports/2026-10-17-claude-code-2.1.302-refresh.md.
4. Collect and fingerprint every eligible first-party source,
   including large changelog/index pages with a separately justified
   download bound. Review current official Markdown sections and
   target-host Mod types/validation. An HTML or Markdown byte change
   does not itself imply an API semantic change, and an unchanged
   paragraph does NOT prove new runtime compatibility.
5. Create version-specific, independently reviewed Claim support,
   preserving historic source reviews, decisions and applicability.
   No silent widening of past approval intervals and no fallback to
   old Claims on an unsupported target. An unreviewed change must
   fail closed at the compilation boundary.
6. When latest Claims are approved, rerun the ONLINE release gate:
   uv run python scripts/check_latest_claude_code.py
   --target-version 2.1.302 --require-installed --require-approved.
   This is a mandatory precondition, not the final release gate.
7. Compile the four downstream outputs from the same SSOT Git
   revision using the explicit latest API version, then compare
   deterministic ZIPs, manifests, hashes and version fields. Test
   actual Skill loading in Claude Code, Codex and Pi Agent separately.
8. Test exact official target-native Mods runtime behavior, including
   safe mock values, errors, denial, exception identity and exactly
   once downstream continuations; do not conflate syntax-only checks
   with verified model-origin executable Mod code.
9. Deploy the approved ChatGPT Plugin to the personal ChatGPT **Chat
   Mode** environment, and test actual plugin loading, retrieval,
   non-activation controls, source and version correctness. Do not
   infer Chat mode acceptance from Codex, Claude Code, Pi or Work mode.
10. Compare controlled current-version A/B/C trials with frozen
    historical results, keeping model, cases and environment
    attribution explicit. A test from an obsolete target version
    remains a historical baseline rather than a current PASS.
11. Recheck official latest before promotion. If it advanced during
    this pipeline, block promotion and rerun the review cycle.

All original model text, private host paths, credentials and account
artifacts remain private. A source-fingerprint update does not approve
new Claims or authorize Plugin publication.

## 2026-10-17 blocked example

All three hosts have first-party native Claude Code CLI 2.1.302 and
passed a known-safe synthetic Mod test. The central SSOT still has
zero formally approved 2.1.302 Claims, so stage 6 BLOCKS. The old
2.1.296 Claims and evaluation artifacts must not be relabeled 2.1.302.


## 2026-10-23 source-only 2.1.309 staging example

The official npm latest dist-tag and GitHub release were 2.1.309 at
this research observation. The five intervening official release-note
bodies and three current Mods/changelog HTML observations were recorded
as SHA-bound, unapproved source facts. In-scope target changes include
additional-directory same-name Skill resolution, nested Skill discovery,
and Mod turn.step alias handling.

See [CLI309 source-only research](../reports/2026-10-23-cli309-firstparty-ssot-rollforward.md).
This is stage 4 source research, NOT stage 5 Claim approval and NOT
stage 6 Skill compilation. Exact latest-version Claim approval, native
agent/Mods acceptance and Chat Mode testing remain mandatory, with the
official npm latest rechecked whenever this target moves.


## 2026-10-27 latest 2.1.310 source-only capture

The official npm latest dist-tag and Anthropic GitHub release are 2.1.310
at this observation; the separate npm stable tag was 2.1.308.
Five selected upstream release-note changes and three registered Mods/changelog
HTTP source revisions were immutably hash-recorded as **unapproved** facts.
Neither earlier 2.1.302 approvals nor true CLI309 host QA become 310
runtime/API approval. See the
[2026-10-27 first-party capture](../reports/2026-10-27-cli310-firstparty-source-review.md).

This is VER-01 source observation under the P4–P6 execution plan,
not VER-02 Claim approval or a new Skill/ChatGPT Plugin release.
Online latest must be rechecked before any future promotion.
