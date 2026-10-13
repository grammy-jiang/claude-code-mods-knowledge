# P4/P5 — ChatGPT Plugin Model-Free Evaluation and Installation

Date: 2026-10-14 (Australia/Sydney). Scope: personal, **skills-only** ChatGPT Plugin, official Claude Code Mods guidance restricted to CLI 2.1.296.

## Evidence levels (must not be conflated)

| Level | What it proves | Current result |
|---|---|---|
| 1. Source and Claim validation | Source IDs, pinned official document sections, state, versions | Passed |
| 2. P4 resource suite | 46 prompts have supporting approved resource references / matching version guards | 46/46 static pass |
| 3. ZIP/package scan | Secure ZIP names, no code/MCP/hooks, stable references and correct checksums | Passed |
| 4. Independent hosts | Python tests + P4/P5 package verification from three machines | Run `bash scripts/p5_model_free_check.sh HOST_ID` on each |
| 5. Personal local marketplace | Plugin source staged and accepted by package manager | Installation state recorded separately |
| 6. ChatGPT Chat-mode account runtime | Plugin visible, enabled, selected or auto-activated and produced appropriate responses | **7 actual Chat-mode observations (3 structural pass, 4 fail); full suite incomplete** |

Passing any earlier level **does not imply** passing a later one.

## Model-free P4

```sh
uv sync --locked
uv run mods-knowledge eval --suite evals/p4_cases.json \
  --report /tmp/claude-mods-p4-static.json
uv run mods-knowledge build --api-version 2.1.296 --surface cli \
  --package-version 0.2.0-beta.1
uv run mods-knowledge package-check --dist dist
```

The P4 suite has 46 realistic scenarios: 30 positive/multi-domain, 8 negative unrelated requests, and 8 version/security boundary conditions. Static tests confirm that approved K IDs and first-party source links appear in the right reference pages, and verify that the Skill is scoped to Claude Code Mods. **They do not run a model**. The evaluator intentionally leaves all 46 host rows marked `not_run` and never reports activation accuracy.

An installed ChatGPT Plugin test should additionally check the user-visible response and whether the Skill was actually loaded: direct/indirect activation, negative non-activation, source/claim citation and safety, version abstention, and follow-up continuity. Save actual results in a separate redacted Chat-mode evidence record, not by editing the P4 static report.

## P5: three independent machines without AI agent model tokens

For MacBook Pro, Raspberry Pi and sextant respectively, in a clean checkout of the same Git commit:

```sh
bash scripts/p5_model_free_check.sh macbook
bash scripts/p5_model_free_check.sh raspberrypi
bash scripts/p5_model_free_check.sh sextant
```

The script only runs Python, Ruff, the static evaluation, a deterministic compiler and ZIP/manifest validation. It **does not run Claude Code, Codex, Pi Agent or ChatGPT models**. It records `/tmp/mods-p5-HOST/P5-HOST.json` with source Git SHA, Python version, platform architecture, unit-test count, P4 resource count, and plugin/Skill ZIP checksums. Compare SHA-256 across machines. It does not change existing global Skills or restart services.

## Personal Marketplace installation

OpenAI's local Plugin Marketplace supports skills-only packages without an MCP server. On a Mac with ChatGPT desktop app installed:

```sh
cd ~/Projects/claude-code-mods-knowledge
uv run mods-knowledge package-check --dist dist
# Dry-run with no account file changes:
uv run mods-knowledge marketplace-stage --dist dist
# With approval to set up the personal local source:
uv run mods-knowledge marketplace-stage --dist dist --apply
```

The staging command writes `~/.codex/plugins/claude-code-mods-knowledge` and a catalog entry in `~/.agents/plugins/marketplace.json`. It preserves pre-existing unrelated entries, detects tampered/manually modified owned payloads, and does **not** mark the plugin as installed or activated in ChatGPT.

The MacBook local package manager may then require adding the personal marketplace and installing the plugin. Its use in package-management-only mode does not issue an AI/model request:

```sh
codex plugin marketplace add ~/.  # use the actual home directory root as the marketplace root
codex plugin list
codex plugin add claude-code-mods-knowledge@mods-knowledge-local --json
codex plugin list
```

