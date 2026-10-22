# CLI 2.1.304: opt-in managed Plugin update coordinator (P1-D)

**Verdict: controlled QA only. Production-wide safety and Stable remain HOLD.**

This effort continues Issue #110 in the original Claude Code Mods SSOT repository.
The pinned native Claude Code 2.1.304 was tested on Raspberry Pi 5, Linux
ARM64; macOS/Linux code uses POSIX flock and must not be assumed portable to
Windows or to a multi-machine filesystem.

## What is genuinely protected?

The coordinator is an external, fail-closed authorization gate for known,
cooperating sessions. Only protected actions invoked THROUGH the managed
launcher can be stopped. It does not intercept built-in Claude Code tools,
arbitrary running instances, managed organization permissions, or an agent
that bypasses the launcher. The loaded Hook can disappear on a bad reload;
the external gate continues to deny opt-in operations, but cannot directly
freeze an unregistered native agent or a disconnected computer.

Therefore this is not a production-wide transactional Plugin updater. A
production solution needs host-level enforcement independent of Plugins,
authenticated complete session inventory, cross-machine fencing, quiescence,
and durable recovery before protected operations can resume.

## Implemented parts

1. Source file src/mods_knowledge/guarded_rollout.py: private mode-0700 state
   directory, mode-0600 atomic JSON state and lock file, POSIX file locking,
   SHA256-hashed 256-bit session secrets, exact session inventory (max 32),
   distinct fencing epochs and one-time host-health challenges. State survives
   coordinator restarts. The default heartbeat lease is 120 seconds.
2. Source file src/mods_knowledge/guarded_host_probe.py: requires the original
   SHA-bound 2.1.304 private native wire, exact session identity and version,
   matching fresh challenge in a zero-model-turn Hook refusal, and the native
   debug Hook loading/registration/dispatch trail. Raw files are owner-writable,
   NOT independently cryptographically host-signed.
3. Script scripts/guard_cli304_managed_run.py: optional external subprocess
   wrapper. Acquires a permit, runs a precisely specified managed command,
   and releases the permit only after normal process exit. Unknown or stale
   session credentials and any frozen phase block execution before launch.
   A timeout blocks the cohort and does not assume descendants are gone.
4. Script scripts/audit_cli304_cohort_p1d.py: replays real private native
   evidence and final persistent gate states. Publishes only bounded outcome
   facts and source/wire SHA256 fingerprints.
5. Source fixture evals/fixtures/cli304-p1d-cohort-20261022: harmless JS
   prompt.submit guard which refuses a unique one-time challenge. No shell or
   write tool is exposed to the QA probes.

## State machine and failure handling

    blocked (initial)
       | explicit enrollment + all genuine per-session baseline proofs
       v
    ready -- begin --> quiescing
                       | no new permits, all existing permits released,
                       | every expected session acknowledges quiescence
                       v
                     applying
                       | exact native binary SHA, candidate name/version/tree
                       | and strict native Plugin validation
                       v
                     verifying
                       | recheck installed bytes; new nonce and genuine
                       | matching native Hook health proof for every session
                       v
                     ready (new version)

    FAILURE while frozen
      -> rolling_back (increment fencing epoch)
      -> restore exact reviewed old Plugin bytes
      -> recheck installed old bytes
      -> fresh old Hook proof from EVERY managed session
      -> ready (old version), but candidate update is REJECTED

    Rollback failure / unknown state / managed-command timeout
      -> blocked until separate audited recovery.

An open permit cannot expire and disappear merely because its process stops
heartbeating. This deliberately blocks updates if an in-flight operation has
not been proven complete. A crashed coordinator leaves a non-ready state.
No permissive force-ready switch is implemented. The installed tree is
independently re-hashed at final release; a caller-reported digest alone is
not sufficient.

Candidate preflight uses the original SHA-pinned native 304 binary and a
private frozen copy of the exact reviewed Plugin. It rejects symlinks,
nonregular files, unreviewed bytes, wrong manifest name/version, parser errors
and native warnings about unguarded Hooks, even when validation exits zero.
It cannot guarantee that an unrelated runtime exception will never occur.

## Optional external launcher

Run only within a fully owned, explicitly enrolled and attested QA cohort:

    uv run --offline --group dev python scripts/guard_cli304_managed_run.py       --state-root /private/cohort/gate       run --session-id managed-session-A       --secret-file /private/cohort/managed-session-A.secret       --timeout-seconds 120 --       /usr/bin/python3 /private/qa/known-safe-command.py

Read-only redacted status:

    uv run --offline --group dev python scripts/guard_cli304_managed_run.py       --state-root /private/cohort/gate status

The private session token file must be owned by the user and mode 0600.
A complete production-safe deployment/rollback CLI is NOT provided;
initialization, quiescence and managed QA updates are Python APIs. Never
give an LLM an arbitrary untrusted shell command to execute as the wrapper
child. A child that daemonizes or evades its process group is not reliably
tracked by this wrapper.

## Completed actual-host evidence

On the Pi, two separately registered managed cohorts of two participant
identities used a total of **eight genuine, fresh CLI304 native QA probes**.
These were separate authenticated host invocations and NOT live reloads of
two continuously running TUI processes.

| Scenario | Verified outcome |
| --- | --- |
| Candidate valid | Two old and two new authentic guard proofs; all 2/2 attested after update; epoch 0 to 1 |
| Candidate bad in second-session check | Old-version rollback; two new independent old-guard proofs; 2/2; epoch 0 to 2 |
| External managed launcher | A genuine CLI304 was launched under a permit and its harmless Hook denied before inference; after freeze, another managed child was refused before it could create its test marker |

Every native guard probe had zero model turns and was bound to its session ID,
fresh nonce, Plugin source SHA and controller epoch. The actual native host
wires, secrets and coordinator states are preserved in a private 0700 Pi
evidence directory outside Git. The auditor re-verified its persisted copies.

The public immutable source fingerprints and sanitized evidence are in
docs/reports/2026-10-22-cli304-p1d-managed-cohort-evidence.json.
CI cannot recreate an authenticated native session or cryptographically
certify the source of owner-writable logs.

## P1-D1 through P1-D4 disposition

| Unit | Implemented/tested | Not achieved |
| --- | --- | --- |
| D1 exact preflight | Original pinned CLI binary, frozen source tree, manifest, strict validation, TOCTOU recheck | Production compatibility approval |
| D2 compensation | Controlled QA apply, exact installed tree check, native per-session health, automatic old-version rollback; refuse on recovery failure | Host-level control of native unmediated tools |
| D3 multiple sessions | Explicit membership, hashed tokens, heartbeats, in-flight permits, POSIX lock and epoch fencing; genuine 2-session QA proofs | Complete discovery/suspension of all unrelated active hosts and cross-machine consensus |
| D4 faults | Source mutation, symlinks, warnings, stale leases, wrong sessions, lost proof, process crash, command timeout, partial cohort and rollback failure | Production distributed crash recovery and organization permission precedence |

The 2.1.304 K-0070 through K-0074 Claims remain unapproved. Full Chat Mode
46-question qualification, broader host/model evaluation, and Stable remain
HOLD. Agent Communication is a separate excluded project.

## Next production milestone

Build a host-level or externally supervised enforcement mechanism that truly
controls EVERY affected live session and its protected native tools, including
other machines, before using automated Plugin replacement outside private
QA. Require explicit inventory attestation, cooperative quiescence, real
in-session reload proof, rollback, and an independently reviewed release
decision. Do not publish this opt-in gate as a general security boundary.
