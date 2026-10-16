# Mac 120B models: Native Pi Agent completion and quality

Date: 2026-10-17. This is actual Mac-local model inference and
reviewed Claude Code Mods Skill evidence, not a simulated benchmark.

## 16K context, 6144 maximum output-token primary experiment

| Model | Engine | Load | Complete | Peak process RSS | Min macOS memorystatus level | Peak swap |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| GPT-OSS 120B | llama.cpp | 18.54s | 4/4 | 59.45 GiB | 36% | 5.5 MiB |
| Mistral Small 4 119B | oMLX | 4.22s | 4/4 | 45.94 GiB | 18% | 5.5 MiB |
| Qwen3.5 122B Heretic v2 | oMLX | 4.26s | 3/4 | 42.51 GiB | 33% | 5.5 MiB |

Process RSS is not full unified-memory usage. Memorystatus level is a
macOS resource indicator, not a direct free-RAM measurement. The
custom 50-percent termination rule and isolated oMLX memory guard
were disabled; native macOS memory management stayed enabled.
A separate emergency Swap cap and independent restoration watchdog remained.

## Exact frozen-case final-answer completion

| Model | POS-E-01 | POS-Q-01 | NEG-TYPESCRIPT | BOUND-VERSION-NEW |
| --- | --- | --- | --- | --- |
| GPT-OSS 120B | completed | completed | completed | completed |
| Mistral Small 4 119B | completed | completed | completed | completed |
| Qwen3.5 122B Heretic v2 | completed | completed | incomplete | completed |

Completion means the native model identity matched, the Agent turn
finished with stop rather than length, and nontrivial final text
was returned. Completion is not correct API or code semantics.

## Heretic TypeScript reliability: separate 8K retest

The 16K NEG-TYPESCRIPT run timed out after repeated successful reads.
With the unchanged frozen prompt but 8K context, three new attempts were:

| Trial | Complete | Repeated tool-call abort | Seconds |
| --- | --- | --- | ---: |
| 1 | no | yes | 76.62 |
| 2 | yes | no | 18.10 |
| 3 | no | yes | 25.65 |

**All three models demonstrated all four case types at least once,
but not 12/12 passes in one uniform configuration.** Qwen Heretic
has inconsistent tool-call termination and remains unreliable.

## Mods Skill production acceptance: FAIL

- Six positive answers, exact approved Claim and official links:
  **0/6** structural passes.
- Three unreviewed 2.1.310 version-boundary answers:
  **3/3** implementation
  scope violations flagged, including cases with disclaimers.
- Mistral negative TypeScript task completed despite 12 tool errors;
  blocked tool actions must not be treated as approved execution.
- No model's generated Mods code received complete native event
  semantic verification, including preservation of downstream errors.

## Environment, provenance and decision

- Two separate bounded maintenance windows stopped and later restored
  Qwen, Whisper, MLX-Audio, Ollama and ComfyUI. All five and the default
  Qwen API were independently verified healthy after each window.
- GPT-OSS ran with llama.cpp and the other two with oMLX; these were
  not Strata-native or MTPLX inference runs.
- Pi global defaults, installed Skill and macOS global Metal/OS limits
  were not changed. Original private event JSONL, answers and local paths
  remain on Mac; only case IDs, metrics and hashes are published.

**Conclusion:** Three models can complete the four test categories,
but none qualifies for unrestricted production Mods Skill use.
Leave P5 Issue #3 and stable release gates open.
