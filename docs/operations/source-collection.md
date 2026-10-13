# Source Registry / Official Documentation Collection

## Scope and trust

This collector is the **first infrastructure stage only**, not a knowledge-claim curator.

- `sources/registry.json` preserves the original 91-row `UNVERIFIED_MIGRATION_SEED`, including M001–M091 and L0/L1/L2/R/C/H.
- Only L0/L1/L2 `https://code.claude.com/docs/en/...` pages and the exact official `https://code.claude.com/docs/llms.txt` index may be fetched.
- R (official examples), C (community), and H (historical) cannot be collected by this command. They require separate, future provenance workflows.
- `sources/snapshots/metadata/Mxxx/<sha256>.json` files record first observations. `sources/snapshots/index.json` tracks the currently observed SHA and metadata hashes for all revisions.
- The collector intentionally stores **no webpage HTML, Markdown or text**, only raw-response SHA-256 and limited HTTP metadata.
- A new fingerprint means **bytes changed**, not that the specification, API, or semantic meaning changed. An HTTP 200 is not proof that a page is current or authoritative for a target Claude Code version.
- No registry entry, API Claim or agent capability is automatically promoted to `approved`. All 91 migrated sources remain unverified.
- Network use is explicit. No daemon, cron, CI workflow, automatic background fetch, or credential-bearing HTTP request is installed.

## Prerequisites

Run from this repository checkout, on Python 3.11+ and macOS/Linux (the version-history file lock uses `fcntl`).

```sh
uv sync --locked
uv run mods-knowledge validate
uv run mods-knowledge list --layer L0
uv run mods-knowledge verify
```

The four commands above do not make network requests; `validate` and `list` only read the registry, and `verify` checks existing local metadata without changing it.

## Explicit official documentation fingerprinting

```sh
# Network action: only this single official source.
uv run mods-knowledge collect --source M001

# Repeat an observation. If unchanged, the history/index bytes are untouched.
uv run mods-knowledge collect --source M001

# Fetch 3 registered official documents, to bound a trial run.
uv run mods-knowledge collect --all-official --limit 3

# Fetch all eligible official documents (43 in the original catalog).
uv run mods-knowledge collect --all-official

# Changelog may exceed 2 MB; increase the cap only for its source ID.
uv run mods-knowledge collect --source M033 --max-bytes 6000000

# Afterwards validate local metadata references and their SHA-256 checksums.
uv run mods-knowledge verify
```

The default response cap is 2,000,000 bytes, with a hard per-request maximum of 8,000,000. Timeout defaults to 12 seconds (permitted range 1–30). The collector uses HTTPS/TLS verification, rejects every redirect and unexpected MIME type, and accepts neither a caller-supplied arbitrary URL nor custom authentication headers. Source URLs are confined to a reviewed exact host and documentation path. When the upstream moves a page, review and update the registry before fetching the new canonical URL.

`collect` reports `new`, `unchanged` or `changed` (raw-byte fingerprint only) for each successful observation. Individual failures return a nonzero status, identify the Source ID, and do not promote evidence. A batch can record successful observations while also reporting a failed source.

## Review and publication boundaries

- Every fingerprint is an **unreviewed observation** of HTML/text at one point in time, even if its SHA is permanently recorded.
- File metadata SHA values are stored in the index and verified locally. This **does not recompute the hash of online source bytes** (the page content is not retained).
- Commit registry changes and collected metadata to Git for provenance. Review `git diff` and enforce SHA/trust/version checks before any generated Skill is allowed to cite them.
- HTML framework releases may cause frequent byte changes without an API change. A future semantic diff/Claim curation stage must review actual official source material and version compatibility independently.
- Existing source artifacts in `docs/research` and `docs/design/mods_ssot_design_v0_1` are intentionally left byte-identical to the import manifest.

## Failure handling

A failed collection cannot mark a source valid, pinned or approved. For a 404, unexpected redirect, MIME mismatch or size limit, investigate the upstream location and record the issue; never bypass host restrictions or apply an arbitrary URL override. Failed writes leave existing index pointers intact; orphaned metadata resulting from an abrupt process termination is surfaced by `verify` for manual investigation. No automated cleanup deletes history.
