# P5 Pi Agent 1.1.0 — real model/read-tool tests (2026-10-14)

Four actual **Pi Agent model inference** calls used the account's ready
`openai-codex/gpt-5.5` OAuth provider in a disposable project. The project
contained only a copy of the generated, Claude Code CLI 2.1.296-scoped
`claude-code-mods-development` Skill and its reviewed references. Pi ran
in `--print --mode json --no-session`, with project context, MCP and extensions
disabled, and **only the native read tool permitted**. No edit, Bash or
web tools were allowed.

The user’s exhausted Claude Code model was not called. One initial selection
of `gpt-5.3-codex-spark` was unsupported by ChatGPT account authorization,
so it produced no model answer and is excluded from these four cases. The
supported model did respond successfully.

| P4 case | Model result | Native read evidence | Qualified verdict |
| --- | --- | --- | --- |
| POS-E-01, tool.call | Correct three-argument callback and reviewed K-0031 + first-party URL | Pi read Skill and events.md | **PASS** |
| NEG-TYPESCRIPT, unrelated TS | Asked for a local file rather than Mods code | Pi nevertheless read the Mods Skill (false activation) | **FAIL** |
| BOUND-VERSION-NEW | Did not invent unverified fields | Pi did not read Skill or cite official sources | **PARTIAL** |
| POS-Q-01, offline testing | Correctly used Mod directory argument | Pi read Skill, but response omitted K IDs/first-party sources | **PARTIAL** |

The actual Pi JSON event streams show tool_execution_start for native
`read` on the project-local SKILL.md and referenced events.md. This is **not**
ChatGPT's `api_tool.read_resource` and is not a Claude Code model invocation.
The raw event streams and model answers remain local to Pi under private
`/tmp`. The public [sanitized evidence](2026-10-14-pi-agent-real-model-qa.json)
includes case IDs, source revision, tool/Skill reads and SHA-256 only.

**P5 Issue #3 remains open**: no full passing positive/negative/boundary
suite across all three agents. Pi's real model was tested, but the negative
false activation and missing boundary/official references show the acceptance
criterion is not met. Claude Code real model tests remain blocked by separate
account limitations; the Codex 0.160.0 real model evidence is separately in
[Codex QA results](2026-10-14-codex-real-model-qa.json).

No personal/global Skill installation, repository writes or source changes
were made by the model.
