# Claude Code 2.1.303 / 2.1.304 — official source and native preapproval

Date: 2026-10-20 Sydney. **Release status: NOT APPROVED for published
Skills, ChatGPT Plugin, or Stable.** This record preserves first-party
version evidence without modifying any approved 2.1.302 Claim or P4/P5/P6
release gate.

## Official upstream releases

Anthropic's own GitHub Releases API provides:

- [v2.1.303](https://github.com/anthropics/claude-code/releases/tag/v2.1.303),
  published 2026-10-18 UTC. Official release-body SHA256
  dd490d3f4e93c8165c0322324024d1202fe097b1be5a232b6035fd40bfee97cc.
  Its generic reliability note does NOT prove API identity to 2.1.302.
- [v2.1.304](https://github.com/anthropics/claude-code/releases/tag/v2.1.304),
  published 2026-10-19 UTC. Official release-body SHA256
  7a6144fde0e5e4733c1108e1890430722c12839159aeb1a5be7bec8aaa881cf8.

The four original 304 release bullets relevant to Claude Mods are
separately SHA-pinned in the adjoining evidence JSON: tool.check
read-only input metadata, human-only permission ask verdict,
skip-hook transcript visibility, and failed-Mod-reload recovery.
These source facts do NOT by themselves approve full API compatibility.

## Native target binary and TypeScript evidence

The official 2.1.304 Linux ARM64 GitHub release tarball was downloaded
to a private temporary directory only and checked against its first-party
asset SHA256:

- Release archive SHA256:
  17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5
- One native executable, SHA256:
  c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3
- That executable reported version 2.1.304 INSIDE a networkless
  Linux Bubblewrap sandbox. It was never installed for the user's
  ordinary sessions.
- Its independently extracted native core TypeScript declaration:
  661,289 bytes, SHA256
  6694767741c445872577d96a55fb08816d0f4b5783bc49e1eacd55f27b383308.
- The reviewed 2.1.302 core source SHA256:
  8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e.

The exact native core types differ in the permission checking API.
In 2.1.302, ToolCheckInput has no isReadOnly member and
ToolCheckDecider accepts only host. In 2.1.304 the input has optional
isReadOnly of literal type true, and the result's decider may be
host or person. The SAME compiled TypeScript source (SHA256
d103f782bea523878d6978354498c25111c1384df60a9d37cb9be83e32c80884)
was rejected by strict TypeScript 6.0.3 against 2.1.302 but passed
against native 2.1.304 core types. No upstream full declaration text
was committed or exposed to the user.

## Actual native permission and compatibility MOCK results

All execution was done on a Raspberry Pi using the official 304
native executable inside Bubblewrap, with no host Home, network,
credentials, account, model request, or real user files mounted.
Synthetic tool-checking code was used, NOT a real permission prompt:

- Native 304 strict plugin validation: PASS.
- Native 304 mocked permission checks: 4/4 PASS. The reviewed
  synthetic hook leaves mocked read-only asks unchanged, routes a
  mocked Write ask to person, preserves denial, and catches a
  deliberately thrown gating exception by refusing the call.
- Strict validation reported an explicit gating hook WITH a catch,
  rather than accepting an unguarded failure path.
- Five individually SHA-pinned original 302 Codex/Sonnet model code
  candidates were revalidated against native 304: 5/5 strict Mod
  validations and 10/10 mocked Read/denial tests PASS, with an
  intentionally result-replacing observer correctly rejected.
  This proves only the tested compatibility subset.

These results are stronger than a release announcement, but STILL DO
NOT validate real human approval dialogs, host permission callbacks,
all generated built-in-tool schemas, or every existing 2.1.302 Claim
under 2.1.304.

## Version/Skill guardrails and deployment blockers

The MacBook Pro and sextant remain on Claude Code 2.1.302; Raspberry
Pi currently runs CLI 2.1.303. Local Skill 0.4.13-beta.1 was synchronized
across all three with original rollback copies. That Skill remains
REVIEWED ONLY for CLI 2.1.302: it must NOT be presented as approved
for CLI 2.1.303/304.

The original Pi 302 model runner was actually executed against native
CLI 2.1.303 and refused before any network health probe or model
inference. The compiler and model gate also reject 2.1.303/304 targets
until reviewed Claims and host acceptance are added.

The Pi local ChatGPT website Plugin management interface returned
HTTP 401. This is an authentication blocker and not proof that the
account currently has beta013 installed. No blind retry or write to
that account was made. The Qwen provider backend remains offline,
with Mac Swap above the existing resource guard, so no new unsafe
Qwen inference was attempted.

## Required next release work

Review each approved 2.1.302 Claim against up-to-date first-party
2.1.304 docs and the actual target native types, including permission
precedence, failure catch paths, agent and read-only distinctions.
Add new Claim IDs and decision provenance rather than silently
changing old version scopes. Run real natural P5 model+Skill cases,
then build and install a SEPARATE reviewed 304 candidate with
ChatGPT account readback and safe rollback.

The strict original P4 eight-boundary Plugin activation result
remains 6/8 FAIL, and full current 46-case Chat Mode qualification,
P5 full host semantics, and P6 Stable eligibility remain HOLD.
The separate Agent Communication project is out of scope.
