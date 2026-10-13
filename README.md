# Claude Code Mods Knowledge

Versioned, evidence-backed knowledge infrastructure for developing **Claude Code Mods** with Claude Code, Codex, Pi Agent, and ChatGPT.

> **Infrastructure status (2026-10-13):** 91 source entries remain in the **UNVERIFIED** migration state. The collector has captured 43 official-document HTTP fingerprints; the new Claim policy stores **six initial candidates and zero approved API claims**. Neither fingerprints nor candidate questions are reviewed API contracts. No installable Skill/ChatGPT Plugin has been published.

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

## Imported research provenance

The original 14 research/design artifacts are preserved **byte-for-byte** with a SHA-256 manifest. No Knowledge Compiler, Agent Skill, Plugin, background update job, or tool that changes Claude Code behavior is installed.

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


## Atomic Knowledge Claims (P1 policy / P2 candidate seed)

`claims/K-XXXX.json` contains source-linked atomic knowledge statements and research questions. Each includes a trust designation, six-domain mapping, version/surface scope, source locator, evidence pins, review status, and runtime test references. `decisions/K-XXXX.json` is created only after an explicit permitted state transition and binds the outcome to Claim and prior decision hashes. Published current-API queries never contain unapproved or historical Claims.

```sh
# Entirely offline, no changes to Claims or network:
uv run mods-knowledge claims validate
uv run mods-knowledge claims list
uv run mods-knowledge claims show K-0002
uv run mods-knowledge claims query --version 2.1.296 --surface cli
uv run mods-knowledge verify
```

The initial six Claims map one each to **E** events, **S** state, **T** types, **Q** quality/testing, **P** permissions/security and **U** UI. They are intentionally all `candidate`; querying a target version currently returns **zero** publishable facts.

See [Claim curation, version/pin rules, explicit transitions, and limitations](docs/operations/claim-curation.md). [Active target profiles](targets/profiles.json) are updateable without editing the immutable design archive; new version/profile IDs must be appended, not overwrite previously verified versions. Review identities and runtime reports are declarative and require external review; the CLI **does not authenticate reviewers or prove that a test log came from a real machine run**.
