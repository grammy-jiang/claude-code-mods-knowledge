# ChatGPT ordinary Chat mode: six-arm Beta.1/Beta.2 routing-factor experiment

**2026-10-15, Australia/Sydney. Verdict: observed 42 real completed conversations; routing NOT FIXED; full planned time-delay protocol NOT admitted.** The actual published Plugin remains `v0.2.0-beta.1`; no variant was released. The experiment used the previously reviewed published Beta.1 ZIP plus the separate rejected Beta.2 source ZIP to create **factor-isolated, temporary** candidate packages. Private raw conversations, browser state, Plugin instance identifiers, account receipts and uploaded/downloaded ZIPs remain outside the public repository.

## What was actually controlled

A 6-arm, sequential, same-account evaluation used independent **ordinary ChatGPT Chat-mode** conversations, each with an original P4 prompt from `evals/p4_cases.json`. Every arm used the same six automatic tests plus one explicitly selected Plugin control. The exact prompts and original response/source fingerprints were checked privately against send receipts. Each real final reply's metadata reported **GPT-6 Thinking / Standard**. Normal automatic sends carried **no explicit Plugin system hint**, and the one explicit control per arm did carry the exact installed Plugin system hint.

| Arm | Changed files relative to published Beta.1 | Positive auto Skill loads | In-scope boundary auto Skill loads | Unrelated false auto loads | Explicit-control Skill reads | Early→late E01 interval |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| **A0** | Original published Beta.1 | **0/4** | 0/1 | 0/1 | 1/1 | **204 seconds** |
| **V** | `plugin.json` version number only | **0/4** | 0/1 | 0/1 | 1/1 | **191 seconds** |
| **D** | `plugin.json` description and `SKILL.md` frontmatter description | **0/4** | 0/1 | 0/1 | 1/1 | **191 seconds** |
| **K** | Knowledge body and two approved technical reference pages | **0/4** | 0/1 | 0/1 | 1/1 | **191 seconds** |
| **F** | The complete experimental Beta.2 content (new version identifier) | **0/4** | 0/1 | 0/1 | 1/1 | **191 seconds** |
| **A1** | Published Beta.1 restored at the end | **0/4** | 0/1 | 0/1 | 1/1 | **55 seconds — fails 180-second interval** |
| **All actual observations** | 42 independent conversations | **0/24** | **0/6** | **0/6** | **6/6** | Five arms met interval; A1 did not |

Per arm, the four positive automatic observations are: POS-E-01 once early and once late, POS-Q-01 and POS-U-01 late. The boundary is BOUND-HISTORY and the unrelated negative is NEG-HVAC. The explicit POS-E-01 control is **not** counted as an automatic pass. An actual canonical `api_tool.read_resource` read, with the correct scoped Skill and Plugin instance, is necessary to qualify. Model answers without that read are correctly treated as routing misses, regardless of whether they sound useful.

## Metadata readiness, real package files and rollback

- All four experimental ZIPs and both published baseline phases had verified **10/10** source files and server-generated sidecar metadata on account read-back before corresponding sends. Their source package hashes and changed-file allowlists are recorded in the [sanitized 42-case JSON](2026-10-15-six-arm-automatic-routing-observations.json).
- The ChatGPT composer's advertised Plugin description was read back at both early and late phases for every arm and matched the installed version's manifest. **This does not prove that the internal model router had refreshed its metadata cache** or that the Plugin was eligible for implicit selection.
- All 42 distinct conversations were source-matched and yielded real final assistant replies with identical declared model/effort. No ambiguous sends were retried, and none is counted as a pass by replacing an actual read trace with a generic model reply.
- After the experiment, account inspection confirmed installed/enabled **`0.2.0-beta.1`**, and the downloaded normalized Plugin contents matched the published Beta.1 source for **10/10** files plus its sidecar. The other **ten** personal Plugins had identical recorded installation/enabled/version/disabled-Skill-name states before and after the run. Point-in-time account checks do not constitute all historical account-provenance proof for P6.
- The **A1 early→late interval was 55 seconds**, not the required 180 seconds. The test script measured delay from the **arm's start time**, rather than from the actual early send, so earlier account read-back activity consumed the wait budget. This is an observable **test-orchestration defect**, not a model routing failure; A1 remains useful factual observations but fails the *complete six-arm timing protocol*.

## What this result does — and does not — establish

**Strong observed distinction:** across these 42 actual ChatGPT turns, ordinary automatic routing produced zero canonical Skill reads while **each of six independently explicit Plugin selections produced one**. This rules out a simple claim that the candidate description or its current Skill content alone guarantees automatic selection under the tested conditions. It also does not demonstrate that merely changing the version number helps.

**Not established:** whether the underlying cause is a model-routing policy, available-tool selection, a platform rollout, internal cache behavior, the visible Plugin hint's `is_auto` property, model configuration, or other time-dependent effects. Cohorts were sequential on one account, not randomized, and the difference from earlier Beta.1's 27/30 positive routing run demonstrates cross-run variability rather than causality. Variant D changes both Plugin and Skill descriptions together, not each independently. The final A1 cooldown deviation further prevents a fully protocol-qualified conclusion. Neither A1's 55-second interval nor any ordinary generic response may be turned into an accepted P4 case.

Explicit controls demonstrate that the installed Plugin could load the expected Skill **when requested**. They do not show that all six explicit replies were technically correct; at least one is structurally deficient and one carries a known-risk code flag. Semantic correctness requires separate version-pinned native and first-party source review.

## Disposition

**Reject promotion of every experimental routing variant.** Keep `v0.2.0-beta.1` installed as the last published baseline. The full P4-B automatic routing/repeatability, P4-C/D semantic and boundary QA, P5 three-host model validation and P6 release controls remain open. No stable tag, account setting change, or new published Beta is justified by this experiment. Public documentation contains only aggregate counts, sanitized Claim IDs and content-addressed observations, never actual personal ChatGPT conversation links or secrets.

The full-protocol validator now explicitly requires per-arm metadata/read-back/explicit-send attestations and a **minimum 180-second actual early-to-late interval**. It rejects the factual A1 result. Thus `42/42 replies collected` must **never** be conflated with `full six-arm protocol passed` or `stable release ready`.
