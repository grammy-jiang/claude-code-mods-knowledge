# Source Registry collector implementation evidence — 2026-10-13

## Scope completed

- Added `sources/registry.json` as a byte-for-byte copy of the 91-entry UNVERIFIED seed; original research/design imports left unchanged.
- Added a Python package and CLI for JSON Schema validation, cross-document identity, provenance, history separation, and official-document eligibility.
- Added bounded, redirect-refusing HTTPS retrieval restricted to L0/L1/L2 official Docs. No R/C/H fetch, arbitrary URL fetch, background scheduler, raw page persistence or API approval.
- Added atomic content-hash-keyed observation metadata, historical revisions, a current-hash index, local metadata integrity checks, and a UNIX file lock for concurrent writers.
- Captured the 43 current official-document pages as `sources/snapshots/metadata/Mxxx/<sha>.json` with a corresponding tracked `sources/snapshots/index.json`.
- Added TDD coverage for the migration, malformed sources, unsafe URLs, redirects, response size/content type, metadata corruption, idempotence, changed content, racing writers and CLI entrypoints.

## Verification commands (MacBook Pro)

```sh
uv sync --locked
uv run --python 3.11 --locked pytest -q
uv run --python 3.14 --locked pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mods-knowledge validate
uv run mods-knowledge verify
shasum -a 256 -c docs/SOURCE_IMPORT_SHA256.txt
cmp sources/registry.json docs/design/mods_ssot_design_v0_1/registry_seed_UNVERIFIED.json
```

Observed before final commit: **62 tests passed on Python 3.11.17 and 62 passed on Python 3.14.8**, formatting/lint checks passed, and 43/43 first-party fingerprints were acquired and verified. The repeated M001 live retrieval was `unchanged`; no second revision was produced.

## Known limitations

- Changes are raw HTTP byte changes, not semantic changes. No HTML or Markdown payloads are stored, so the original content digest cannot be recomputed offline from payload bytes.
- The source-level migrated snapshots remain unpinned and unapproved. No Claim or target-version API contract is approved, and GitHub/Playground examples (R) are not source-pinned by this collector.
- Only first-party Docs webpages are eligible. GitHub source pinning, claim curation, semantic diff, Knowledge Compiler, platform Skills and ChatGPT Plugin remain future tasks.
- This stage was tested with macOS Python, not directly exercised on Pi or a noninteractive ChatGPT plugin host. `fcntl` file locking limits this implementation to POSIX targets.
- No GitHub Actions workflow was enabled, avoiding unsolicited private-repository CI billing.
