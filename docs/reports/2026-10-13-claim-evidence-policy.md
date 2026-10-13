# Knowledge Claims and evidence-policy implementation — 2026-10-13

## Deliverables

- `claims/K-0001..K-0006.json`: one `candidate` per E/S/T/Q/P/U area, with only authoritative source *references*; no API Claim approved or promoted.
- `src/mods_knowledge/claims.py`: validates original Claim Schema, stable IDs, cross-Claim references/cycles, evidence trust/type, observed content fingerprints, reviewed locator/source identity, bounded versions and surface scope, normative conflict and history firewall.
- `src/mods_knowledge/decisions.py`: explicit `candidate -> reviewed -> approved` transition and terminal reject/deprecate actions, with integrity-linked decision history, reviewer label, rationale and atomic local writes under a POSIX file lock.
- `src/mods_knowledge/runtime_evidence.py`: checks content-addressed runtime reports, logs, active target profile identity and declared versions. These reports can be fabricated by a privileged editor; Git review and actual execution inspection are still necessary.
- `targets/profiles.json`: initial copy of the 2026-10-13 target versions, maintained separately from the archived design; future updates append new profile identities.
- `mods-knowledge claims {validate,list,show,query,transition}`; top-level `validate` and `verify` additionally validate Claims.
- `docs/operations/claim-curation.md`: source review, promotion, rollback and recoverability instructions.

## Key restrictions

- The original 91-entry Source Registry remains `UNVERIFIED_MIGRATION_SEED`; its 43 HTML byte digests are not source-content semantic review.
- All six initial Claims are `candidate`, with `verification.runtime=not-run`, no approved or reviewed knowledge. Approved current query on `--version 2.1.296 --surface cli` is empty.
- H sources cannot support active API Claims; C/R sources cannot supply normative proof. GitHub example SHA alone is not a verified source pin.
- Normative approval is structurally blocked without a reviewed and pinned L0/L1 locator, an observed matching HTTP metadata SHA, bounded applicable versions, a compatible targeted runtime record and no unresolved conflicts.
- Stored event hashes and test report log hashes detect inconsistent edits but are **not digital signatures nor proof that a source or runtime test actually happened**. A reviewer's `--actor` value is claimed identity, not authenticated identity.
- Transition writes update the decision and Claim atomically *per file*; a power failure between the two is detected by `claims validate` and must be recovered from Git.
- This stage does not implement official source text/line provenance, cryptographic attestations, automatic approval, the Knowledge Compiler, Skills, ChatGPT Plugin or continuous monitoring.

## Verification evidence

On MacBook Pro:
- `uv run --python 3.11 --locked pytest -q` — **128 passed** on Python 3.11.17.
- `uv run --python 3.14 --locked pytest -q` — **128 passed** on Python 3.14.8.
- `uv run ruff check .` — passed; `uv run ruff format --check .` — 29 files formatted.
- `uv run mods-knowledge claims validate` — 6 candidate, 0 approved, 1 per engineering area.
- `uv run mods-knowledge verify` — consistent snapshot and Claim metadata; original research SHA files unchanged.

Test details include offline schema/evidence policy negatives, malicious source/locator drift, hash tampering, target-profile mismatch, runtime report semantic tampering, conflicting normative subjects, version/surface filtering and concurrent review transitions. Tests for approved normative Claims are **synthetic fixtures**, never represented as actual Claude Code runtime compatibility.
