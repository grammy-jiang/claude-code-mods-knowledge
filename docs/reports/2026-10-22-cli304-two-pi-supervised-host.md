# CLI 2.1.304: two Linux hosts under isolated managed supervision

Date: 2026-10-22 Australia/Sydney. Tracking: GitHub Issue #110.
**Result: authentic controlled-host partial PASS. Stable and all new 304 Claims HOLD.**

The same SHA256-pinned original Claude Code 2.1.304 Linux ARM64
executable ran in private Linux mount namespaces on Raspberry Pi 5
(rpi-a) and Sextant (rpi-b). Sextant's official versioned release
archive was independently downloaded and verified against the previously
recorded original archive SHA256
17cc5d933babad064bed65b3a4fbafab29556fbbfc12aa7888ae1f6c320e08c5.
Both extracted actual native executables matched
c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3.
Neither installed production CLI, any existing session, account, Skill or
physical machine's /etc directory was changed.

## Independent managed host boundary

The QA launcher is scripts/cli304_supervised_qa.py. It starts only a
fixed, bounded benign Read scenario inside Linux bubblewrap. Host root
is mounted read-only, selected temporary QA directories writable,
and a private 0600 managed-settings.json is mounted read-only at
/etc/claude-code/managed-settings.json inside the sandbox.

The managed settings define allowManagedHooksOnly and
allowManagedPermissionRulesOnly, deny Write/Edit/Bash, and register one
independent managed PreToolUse command hook with onFailure: block.

The external hook is scripts/cli304_supervised_pretool.py. It allows
only an existing file Read from the isolated QA workspace when its
privately owned supervisor lease is fresh, properly formatted, still
associated with the correct native session and actual live parent.
Unknown native tools, corrupted/missing state, unexpected processes,
wrong boot identity, PID reuse, symlink escapes or frozen state
default to refusal.

The state machine src/mods_knowledge/cli304_supervised_lease.py holds a
0600 atomically replaced JSON lease in a 0700 QA directory. It binds
Linux boot UUID, supervisor PID and start ticks, random generation,
session ID, monotonic deadline and phase. A supervisor heartbeat renews
at 300ms intervals with a short two-second lease. Frozen/blocked
supervisors cannot silently restore ready status without a new
generation. The parent cleans up its own process group on exit.

Official upstream references:
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/permissions
- https://code.claude.com/docs/en/hooks

## Four authentic native host scenarios

Two actual Sonnet 5.5 runs on each of two physical hosts, each with
two tool calls inside a SINGLE continuing Claude Code 2.1.304 process:

| Actual same-process scenario | rpi-a | rpi-b |
| --- | --- | --- |
| Supervisor moves from ready to frozen | First Read succeeds, second blocked | First Read succeeds, second blocked |
| Supervisor stops renewing while native process remains alive | First Read succeeds; after lease expiry next Read blocked | First Read succeeds; after lease expiry next Read blocked |

The real native JSONL/debug contains two Read tool uses and two
successful native result messages, including the first benign file
content, the second explicit independent hook denial, managed policy
loading and the exact CLI version. The model was genuine authenticated
Sonnet, not a simulated test double. No protected real user files,
external shell tools or installed production programs were modified.

Independent script scripts/audit_cli304_supervised_native.py replays the
original native wires, debug, SHA-pinned code and policy files,
process/session continuity and final blocked state. It was executed on
BOTH original machines from separately preserved mode-0700 private
archives; the resulting redacted JSON was byte-identical to the
original report on each host. Signed private QA records, full model
text, session identifiers, boot identifiers and PID values stay off Git.

The public report is
docs/reports/2026-10-22-cli304-two-pi-supervised-native-evidence.json.

## Live supervisor Ed25519 witness versus current freshness

At a real time when the managed binary process and short supervisor
lease were BOTH active, each host observed its managed policy file,
actual native successful Read, unique process group, CLI identity,
parent PID/start ticks, and fresh lease. Each machine signed its own
short-lived observation with a different locally owned Ed25519 QA key.
The raw signed payload contains hashed process and boot identifiers;
it and the PRIVATE keys remain in owner-private host directories.

The coordinating Mac received the two original signed observations
AFTER their 14-second validity intervals expired. The verifier
**correctly refused live readiness**. At the original observation
instant, the historical detached signatures verify with each host's
public key and the same random challenge. Historical replay is
explicitly marked as such and never authorizes current operations.

The signed private host observations are not TPM-backed remote
attestations and cannot show coverage of other native sessions.
Public evidence contains only the historical report hashes, not
the hashed underlying device/process fingerprints.

## What is still NOT implemented

The managed boundary only applies to sandbox-launched QA Claude
processes. Other existing local or remote/background Claude sessions
are not automatically discovered, restrained or migrated. No machine
system policy or MDM enrollment has been deployed.

Most critically, the short-lived lease checks local supervisor
heartbeats. A local supervisor could continue renewing even after
the coordinating Mac becomes unreachable. **No real cross-machine
coordinator-disconnect forced refusal has yet been proven.**
The loss-of-heartbeat test simulates local renewal failure, NOT an
actual remote network partition.

The Linux namespace is a user-owned QA environment, not an
OS-level privilege-separated mandatory supervisor. User-owned lease
files and private signing keys can be modified by their owning user;
unknown daemonized descendants are not guaranteed contained by
a simple process-group kill.

All version-specific CLI304 Claims remain unapproved. Chat Mode P4
46-case, Claude/Codex/Pi model P5, and Stable P6 remain HOLD.
Agent Communication is a different project and remains out of scope.

**Next security milestone:** require short-lived coordinator-issued,
signed epoch authorization before local heartbeat renewal, then test
deliberate two-host partition, timeout, rediscovery and repair.
Production scope would still require a complete authenticated native
session inventory and mandatory managed policy distribution.
