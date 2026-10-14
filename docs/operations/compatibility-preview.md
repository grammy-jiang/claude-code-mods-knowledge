# Opt-in, nonpublishable compatibility routing Skill

Use `mods-knowledge preview-compat-build` for an **experimental** second ChatGPT Skill named `claude-mods-compatibility`. It is generated from the same five approved first-party SSOT Claims (K-0015, K-0016, K-0023, K-0026, K-0030) and previously generated official reference documents. It does not edit the canonical Claude Code, Codex, Pi Agent or ChatGPT development Skill bytes and never installs plugins or calls AI models.

```sh
uv sync --locked
uv run mods-knowledge preview-compat-build \
  --api-version 2.1.296 --surface cli \
  --package-version 0.2.0-preview.1 \
  --source-revision "$(git rev-parse HEAD)" \
  --out dist-preview
uv run mods-knowledge preview-compat-verify --dist dist-preview
```

The preview's version must have suffix -preview.N. Its manifest explicitly sets `preview_extension.publishable=false`. The standard release/package validator rejects additional unapproved Skills; the dedicated preview verifier checks exact byte reproducibility and ZIP member safety. Output is Git-ignored and existing output directories are not overwritten.

A separate **hand-built prototype** (not this exact compiler output) was tested in 48 real Chat mode conversations: two-Skill boundary auto-loading 7/16 versus single-Skill control 3/16. Both variants had 0/4 irrelevant-task false activations. These small nonrandomized results are not proof of stable routing improvement, and some loaded replies still contain unverified API/host details. See [A/B summary](../reports/2026-10-14-multiskill-routing-a-b.md).

Do not install this preview in the owner's ChatGPT account or publish it as a GitHub Release until its **exact generated** package undergoes separate Chat-mode and security acceptance. The account currently uses published v0.2.0-beta.1.
