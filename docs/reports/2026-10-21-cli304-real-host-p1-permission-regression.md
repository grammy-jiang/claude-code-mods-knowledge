# Claude Code 2.1.304: actual-host permission and failed-reload QA (P1)

Date: 2026-10-21 AEDT. **Release verdict: HOLD. Security-adverse result.**
This is a new live, native Claude Code host investigation, not a synthetic
plugin test, a mock, or an approval of new 2.1.304 Claims.

## Target and strict scope

- Raspberry Pi 5, Linux ARM64; original first-party Claude Code **2.1.304**
  release executable SHA256
  **c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3**.
  The previously pinned first-party release archive is
  **17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5**.
- An actual authenticated Claude model/host run per simple scenario,
  and a *single multi-turn instance* for each reload sequence. Native wire
  identity: **claude-sonnet-5-5**; requested medium effort, bounded cost and
  turns. Six canonical real-host scenario receipts cost **USD 0.0508704**,
  as reported by native result events. These are not a statistical model A/B.
- The executable ran by its **private temporary path**, not installed over
  the user's production 2.1.303 CLI. Private test plugins and benign files
  lived only under a mode-0700 temporary directory.
- Execution deliberately supplied **--restricted**, **--strict-mcp-config**,
  an empty **--setting-sources**, **--permission-prompts none**,
  **--no-session-persistence**, explicit private **--plugin-dir**,
  **--model sonnet**, and **--effort medium**. Stream-json verbose output
  captured real tool uses/results and host diagnostics. No permission bypass
  was enabled; the only attempted Write was rejected and its target did not
  exist afterward.
- User credentials, session IDs, raw model messages, complete debug text
  and raw prompts are **not** in Git. Those raw files remain on the
  originating Raspberry Pi for independent replay. Their SHA256 hashes,
  source fingerprints, redacted facts and exact outcomes are in the
  [JSON evidence report](2026-10-21-cli304-real-host-p1-evidence.json).
  All harmless reviewed fixture code is under the directory
  **evals/fixtures/cli304-real-host-p1-20261021/**.

## Actual observations

| Claim | Actual native host evidence | Qualification |
| --- | --- | --- |
| **K-0070**, human decider | Real Write call, inherited decision ask; Mod returned a person-decider requirement. Unattended host refused and target file was absent. | **Partial PASS**: no interactive human approval or managed override tested. |
| **K-0071**, isReadOnly | Two real Read tool calls reached tool.check with isReadOnly true and base decision allow; both were denied for safe QA. | **Partial PASS**: not a complete tool classification matrix. |
| **K-0072**, plugin skip | Two independently loaded tool.call Mods: outer short-circuit suppressed inner; matched pass-through control executed outer/inner and completed the benign Read. | **Partial PASS**: the expected user-visible skipped-Hook transcript was not found in this print-mode profile; do not infer TUI parity. |
| **K-0073**, failed reload | Good module loaded; module intentionally corrupted; same host executed reload-plugins. Host debug logged syntax failure and old module unload, while CLI returned a superficially successful reload line. Existing command name still ran, but with **newly edited** command content. | **FAIL for prior safety-guard preservation and coherent previous version** in this inline-plugin profile. |
| **K-0074**, hook exception catch | Actual Read event intentionally threw; actual tool-result refusal contained the registration catch's fail-closed marker. | **Partial PASS**: only this actual exception/deny path, not all host permission precedence. |

### Security-negative K-0073 control

The critical failed-reload observation was independently reproduced using
a separate, **harmless prompt.submit guard**, not just command registration:

1. With the original registered guard active in the same native 304 session,
   the sentinel-bearing harmless QA prompt was refused: **0 model turns**.
2. The local Hook module was replaced with an intentional JavaScript syntax
   error, and the live session executed **/reload-plugins**. The CLI reported
   a nominally successful reload while private host debug recorded both the
   parse failure and the diagnostic **"the version loaded before is unloaded"**.
3. Re-sending the **same harmless prompt** in the same session then reached
   the model successfully: **1 model turn**. The original guard-entry debug
   marker occurred exactly once, before failure, and not afterward.

No forbidden shell command, real user-file write or managed-policy bypass was
attempted. This establishes the **loss of the local Mod guard** in the stated
native inline plugin / noninteractive stream-json host profile. It does **not**
prove a universal bypass of Claude Code's independent built-in permission
system. Other plugin-loading profiles may behave differently.

The command continuity control also showed that the existing slash command
name remained callable while its updated markdown content took effect after
the failed module reload. Mere command presence is therefore **not** evidence
that the previously loaded safety Hook or previous-version bytes survive.

## Reproduction, negative controls and Claim gate

The SHA-pinned source, native model events, debug logs and redacted facts were
independently re-audited by **scripts/audit_cli304_live_host_p1.py** on the
Raspberry Pi. The script parses six actual-host private JSONL receipts and
rejects absent real tool events, missing refusals, missing inner-plugin
pass-through control, ambiguous reload results, missing guard bypass,
unreviewed test source bytes and incorrect official binary/asset hashes.
It publishes no raw model text. Its own SHA256 is pinned in the public report.

The offline CI test **tests/test_cli304_live_host_p1_evidence.py** checks
the immutable redacted report, full public test fixture source matches,
auditor SHA and fail-closed release classification. **CI cannot independently
replay a paid model or recover the private original debug/wire log bodies**;
those are retained privately with their published digests and must be
reviewed separately for production approval.

All **31 prior CLI 2.1.302 Claims remain unapproved for 2.1.304**.
K-0070 through K-0073 remain candidates, K-0074 remains source-reviewed
only. No integration-pass promotion, approved 304 Skill, production account
or CLI modification, or Stable release is authorized. The P4 46-case Chat
Mode qualification and full P5/P6 release gates remain HOLD.

## Next required tests

1. **P1-A, critical:** Reproduce K-0073 with an isolated genuinely installed
   Plugin on 2.1.304, compare print-mode with interactive host behavior, and
   require the safety invariant: a failed reload must either keep the
   previously effective safety Hook or fail closed for dependent actions.
   A nominal reload success line is not an acceptance criterion.
2. **P1-B:** Test true interactive human permission approval/denial and
   managed-rule precedence without granting an unattended writer permission.
3. **P1-C:** Cover isReadOnly presence/absence for other tool classes, plus
   user-visible skipped-Hook transcripts in an appropriate interactive UI,
   and stronger two-Plugin ordering controls.
4. Independently review source/version semantics and the adverse private
   receipts. Do not approve K-0073 or Stable before resolving this issue
   or enforcing a separate fail-closed safeguard.

Agent Communication is a separate project and remains out of scope.
