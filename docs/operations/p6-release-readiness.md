# P6 release readiness — fail-closed host and ChatGPT evidence


> Latest-release requirement (2026-10-17): Before any new Skill/Plugin
> publication, follow [Latest-only Claude Code SSOT roll-forward](latest-version-rollforward.md)
> and pass the online npm latest-target and approved-Claim preflight.
> The 2.1.296 commands below are historical reproducibility examples,
> **not** release instructions for the current 2.1.302 host binaries.
> Do not publish or install a newly labeled package using old scoped Claims
> until current official sources and target-native semantics are reapproved.

This is a **read-only** release-eligibility assessment. It neither runs an AI model nor publishes a GitHub Release.

## Required acceptance gates

- Compiler and source: valid SSOT approvals, exact Claude Code CLI 2.1.296 scope, reproducible ZIP/source manifest, matching full Git SHA.
- **Chat mode**: all 46 P4 cases completed in distinct, actual ChatGPT ordinary Chat conversations; 46 passes with independent technical review; correct Plugin resource reads for all positive/boundary cases; no read for unrelated negative cases. Explicit `@plugin` controls never count as automatic-loading successes.
  The sanitized evidence must explicitly record `invocation_mode: automatic` from the real send trace. Missing provenance is `unverified` and fails closed; the evaluator does not assume automatic selection. Only the canonical `claude-code-mods-development` Skill URI and safe descendants count as Plugin reads (not a sibling Skill or a path-traversal alias).
- **Three Agent models**: real, independently evidenced Claude Code, Codex and Pi Agent model turns; native Skill discovered; positive, negative and boundary cases per host; source/version and answer quality verified. A native loader or static lint pass is not inference.
- **Account installation and rollback**: supply the exact account-downloaded normalized Plugin ZIP, cryptographically link its ten reviewed files and sidecar to the compiler's source ZIP, and separately substantiate Chat installation/enablement and verified rollback. A claimed upload ZIP hash is not evidence that ChatGPT installed the same instructions.
- **Privacy**: published reports may contain case IDs, hashes, scoped verdicts and blockers, but no raw chats, credentials, account IDs or cookies.

## Commands

```sh
uv run mods-knowledge build --api-version 2.1.296 --surface cli \
  --package-version 0.3.0-beta.1 --source-revision "$(git rev-parse HEAD)"
uv run mods-knowledge package-check --dist dist

uv run mods-knowledge stable-readiness \
  --dist dist \
  --chat-report /secure/qa/live-chat-report.json \
  --agent-report /secure/qa/real-agent-model-report.json \
  --account-report /secure/qa/installed-account-report.json \
  --account-download-zip /secure/qa/account-downloaded-plugin.zip \
  --out /tmp/mods-stable-readiness.json --require-ready
```

- Exit **0** with all checks passed: `READY_FOR_STABLE_RELEASE` eligibility (not an actual publication).
- Exit **3**: package is valid but P4/P5/account evidence is missing or failing; report status `STABLE_RELEASE_BLOCKED`.
- Exit **2**: tampered/unsupported compiler build or invalid input.
- Omit optional evidence files for a safe *inspection*: each missing category blocks rather than fabricates a pass. Without `--require-ready`, a generated inspection report uses exit 0 even when blocked.

The evaluator checks distinct hashed conversations and host evidence across cases, automatic versus explicit routing, target versions, manual review, and **exact normalized account ZIP contents**. A missing or tampered downloaded account ZIP now prevents `READY_FOR_STABLE_RELEASE`, even if a report contains matching-looking hash strings. The normalized content check accepts precisely ten original reviewed files and the approved sidecar, and compares every byte to the source-built ZIP in `dist`.

The account report must contain `schema_version: 1`, the independently inspected `installed_plugin_version`, `installed_enabled`, `skill_enabled`, `chat_surface: chat`, `rollback_verified`, and a SHA-256 audit `evidence_sha256`. It must also contain `installed_bundle_sha256` of **the downloaded archive**, `source_bundle_sha256` of the **compiled uploaded archive**, and `canonical_content_sha256` and `server_sidecar_sha256` calculated by `account-archive-check`. An older report that only asserts the uploaded SHA as the installed bundle fails closed.

**Provenance limitation:** This verifies supplied bytes and cross-report consistency, not whether the supplied ZIP truly came from an authenticated account. The flags and audit digest still require a trusted operator to review the account management logs and rollback. The tool never logs into ChatGPT, never changes settings, and never upgrades a partial P4/P5 verdict.

## Current facts

