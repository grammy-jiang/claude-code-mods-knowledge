# P5 — Native Pi 120B-class Mac benchmark, 12 frozen cases × 3

Date: 2026-10-17 Sydney, MacBook Pro M5 Max / 128 GiB. This is a
real Pi Agent 1.3.0 research-only model test, not Mod production approval.

## Identical source and inference settings

- Frozen original P4 prompts from `evals/p4_cases.json` SHA256
  `a5bc6c89f993772dc324d323617bb98cf9f5709bd5af9b903f86f320cad0b8bb`.
  12 unique cases: four positive Mods, four unrelated controls, four
  official source/version boundaries. Three independent turns per
  model/case: **108 real native turns**.
- Exact manifest: `evals/p5_big_three_auto_12x3.json`. All three
  models have 16K context and 6144 max output tokens.
- GPT-OSS 120B llama.cpp GGUF MXFP4 uses medium; Mistral Small 4
  119B oMLX 4-bit uses thinking off; Qwen3.5 Heretic 122B oMLX mixed
  3.8-bit uses thinking off.
- Same reviewed installed Mods Skill SHA256
  `03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e`,
  officially scoped only to Claude Code CLI 2.1.296.
- Ordinary automatic Pi Skill discovery, no explicit Skill directive
  appended. Read-only tools read, ls, find and grep, with native test-only
  path scope extension. The maximum identical adjacent tool-call
  repetition is six; maximum total tool calls 48; each model turn
  has a 95-second hard wall clock budget.

## Short safety-bounded service windows

- Each window runs six real model turns and then unloads the candidate,
  restores the existing Qwen, Whisper, MLX-Audio, Ollama and ComfyUI,
  and confirms Qwen's old API. Eighteen windows planned.
- Separate recovery watchdog acts if the owning inference process
  crashes or hangs. Do not continue into next window unless all five
  AI services and the original Qwen endpoint are verified healthy.
- Previous artificial 50% free-memory abort remains disabled at
  user request. macOS native memory controls unchanged. The isolated
  test has a 4 GiB emergency disk Swap ceiling, explicit timeouts
  and process RSS/Swap/memorystatus sampling.
- No downloads, no concurrent heavyweight inference, no global Pi
  defaults/Skill updates. GPT-OSS medium, other two off, no Claude
  or hosted Codex model inference in this new 108-turn study.

## Scoring and evidentiary limits

- Native JSONL, original prompts and full model text stay in the Mac
  private benchmark directory. Each trial preserves SHA256 and its
  original result. No failed call can be silently replaced by a
  more favorable trial.
- Report actual Skill reads, precise approved Claim IDs and first-party
  source fragments, native provider/model identity, complete stop
  reason and nontrivial final response, no-Skill controls, rule-detected
  version-boundary code, timeouts and repeat-loop terminations.
- Boundary prompts can be sent only as **private research**, not as
  final end-user code delivery; ordinary production would refuse
  unsupported versions before model inference.
- Structural exact-source success is not proof of code correctness or
  tool/exception identity. The stable-release P5 gate remains blocked
  without target-native CLI 2.1.296 behavior testing and independent
  semantic review.

Public report is permitted only after 108 original native model
attempts are reconciled and 18 windows all satisfy service restoration
verification. Otherwise report IN PROGRESS, not a completed ranking.
