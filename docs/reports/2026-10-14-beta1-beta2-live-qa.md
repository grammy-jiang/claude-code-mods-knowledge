# Beta.1 → Beta.2 real Chat-mode regression (targeted 26-case set)

Date: 2026-10-14. This is **real ChatGPT ordinary Chat mode**, not Work or synthetic model replies. The authorized user account's own ChatGPT Plugin was installed/enabled at v0.2.0-beta.2. The main prompt texts were **unchanged** from P4; one fresh conversation per case.

## Beta.1 baseline

- Full P4 set: 46 responses; positive cases 27/30 triggered Skill; 8/8 unrelated tasks did not.
- Positive structural result: 15/30 passed, 15/30 failed.
- Exactly 3 failures were missing real Skill activation; 12 were loaded but omitted required reviewed Claim IDs and/or direct official URLs.
- 8/8 history/version/security boundary cases did not activate this Plugin, although some of the generic model replies were safe.

## Beta.2 targeted A/B

26 new real Chat conversations: **the original 15 positive failures**, **all 8 boundary cases**, and controls POS-E-01, POS-E-02 and NEG-HVAC.

| Group | Before | After |
|---|---|---|
| 15 originally failed positive cases | 0 structural PASS | **8 PASS, 7 FAIL** |
| Boundary Skill activation | 0/8 | **2/8** |
| Baseline POS-E-01 and POS-E-02 | structural PASS | PASS/PASS |
| Irrelevant HVAC task no auto-activation | PASS | PASS |

The eight recovered positives: POS-E-03, POS-S-02, POS-S-03, POS-T-02, POS-T-03, POS-T-04, MODS-UI-Q, MODS-SKILL-GUIDE. The registered Mod callback example also changed to the documented `export function register(on)` in POS-E-02.

Remaining seven: POS-Q-03, POS-P-04, POS-U-04, MODS-STATE-UI, MODS-EVENT-SEC have **no Skill resource read**; MODS-TYPE-Q and MODS-STORE-SEC loaded the Skill but omitted some expected Claim IDs. This exhibits nondeterministic host auto-routing: for example POS-Q-03 was loaded in the Beta.1 run but did not load in Beta.2, despite the changed description. A zero-load case is a routing failure, not proof the raw model answer was unsafe.

Boundary cases: BOUND-VERSION-OLD and BOUND-UNKNOWN-VERSION read the Skill; the other six did not. Structural grading for those two remains *inconclusive* pending separate semantic review. BOUND-VERSION-NEW accepted the user's “without checking docs” premise while disclaiming compatibility, so is not acceptable as verified use of the current Mods API.

## Portability blocker found before tagging Beta.2

The expanded Skill description had an unquoted YAML colon. Ruby/Psych rejected the exported SKILL.md frontmatter. Therefore **do not tag Beta.2 as a portable release**, even though ChatGPT's account uploader accepted it. The next candidate must quote the description with a JSON-compatible YAML string and make the release validator reject malformed frontmatter.

## Follow-up change under test

- Preserve all reviewed Claims and the source trust/version boundaries.
- Improve the root Plugin manifest discovery description and keywords to explicitly mention Mods tool middleware, state, UI host differences, managed permissions and old preview versions. This is routing metadata, not a new technical API assertion.
- Keep the Skill's source-derived 26-Claim lookup, source-link contract, correct module export example and real Markdown formatting.
- Retest remaining failures and unrelated negative controls on the YAML-safe package in actual Chat mode. Neither a successful ZIP parse nor a safe generic-model refusal is sufficient to assert the plugin auto-activated.

The raw conversational transcripts and credentials remain outside GitHub. Only the sanitized, test-scoped measurement summaries belong in the private repository.
