# Source Registry and Official Documentation Fingerprints — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task, following test-driven development.

**Goal:** Safely import the 91 existing Mods references, validate their metadata and trust partitions, and record immutable, byte-level fingerprints of current official documentation without treating an HTTP fetch as approval of an API contract.

**Architecture:** Preserve all migrated records byte-for-byte in `sources/registry.json`. Add a small Python package responsible for validating the original JSON Schema and cross-record policy, strictly restricted HTTPS fetching from approved first-party documentation hosts, append-only hash-keyed observation metadata, and a deterministic current-hash index. No source HTML/text is stored and no Claim is promoted.

**Tech Stack:** Python >=3.11, jsonschema Draft 2020-12, Python stdlib `urllib`, pytest, uv.

**Spec:** `docs/design/mods_ssot_design_v0_1/ARCHITECTURE.md` (§3, §4, §7, P0 and the snapshot portion of P1).

## Global Constraints

- User-approved work happens in isolated sibling worktree; do not mutate other repositories or processes.
- Keep `docs/research/` and `docs/design/mods_ssot_design_v0_1/` original 14 input artifacts unchanged.
- Registry stays unverified; no code may implicitly upgrade `review_state`, create approved Claims or mark online HTML as version-specific authoritative.
- Only HTTPS `code.claude.com/docs/en/` pages from L0/L1/L2 qualify for active collection; R/C/H sources must be rejected. No arbitrary URL fetch through CLI.
- Redirects off the approved host are rejected; TLS verification is enabled; no auth token is ever sent; response size and request timeout are bounded.
- Store full SHA-256 of received bytes and HTTP metadata, but not the copyrighted web page content; raw-byte changes are **not** a semantic diff or API change.
- Files are written atomically; replaying the same fingerprint is idempotent and does not rewrite the metadata or hash index. Failures must not change current successful state.
- No new background daemon, scheduled automation, continuous scraper, host Skill or ChatGPT Plugin installation.

## Review Focus

1. An untrusted/community URL redirects to an internal host → block before following it; test restrictive URL and redirect policy.
2. Huge/HTML-invalid/empty response → reject with no index/partial metadata mutation; test bounded payload reader.
3. Newly collected document differs only in framework HTML bytes → report byte-change (not API-change); retain both observations.
4. Partial writes / failed network → previous current pointer remains intact and manifest coherent.
5. Duplicate source IDs, URL aliases, historical trust or invalid snapshot-state combinations → reject registry; keep original 91 input identities.

---

### Task 1 — Registry Import + Policy Validation

**Files:** `sources/registry.json`, `src/mods_knowledge/registry.py`, `src/mods_knowledge/errors.py`, `tests/test_registry.py`, `pyproject.toml`, `uv.lock`.

**Interfaces:**
- `load_registry(path: Path) -> dict[str, dict]`
- `validate_registry(data: dict, schema_path: Path) -> dict[str, dict]`
- `eligible_official_sources(registry: Mapping[str, dict]) -> list[dict]`

- [ ] Write failing tests for count 91, L0 10/L1 19/L2 14/R 17/C 28/H 3, duplicate ID and URL, invalid layer/source type, forbidden non-HTTPS URLs, broken historical/superseded references, and illegal pin fields.
- [ ] Run focused tests; verify RED from missing implementation.
- [ ] Copy seed to registry unchanged and implement JSON Schema validation plus cross-record policy. Preserve original `review_state`.
- [ ] Run focused tests, verify GREEN.

### Task 2 — Safe Fetch and Immutable Fingerprint History

**Files:** `src/mods_knowledge/collector.py`, `src/mods_knowledge/storage.py`, `tests/test_collector.py`, `tests/test_storage.py`.

**Interfaces:**
- `fetch_document(url: str, timeout: float = 12.0, max_bytes: int = 2_000_000) -> FetchResult`
- `record_observation(root: Path, source: dict, fetch: FetchResult, at: datetime) -> ChangeResult`
- `verify_snapshot_store(root: Path) -> list[str]`

- [ ] Write offline failing tests for HTTPS scope, redirects, content type, maximum response size, hashing, atomicity, unchanged idempotence, changed versions, integrity verification, and source trust firewall.
- [ ] Verify RED.
- [ ] Implement fetching (strict origin; TLS) and metadata store; no source content persisted.
- [ ] Verify GREEN.

### Task 3 — CLI, Safe Read-Only Commands and Documentation

**Files:** `src/mods_knowledge/cli.py`, `tests/test_cli.py`, `docs/operations/source-collection.md`, `README.md`.

**Interfaces:** `mods-knowledge validate`, `mods-knowledge list`, `mods-knowledge collect --source M001 [--timeout ...]`, `mods-knowledge verify`. Explicit `collect` required for network calls.

- [ ] Write CLI tests: offline `validate/list/verify`, fail-closed eligibility, collection network call boundaries, meaningful exit codes.
- [ ] Verify RED, implement minimal CLI and operational guidance, verify GREEN.
- [ ] Run full `uv run pytest`, `uv run ruff check`, source checksum verification, `git diff --check`.
- [ ] If the first-party live endpoint is available, collect a small labeled sample; retain byte-change semantics and note failures. Do not claim semantic/API verification.

### Task 4 — Integration Review and Git Publication

**Files:** existing tests/docs and generated `sources/snapshots/metadata/` (only explicit first-party retrievals).

- [ ] Inspect diff and run all verification commands fresh.
- [ ] Review security, exact source count, no credentials, immutable history and unchanged imported artifacts.
- [ ] Commit on isolated branch and publish; fast-forward merge into `main` only when both worktrees are clean and remote head matches inspected base.
- [ ] Verify remote SHA equals local `main` and report all unverified areas separately.

## Non-goals for This Iteration

Claim curation/approval, semantic document diff, Codex/Claude/Pi Skills generation, ChatGPT Plugin publication, service deployment, cron monitoring, or automatic trust promotion. Those remain subsequent work packages.
