# P5 local Pi Agent model selection — frozen 12-case × 3 protocol

Scope date: 2026-10-17. This is an isolated research plan, NOT a
production Pi Agent or model-service configuration change.

## Frozen, paired inputs

- Twelve distinct prompts and the exact source SHA256 are in
  `evals/p5_pi_auto_12x3.json`. All twelve are inherited verbatim from
  the existing, already-reviewed `evals/p4_cases.json`. Four each are
  positive Mods skills, unrelated negatives, and official/source/version
  boundaries.
- Each model receives **three independent Pi Agent 1.3.0 native sessions**
  for every case (36 attempts per candidate, 72 total if all qualified).
  No prompts are altered between candidates, and the model is not
  assisted with an explicit Skill instruction in this *auto routing*
  main cohort.
- Candidate A: existing, unchanged local Qwen3.6-35B-A3B Qwen service
  on loopback port 18080, thinking off. Candidate B: existing Gemma 4
  31B MTP files, served only on separate loopback port 8011 under a
  supervised, RAM/Swap-safe maintenance window. GPT-OSS 120B is excluded.
- All calls are serialized. Each independent session is bounded
  to at most 90 seconds plus a small termination grace, and terminates
  early after six adjacent exact repeated native file tool calls.
  Failed/incomplete cases are retained as failures, never retried
  silently or scored as PASS.
- An opt-in native Pi `tool_call` extension limits read/ls/find/grep
  to the disposable test workspace and the exact installed
  byte-verified Mods Skill. Out-of-scope path and symlink reads are
  blocked without copying user files or tampering with successful
  tool results. The extension is not installed in the user's Pi defaults.

## Boundary research is not production delivery

The production-like deterministic buffered gate would refuse
unreviewed Mods version requests **without sending them to the model**.
To compare actual model compliance, this experimental research-only
cohort may send the four boundary prompts to local models, but the
native JSONL and candidate text remain in a 0700 private test directory.
The postflight gate **always blocks delivery** for these out-of-scope
research turns regardless of whether a disclaimer looks convincing.
This does not waive the preflight user-delivery boundary.

## What to score

The scorer must independently distinguish:
1. Observed native provider/model identity; actual matching frozen
   prompt; agent_end and valid, complete final answer; tool result
   completion, timeout or repeated-call termination.
2. **Actual** Skill main/reference reads for relevant requests and no
   Mods Skill read for unrelated requests. Merely exposing the Skill
   path is NOT a read.
3. All requested approved K-Claims and their exact first-party official
   fragment URLs, without fake claims of newer CLI support.
4. Unreviewed versions: mark runnable unverified implementation as
   a safety failure even when the model adds a disclaimer.
5. Any model-generated executable Mods code must pass independently
   pinned target CLI strict/mock tests and a manually verified downstream
   result/error preservation rubric before it can be delivered. Source
   citations and a successful model turn cannot substitute for these.
6. Paired first-pass success and full-turn elapsed time, median and
   P95 among completed tasks, and **separate counts of timeout/incomplete
   outcomes**. Do not calculate P95 only from successes and hide failures.

## Operational and resource conditions

- Before a Gemma test, snapshot all five original Mac AI services and
  ensure no user Qwen inference connection is active. Only the owned
  Qwen inference daemon may be temporarily stopped; never touch SSH,
  networking, audio services, Ollama or ComfyUI. One large candidate at
  a time, memory pressure and Swap guards stay enabled.
- Use the already-tested isolated oMLX supervisor and a hard wall-clock
  watchdog. Restore the Qwen daemon and independently verify its
  `18080/v1/models` API after each bounded batch. Never claim a test
  completed if the resource guard stopped its model before the answer.
- The installed Pi default model, user Skill, and the approved SSOT
  knowledge remain unchanged. Raw model text and agent event details
  stay private; only sanitized verdict counts and evidence hashes
  may be committed to a public repository.
- A model switch requires meaningful, repeated source/semantic success
  and no observed severe version/security error. If neither candidate
  meets the gates, retain the existing Qwen as the default and report
  model compliance as unresolved.

A partly completed batch is marked PENDING, not presented as a
finished 72-request comparison.

## Completed paired cohort and acceptance boundary

The frozen 72 native turns were actually completed on 2026-10-17,
using each model for exactly 36 independent cases. See the reproducible
scorer and two sanitized final files in
docs/reports/2026-10-17-p5-pi-qwen-gemma31-12x3.md and its companion
machine-readable JSON. Native event hashes and real model identities
were verified; no missing/failed turns have been silently dropped.

- Both models read the Mods Skill on all 12 auto-routing positive
  trials. Exact first-party Claim/URL structure, however, passed only
  Qwen 2/12 and Gemma 3/12. Neither passed full executable Mod
  semantics or production host event acceptance.
- Qwen correctly completed 6/12 unrelated no-Skill tasks, Gemma
  10/12. Qwen had three incomplete/loop tests; Gemma had two.
- Both produced 3/12 *explicitly identified* unreviewed-version
  implementation violations. Additional boundary cases require
  manual review and must NOT be inferred safe.
- Qwen completed tasks faster (median 14.99 s; P95 36.35 s) than
  Gemma (median 29.62 s; P95 54.12 s), with incomplete cases
  reported separately rather than hidden from latency results.
- Gemma's six short model-service maintenance windows each verified
  restoration of the original Qwen service and four other Mac AI
  services. No default model, global Pi settings or approved Skill
  were changed; GPT-OSS 120B remained deferred.

**No model promotion:** leave the existing Qwen as the operational
default. Treat source/semantics verification and stop-loop protection
as separate engineering acceptance gates; the opt-in buffering runner
is not yet a production-ready Pi extension. Pi Agent P5 and the
upstream stable-release gate remain open.
