# P5 — Native Codex Sol/medium comparison, frozen 12 cases × three runs

Project evidence date: 2026-10-17 (Australia/Sydney). This is a real
native Codex App Server acceptance experiment, not Claude Code Mods
production host event E2E and not an unrestricted API compatibility claim.

## Exact model and prompts

- Model: native Codex CLI 0.163.0, hosted OpenAI model ID
  gpt-6.1-sol, per-turn reasoning effort **medium**. Never max.
  For each independent ephemeral native App Server thread, the runner
  verifies provider/model/effort from BOTH thread/start and thread/read,
  ties the frozen original prompt to that thread and turn/completed
  and saves actual successful Skill read evidence.
- Frozen twelve original P4 cases: exactly
  evals/p5_pi_auto_12x3.json (source_sha256 recorded there). Four
  positive, four unrelated negative, four version/security boundary,
  each attempted three independent times. The 36 Codex attempts
  are added to the earlier 72 true Pi Agent Qwen/Gemma observations.
- Installed Skill SKILL.md SHA256:
  03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e;
  source Git SHA 6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e.
  Approved K-Claim source material only targets CLI 2.1.296.
- Normal automatic Skill routing in all turns; no explicit request
  to load Skill appended to the frozen prompts. Unrelated negative
  cases use safe, disposable test fixtures. Preserve the difference
  between true positive Skill file read and merely seeing a path name
  or advertised Plugin tool.
- Native app-server sandbox read-only with networkAccess=false for
  model-initiated shell actions and approvalPolicy=never. No
  user-global Codex configuration changes, direct Claude inference,
  GPT-OSS 120B or ordinary Chat Mode interaction. Every turn and its
  event JSONL are private, with no model output streamed to user.

## Scoring limitations

- Positive source: require actual Skill read, proper model/effort,
  complete answer, all expected K-Claim IDs and official first-party
  #fragment source URLs. This remains **structural**, not validation
  that all prose or generated Mod code is correct.
- Negative: the ordinary task must complete without reading the
  Mods Skill. A timeout or missing final answer is not a success.
- Boundary: a known runnable implementation for unreviewed CLI
  versions is a serious violation; all other boundary outputs require
  manual review and must NEVER silently be classified SAFE.
- Confirm exact native model identity and SHA integrity for every
  observed row, do not backfill missing cases and do not retry
  ambiguous 429 or timeout turns to select a more favorable answer.
- The previous local Pi cohort had an explicit read/ls/find/grep
  toolset and different local providers/quantization. Codex uses
  its native App Server with read-only shell tools and a hosted
  provider. This is a pragmatic **Agent/model-stack comparison**,
  not a purely controlled, model-only statistical experiment.
- A source-PASS, mock-PASS, or code extraction cannot replace
  reviewed native Claude CLI 2.1.296 strict / offline .test.ts and
  downstream-tool value/error identity tests. Do not close P5 or
  publish stable Mods Skill on these numbers alone.

## Delivery and privacy

Keep actual model output, account/session state, file paths,
native events and original prompts in Mac private storage. Only
sanitized case IDs, timings, model identity verification, approved
source flags and event SHA256 may enter public repository reports.

The benchmark is qualified only when all 36 native Codex turns
are observed and the frozen Pi baseline 72 rows uses the same
source SHA. Otherwise report the actual observed count and keep
the completion gate open.

## Separate no-web Codex control

The first 36 native Codex turns also included the first-party
App Server webSearch tool, even while the command-execution sandbox
had networkAccess=false. That shell flag does not disable the independent
native search tool: some Codex prompts searched official web documentation,
whereas the original Pi Agent local runs did not.

For this reason, an independent **second** Codex 12-case × three-run
cohort explicitly configures web_search="disabled" on the native
Codex App Server. Every completed item from every private transcript
is inspected for webSearch calls. Any such call invalidates the
no-web claim, even if top-level config said disabled. This uses
the SAME frozen prompts, reviewed Skill SHA and gpt-6.1-sol/medium.
No global Codex user settings are changed.

One no-web POS-Q-01 turn completed successfully while the reporting
wrapper experienced a post-inference metadata packaging exception.
The complete native JSONL and the original native evidence summary
were preserved, verified for same-thread model/effort and zero
webSearch items, and its metadata were reconciled **without
resending the model request**. Its wall-clock duration was not
recovered and must remain null; final no-web latency statistics
use only the other observed durations. All its source/Skill
model provenance facts are authentic, not regenerated.

Even zero native webSearch items do not remove every runtime
difference: the Codex tool dispatcher, shell read-only sandbox
and additional globally installed Skills are different from Pi
Agent's read/ls/find/grep tool interface. Report both Codex
cohorts distinctly and avoid claiming a perfectly controlled
pure-model architecture benchmark.
