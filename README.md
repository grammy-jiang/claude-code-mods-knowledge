# Claude Code Mods Knowledge

Versioned, evidence-backed knowledge infrastructure for developing **Claude Code Mods** with Claude Code, Codex, Pi Agent, and ChatGPT.

**Project status — 2026-10-14:** 91 source records and **29 approved, strictly Claude Code CLI 2.1.296-scoped Claims**, plus 5 unapproved candidates. Generated Agent Skills target Claude Code, Codex, Pi Agent and a skills-only ChatGPT Plugin. [Source and strict manifest validation](docs/reports/2026-10-14-strict-author-investigation.md) added K-0034 to the existing K-0032/K-0033 CLI code safeguards.

**Distribution:** [v0.2.0-beta.1](https://github.com/grammy-jiang/claude-code-mods-knowledge/releases/tag/v0.2.0-beta.1) remains the last published GitHub Beta and **currently installed, enabled ChatGPT account version**. Experimental Chat-mode candidates are not equivalent to a new public release and are rolled back when they regress. [Beta.5 real Chat-mode findings](docs/reports/2026-10-14-beta5-chat-mode-qa.json) document 14 automatic test conversations and 3 explicit Plugin calls. No newer candidate is presented as stable or fully host-verified.

**Quality boundary:** The first full 46-question Beta.1 Chat-mode run had 27/30 positive automatic Skill loads but only 15/30 positive structural evidence checks passing; independent semantic QA is more restrictive. The Beta.5 targeted run had **zero automatic Skill reads in 8 positive and 4 boundary cases** but **3/3 verified Plugin reads when explicitly invoked**; unrelated requests remained untriggered. Auto-routing is not controllable deterministically by a skills-only plugin. See [full current state/QA report](docs/reports/2026-10-14-p4-p5-status-and-next.md). Issues #1–#4 remain open for model reliability, semantic correctness, cross-host inference, and stable release acceptance.

**Release safety:** The new [fail-closed stable-readiness gate](docs/operations/p6-release-readiness.md) checks all 46 real Chat-mode cases, source-matched real Claude/Codex/Pi inference cases and account install/rollback evidence. Its [current real-evidence inspection](docs/reports/2026-10-14-stable-readiness-blocked.json) explicitly blocks a stable tag; QA ZIP checks alone are not sufficient.

**CI:** GitHub Actions now executes real, model-free Python 3.11/3.14 regression jobs on PRs and main. See [workflow and authorization record](docs/operations/qa-workflow-install.md). These green checks are static/package evidence, not ChatGPT runtime acceptance.

**Source provenance:** Nine first-party Mods documents have reviewed, SHA-pinned sections. The original fourteen research/design artifacts are immutable under [SHA-256 validation](docs/SOURCE_IMPORT_SHA256.txt); historical and community sources cannot override active API contracts. The catalog's original unverified migration envelope is intentionally retained.

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

The six original Claims map one each to **E** events, **S** state, **T** types, **Q** quality/testing, **P** permissions/security and **U** UI. Five original API Claims remain candidates. Across the reviewed SSOT there are 26 approved, CLI 2.1.296-scoped Claims.

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


## P4–P6 qualification, personal installation and private release

The P4 Chat-mode source/trigger/negative-prompt scenario bank has 46 cases (30 positive, 8 unrelated negative, 8 version/security boundary). The runner grades **static resource coverage only**, never invented ChatGPT model responses.

```sh
uv run mods-knowledge eval --suite evals/p4_cases.json --report /tmp/mods-p4.json
uv run mods-knowledge build --api-version 2.1.296 --surface cli \
  --package-version 0.2.0-beta.1
uv run mods-knowledge package-check --dist dist
uv run mods-knowledge marketplace-stage --dist dist  # dry-run; --apply stages local source
```

For model-free cross-device testing (MacBook + two Raspberry Pi 5 machines), use `bash scripts/p5_model_free_check.sh macbook|raspberrypi|sextant` separately on each host. No `claude`, `codex`, `pi` or ChatGPT model calls are made by that script.

See [P4–P6 operating procedures and unverified host boundaries](docs/operations/p4-p6-chatgpt-plugin.md). A private GitHub `-beta.N` release contains the Plugin ZIP plus standalone and per-host Skill ZIPs; partial Chat-mode successes and failures are recorded, not described as a fully qualified general-availability release; **it must never be described as a fully host-verified stable release**.

## P5 authenticated Chat-mode observations

Raspberry Pi's signed-in ChatGPT account has loaded this personal plugin. Seven actual Chat-mode conversations in v0.1.0-rc.2 had 3 structural passes and 4 structural failures; some automatic activations failed while explicit @claude-code-mods-knowledge loaded reviewed documentation and produced the corrected hook signature. See `docs/reports/2026-10-14-p4-p5-evidence.md` and the redacted SHA-only `docs/reports/p5_chat_mode_rc2_observations.json`. P6 remains a private prerelease until full Chat-mode QA succeeds.

## Private Beta Release

The P6 Beta release includes both the ChatGPT personal Plugin and installable Skill packages for Claude Code, Codex and Pi Agent. The GitHub [Releases page](https://github.com/grammy-jiang/claude-code-mods-knowledge/releases) contains the tagged source, version-specific ZIPs, SOURCE-SBOM, P4 static suite, P5 cross-device/Chat evidence matrix, release notes, and SHA256SUMS. This project remains private.

**Beta means qualified infrastructure, not complete ChatGPT auto-trigger reliability.** Actual Chat-mode evaluation revealed intermittent non-activation even when installed, and 26 approved Claims are only scoped to Claude Code CLI 2.1.296. Claude/Codex/Pi model-running acceptance remains deferred until local token quotas are restored.
