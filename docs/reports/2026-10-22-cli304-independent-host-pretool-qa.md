# CLI304 independent PreToolUse host guard: genuine native QA

Date: 2026-10-22 Australia/Sydney. Tracking: GitHub Issue #110.
**Verdict: scoped QA prototype only; Stable and all new CLI304 Claims HOLD.**

This continues the same Claude Code Mods SSOT repository and the existing
managed-cohort QA milestone. It does not modify production CLI, Skills,
the user's real Plugin accounts or any existing live Claude processes.

## First-party source and design boundary

Official Claude Code documentation explicitly distinguishes an exit-2
blocking error from ordinary hook failures that allow execution. Starting
with CLI 2.1.295, a command PreToolUse hook with onFailure: "block"
can block when its executable cannot start, returns an invalid result, or
times out. External settings hooks have a different lifecycle from the
reloadable Mods API.

Sources:
- https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails
- https://code.claude.com/docs/en/hooks#pretooluse
- https://code.claude.com/docs/en/permissions#precedence-among-rules-hooks-and-mods

This investigation loaded an explicit private --settings file, NOT centrally
managed organization policy. A CLI instance that did not load this exact
settings file cannot be counted as protected. No claim is made that the
host's built-in or organization-managed permissions can be bypassed.

## Actual implementation

- src/mods_knowledge/guarded_rollout.py now associates a native tool_use_id
  with a persistent per-session external permit. PreToolUse grants a permit
  only to an authenticated enrolled session while the cohort is ready.
  PostToolUse and PostToolUseFailure release only a matching started permit.
  Missing completion leaves the permit held and therefore blocks updates
  instead of silently expiring a running tool.
- scripts/cli304_host_tool_gate.py parses native input and verifies the
  enrolled session, private secret, event identity and exact existing path.
  The narrow reviewed QA rule allows only Read of files inside its private
  workspace. Write, Bash, Edit, MCP and unknown tools are refused.
- scripts/cli304_host_tool_settings.py emits three direct exec-form
  command hooks, with a 12-second timeout and onFailure: "block".
- scripts/audit_cli304_host_tool_evidence.py independently parses private
  native event/debug files to produce SHA-linked sanitized release-HOLD
  evidence. No raw session ID, token, command prompt or full transcript is
  published.

The private QA setting is user-owned and can be omitted or modified by
the owner. It is not an immutable OS policy or mandatory launcher, and
does not stop unregistered agents.

## Official 2.1.304 authenticated target-host observations

Raspberry Pi 5 ran the original SHA-pinned first-party ARM64 CLI with an
authenticated Sonnet model. Only temporary harmless files were accessed.

| Actual scenario | Observed outcome |
| --- | --- |
| Unregistered native session | Actual Read and Write denied by external hook |
| Enrolled, real healthy session | Actual Read succeeded; actual Write denied even if preallowed for the isolated QA |
| PostToolUse after successful Read | The native tool-use permit was released; zero outstanding permits |
| Same host after deliberate Mod parse failure and unloaded old Mod | External PreToolUse still denied Write both before and after reload |
| Missing PreToolUse executable, no onFailure: block | Real Read went through: intentionally unsafe negative control |
| Same missing executable, with onFailure: block | Real Read blocked, file contents not disclosed |
| One continuing streaming native session | Read succeeded while ready, then coordinator switched to quiescing and the next Read was denied without restarting Claude |

Two authentic native guard challenges were used for initial enrollment.
The first attempted live-fence run was denied by the expected expired-lease
policy before a positive baseline and is EXCLUDED from the final two-turn
transition claim. A separately bootstrapped fresh session completed the
valid before-and-after freeze experiment.

Original native wire JSONL, debug logs, session metadata, secrets and actual
host settings were preserved in an owner-only private Pi evidence directory
outside Git. Replaying the independent auditor from persisted evidence
twice produced byte-identical sanitized JSON. Review:
docs/reports/2026-10-22-cli304-host-level-pretool-evidence.json.

The original logs are user-writable, not signed native attestations.
Passing this QA evidence does not establish a production-ready host
authorization layer.

## Three-machine process visibility snapshot

Read-only process-name scans showed zero visible native Claude process
candidates on the MacBook Pro, 13 on Raspberry Pi and one on Sextant.
None were independently attested as loading this specific host gate.
The snapshot is incomplete and time-dependent: it does not establish
a complete process/session inventory, nor prove the other instances
are vulnerable. None were restarted, inspected for private data or altered.

Production enforcement remains blocked until all affected sessions,
including background and remote ones, can be independently inventoried
and forced through a trusted host/tool-level boundary. A user-supplied
settings file cannot guarantee global adoption. Managed policy
precedence and the full native tool taxonomy are unverified.

## Release boundary and next steps

Keep Issue #110 OPEN. The reviewed CLI304 Claim count remains zero.
P4 Chat Mode 46-case acceptance, P5 multi-agent model quality, and P6
Stable remain HOLD.

Next production milestone: verify an authenticated, complete active-session
inventory; enforce mandatory native host settings or OS-level containment
outside hot-reloadable Mods; prove crash/timeout and multi-machine
quiescence; obtain real live per-session reload health and independent
rollback review. Agent Communication is not part of this project.
