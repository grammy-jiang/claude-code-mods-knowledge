# P5 Codex: privacy-preserving generated-code static audit

Date: 2026-10-17. This is a **follow-up static triage**, not part of the original
frozen A/B/C outcomes and not a production Mod-code acceptance.

Scope: all 12 originally recorded positive answers from the frozen
C_context_gate arm (four Mods questions x three repeats). Each original
native record and answer was verified against the immutable P5 A/B/C
provenance and SHA256 before examining code fences. The original question
set, model output and postflight gate decisions were not modified.

| Signal | Observed |
| --- | ---: |
| Verified original native answers | 12/12 |
| Answers with Markdown code fences | 6/12 |
| JavaScript code blocks | 6 |
| JavaScript syntax-only checks passed | 6/6 |
| Shell code blocks, **not executed** | 3 |
| Answers held by P3 for runnable code review | 6 |
| Model-origin code executed | **0** |
| Native Mod semantic approvals granted | **0** |

Three POS-E-01 answers each contained two small JavaScript code blocks;
all six passed a bounded local Node syntax parser. Three POS-Q-01
answers each contained a shell code fence, which was not executed.
The other six positive answers did not contain fenced executable blocks.
No generated code was installed, imported, executed or granted Mod API
authority. These results do not prove correct event values, callback
identity, deny/error handling, downstream exception preservation,
exactly-once continuation or real target host compatibility.

The script uses only Node syntax-check mode, with no shell expansion,
a bounded timeout, a disposable private working directory and empty
NODE_OPTIONS. Original model text, prompt details, local account paths,
event contents and arbitrary source snippets are not included in either
report. Absence of a syntax error is **not** a pass for P5 semantic
acceptance.

To reproduce this study, use the same private, original native wire
evidence and run scripts/audit_p5_generated_code_static.py with the repo
src and scripts import roots. If raw evidence is missing or inconsistent,
the script blocks rather than inventing successful observations.

Remaining P0: independently safety-review each model-origin candidate,
then test only approved snippets inside a restricted version-matched
Claude Code CLI 2.1.296 native Mod environment against success,
isError, deny, downstream exceptions, logger failure, identity and
exactly-once next semantics. Leave P5 Issue #3 open.
