# CLI304 SSOT: seven fresh official observations, deliberately NOT reviewed or approved

Date: 2026-10-20 (Australia/Sydney). **Administrative source-observation milestone only.** No Claude Code CLI 2.1.304 API Claim, native Skill, ChatGPT Plugin, or Stable release was approved or installed.

## Input evidence

The independent [P1 current-document anchor review](2026-10-20-cli304-p1-firstparty-31-claim-and-permission-review.md) verified the byte digests of **7** official `code.claude.com` Mods HTML/Markdown documents, **31** original CLI302 Claim/decision pairs, and **32** exact official source locator occurrences. Those raw document bytes were held in a private local cache and were not copied into the repository.

Only the seven HTML fingerprints already attested by that report were accepted. The recorder independently checks their size, SHA256, allowlisted registered source URL, original pinned Registry SHA256 and observed file timestamp before writing anything to the source store.

## Atomic immutable SSOT changes

Existing `mods_knowledge.storage.record_observation` machinery atomically added one new immutable metadata revision for each of **M001, M002, M003, M004, M006, M008 and M010**, then updated `sources/snapshots/index.json` to identify the latest observed version. Each metadata file explicitly retains:

- `approval_status: not-approved`;
- `semantic_status: not-assessed`;
- `hash_basis: raw-http-response-bytes`;
- an exact first-party source URL, SHA256 and observed UTC time;
- no raw HTML, Markdown, model transcript, private device path or credential.

The original `sources/registry.json` source `snapshot.sha256` pins remain **unchanged**. Historical approved CLI 2.1.296 and 2.1.302 Claims, their decision ledgers and previously approved source evidence remain valid. No `sources/reviews/revisions/` approval or target-304 Claim decision was created.

**Important:** `index.current` identifies the most recent *observed* HTTP bytes. It does **not** confer review status or update any Registry-approved source pin. A new 304 Claim citing one of these new HTTP digests is still rejected by the existing independent official section-review gate until a target-scoped review attestation and explicit Claim lifecycle decisions exist.

The redacted SHA-bound seven-source result is at
`docs/reports/2026-10-20-cli304-seven-unapproved-source-observations.json`.

## Reproduce without repeated web requests

`record_cli304_unapproved_source_observations.py` reuses the private official docs captured for the previous P1 audit and cannot access the network itself. On a checked-out source tree with the original private files still present:

```sh
uv run --offline --group dev python scripts/record_cli304_unapproved_source_observations.py \
  --private-official-pages /tmp/mods-cli304-firstparty-31claim-20261020 \
  --out /tmp/mods-cli304-firstparty-31claim-20261020/another-unapproved-source-check.json
```

The source collector is idempotent when the exact currently observed SHA is already indexed. It does not silently overwrite any immutable historical metadata; the indexed metadata store is checked for orphan or tampered records. A wrong hash, missing source, out-of-scope timestamp, unreviewed Registry identity or unexpected 304 Claim promotion blocks before new observations are recorded.

## Status and next work

**0/31 previous CLI302 Claims have been approved for CLI304.** The next independent review must read and attest exact current official Markdown sections and native target types for each proposed new Claim, then run the appropriate real host/permission/reload evidence. Prioritized blockers are `tool.check` human decider, genuine read-only metadata, managed policy precedence, skipped Hook transcripts and failed Mod reload/state recovery. Passing synthetic native tests is insufficient for those semantics.

P4 automatic Chat Mode activation, complete 46-case qualification, native model-host acceptance and Stable remain HOLD. Agent Communication is a separate excluded project.
