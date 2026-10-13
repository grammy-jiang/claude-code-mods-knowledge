# Knowledge Claims and Evidence Gates — Implementation Plan

> **For agentic workers:** Use test-driven development for each deliverable. Work in an isolated Git worktree.

**Goal:** Build fail-closed validation and a traceable review/approval workflow for atomic Claude Code Mods claims, then seed six engineering domains with explicitly unapproved candidates.

**Architecture:** Keep the 91-entry source registry and first 43 metadata-only SHA fingerprints unchanged. Add `claims/K-XXXX.json` records validated using the previously published `claim.schema.json` and cross-record/target-version policy. Keep `decisions/K-XXXX.json` as a bound audit trail. A CLI may propose and record human/agent-attributed decisions, but it cannot promote claims that lack official pinned version evidence. No source-HTML copies, network fetches, compiler, skills, or plugins in this phase.

**Tech Stack:** Python 3.11+, jsonschema, pytest, Ruff, uv. macOS tested; policy validation independent of OS.

**Spec:** `docs/design/mods_ssot_design_v0_1/ARCHITECTURE.md` §§3.2, 4, 7 and P1–P2.

## Global constraints

- Preserve the 14 originally imported research/design files' SHA-256 and the 91 source identities/first-stage fingerprints unchanged.
- Distinguish: official index presence; raw-byte HTTP digest; actually reviewed evidence with pinned source; and runtime validation of a target version.
- A raw observation alone is insufficient to approve a current API claim.
- Normative approvals require a locked L0/L1 supporting source, matching observed digest, nonempty stable evidence locator, explicit target version interval and supported surfaces, reviewed source status, runtime evidence (for strict mode), a decision record, and no unresolved contradictions or overlapping normative subjects.
- Historical H can only support history; C/R are never sole authoritative proof of a normative API.
- A reviewer name in CLI is *recorded attribution*, not cryptographic authentication. CLI must not silently approve or infer approval from source list membership.
- Prefer pure validation; fail closed, no mutation during `claims validate` and `claims list`. Update individual JSON files atomically and reject invalid post-transition state.
- Only explicit, local CLI actions change Claims. No background/scheduled work and no ChatGPT plugin installation.
- No user credentials or private user data in committed artifacts.

## Tasks

### Task 1 — Cross-record Claim validator (P1)

**Files**: `src/mods_knowledge/claims.py`, `src/mods_knowledge/errors.py`, `tests/test_claims.py`.

**Interfaces**:
- `load_claims(claim_dir: Path, source_registry: Mapping[str,dict], snapshot_root: Path, decision_dir: Path) -> dict[str,dict]`
- `validate_claims(claims: Mapping[str,dict], source_registry: Mapping[str,dict], snapshot_root: Path, decision_dir: Path) -> None`
- `approved_claims(claims: Mapping[str,dict], version: str, surface: str) -> list[dict]`

RED tests: schema and ID/path binding; duplicate IDs, malformed versions/intervals, unknown source/reference IDs, evidence kind/layer mismatch, unsafe paths, historical firewall, candidate admissibility, normative false positive on raw fingerprint, pin mismatch, missing runtime/decision, cross-claim version conflict, dangerous contradictory evidence, target-version filtering, and negative/offline fixture. GREEN minimal pure validator. Run full suite.

### Task 2 — Review decision/audit state transitions (P1)

**Files**: `src/mods_knowledge/decisions.py`, `tests/test_decisions.py`.

**Interfaces**:
- `transition_claim(root: Path, claim_id: str, action: str, actor: str, rationale: str, at: datetime) -> dict`

Create `candidate -> reviewed -> approved` and `candidate/reviewed -> rejected`; `approved -> deprecated` only. Each mutation records an audit event with previous/current-state content digests and simple date. Verify current claim hash against final ledger entry. RED tests for valid/invalid transition, audit tamper, stale source pin, no network, concurrent state change serialization, and missing rationale.

### Task 3 — CLI and six conservative candidate claims (P2 initial)

**Files**: `src/mods_knowledge/cli.py`, `tests/test_cli_claims.py`, `claims/K-0001..K-0006.json`, `docs/operations/claim-curation.md`, `README.md`.

CLI: `mods-knowledge claims validate`, `claims list`, `claims show K-0001`, `claims transition <id> --to reviewed|approved|rejected|deprecated --actor <text> --reason <text>`; `claims query --version ... --surface ...` returns approved only.

Seed six *candidate* guidance/API research questions (one primary E, S, T, Q, P, U) with source IDs and URL anchors, but no assertion that the current API is proven. No approve until evidence actually verified against correct bytes/versions.

RED CLI tests for no implicit network, candidate/approved output, invalid state rejection, and duplicate parsing. GREEN minimal.

### Task 4 — Quality and publication

Validate Python 3.11 and 3.14 full tests, Ruff, source SHA-256 manifest, snapshot integrity, claim policy, no secrets, Git clean after commit. Commit to branch, merge fast-forward only if remote `main` has not changed, push, verify remote SHA. If inability to verify normative claims remains, preserve them as candidates; do not represent the system as having approved API knowledge.
