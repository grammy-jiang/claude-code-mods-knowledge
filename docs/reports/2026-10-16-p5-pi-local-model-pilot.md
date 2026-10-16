# Mac Pi Agent local-model comparison — 2026-10-16

**Status: completed bounded pilot; none qualified for full P5.**

## Environment and evidence policy

- MacBook Pro M5 Max, 128 GiB, Pi Agent 1.3.0; frozen four Mods cases.
- Same installed reviewed Skill from source `6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e` and SHA256 `03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e`.
- Isolated Pi settings; no persistent sessions, no MCP, extensions, context files, or write tools; permitted native tools: read, ls, find, grep.
- Auto-activation is credited ONLY for actual native file reads. Positive source pass requires scoped K-Claim IDs plus each exact first-party anchor. CLI exit 0 alone proves nothing.
- Raw prompts, replies and tool traces are retained privately on the Mac, never in this report or public Git.

## Real four-case final run

| Model | Observer positive | Test-command positive | Unrelated TypeScript | Unsupported 2.1.310 |
| --- | --- | --- | --- | --- |
| Gemma 4 31B oQ4e MTP | Read Skill; exact Claim/source FAIL | Read Skill; exact Claim/source FAIL | No Skill read; completed | Did not read Skill; supplied unverified Mod implementation |
| Gemma 4 26B-A4B 8-bit | Did not read Skill; FAIL | Read Skill; exact Claim/source FAIL | No Skill read; completed | Did not read Skill; refusal lacked source-based reasoning |
| Qwen3.6 35B-A3B baseline | Read Skill; exact Claim/source FAIL | Read Skill; exact Claim/source FAIL | Timed out after 110s; incomplete | Read Skill; `boundary_scope_violated` |
| GPT-OSS 120B | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED | NOT OBSERVED |

## Sanitized native-model evidence

| Model ID | Case ID | Native verdict | Skill read | Model completion | Duration (s) |
| --- | --- | --- | --- | --- | ---: |
| gemma4-31b-mtp | POS-E-01 | structural_failed | yes | yes | 31.36 |
| gemma4-31b-mtp | POS-Q-01 | structural_failed | yes | yes | 18.06 |
| gemma4-31b-mtp | NEG-TYPESCRIPT | negative_nonactivation_observed | no | yes | 36.1 |
| gemma4-31b-mtp | BOUND-VERSION-NEW | activation_failed | no | yes | 17.82 |
| gemma4-26b-a4b | POS-E-01 | activation_failed | no | yes | 18.77 |
| gemma4-26b-a4b | POS-Q-01 | structural_failed | yes | yes | 10.61 |
| gemma4-26b-a4b | NEG-TYPESCRIPT | negative_nonactivation_observed | no | yes | 20.2 |
| gemma4-26b-a4b | BOUND-VERSION-NEW | activation_failed | no | yes | 3.7 |
| qwen36-35b-a3b-mtp | POS-E-01 | structural_failed | yes | yes | 25.59 |
| qwen36-35b-a3b-mtp | POS-Q-01 | structural_failed | yes | yes | 8.77 |
| qwen36-35b-a3b-mtp | NEG-TYPESCRIPT | blocked_or_incomplete | no | no/incomplete | 110.08 |
| qwen36-35b-a3b-mtp | BOUND-VERSION-NEW | boundary_scope_violated | yes | yes | 13.59 |

## Resource safety and rollback

- With the normal Qwen service running, both Gemma models loaded but triggered the existing memory-pressure stop gate at levels 48 and 46. Later turns were invalid due to model-service loss; do not count them as passed or failed model answers.
- Temporarily suspending ONLY the Qwen inference LaunchDaemon in a controlled maintenance window permitted valid four-case Gemma testing. Whisper, MLX-Audio, Ollama and ComfyUI continued running.
- GPT-OSS 120B local GGUF (approximately 63.39 GB) and llama-server capabilities passed metadata preflight. Even with Qwen paused, loading triggered the hard memory guard at pressure 35, before API/model inference. NEVER weaken resource safeguards to force this 120B model.
- After maintenance, all five original AI services were independently verified running, the Qwen `18080` API returned its expected model, test port `8011` was closed, the lab server script was byte-for-byte restored and Swap usage was 5.50 MiB.

## Decision and limitations

**Do not replace the default Pi model yet.** Gemma 31B showed 2/2 relevant Skill reads versus Gemma 26B at 1/2, but neither passed exact source/Claim gates and neither demonstrated reliable unsupported-version behavior. Existing Qwen also did not pass the stricter rubric.

These are single-attempt frozen cases, not the intended 12×3 repeated acceptance matrix; Qwen boundary was a separate replay because its negative test timed out. No statistical ranking, production Mod hook E2E, or real 120B tool-call quality result can be inferred.

Future choices: (a) test smaller Gemma variants with improved source compliance; (b) explicitly allow a deeper resource-maintenance plan for GPT-OSS 120B, still maintaining safety guards; (c) emphasize explicit source-scoped output validation because swapping models did not by itself repair the Skill failure.
