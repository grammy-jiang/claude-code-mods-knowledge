# P6 release readiness — fail-closed host and ChatGPT evidence

This is a **read-only** release-eligibility assessment. It neither runs an AI model nor publishes a GitHub Release.

## Required acceptance gates

- Compiler and source: valid SSOT approvals, exact Claude Code CLI 2.1.296 scope, reproducible ZIP/source manifest, matching full Git SHA.
- **Chat mode**: all 46 P4 cases completed in distinct, actual ChatGPT ordinary Chat conversations; 46 passes with independent technical review; correct Plugin resource reads for all positive/boundary cases; no read for unrelated negative cases. Explicit `@plugin` controls never count as automatic-loading successes.
- **Three Agent models**: real, independently evidenced Claude Code, Codex and Pi Agent model turns; native Skill discovered; positive, negative and boundary cases per host; source/version and answer quality verified. A native loader or static lint pass is not inference.
- **Account installation and rollback**: the exact target Plugin ZIP installed and enabled in Chat, bundled Skill enabled, successful rollback, hash-linked evidence.
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
  --out /tmp/mods-stable-readiness.json --require-ready
```

- Exit **0** with all checks passed: `READY_FOR_STABLE_RELEASE` eligibility (not an actual publication).
- Exit **3**: package is valid but P4/P5/account evidence is missing or failing; report status `STABLE_RELEASE_BLOCKED`.
- Exit **2**: tampered/unsupported compiler build or invalid input.
- Omit optional evidence files for a safe *inspection*: each missing category blocks rather than fabricates a pass. Without `--require-ready`, a generated inspection report uses exit 0 even when blocked.

The evaluator checks distinct hashed conversations and host evidence across cases, automatic versus explicit routing, target versions, manual review and rollback ZIP equality. It cannot independently authenticate the origin of fabricated JSON: primary logs still require a trusted human/operator audit in a private workspace.

## Current facts

The released account Plugin is `v0.2.0-beta.1` (26 Claims at that release's source), while main contains 29 approved Claims. Earlier 46-case Beta.1 Chat mode quality was **15 pass / 25 fail / 6 inconclusive**. A research two-Skill preview is under full Chat-mode test and must not be considered a production release. Real Codex model tests became possible after its quota check recovered, but all host categories remain incomplete. Thus the current stable gate is **blocked**.

OpenAI documents model-mediated Skills selection at https://developers.openai.com/plugins/concepts/skills and requires positive, negative, boundary and repeat consistency tests at https://developers.openai.com/plugins/deploy/connect-chatgpt.
