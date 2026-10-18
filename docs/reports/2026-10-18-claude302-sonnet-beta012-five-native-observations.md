# P5 Sonnet native 2.1.302: five completed original turns

Date: 2026-10-18 Sydney.
Native Claude Code CLI: 2.1.302, not ChatGPT Chat Mode.
Native model: claude-sonnet-5-5, requested Medium thinking.
Installed reviewed Skill: beta 0.4.12-beta.1, source revision
6f92571f0a0ab5b637b1b36607d5ff2ddd4860a8.

The original commands used print mode, an ephemeral session, no Chrome,
read-only Skill and Read tools, no Bash/Edit/Write/Web tools, per-turn
budget limits, and no execution of generated code. The observed model
identity is confirmed in the real native completion metadata. Requested
Medium thinking is not independently certified by the model provider.

## Actual model results and original tool evidence

Five original, different private native CLI runs were completed,
at an estimated combined cost of US$3.874. An offline read-only
verifier recomputed every original complete wire SHA256, original
prompt fingerprint and final answer SHA256. Private transcripts,
tool-result bodies and model outputs remain outside Git.

| Original case | Actual Mods Skill | Read activity | Narrow QA verdict |
| --- | --- | --- | --- |
| POS-Q-01 | 1 real Skill call | testing.md + claim-evidence.md; 0 errors | Approved Claim/official source structure PASS |
| POS-E-01 | 1 real Skill call | events.md + claim-evidence.md; 0 errors | Approved Claim/official source structure PASS |
| NEG-TYPESCRIPT (no source fixture) | 0 | 5 unsuccessful project-file reads | Correct Mods nonactivation; task content unverified |
| BOUND-VERSION-NEW (unreviewed 2.1.310) | 1 real Skill call | No reference reads | Textually safe abstention, but NOT full Skill+reference boundary approval |
| NEG-TYPESCRIPT-FIXTURE | 0 | 2 successful metadata reads; 4 unsuccessful filename guesses | Correct Mods nonactivation; actual overloads.ts was not discovered |

Both positive answers cited each required first-party Claim URL,
including K-0052/K-0053/K-0065/K-0067 in POS-Q-01 and
K-0040/K-0041/K-0064/K-0065/K-0067/K-0068/K-0069 in POS-E-01.
The checker found no missing exact official URL, no unapproved Claim
and no source-lint risk in either positive answer. Both generated
illustrative code snippets, but NO generated executable was run and
native Mod runtime semantic correctness is not certified.

The future-version boundary answer refused to treat CLI 2.1.302 as
2.1.310, provided no unapproved implementation code and accurately
reported not reading the reference files. It DID call the installed
Skill once, but no topic reference was read. The strict Plugin
entrypoint-plus-reference boundary obligation cannot be considered
passed simply because the refusal was safe.

## Harness limitation discovered and preserved

The unrelated TypeScript task correctly avoided loading the Mods
Skill in BOTH runs. The first provided no project fixture at all.
The second provided src/overloads.ts plus package.json and tsconfig.json,
but permitted only the native Read tool. The model read two available
project metadata files but could not discover the overload source's
filename, attempting common filenames and getting four errors.

These are negative Skill ISOLATION observations, NOT proof that the
unrelated TypeScript task was solved. A future test harness should
offer the native read-only directory discovery tool (Glob) alongside
Read, with an explicitly bounded project fixture, or provide the
exact reviewed file path. We did NOT keep retrying expensive model
turns merely to repair this test harness issue.

## No silent promotion to production

The previous budget-limited interrupted Sonnet turn was excluded,
not scored as completed quality evidence. The five completed
originals do not cover native host generated-code semantic execution,
all P4 boundary families, all Claude Code/Code Modes, native Pi Agent
Qwen quality or full 46-case ChatGPT Plugin acceptance. Original P4
strict 6/8 boundary result is unchanged. Stable Release remains HOLD.

Original raw prompts/answers, environment values, source paths and
account credentials are not committed. The JSON report includes
only hashes, bounded native tool counts and narrow results. Agent
Communication remains outside scope.