The directory `~/.codex/plugins/cache/mods-knowledge-local/claude-code-mods-knowledge/local/` is the expected installed local cache if the manager accepts this source. The account-level plugin was separately uploaded and enabled through the authenticated ChatGPT Chat-mode client on Raspberry Pi. If the desktop app is not available or UI automation is denied, record `host_runtime_not_verified`; do not fabricate an evaluation result.

**Important:** Desktop marketplace sources are local to that Mac; staging/installing there is not proof the Plugin is available on the user's iPhone or a different ChatGPT account surface. Account-level plugin upload has now been verified independently through the authenticated Raspberry Pi ChatGPT client.

### Verify in ChatGPT Chat mode when available

Open the Mac ChatGPT app's Plugins Directory, select the personal marketplace, confirm `Claude Mods Knowledge` is present and enabled, then start a *new Chat-mode chat* with `@claude-code-mods-knowledge`. Run representative prompts from `evals/p4_cases.json`, including an unrelated request and one for unsupported Claude Code 2.1.310. Record whether the bundled Skill loaded, which K source IDs were given, whether it abstained on unsupported versions, and whether it refused untrusted/historical instructions. The app UI may require a manual selection; never assert it happened based on a ZIP on disk.

## P6: private, auditable release candidate

Public Plugins Directory submission is intentionally out of scope: this is a private knowledge Skill, and the public review/verification process should not be initiated without a separate product/publication decision.

Use the same commit on all three hosts, then on a clean Mac main checkout:

```sh
SHA=$(git rev-parse HEAD)
uv run mods-knowledge build --api-version 2.1.296 --surface cli \
  --package-version 0.2.0-beta.1 --source-revision "$SHA"
uv run mods-knowledge package-check --dist dist
uv run mods-knowledge release --dist dist --out release/v0.2.0-beta.1 \
  --source-revision "$SHA" --tag v0.2.0-beta.1 \
  --host-matrix release/p5_host_matrix_final.json
uv run mods-knowledge release-verify --dir release/v0.2.0-beta.1
```

The private release bundles include five ZIPs: ChatGPT Plugin, generic Skill, Claude Code Skill, Codex Skill, and Pi Agent Skill. They are accompanied by provenance/SBOM, a P4 static report, a P5 host evidence matrix, release notes/manifest and SHA256SUMS. The tag remains a `-beta` prerelease until automatic routing and all 46 Chat-mode model cases pass; explicit activation was verified, but full evaluation remains incomplete. The release archive does not collect credentials or launch agents.

## Rollback

The previous release remains available in the private GitHub releases. To revert the local installation, use the plugin manager to remove **only** `claude-code-mods-knowledge@mods-knowledge-local`, restore a previous tagged release's plugin source directory, and reinstall. The `~/.agents/plugins/mods-knowledge-install.json` marker protects managed local writes; don't delete unrelated marketplace entries or modify unrelated Codex settings. The Git repository and source registry are not changed during an installation rollback.

### Install or update directly in the ChatGPT account (Chat mode)

The Raspberry Pi has a dedicated, already authenticated ChatGPT browser and the owner-maintained `chatgpt-web-operations` Skill. This is the tested pathway for **account-level** deployment rather than only Mac's local Marketplace cache. Upload a release ZIP from the `dist/packages` directory through:

```sh
S=~/.claude/skills/chatgpt-web-operations/scripts
python3 "$S/preflight.py" --browser
python3 "$S/manage_plugins.py" list
python3 "$S/manage_plugins.py" update claude-code-mods-knowledge \
  dist/packages/claude-code-mods-knowledge-0.2.0-beta.1.zip
python3 "$S/manage_plugins.py" update claude-code-mods-knowledge \
  dist/packages/claude-code-mods-knowledge-0.2.0-beta.1.zip --apply
python3 "$S/manage_plugins.py" show claude-code-mods-knowledge
```

For first-time deployment use `manage_plugins.py upload ARCHIVE --install` instead of `update`. A successful `show` verifies account-level installation/enablement, **not** actual auto-triggering. Start a **new ordinary Chat conversation** (Chat toggle, not Work), explicitly select `@claude-code-mods-knowledge` for one regression test and test a second time without explicit selection. Read actual conversation metadata: look for `api_tool.read_resource` with the expected `skill_plugin_id` and `invoked_resource` URIs; score replies against reviewed Claims, including `K-0031` full callback arguments. Save only hashes and resource URIs in the release QA matrix, not raw conversation text.
