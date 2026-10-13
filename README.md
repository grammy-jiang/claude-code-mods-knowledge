# Claude Code Mods Knowledge

Versioned, evidence-backed knowledge infrastructure for developing **Claude Code Mods** with Claude Code, Codex, Pi Agent, and ChatGPT.

> **P2/P3 build status (2026-10-13):** 25 approved, version-scoped knowledge Claims (24 official guidance + 1 narrow CLI test-kit observation); 5 unapproved API candidates. The deterministic compiler produces **Claude Code, Codex, Pi Agent Skills and a portable ChatGPT Plugin** locally in the Git-ignored dist directory. These packages have not been installed or host-evaluated on ChatGPT; P4/P5 remain future phases.

> **Curation status (2026-10-13):** 91 indexed sources and 43 initial official-document HTTP fingerprints. Nine official Mods documents now have reviewed Markdown section attestations; **24 guidance Claims and one narrowly scoped real CLI test-kit observation** are approved for Claude Code CLI 2.1.296 only, while five API Claims remain candidates. No Agent Skill or ChatGPT Plugin is installed or published. Raw HTML fingerprints alone never constitute API proof.

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

## P2 reviewed knowledge

Official document reviews (without redistributed source text) are indexed in `sources/reviews/`. Current approved knowledge is strictly version/surface scoped and verified through the original Claim policy and its hash-linked approval record.

```sh
uv run mods-knowledge claims validate
uv run mods-knowledge claims query --version 2.1.296 --surface cli
# Any unsupported version or non-CLI surface must be checked against current official docs first.
uv run mods-knowledge claims query --version 2.1.297 --surface cli
```

See [P2 source/claim review evidence](docs/reports/2026-10-13-p2-curation.md), including what the actual `claude plugin validate/test` run does **and does not prove**.


## P3 deterministic Knowledge Compiler

The build compiler consumes **only** source-bound, approved Claims for an explicit Claude Code version and host surface. It fails closed when no matching approved knowledge exists, including versions before or after 2.1.296. It has no network, model invocation, credential access, automatic plugin installation or approval side effects.

```sh
uv sync --locked
uv run mods-knowledge claims validate
uv run mods-knowledge build --api-version 2.1.296 --surface cli
(cd dist && shasum -a 256 -c manifests/checksums.sha256)
```

Outputs: `dist/common/`, `dist/claude-code/.claude/skills/`, `dist/codex/.agents/skills/`, `dist/pi/.agents/skills/`, `dist/chatgpt/claude-code-mods-knowledge/`, deterministic ZIPs under `dist/packages/`, and provenance/checksums under `dist/manifests/`. The ChatGPT Plugin uses the **Agent Plugins 1.0** portable `plugin.json` format and bundles a Skill only. All generated platform Skills share byte-identical instructions and references, including first-party source navigation and official examples clearly separated from approved API evidence.

See [P3 operation and limitations](docs/operations/knowledge-compiler.md) and [P3 validation report](docs/reports/2026-10-13-p3-compiler.md). Generating a package is not a claim that its host loaded or followed the Skill; that belongs to P4/P5.
