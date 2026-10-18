# P5 source-matched Claude Code 2.1.302 core TypeScript acceptance

Date: 2026-10-19 Sydney. Scope: reviewed CLI 2.1.302 core type declarations
and FIVE exact native Codex/Sonnet model observer code snippets. No model calls.

## First-party provenance

The installed Claude Code CLI 2.1.302 executables contain embedded Zstd
compressed core API TypeScript declaration source (651,852 bytes). Two
distinct installed binaries were independently scanned/decompressed:

- MacBook Pro binary SHA256:
  5262ce9de86243fed0d21edc39b271555d56780d0112e2b194439fe1c6662d37
- Raspberry Pi binary SHA256:
  2bd4f4e5ed5cb09955b490098f745321cb5491e7ea8c752ba1e3bb010cdadb10
- SAME core source SHA256 from both:
  8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e

The engine would add a version header when plugin loading writes its type
directory. We tested offline plugin validate/test/init, which DID NOT
generate this type directory. The safe extractor recovers the byte-exact
core source from the installed binary itself; it does NOT pull historical
2.1.277 early-access published GitHub declarations.

IMPORTANT: the core source does not include dynamically merged built-in
tool input/result tables, MCP tool schemas or dependent plugin modules
generated during a full authenticated interactive session. These are
not claimed verified. The copyrighted upstream full .d.ts stays in
private /tmp only, never public Git.

## Actual source-model TypeScript checks

Raspberry Pi ran local TypeScript 6.0.3 with strict, checkJs, noEmit,
noUncheckedIndexedAccess, ES2023 without DOM/Node global types, and the
real 2.1.302 core module declarations. All five model JavaScript bodies
were SHA-pinned to genuine original Codex/Sonnet answers. Each test-only
staged source adds a JSDoc type for the register(on) argument plus a
separate TypeScript Register structural assignment. Two bare Sonnet
fragments are enclosed in explicit TEST-ONLY register(on) wrappers.

Actual result: **2/5 ORIGINAL examples pass, 3/5 fail** with TS2584
Cannot find name console:
- Codex codex-02.mjs, a complete observer module;
- Sonnet sonnet-02 fragment, wrapped for tests only;
- Sonnet sonnet-03, a complete observer module.

The reviewed core type for a Mod hook module does not make Node/DOM
console available. It does explicitly provide the engine UI logging
API $.ui.log(text, { to: "debug" }). Replacing only the three
console.log("observer done") expressions in clearly labeled private
TEST-ONLY proposed copies makes **all 5/5 pass the same core types**.
This is NOT an alteration of the original model output, and is NOT
production host validation of those proposed edits.

Prior JavaScript syntax 5/5, synthetic next(e) behavior 48/48 and
real CLI 2.1.302 mocked Mod kit validation 5/5 / Read-denial tests
10/10 remain genuine observations, but cannot override these actual
type errors. This is precisely why separate deterministic type-check
gates are needed.

The accompanying JSON is limited to native binary/core/code SHA256
values, case names and TS error codes. No raw original model messages,
account secrets, absolute private paths or upstream full declarations
are committed. Zero model/API requests or generated-code execution.

## Still blocked

Live interactive permission semantics, dynamic full generated built-in
tool types, true current Pi Agent/Qwen inference, full latest Chat Mode
46-case acceptance, original P4 strict boundary 6/8 failure and
Stable release remain unresolved. The Agent Communication project
is outside this work.
