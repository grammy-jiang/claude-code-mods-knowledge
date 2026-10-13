# Claude Code Mods Knowledge

Versioned, evidence-backed knowledge infrastructure for developing **Claude Code Mods** with Claude Code, Codex, Pi Agent, and ChatGPT.

> **Infrastructure status (2026-10-13):** The 91-document Source Registry is still **UNVERIFIED** and has zero approved API claims. A first-party HTTPS fingerprint collector has captured 43/43 official-document byte hashes and immutable HTTP metadata; **these observations are not reviewed API contracts**. No installable Skill/ChatGPT Plugin has been published.

## Existing material

- [Original research index](docs/research/claude_code_mods_research_index_2026-10-13.md)
- [Categorized knowledge/references and six-area mapping](docs/research/claude_code_mods_knowledge_base_v2_2026-10-13.md)
- [Official source and example review](docs/research/claude_code_mods_official_source_review_2026-10-13.md)
- [91-entry original catalog](docs/research/claude_code_mods_catalog_v2_2026-10-13.json)
- [SSOT architecture and Knowledge Compiler design v0.1](docs/design/mods_ssot_design_v0_1/ARCHITECTURE.md)
- [SSOT v0.1 schemas, unverified registry seed, target profiles and validation results](docs/design/mods_ssot_design_v0_1/README.md)
- [Original import SHA-256 manifest](docs/SOURCE_IMPORT_SHA256.txt)

## Evidence and trust rules

1. Current Mods official specifications, directly related official mechanisms, and indirectly relevant documentation are cataloged separately from community articles and historical proposals.
2. Historical proposals and stale API snapshots are for background only and **must not** be used as current implementation contracts.
3. Official examples illustrate design choices but do not override a target-version API contract.
4. A catalog entry is not an approved knowledge claim. Promotion requires a pinned source snapshot, evidence locator, applicable versions, and recorded verification.
5. Skills and ChatGPT plugins will be **generated** from approved SSOT knowledge, not hand-maintained as independent sources.

## Scope of this initial commit

Preserve the previously produced 2026-10-13 research/design files **byte-for-byte**, together with their SHA-256 hashes. No compiler, installer, update automation, remote knowledge fetcher, or Agent host smoke test is introduced in this bootstrap commit.

Next steps will be discussed and planned separately.

## Source Registry and collector (P0 initial implementation)

The initial source ingestion tool is written in Python and tested without touching the other development repositories. It copies the 91 imported Source Registry entries **without trust promotion**, validates cross-record policy, and records append-only SHA-256 metadata for allowlisted official documentation only. No raw upstream HTML/text is copied.

```sh
uv sync --locked
uv run mods-knowledge validate
uv run mods-knowledge list --layer L0
uv run mods-knowledge verify
# The following is an explicit network action:
uv run mods-knowledge collect --source M001
uv run pytest
uv run ruff check .
```

See [operational instructions](docs/operations/source-collection.md) and the [first official fingerprint baseline](docs/reports/2026-10-13-official-doc-fingerprint-baseline.md). The initial registry is in [sources/registry.json](sources/registry.json); fingerprint metadata and current hash pointers are under `sources/snapshots/`. Source records remain unpinned/unapproved at the claim level regardless of collection success.