The last **published GitHub Beta** is `v0.2.0-beta.1` (26 Claims at that release's source). The personal ChatGPT account was subsequently observed running the **unpublished experimental** `0.3.0-beta.1` single-Skill candidate, whose ten reviewed files match its uploaded source. See the [targeted Chat pilot](../reports/2026-10-14-v030beta1-real-chat-targeted.md). Main has 29 approved Claims scoped to CLI 2.1.296. Earlier Beta.1 full Chat semantic QA scored **15 pass / 25 fail / 6 inconclusive**. The two-Skill preview was separately tested and failed auto-activation. Real Codex/Pi model tests remain partially accepted, and real Claude inference is still unverified. Thus the current stable release gate is **blocked**.

OpenAI documents model-mediated Skills selection at https://developers.openai.com/plugins/concepts/skills and requires positive, negative, boundary and repeat consistency tests at https://developers.openai.com/plugins/deploy/connect-chatgpt.

## ChatGPT account ZIP normalization audit (2026-10-14)

The ChatGPT account's real `manage_plugins.py download` ZIP is **not byte-for-byte
identical** to the original compiler upload: the observed download strips the
`claude-code-mods-knowledge/` root and adds `.codex-plugin/plugin.json` alongside
root `plugin.json`. Consequently a raw ZIP SHA mismatch, by itself, does not
establish that the installed **instructions** differ. Do not declare a match
from the version string or Skill filename either.

Use the offline, fail-closed comparator with the *exact uploaded* ZIP and an
account-downloaded ZIP (keep the downloaded original in a private directory):

```sh
uv run mods-knowledge account-archive-check \
  --uploaded dist/packages/claude-code-mods-knowledge-0.3.0-beta.1.zip \
  --downloaded /private/account-download.zip \
  --out /private/account-archive-evidence.json
```

This compares the ten approved files by **exact decompressed bytes**, requires
the precise reviewed single-Skill file allowlist, and validates the normalized
sidecar's metadata against the signed-off portable manifest. It refuses extra
Skills/references, changed instructions, path traversal, duplicate members,
executable/symlink content, invalid ZIPs and injected sidecar metadata. It
reports upload/download ZIP hashes and a canonical content hash, without raw
model replies, account identifiers or ZIP file content.

The comparator alone does **not** authenticate where the supplied files came from, certify the account's enabled state, demonstrate Chat mode selection or substitute for P4/P5/rollback acceptance. The stable-readiness gate now requires the actual downloaded ZIP bytes in addition to the account's independently reviewed status record; it recalculates both ZIP SHA-256 values and the normalized content/sidecar digests, refusing arbitrary hash assertions. Platform login, ownership and rollback still require an external trusted audit. Do not record the private ZIP or raw account/session data in public GitHub.

## Package-content security gate (2026-10-14)

The release package validator now requires the exact approved file layout:
plugin.json, one canonical SKILL.md, and eight named reference pages.
It rejects extra Skill directories, arbitrary Markdown policies,
undeclared reference pages, and any preview_extension build marker.
The same constraint applies to the standalone Skill ZIP.

All published plugin and standalone Skill archives also reject high-confidence
private content *inside otherwise approved files*: real-shaped ChatGPT
conversation links, personal Plugin instance IDs, and GitHub/OpenAI token-shaped
secrets. This is enforced during normal `package-check` / `validate_bundle`,
not merely as an after-the-fact public repository text scan. Errors identify
only the marker class, never reproduce sensitive values. Examples with obvious
nonsecret placeholder markers remain permitted. This is a defense-in-depth
filter, not a substitute for reviewing releases or scrubbing historical Git
refs that already exposed private conversation URLs.

Five new regression cases first demonstrated the unreviewed content bypass.
They now fail closed; the full Python suite passes after the fix. No account
credentials, models or publishing are involved.

A multi-Skill preview MUST use the separate nonpublishable verification route.
Do not weaken the normal release gate to make an experimental ZIP installable.
Any future multi-Skill release needs explicit per-Skill SSOT provenance,
an authored file allowlist and real host/model acceptance evidence.

## 2026-10-18: current approved CLI 2.1.302, fail-closed versioned evaluation suite

The original public evals/p4_cases.json is an immutable CLI 2.1.296
benchmark. It must not be used to certify the 31 separately approved
CLI 2.1.302 Claims or new ChatGPT Plugin versions.

The stable-readiness gate now selects a version-specific frozen 46-case
public suite from the built distribution target. CLI 2.1.296 uses the
original file; CLI 2.1.302 uses evals/p4_cases_cli_2_1_302.json.
Future CLI versions require their own checked-in, exact-version suite
with the same naming convention. Missing, malformed or mismatched
suite/target metadata fail closed; the gate does not silently select
a historical or assumed latest suite. The CLI 2.1.302 positive required
Claim IDs derive from the separately approved SSOT supersedes ledger,
and the negative and boundary prompts preserve the original task intent.

This fixes a gate-dispatch version mismatch only. A package may now
pass integrity/target checks yet correctly return STABLE_RELEASE_BLOCKED
for real Chat Mode semantic/activation, agent-host model or account
rollback evidence that is missing or failed. Source and tests passing
never convert blocked external observations into a stable release.

### Private prerelease artifact staging for CLI2.1.302

The private beta/rc release-builder originally also selected the frozen
evals/p4_cases.json (CLI2.1.296) regardless of the candidate version.
It now resolves the same explicit, reviewed, version-specific public
P4 suite as stable-readiness before running offline resource and
provenance checks. A future CLI without a separately checked-in exact
evaluation suite cannot be packaged for private prerelease.

Release notes no longer assert that nobody has run Claude/Codex model
inference: subsequent controlled native tests exist. They now
distinguish static prerelease packaging from separately documented
model evidence, without conflating offline checks with real host
acceptance. Prerelease packaging does not authorize Stable deployment.
