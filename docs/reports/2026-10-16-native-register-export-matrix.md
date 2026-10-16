# K-0038: native Claude Code Mod registration export shapes

**2026-10-16, Australia/Sydney. Scope: Claude Code CLI `2.1.296` on MacBook Pro, no model-origin code execution.**

## Why this source correction was necessary

A controlled **ordinary ChatGPT Chat Mode** experiment temporarily installed private Plugin `0.3.3-beta.3` built from source reviewed for CLI 2.1.296. Mac Codex used the installed Agent Communication Skill to send three **new** frozen prompts, stopped after the second one failed a semantic acceptance gate, and the outer owner restored and independently verified the original published `v0.2.0-beta.1` account Plugin. The other ten personal Plugin states were unchanged. No ChatGPT Work Mode task was counted.

The two actually sent Chat cases `POS-E-01` and `POS-E-ASYNC-LOGGER` both returned an exact `FINAL_VERIFIED` (GPT-6 Thinking / Standard) and used the real correctly scoped Plugin Skill (4 and 5 `api_tool.read_resource` messages). Their cited approved Claims had **9/9** and **11/11** exact first-party source links respectively. The initial transparent observer's recommended fail-isolated logging looked sound on manual inspection, but its reply also included a clearly labeled unsafe *counterexample*, so the earlier conservative lint flagged code despite the negative context; it remains **REVIEW_NEEDED**, not native-certified. In the second answer the model's inline implementation handled async diagnostic rejection, but an offered downloadable entry point was described as a standard Mod while using the syntactically indirect `export const register = createRegister()` initializer. The original downloadable artifact was **not** independently recovered byte-for-byte or executed on Mac; the observed source shape was audited in the canonical response. Accordingly this answer failed the requested registered-function artifact contract. The third `BOUND-INJECTION` case was **NOT SENT** because the fail-stop gate fired; it must not be counted as a tested refusal.

Previously approved **K-0032** said the register module *must* use the literal `export function register(on)` form. Official first-party [M003: reference/Files](https://code.claude.com/docs/en/plugins/mods/reference#files) presents that conventional named entry. It does not itself establish that no other named function expression can work. The target CLI's actual loader evidence is more nuanced.

## Independent Mac CLI 2.1.296 experiment

Seven **assistant-authored, disposable** isolated Mods shared an identical safe `tool.call` transparent callback and `.test.ts` that mocked a Read tool. None ran model-origin JavaScript, touched a real file, network, Chrome account, secrets, or user Plugin.

| Hook registration source | `claude plugin validate --strict <mod>` | `claude plugin test <mod>` |
| --- | --- | --- |
| `export function register(on) { ... }` | **PASS** | **1 pass, 0 fail** |
| `export const register = (on) => { ... }` | **PASS** | **1 pass, 0 fail** |
| `export const register = async (on) => { ... }` | **PASS** | **1 pass, 0 fail** |
| `export const register = function(on) { ... }` | **PASS** | **1 pass, 0 fail** |
| `const register = (on) => ...; export { register };` | **PASS** | **1 pass, 0 fail** |
| `export const register = createRegister()` | **FAIL** | **FAIL** |
| `const fn = (on) => ...; export const register = fn` | **FAIL** | **FAIL** |

The two rejected shapes caused the native validator to report that `register` was exported as something other than a const function, and the native test runner failed to load their hooks. This is independent evidence of which source forms are admitted **on this target version only**. There is no claim that all possible alternate function or TypeScript compiled source shapes were exhaustively tested.

## Single Source of Truth and deterministic checks

The original K-0032 approval is not rewritten: a third SHA-linked, AI-attributed lifecycle event marks **K-0032 deprecated**, and new **K-0038** (`mods.types.static-discoverable-registration-export`) is separately `candidate -> reviewed -> approved` with two SHA-linked events. K-0038 `supersedes: [K-0032]`, uses the already-pinned official M003 `#files` URL for the basic documented named entry, and attributes broader syntax observations to the above independently executed native checks—not to claims allegedly spelled out by the official reference.

Only active approved **K-0038** is selected by the central compiler into portable Skills and `references/types.md` for ChatGPT, Claude Code, Codex and Pi Agent. A bounded answer-risk linter now flags recommended factory/indirect alias `register` exports (and treats explicitly labeled wrong examples as manual review only), while it does **not** incorrectly reject native-tested direct arrow/function expressions or local `export { register }`.

The repository now has **31 active approved Claims, 5 candidates and 2 deprecated Claims (K-0032 and K-0036)**. The published personal Plugin remains `v0.2.0-beta.1`, which contains an earlier smaller knowledge set; neither retiring K-0032 nor merging source code silently changes the installed account package. The registration update requires a *new* versioned Chat Mode candidate, source ZIP account read-back and genuine code-quality QA before it can be promoted. A passing static/mock native loader is not sufficient to certify the model-generated artifact.

**Disposition: P4 semantic acceptance OPEN; P5 real model/host matrix OPEN; P6 stable release BLOCKED.** Do not erase or move Git history to alter private chat references without coordinated authorization. Public audit contains no personal Chat/Project/Plugin IDs, private replies or credentials.
