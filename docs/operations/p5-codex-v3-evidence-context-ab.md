# P5 controlled Codex V3 Skill evidence context A/B/C experiment

Date: 2026-10-17, Australia/Sydney. Research and development only,
not production Mod code certification or ChatGPT Chat-mode Plugin acceptance.

## Frozen environment, exactly one variable

Codex App Server model gpt-6.1-sol, medium reasoning, disabled web
search, read-only sandbox and ephemeral one-shot threads are the same
in A, B and C. The V3 Skill is compiled from merged source commit
a543fd535c93a865dc5ab9b4949bd6e15c2628ce and has SHA256
259535287ef965e516a79283144445228ff84653aae67189b5d2476c70f10baf.
A private Codex HOME contains exactly one reviewed V3 Skill and
owner-only authentication access; original global settings unchanged.

- A: the original V3 Skill available, no additional task context.
- B: exactly the same V3 Skill plus approved task-matched Claim/official
  URL evidence delivered through the native thread/start
  developerInstructions field on positive cases. The original frozen
  user message is separately submitted, byte-identically unchanged.
- C: same treatment as B, plus a private postflight buffer checker.
  The gate never edits model text, only allows structurally checked
  candidate output or withholds it. All boundary research stays private.

Actual native model/effort/Skill registration, prompt equality and
completed Skill file-read events are verified. Context SHA proves
developerInstructions was submitted to Codex, not that the model
attended to every Claim internally.

## Genuine evaluation

Frozen 12 original P4 prompts x 3 independent turns x 3 conditions:
108 original native Codex turns. The condition order is rotated
over case and trial to reduce time-order confounding. Separately
frozen new holdouts in evals/p5_codex_ab_holdout_cases_20261017.json
include two positive Mods questions, one unrelated Python control,
and one unreviewed CLI version boundary; 4 x 3 x 3 = 36 more turns.

The heldout cohort waits for all 108 original turns to complete.
Total 144 native observations, every wire/trial retained with SHA256,
no silent retries or substituted successes. Hosted model, effort,
tools, no-web setting and global Skill remain unchanged.

## Reporting and limitations

Report raw exact atomic Claim+URL matches separately from actual Skill
reads, context submission receipts and structural delivery-gate results.
A P3 gate pass is not the same as native executable Mod code semantics.
A zero automatically detected version violation is not safe-version
certification; all unsupported-version answers stay private. The
reviewed target remains Claude Code CLI 2.1.296 only. Raw user/model
content, private host paths, Codex session identifiers and account
credentials are excluded from public artifacts. Keep P5 Issue #3 OPEN.
