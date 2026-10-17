# Real Claude Code CLI 2.1.302 host model acceptance — Sonnet Medium

Five different, genuine native Claude Code CLI -p stream-json model turns were
captured privately on MacBook Pro. Actual completed model usage was
claude-sonnet-5-5; each turn requested Medium effort and used installed CLI
2.1.302. The --add-dir flag narrowly authorized the generated Mod Skill
reference directory for necessary Read calls. Tests never bypassed
permissions, edited user files or executed model-generated Mod code.
Original stream-wire and final-answer SHA256 identifiers are recorded in
the redacted machine-readable companion report. Raw prompts, replies,
account metadata, tool paths and auth data remain private.

| Native scenario | Actual Skill and reference use | Strict verdict |
|---|---|---|
| Explicit positive | Skill plus 2 Read calls, exact approved URLs | Structural pass |
| Natural automatic positive | Skill plus 1 Read call | Fail: K-0065 cited without exact official URL |
| Unrelated Python question | Zero Skill and Read | Negative isolation pass |
| Automatic unsupported-version boundary | Skill called; no runnable API code | Safe abstention pass |
| Explicit unsupported-version boundary | Skill called; no runnable code | Boundary text still problematic: offered an unverified draft as a possible override |

An earlier, separately recorded Haiku/Low genuine CLI trial also completed,
but its initial Read of the reference file was denied under non-interactive
permission boundaries, so it cannot be promoted to a source-complete
acceptance. Sonnet/Medium confirms model and Skill tooling actually work
when generated references are inside the authorized directory.

The automatic positive missing-source case is a real remaining failure
after ChatGPT Chat Mode root-URI scorer correction. The explicit unsupported
version override offer is a separate semantic-policy failure. Do not
upgrade either to pass by merely counting citations or a Skill tool call.
Natural automatic activation and explicit selection have separate metrics.
This document is not production deployment certification and does not
supersede the Codex gpt-6.1-sol / medium 144-turn controlled benchmark.

Stable-release gate remains HOLD until a full Chat Mode candidate
regression, all P5 actual host evidence and account rollback checks pass.
