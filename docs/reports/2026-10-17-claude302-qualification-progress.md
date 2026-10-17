# Claude Code 2.1.302: native A/B/C and Chat Mode qualification

2026-10-17 (Sydney). Approved source commit: `e1f080ea46102cb257ad57a64f2fecf9fe1cf037`. The official npm latest dist-tag remained 2.1.302 when independently checked at 12:08 UTC. This is a **progress audit**, not a stable release promotion.

## Native Codex campaign: MacBook Pro

The private `p5-codex-302-abc-20261017` study has **144/144 original completed native turns**. An independent, read-only verifier confirmed each exact source and Skill SHA, each unique wire SHA and answer SHA, per-cell installed Skill SHA, and exactly one successfully completed native App Server turn for every distinct case/condition/trial. All turns used `gpt-6.1-sol`, medium effort, disabled Web search. No case was retried or its private transcript exported.

| Cohort | A: Skill v3 | B: context | C: context + gate |
| --- | --- | --- | --- |
| Frozen: required positive Claims and exact URLs | 12/12 | 12/12 | 12/12 |
| Frozen: unrelated negative no Skill | 12/12 | 12/12 | 12/12 |
| Frozen: completed boundary turns | 12/12 | 12/12 | 12/12 |
| Heldout: required positive Claims and exact URLs | 6/6 | 6/6 | 6/6 |
| Heldout: unrelated negative no Skill | 3/3 | 3/3 | 3/3 |
| Heldout: completed boundary turns | 3/3 | 3/3 | 3/3 |

All three arms met 18/18 predeclared case-required positive source checks and 15/15 negative nonactivations; the context variants did not improve that metric. C's structural gate identified **7/18 positives** as candidates (6/12 frozen; 1/6 heldout), but **11/18** need technical code/source review. All 15 C boundary cases still require manual review. These are not native Mod semantic passes.

In all nine heldout HOLD-T-01 turns the task selector offered two supporting Claims, but the actual case required just one of them. The additional unrequested Claim was absent, so an *all offered context Claims must appear* diagnostic fails nine times. This is a stricter diagnostic, **not** a failure under the predeclared case-required metric. Both facts are retained; original historical evidence was not edited.

## Genuine ChatGPT Chat Mode: Raspberry Pi

The personal account's Plugin `claude-code-mods-knowledge` is enabled and installed at **0.4.7-beta.1**. Four prior, genuinely completed ordinary Chat Mode conversations (not Work) were read back without resending. Each contained a full multi-segment final answer under GPT-6 Thinking / Standard.

| Case | Plugin selection | Actual matching resource reads | Exact approved Claim/URL | Disposition |
| --- | --- | ---: | ---: | --- |
| 1 positive | Named in prompt text, not selected in composer | 4 | 11/11 | Structural source success; version review needed |
| 2 unrelated negative | Neither requested nor selected | 0 (correct) | Not applicable | Negative nonactivation success |
| 3 unsupported version | Named in prompt text, not composer | 4 | 8/8 | Structural source success; semantic boundary review pending |
| 4 positive | No name or composer selection | 4 | 8/8 | One actual automatic Plugin activation; native semantics pending |

All 12 canonical `api_tool.read_resource` events were from the **same currently installed Plugin identity** and its expected Skill/reference URIs. They prove authentic read-event metadata, not returned reference bodies. Static lint observed no known hard hazard, but two answers need version/semantic review. Some reply metadata indicated Web search usage even though search was not requested; the Chat study is not a no-web control. Neither exact-source URLs nor absence of regex lint errors prove generated runnable code is correct.

## Outstanding acceptance gates

The **46-case full live Chat Mode suite remains unexecuted for this specific Plugin version**. These four targeted observations cannot be counted as that full acceptance. Case-by-case boundary semantics and generated Mod examples still require independent review, with executable examples tested only in disposable, mocked environments on the exact native CLI. Reuse original Chat IDs and respect HTTP 429 without ambiguous resends.

Recheck the official latest dist-tag immediately before any promotion. If it advances, stop 2.1.302 promotion and perform a new source/Claim/Skill/Plugin rollforward. Keep the existing beta on **HOLD** until actual latest-version model acceptance finishes. Machine-readable redacted reports carry aggregate native hashes, separate frozen/heldout counts, Chat read provenance, and SHA-only answer identifiers. Private prompts, transcripts, wire data and account identifiers remain off Git.


## Follow-up original-answer semantic and boundary triage

All 45 genuine version/host/historical boundary answers from the 144-turn
Codex campaign were independently re-read and verified against their
original native answer/wire hashes. All 45 contained non-guarantee or refusal
language, zero contained runnable fenced code, and P3 withheld all 15
C-condition boundary replies. These language/pattern checks are triage signals,
not full independent semantic certification of every explanatory statement.

In C's 18 native positive answers, eight original JavaScript observer
blocks were independently inspected: three simple exact passthrough shapes
and five exactly matching a fail-isolated async logging shape. One
original model-origin JavaScript snippet matching the manually reviewed
non-I/O shape was embedded into an authorized disposable
register(on) wrapper. First-party Claude Code CLI 2.1.302 strict
validation passed, with 3/3 mocked native success/deny/isError tests.
Six independent JavaScript tests also passed exact downstream result/error
identity and exactly-once next(e), including throwing and rejected
diagnostics. No user Bash tool or actual network operation was run.

**Scope remains narrow:** identical shapes in other model answers were
not individually executed, shell snippets were not executed, and no whole
generated answer or production plug-in is declared semantically certified.
See the paired JSON metadata-only reports and retain the overall HOLD gate.
