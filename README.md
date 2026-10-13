# Claude Code Mods Knowledge

Versioned, evidence-backed knowledge infrastructure for developing **Claude Code Mods** with Claude Code, Codex, Pi Agent, and ChatGPT.

> **Bootstrap status (2026-10-13):** This repository currently contains research and architecture artifacts, **not** an approved API knowledge base or an installable Skill/Plugin. The migrated 91-document source registry is **UNVERIFIED**; no source snapshots are pinned and no API claims have been approved.

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
