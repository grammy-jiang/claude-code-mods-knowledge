# P5 first native medium/default-model case evidence (sanitized)

2026-10-16 Sydney. This report records **real native model attempts**,
not full P5 host acceptance and not a stable release gate.

## Sources and boundaries

- Repository merged baseline: d3db512 (PR #49), reviewed installed Skill
  source SHA: 6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e.
- Four frozen case IDs come from evals/p4_cases.json; exact source-file SHA256:
  a5bc6c89f993772dc324d323617bb98cf9f5709bd5af9b903f86f320cad0b8bb.
- Mac native Codex CLI 0.163.0, explicit gpt-6.1-sol/medium, ephemeral
  read-only execution. Native model/list supports this exact requested model
  and effort; exec JSONL does not independently confirm resolved identity.
- Mac Pi Agent 1.3.0, the preconfigured local mac-qwen/qwen36-35b-a3b-mtp
  with off thinking (model does not support a thinking level). Actual Pi
  message_end provider/model fields independently matched on all four cases.
- Mac Claude Code auth restored; Claude inference was **not** invoked due
  to exhausted Claude quota. Installed CLI is 2.1.301, source-scoped
  Claims remain qualified for CLI 2.1.296.
- Private native traces, prompts, model replies and generated artifact bytes
  remain in private local test storage. This report contains only IDs,
  statuses, metadata and SHA256 checksums.

## First four-case real model cohort

| Case | Codex command/read | Pi command/read | Status |
| --- | --- | --- | --- |
| POS-E-01 | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read true | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read true | Two Codex and two Pi original generated JS snippets independently passed strict CLI 2.1.296 validate and a benign native mock (details below); full semantics unverified. |
| NEG-TYPESCRIPT | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read false | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read false | Initial empty workspace was an invalid ordinary-TypeScript fixture; Pi ended in model error after 58 read attempts. This is not evidence of Mods Skill false activation. |
| POS-Q-01 | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read true | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read true | Both models read relevant Skill and returned directory-style offline test advice; native no-arg test current-directory default was separately confirmed in 2.1.301 CLI help. Full source/semantic review pending. |
| BOUND-VERSION-NEW | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read true | COMMAND_OK_SEMANTICS_UNREVIEWED; Mods read true | Both read Mods Skill; Codex cautiously marked 2.1.310 unverified; Pi mixed scoped legacy API facts and an explicit newer-version disclaimer; independent boundary review pending. |

### Raw-event integrity hashes (private content not distributed)

| Case | Codex JSONL SHA256 | Pi JSONL SHA256 |
| --- | --- | --- |
| POS-E-01 | 2eb0cde9bb1f7da9cac51de46927d812697f01b40972d8d1f28ebe1baa0d2847 | 1e33b0c51b02d4e1fe35d92d48abeed0c93de7025f8e888ae6d35d5b24bcbf82 |
| NEG-TYPESCRIPT | 1f2cebc2e90a3baf9f448198be47c2cedd4b1102409ce4627812ac455706e806 | 66744cc6c6f6b453a01d5c1951f665a84561ac9baf1ef0aeb77e849b80741526 |
| POS-Q-01 | 08fcdbc01c058eb17fef7540f94875ccd01014e8b784232bb4be9742d8d7ecf8 | ed0e691cfa33b09268950c7b17e9605d9760d3b6d6b2e916fde800d42ef91917 |
| BOUND-VERSION-NEW | a77929c96623b1c489cdf0eaffa4be76814e494da36ce1e7ede3cb82d3d67b93 | f641e45b63962cfa347b58bc4b4ecc06d238e8a7484c79543f446ae015a7d30d |

## Corrected negative-control test environment

After the initial no-project negative run, a separate safe, ordinary
TypeScript mini-project was created with overloaded generic functions.
The original prompt was unchanged. The results are kept as separate
cohorts rather than silently replacing the original attempts.

| Control | Result | Mods Skill read | Interpretation |
| --- | --- | --- | --- |
| Codex read-only | EXIT_0, 22.03 s | false | Completed a normal TypeScript recommendation; no Mods Skill read. |
| Pi read only (no file discovery) | TIMEOUT, 125.14 s | false | 74 attempted read calls; 71 native tool error flags, repeated directory reads; hit 125-second timeout. Artificially limiting a repository-inspection task to read without ls/find/grep is not valid standard-user acceptance. |
| Pi read + ls/find/grep (read-only discovery) | EXIT_0, 21.0 s | false | Completed in 21 seconds, returned TypeScript-specific recommendations, no Mods Skill read. The runaway loop was resolved by supplying normal read-only discovery tools. |

## Original model-generated Mod code tested against exact target CLI

The two self-contained named register snippets from each POS-E-01
model response were independently extracted, manually inspected for
dangerous side effects and placed into disposable, source-controlled
synthetic Mod fixtures. Exact retained native CLI **2.1.296** was
verified before invocation. Each was validated using native strict
plugin validation and the fixture native tool.call mocked test.

| Agent | Model-origin snippet | JS SHA256 | Strict 2.1.296 | Native mock |
| --- | --- | --- | --- | --- |
| Codex | minimal passthrough | f87407e6b732e345d2884c9513947573f75e8429e53a08263272ac6c9ab69647 | 0 | 1/1 pass |
| Codex | guarded finally diagnostic | bc734e31ecd1d5ed0208e83a647162aae50a21e5e4bdf212a67b3174739f63e5 | 0 | 1/1 pass |
| Pi | minimal passthrough | 11eec5ae1d989e4355e9a44dfcbf9fbd9c520f67b352548a4884afa8508ac279 | 0 | 1/1 pass |
| Pi | logging diagnostic | eb5dc1575a6c1f8c3a7b4f2244ad6af87828236da89c602776f70a556cc81518 | 0 | 1/1 pass |

These are **real model-origin code** checks, but the synthetic native mock
does not prove downstream rejection identity or actual production Mod
event integration. Pi logging guidance still needs independent review:
awaiting a synchronous console.log does not itself demonstrate handling
an independently rejecting asynchronous logger. A mock PASS must not
erase that semantic limitation.

## Readiness decision

**PARTIAL — P5 #3 remains OPEN.** Authentication and CLI discovery are
complete; first local Codex/Pi medium/default model cohort and four
model-generated safe native smoke tests were executed. Remaining:
independent exact Claim/source anchors and full semantic qualification,
observed Codex model provenance, production CLI event path, cross-device
acceptance and Claude Sonnet after quota reset. P4 and stable P6 remain
separately blocked.
