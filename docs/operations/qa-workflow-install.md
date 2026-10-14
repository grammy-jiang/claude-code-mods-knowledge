# Offline SSOT and Skill CI — enabled

**Enabled on 2026-10-14.** The model-free GitHub Actions workflow now lives at
[`.github/workflows/qa.yml`](../../.github/workflows/qa.yml) and runs on pushes
to `main`, pull requests targeting `main`, and manual `workflow_dispatch`.

The initial push from the macOS `gh` CLI was rejected because that OAuth token
had `repo` access but lacked the GitHub `workflow` scope. The user-connected
GitHub App's normal authorized repository content tool successfully created the
workflow on a separate branch and opened [PR #13](https://github.com/grammy-jiang/claude-code-mods-knowledge/pull/13).
Both matrix checks **passed on the PR and on the merged `main`**. The workflow
is not a permission bypass; its creation used an independently authorized
repository connection. Do not treat unavailable workflow permissions as
implicitly granted to other credentials.

Validation covers Python 3.11 and 3.14, Ruff lint/format, all unit tests,
SSOT registry/Claim provenance, original 14-file SHA manifests, deterministic
packaging and ZIP checksum verification. **It does not invoke AI models or
prove actual ChatGPT Chat-mode Skill activation.**

Keep the reviewed original under
[`docs/operations/qa-workflow-template.yml`](qa-workflow-template.yml)
for reference. For local, token-free verification, run:

```sh
MODS_PYTHON_VERSION=3.11 bash scripts/ci_offline.sh
MODS_PYTHON_VERSION=3.14 bash scripts/ci_offline.sh
```

[First PR workflow run](https://github.com/grammy-jiang/claude-code-mods-knowledge/actions/runs/38503128539) · [First merged-main workflow run](https://github.com/grammy-jiang/claude-code-mods-knowledge/actions/runs/38503239206)
