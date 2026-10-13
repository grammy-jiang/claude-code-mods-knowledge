# P3 Knowledge Compiler — Build and Verification

**Status:** deterministic, offline Skills/Plugin packaging for the approved SSOT subset. Not an automatic publication, installation or actual ChatGPT host load test.

## Target and confidence boundary

As of the 2026-10-13 baseline, the SSOT has **25 approved claims** (24 reviewed official-document guidance claims; one Claude Code 2.1.296 CLI synthetic testing-tool behavior) and **5 candidate/unapproved claims**. Only `--api-version 2.1.296 --surface cli` currently yields content. Other versions and hosts fail closed until reviewed knowledge actually covers them.

The compiler cannot fetch upstream pages, invoke an LLM, edit approvals, install Skills, load Mods or call any model API. All generated paragraphs derive from previously accepted Claim statements, official source pointers and deterministic workflow templates. No historical H or community C material is emitted as active API guidance. R-tier examples appear only as explicitly non-normative navigation pointers.

## Build

From the root of the private repository on macOS:

```sh
uv sync --locked
uv run mods-knowledge validate
uv run mods-knowledge verify
uv run mods-knowledge claims validate
uv run mods-knowledge claims query --version 2.1.296 --surface cli
uv run mods-knowledge build --api-version 2.1.296 --surface cli
(cd dist && shasum -a 256 -c manifests/checksums.sha256)
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

The output folder is `dist/` (Git-ignored). Build artifacts include:

| Location | Meaning |
|---|---|
| `dist/common/claude-code-mods-development/` | The canonical generated Skill with one short SKILL.md and eight reference pages |
| `dist/claude-code/.claude/skills/claude-code-mods-development/` | Claude Code project Skill layout |
| `dist/codex/.agents/skills/claude-code-mods-development/` | Codex project Skill layout |
| `dist/pi/.agents/skills/claude-code-mods-development/` | Pi project Skill layout |
| `dist/chatgpt/claude-code-mods-knowledge/` | Portable Agent Plugins 1.0 `plugin.json` and its Skill (no MCP, hooks, telemetry or authentication) |
| `dist/packages/*.zip` | Deterministic portable standalone Skill and ChatGPT Plugin ZIP bundles |
| `dist/manifests/` | Input and output SHA-256, selected Claim IDs, six-domain coverage, target versions and source revision |

The four host Skills and the common Skill contain **identical bytes**. The ChatGPT Plugin does not include executable code or MCP actions; attaching it to a ChatGPT account and testing its activation belong to P5. Likewise, generating a Claude or Codex Skill is not equivalent to installing it.

The developer may supply `--source-revision <git-sha>`, `--knowledge-version 0.1.0`, and `--package-version 0.1.0`. Without a source override, the CLI tries to read the local Git HEAD. **That HEAD alone is not a full proof of checked-in inputs**: compare the manifest's complete `input_sha256` map with a clean commit before publishing. If you run while the worktree is dirty, the build is a candidate, not a release attestation.

## Official docs, evidence and version routing

The main Skill explains when to look up the six domain references and when to consult first-party documentation. Each active knowledge record includes the original Claim ID, source ID, reviewed section URL, authority, bounded Claude Code version and verification scope. The official source index lists all 43 L0/L1/L2 documents; entries without review attestations are explicitly marked `unreviewed`. The reference example list contains only R-tier pointers with an `not an API contract` warning.

If a user asks about a different Claude Code version, the Agent must read the currently installed version's generated type declarations and current official Docs, rather than assert 2.1.296 behavior. P3 intentionally refuses to compile an unsupported version, including 2.1.297, instead of silently substituting the nearest one.

## Reproducibility

The compiler uses sorted records, stable JSON keys, no build timestamps, fixed ZIP timestamps (1980-01-01), no LLM/network and content-addressed inputs. Two compilations with identical input files, versions and source revision produce identical file bytes, ZIP bytes and SHA-256 manifests. If code, reviewed knowledge, approvals, sources or targets change, the build input fingerprint changes and the output must be retested.

All 14 original research and design attachments are still checked using `docs/SOURCE_IMPORT_SHA256.txt`; no whole upstream HTML pages or Markdown articles were copied into the release bundles.

## Future release steps

P4: evaluate Skill triggering, answering, refusal for stale API and official source lookup with representative tasks. P5: test actual auto-loading on Claude Code, Codex, Pi Agent and ChatGPT, including multiple installed versions. P6: distribute signed/reviewed packages and support rollback; P7: optionally add a read-only live documentation MCP.

**Do not install these generated packages automatically into existing user-level Agent configurations**: the packages are ready for explicit host testing and review, but the current P3 build does not prove those host acceptance steps.
