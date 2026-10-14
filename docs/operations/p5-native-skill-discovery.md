# P5 Model-Free Native Agent Skill Discovery

Date: 2026-10-14, Australia/Sydney. Audited source commit: `b229bca7fa3a2be96b0cbf65f5a1080332322948`.

Run the following on the MacBook Pro or Raspberry Pi checkout after compiling a
version-appropriate package:

```sh
uv run mods-knowledge build --api-version 2.1.296 --surface cli
uv run python scripts/verify_host_skill_discovery.py \\
  --dist dist --report /tmp/mods-host-native-check.json
```

This probe creates a **disposable project-local copy** and uses the hosts'
own loader/validator APIs, then removes the temporary directory. It never
invokes an inference turn, sends a prompt, modifies personal global Skill
directories or GitHub state, nor claims any Claude Code/Codex/Pi answer quality.

- **Codex:** starts a temporary `codex app-server --stdio`, calls
  `initialize`, `initialized`, and `skills/list` with `forceReload=true`.
  Confirms the exact Mods Skill appears once with `enabled=true`; then stops the
  subprocess. No model execution. This succeeded on MacBook, Raspberry Pi
  and sextant.
- **Pi Agent:** imports the actually installed `loadSkillsFromDir` plus
  `formatSkillsForPrompt`, detects one Skill with no errors and checks its
  name in system-prompt metadata. This succeeded on MacBook and Raspberry Pi.
  Pi Agent was not installed on sextant; mark it `unavailable` rather than
  `pass`.
- **Claude Code:** wraps the generated Skill in a temporary valid Claude
  plugin manifest and runs `claude plugin validate --strict --json`. This
  verifies a manifest accepted by the local CLI; it **does not prove**
  automatic Skill discovery/invocation in a real Claude Code model turn.
  Sextant reports Claude 2.1.289 while the SSOT knowledge is limited to
  CLI 2.1.296; do not assert cross-version API compatibility.

Evidence: `docs/reports/2026-10-14-native-agent-skill-discovery.json`.
The host summary deliberately excludes machine paths, usernames, tokens,
conversation IDs and model replies.

When model quotas return, Issue #3 still requires real workflow tasks,
version/permissions validation, and end-to-end behavioral tests. Do not
close it just because Codex/Pi natively discovered the files.

## Real model turns: pin and verify the actual Pi Agent provider

The model-free loader check above remains valuable but is not P5 model inference.
Actual real Pi Agent 1.1.0 replays on 2026-10-14 defaulted to a **different
model** from the earlier `openai-codex/gpt-5.5` acceptance trials. A desired
model inferred from flags or settings is insufficient: verify the actual
assistant `message_end` **provider** and **model** metadata and the exact user
prompt in the captured private JSONL.

For a new, disposable, owner-approved **native model** QA case, explicitly pin
its provider/model at invocation (do not change global settings):

```sh
pi -p --provider openai-codex --model gpt-5.5 \
  --no-session --no-mcp --no-extensions --no-context-files \
  --tools read --skill /private/disposable/skill \
  --mode json --thinking low "$EXACT_ORIGINAL_P4_PROMPT" \
  > /private/qa/native-pi-events.jsonl
```

The private event stream must be reviewed by
`mods_knowledge.pi_model_evidence.summarize_pi_model_trace`, passing
`model_was_pinned=True` **only** if the command genuinely included both flags.
Compare its `model_observed`, `model_pin_matched`, `prompt_matched`, actual
Skill-relative read paths, source hash and separate semantic verdict. Do not
record a model pass from mere Skill exposure or a successful process exit.
The [sanitized 2026-10-15 evidence](../reports/2026-10-15-p5-native-model-pinning.md)
retains genuine positive structural failures and the unpinned Qwen cohort.
