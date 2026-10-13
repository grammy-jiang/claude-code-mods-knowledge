# First official documentation fingerprint baseline — 2026-10-13

## Source and environment

- Host: MacBook Pro (macOS), isolated `feat/source-registry-20261013` worktree.
- Original research input: 91 sources M001–M091, retained unchanged as `UNVERIFIED_MIGRATION_SEED`.
- First-party collection scope: exactly 43 official documents (L0=10, L1=19, L2=14) from `code.claude.com`.
- Excluded: all R (17), C (28) and H (3) sources. Those URLs were neither fetched nor treated as normative.
- Archive content: metadata-only fingerprints, no copyrighted raw page copies or retrieved HTML.

## Actual observation

The first live run collected 41/43: 40 new plus one previously fingerprinted M001 reported unchanged. M033 (Changelog) and M075 (Hooks Reference) exceeded the default 2 MB cap and were initially refused. The 4 MB cap subsequently permitted M075. The Changelog HTTP payload was independently measured at 4,804,434 bytes, and M033 was collected successfully only after explicitly increasing the per-source cap to 6,000,000 bytes.

**Final captured coverage: 43/43 official documents, 43 source IDs, 43 immutable content SHA records.** Local `mods-knowledge verify` reported an internally coherent index and metadata hashes. The independently repeated M001 fetch was byte-identical and did not create a second revision.

## Interpretation and limits

This is not a review or approval of 43 Mods API contracts. The page bytes are not archived; content digests demonstrate which exact bytes were seen but do not establish target-version semantics or future webpage accessibility. In particular, `docs/en/changelog` is large; raw-byte changes there might be entirely unrelated to Mods. The initial 91 source records still have unpinned registry-level snapshots, and zero Knowledge Claims are approved.

Semantic change detection, source-to-Claim evidence review, version compatibility testing, and all host Skills/Plugin installation remain subsequent phases.
