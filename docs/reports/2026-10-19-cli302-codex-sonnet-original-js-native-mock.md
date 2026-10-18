# P5: actual Codex/Sonnet observer code in native CLI 2.1.302 sandbox

Date: 2026-10-19 Sydney. Reviewed host version Claude Code CLI 2.1.302.
This is genuine ORIGINAL model-origin code in networkless OS isolation,
not fresh model inference and not production user-tool execution.

## Provenance: five exact native model code blocks

The model code blocks are byte-for-byte copies of the original answers,
with individually pinned SHA256 fingerprints and source full-answer/wire
SHA256 identity in evals/fixtures/p5-native-model-code-302/manifest.json.
No private chat transcripts, model prompts, credentials or real local
host paths are included.

- Native Codex gpt-6.1-sol, requested Medium: 2 complete register(on)
  modules from one successful POS-E-01 native answer.
- Native Claude Code Sonnet 5.5, requested Medium: 1 complete module and
  2 bare tool.call fragments from POS-E-01. The fragments are NOT
  installable without an explicit synthetic register(on) wrapper.
- Sonnet POS-Q-01 also included a sample shell invocation for native
  plugin testing. That was NOT treated as code, executed, or assessed as
  a Mod module.

All code SHA256 values matched and the tested files contained only
locally reviewed tool.call event pass-through/logging code.

## Tier 1: actual Node and synthetic next(e) behavior

Within a Linux Bubblewrap namespace on Raspberry Pi 5 using native
Node 24.19.0:

- 5/5 JavaScript syntax checks passed, including the two distinctly
  documented Sonnet wrapper adapters.
- 48/48 trusted synthetic event/middleware contract tests passed:
  exact original result object/primitive identity, exact event object,
  single next(e), synchronous and asynchronous original exception
  preservation, and both synchronous and rejected-Promise logger
  error isolation.
- A deliberately WRONG observer that fabricated a new downstream
  result failed 9 tests, proving the harness catches this defect.

All model code execution was inside an unprivileged OS namespace with
no original host Home or external network access. No model or user
tool request was issued.

## Tier 2: genuine Claude Code CLI 2.1.302 Mod mock testing

The actual native ARM64 Claude Code CLI 2.1.302 binary was mounted
read-only INSIDE a second Bubblewrap sandbox with no host Home,
credentials or network. The five vetted observer candidates were
placed into disposable native Mod folders with the required
plugin/hook manifests. The two Sonnet fragments had their clearly
labeled TEST-ONLY wrappers; they are not original complete modules.

For each of the five candidates:

- Native plugin validate --strict: **5/5 PASS**.
- Native plugin test: **10/10 PASS, zero fail** in total (two tests
  per candidate). The test kit uses mocked Read tool calls only,
  verifying both the returned tool result value and a mocked
  permission-denial result/isError flag remain unchanged.
- Deliberately corrupted observer replacing the result was rejected
  by the actual native plugin test kit; strict validation alone
  would not constitute semantic approval.

The native test kit did NOT execute actual user Bash, Read, disk
modifications, external model calls, web/API accesses or permission
requests. All tested Mod hooks and test files resided solely in an
isolated disposable private workspace, never an installed user Mod.

## Limitations: do not silently promote to Stable

These are authentic version-specific native MOCK tests but DO NOT
establish full interactive session permissions, real user tool
semantics, all concurrency/error behavior, arbitrary code in a
full model answer, or production model-generated Mod deployment.
Actual CLI 2.1.302 generated TypeScript declaration type-checking
has NOT been completed; the approved source/CodeX native source
references remain a separate review requirement.

The current Chat Mode 46-question full run, the historical P4 strict
8/8 boundary requirement (observed 6/8), complete three-host native
inference and any production Stable Release remain HOLD.

The separate Agent Communication project is outside this QA.
