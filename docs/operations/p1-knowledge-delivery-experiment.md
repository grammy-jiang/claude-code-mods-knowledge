# P1 — Deterministic knowledge delivery and controlled native Agent evaluation

**Date:** 2026-10-17 (Australia/Sydney). **Research-only** branch stacked on the completed P0 diagnosis. Does not modify the published ChatGPT Plugin, installed user Skills or running AI services.

## Why this exists

P0 demonstrated 84/84 selected evidence files present but only 1/84 truly opened by a native Agent. The main Skill was read in 76/84, while exact approved Claim/URL answer structure passed in only 39/84. This separation requires two distinct measures: *delivery* and *use*. A file existing is not proof that a model saw it. A native system/developer context acknowledgment is not proof that the model applied it.

## Changes

### 1. Version- and intent-conscious routing

`src/mods_knowledge/task_evidence.py` now handles abbreviated Mod prompts, filters known incidental Python/Node/Codex runtime versions out of the Mod-target version set, blocks unreviewed version/surface implementation requests and treats "latest/current" API questions (including Chinese variants) as requiring fresh first-party verification. It does not convert "latest" into the pinned historical 2.1.296. Pure surface-comparison questions remain answerable with an explicit unverified-surface caveat. Hazardous "ignore official docs / skip permissions / upload secrets" signals fail closed.

Routing is conservative regex-based metadata, not a semantic retrieval search engine, a legal safety policy or a guarantee of automatic ChatGPT Plugin activation.

### 2. Trusted task-evidence envelope

`src/mods_knowledge/knowledge_delivery.py` now **reselects directly from the approved SSOT** using the original task prompt and verified local Claims, rather than accepting caller-constructed facts. Unsupported versions/surfaces, unrelated prompts, missing approvals, malformed sources, overlarge evidence and mismatched digests fail closed. No new official API statements are generated.

A bounded, SHA-256-tagged evidence envelope is supplied *before* inference using two opt-in host transports:

| Host | Delivery transport | Evidence measure | Verified scope |
| --- | --- | --- | --- |
| Codex App Server 0.163.0 | `thread/start` `developerInstructions` | Exact payload digest plus successful native thread-start response | **Real** Codex A/B tested |
| Pi Agent 1.3.0 | Owner-only file supplied by `--append-system-prompt` | SHA-matched private file and native CLI argument construction | Implemented + offline unit-tested, **model-runtime acceptance open** |
| ChatGPT ordinary Chat mode (skills-only Plugin) | No deterministic pre-inference host adapter presently established | Existing auto/explicit read receipts only | **Not changed or retested in P1** |

Codex's `developerInstructions` field was checked against the locally generated App Server JSON schema. Pi's `--append-system-prompt` was checked against the installed native CLI help. No MCP server, extra Plugin tool or persistent Extension was installed.

### 3. Frozen hosted Codex A/B

- Manifest `evals/p1_codex_delivery_ab.json` preserves the original `evals/p4_cases.json` SHA-256 and frozen experimental Skill SHA-256. The candidate Skill was copied into an owner-only private workspace from an immutable original P5 case, with the original case's selected-evidence file **excluded** to prevent cross-case contamination.
- Four positive tasks × 2 repetitions × 2 delivery arms, plus four unrelated negative tasks × 1 repetition × 2 arms = **24 real native Codex turns**. All are serialized; a private lock prevents simultaneous experiments.
- Both arms contain the **same optional selected-evidence.md** in an isolated Skill. The original user message bytes, model, reasoning effort, disabled-web-search setting and frozen Skill remain identical. **Only** the `preload` arm sends approved evidence with native developer instructions. Order is reversed between positive repetitions to reduce obvious sequencing bias; this is not a randomized clinical-style experiment.
- Every raw wire transcript remains private; the sanitized result contains per-trial outcome, evidence/SHA digests, actual Skill and selected-file reads and honest semantic-qualification flags. No private answer or user conversation link enters Git.
- `scripts/score_p1_codex_delivery.py` rechecks all original wire SHA-256 digests, unchanged case scope, model resolution and App Server provenance, zero webSearch items, correct evidence selection/payload and exact full matrix before publishing a final report. It refuses incomplete, missing or cross-arm trials.

## How to reproduce safely

**Offline only**, without calling models:

```sh
PYTHONPATH=src uv run pytest -q
PYTHONPATH=src uv run ruff check .
PYTHONPATH=src uv run python -m pytest -q tests/test_p1_task_router.py tests/test_knowledge_delivery.py
```

**Actual hosted model request (explicit action only, never CI)**:

```sh
PYTHONPATH=src uv run python scripts/run_p1_codex_delivery_case.py \
  --arm preload --case POS-E-01 --trial 1
```

The original report is immutable evidence and no completed trial may be overwritten. Do **not** rerun a case/trial already recorded. Production Skill configuration is not touched; this command needs the archived frozen native Skill, valid Codex account/model access and its isolated research-only HOME. Do not use it as a production agent entrypoint. Historical model responses must never be replaced to improve a score.

**Offline private-evidence verification (requires original private Mac traces):**

```sh
PYTHONPATH=src uv run python scripts/score_p1_codex_delivery.py
```

The scorer does not call a model; it *does* access private original wire files to verify SHA-256 and must not run in public CI.

## P1 verdict and remaining gates

The 24-turn Codex benchmark recorded **7/8** exact Claim/official-URL structural passes for preloaded evidence versus **5/8** for file-only; 8/8 positive preload thread starts were accepted; **8/8** negative turns finished without Mods Skill activation, 0/8 negative evidence injections. This is *exploratory* and too small to claim causal or generalizable improvement. Both arms mostly read the main Skill, but rarely read the selected file. Model-context delivery may improve selected fact *availability*; it cannot force understanding.

Do **not** promote to Stable. Remaining separate acceptance requirements:
1. Real Pi model inference with the new `--append-system-prompt` adapter in isolated, resource-safe conditions.
2. Target-native Claude Code CLI 2.1.296 **semantic** Mods tests for resulting code; the Mac currently runs a newer unreviewed CLI.
3. Independent ordinary ChatGPT **Chat-mode** Plugin auto/explicit activation qualification; Chat mode does not inherit Pi or Codex host injection mechanisms.
4. A larger repeated/interleaved benchmark of retrieval/use/semantic outcomes, with both positive and unrelated negative controls, before inferring reliable improvement.
