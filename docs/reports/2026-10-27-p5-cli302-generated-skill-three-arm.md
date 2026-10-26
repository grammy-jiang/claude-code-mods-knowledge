# P5 — CLI302 approved generated Mods Skill, real Sonnet model three-arm QA

**Date:** 2026-10-27 (Australia/Sydney). **Status:** genuine native QA evidence with an important **FAIL** in opening Evidence completeness; no full P5/Stable PASS.
**Git source revision of compiled Skill:** 814bbdaf385feac5d8f022ff8615991a42038ff7 (before WIP audit enhancements).
**Test scope:** one factual observation-only tool.call hook task on an actual installed Claude Code CLI 2.1.302 and one explicit version-mismatch turn on official native CLI 2.1.309. This is **not** a cross-model 3-agent acceptance result.

## Why this exists

The old audit_claim_source_links checker ensures cited Claims have approved exact official first-party URLs **somewhere** in a reply. The compiled Skill explicitly requires a stronger contract: start with Evidence, then Scope, then Answer, and place **each cited K-Claim and its own exact official URL** on a separate opening Evidence line.

This is not cosmetic. A model reply can pass old structural coverage even when the Evidence list is missing some of the Claims used in its body. The new audit_claim_evidence_section checks this additional rule without conflating URL structure with executable Mod correctness or native model invocation.

## Real original native model cohorts

| Case | Native model and actual source | Native Skill/Read trace | Outcome |
| --- | --- | --- | --- |
| skill302 | Claude Code CLI 2.1.302 / real Sonnet 5.5; reviewed generated CLI302 Skill with 31 approved Claims | One real Skill call, then real Read of events and claim-evidence reference files; no read errors | Eight Claims used; all exact official URLs present somewhere, but Evidence misses K-0041 and K-0067. **Quality FAIL**. |
| baseline302 | Same target CLI302/Sonnet, same operator-owned prompt file, test folder with no project-local Skill | No Skill invocation; one attempted Read produced an error | Zero Claim IDs and zero accepted official URLs; fails source quality. The Read failure means this is **not** a perfectly matched A/B control. |
| mismatch309 | Exact SHA-pinned official CLI309 / Sonnet 5.5, with the historical CLI302 Skill still discoverable | Real Skill call and Read of both reference files, no errors | Explicitly identifies mismatch and declines to guarantee any approved CLI309 behavior. **Narrow history firewall PASS**, not 309 compatibility approval. |

The generated local Skill has SHA256 619787ebd651b572fc8014526d4b283501db882528f56d76920ddda5a92ca42a. Both target reference files are SHA-pinned in the public evidence. An independent genuine native binary SHA is recorded for both CLI302 and CLI309. There was no installation into a global user Skill directory and no production account/plugin changes.

### Findings: original 302 Skill answer

- Actual native Skill tool use and both required reference Read operations occurred. The model was genuinely Sonnet 5.5 according to original native modelUsage, not just requested in a CLI flag.
- Old anywhere-in-reply direct-first-party Claim URL checker: **PASS**.
- New opening Evidence per-Claim exact link checker: **FAIL**. The reply cites 8 approved Claims but its Evidence list contains exact locators for only 6; K-0041 and K-0067 appear in body without their own opening Evidence lines.
- Narrow code risk signals and manual review flags: none. That is **not** a typecheck, actual runtime test or proof of semantic correctness.
- Scoped QA can say the Skill helped this answer use approved references, but may **not** say overall model correctness was proven or that an API generated code sample is production safe.

### Findings: no-Skill control

The no-Skill CLI302 arm finished a real Sonnet turn but failed one Read request for missing local evidence. That failure is retained as an unequal-source condition. It offered no verifiable approved Claim ID or direct Mods source URL for this task. This supports only a **bounded sample** difference, not a 100% Skill uplift, no-tool baseline, or identical retrieval condition.

### Findings: CLI309 against a historical CLI302 Skill

The real native CLI309 process genuinely loaded the old Skill and read references, then explicitly said its approved assertions were limited to CLI302 and refused to claim they had been validated on CLI309. This is a **version-boundary behavior check**, not a new approved CLI309 Claim.

## Original artifacts and deterministic QA

The original full model text, prompts, private paths, IDs and native stream-json/debug are retained in a restricted Sextant local QA directory. The independent auditor scripts/audit_p5_cli302_generated_skill_cohort.py replayed all three original streams twice, producing identical SHA-bound sanitized reports. Public evidence is in docs/reports/2026-10-27-p5-cli302-generated-skill-three-arm-evidence.json.

The source checker implementation is in src/mods_knowledge/claim_source_link_coverage.py. Focused deterministic regression tests in tests/test_claim_evidence_section_coverage.py cover:

1. Correct opening Evidence/Scope/Answer order and per-Claim direct anchor PASS.
2. A real-like reply where exact URLs occur in the body but not in opening Evidence.
3. Wrong anchor on the same official page.
4. Intro before Evidence, duplicated/wrong section order and multi-Claim lines.
5. CLI309 source-scope mismatch and malformed/oversized input fail-closed.

CI validates public sanitized original SHA provenance, exact Claim outcome and absence of private account artifacts. CI cannot redo authenticated inference without the user-only raw original records. No original model text, session ID or credentials may enter Git.

## Explicit release boundary

CLI 2.1.302: 31 approved, version-limited Claims unchanged. CLI 2.1.309 and current latest 2.1.310: 0 approved Claims. None of the evidence in this report promotes any Claim or authorizes 309/310 Skills/Plugin publication.

**P5 remains OPEN**, while complete Codex/Pi Agent current-approved-target/model QA, native runnable Mod correctness and ChatGPT Chat Mode 46-case remain to be verified. Issue #3 captures this work. The unrelated archived cross-machine security implementation is outside scope.
