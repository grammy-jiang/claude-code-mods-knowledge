# P4 real ChatGPT Skill routing — factor-isolated evaluation safeguards

The public `mods_knowledge.routing_factorial.validate_routing_factorial` is an **offline evidence validator** for a six-arm experiment: published Beta.1 before/after, version-only, descriptors-only, knowledge-only and full experimental Beta.2 content. It does **not** send ChatGPT messages, install Plugins, access a browser, or guarantee Skill selection. Synthetic unit tests are **not** model acceptance. Actual experiments are in owner-authorized, ordinary Chat mode only.

## Required case/mode matrix per arm

Each arm must have exactly seven **distinct real conversations**:

| Phase | Original P4 case | Invocation mode | Eligible for automatic-routing denominator? |
| --- | --- | --- | --- |
| Early | POS-E-01 | automatic | Yes |
| Control | POS-E-01 | explicit selected Plugin | **No** |
| Late | POS-E-01 | automatic | Yes, a repeated high-risk prompt in a *new* chat |
| Late | POS-Q-01 | automatic | Yes |
| Late | POS-U-01 | automatic | Yes |
| Late | BOUND-HISTORY | automatic | Yes, boundary tracked separately |
| Late | NEG-HVAC | automatic | Yes, unrelated false-activation control |

The actual prompts must match `evals/p4_cases.json` by SHA-256, and every conversation fingerprint must be unique globally. The account read-back for each arm and a verified published Beta.1 rollback are prerequisites to a **complete structural experiment**. Actual final model metadata must say `gpt-6-thinking` / `standard`, and a canonical read must be from the installed `claude-code-mods-development` Skill URI and a single hashed Plugin instance. Both timestamps and explicit composer `system_hint` provenance must be checked privately by the collector before publishing sanitized records. Nonresponses, ambiguous sends, account metadata mismatch, 429, login challenges and transport errors are *blocked*, never a routing success or a code-semantic failure.

`validate_routing_factorial(report, suite)` refuses incomplete counts, unknown changed package files, different prompt categories, model drift, duplicate conversation hashes, mismatched Plugin versions, noncanonical Skill reads, and any leaked/raw conversation identifier fields. It validates cohort counts again instead of trusting an aggregate's claimed successes. Its only successful return status is `REAL_SIX_ARM_STRUCTURAL_OBSERVATIONS_ONLY` and expressly says neither model answer semantics, causal mechanism, full P4 46-case acceptance nor stable-release readiness has been established.

## Real experiment result and timing contract (2026-10-15)

The [sanitized 42-conversation experiment](../reports/2026-10-15-six-arm-automatic-routing-observations.md) contains 6/6 completed arm result sets, with **0/24** relevant positive automatic Skill reads, **0/6** boundary automatic reads, no unrelated false reads and **6/6** positive explicit-control reads. Both published baseline bookends also had no automatic reads. This provides **no evidence that the Beta.2 trigger descriptions caused the earlier regression**, but does not identify the ChatGPT model-side root cause either.

The experiment runner incorrectly measured a nominal three-minute hold from the **start of arm preparation**, not from the actual early send. Five arms had early-to-late gaps of **191–204 s**, but the final restored Beta.1 arm A1 had only **55 s**, below the promised 180 s. This observed timing defect must be disclosed. The strict full-admission validator now additionally requires `arm_conditions` containing exact numeric `early_to_late_seconds >= 180` and verified source download, advertised early/late metadata, absent automatic system hints and present explicit selected-Plugin hint. Missing/wrong conditions fail closed; the actual A1 timing prevents a fully qualified six-arm acceptance. Claimed source/metadata booleans still require trusted private send/account provenance, not only operator assertions.

## Conclusions the experiment cannot automatically justify

- **Description-only activation changes are not proof of causality.** The serial, same-account samples may also vary due to model selection, time, provider availability, platform changes or metadata propagation. A visible composer descriptor is not proof of the model's internal routing context.
- **Explicit Plugin success is a positive integration control only**, never automatic invocation. Ordinary correct model replies without `api_tool.read_resource` must not be passed as Plugin activations.
- **Offline packaging and a validated rollback are not a stable release gate.** Continue P4 semantics, P5 native model acceptance, user account identity/provenance review, historical Git privacy and full 46-case ChatGPT real-model QA before considering publication.

Never publish original chats, account Plugin identifiers, browser cookies, private ZIP copies or actual session IDs. Publish only the previously sanitized and independently verified evidence, model/effort metadata, Claim IDs, direct public source URIs and salted/private input fingerprints where appropriate.
