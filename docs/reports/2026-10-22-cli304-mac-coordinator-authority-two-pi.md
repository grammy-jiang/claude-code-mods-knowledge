# Claude Code 2.1.304: Mac-issued epoch authorization on two Pi supervisors

Date: 2026-10-22 Australia/Sydney. Tracking: Issue #110.
**Result: original-host QA partial PASS for withheld authorization delivery,
expiry and new-generation recovery. Stable and every new CLI304 Claim HOLD.**

Same Claude Code Mods SSOT repository. Original official SHA-pinned CLI304
ARM64 native Claude on Raspberry Pi (rpi-a) and Sextant (rpi-b) inside
owner-private Bubblewrap mount namespaces. Production CLI, real /etc policy,
installed Skills, ChatGPT Plugins and existing user agents were untouched.

## Two independent prerequisites for native Read

The pre-existing Linux managed PreToolUse command hook validates the
native session, live local supervisor boot/PID/start tick/generation,
short monotonic local heartbeat, and benign workspace Read scope.

NEW: that same independently configured managed hook also validates
a **MacBook Pro-issued Ed25519 grant**, including: host allowlist, exact
cohort, fresh run nonce and supervisor generation, native session
digest, machine boot digest, exact managed policy SHA256, official native
binary SHA256, explicit signed epoch, signed wall-clock expiry and an
additional locally recorded monotonic expiry. The local supervisor
renews its heartbeat ONLY while the Mac grant remains verifiable. Even if
a local renewal thread were to continue in error, the native Hook rechecks
the grant on every tool call and independently refuses expired authority.

The only private signing key was created and retained on Mac; Raspberry Pi
and Sextant only received the matching public key and individualized
short-lived signed grants. The signer has an explicit two-host allowlist.
No shared HMAC master secret, production network service or new cloud key
was introduced. Grant TTL was bounded by code to 10 through 30 seconds.

Implementation:
- src/mods_knowledge/cli304_coordinator_grant.py
- scripts/cli304_mac_issue_grant.py
- scripts/cli304_coordinator_pretool.py
- scripts/cli304_mac_granted_supervisor_qa.py
- scripts/audit_cli304_coordinator_native.py

The Linux QA namespace still mounts a private managed-settings.json
read-only at its managed policy path, with onFailure:block, and does
not touch the real host /etc. It permits only a harmless existing Read.

## Genuine first-party target host results

Mac issued host-bound epoch 1 Ed25519 grants with a **24-second**
authorization lifetime. Each original 2.1.304 Sonnet host was allowed
one successful Read during this window. Then no further Mac grants
were delivered, while the Pi local supervisors remained alive:

| Authentic same native host | rpi-a | rpi-b |
| --- | --- | --- |
| Mac epoch 1 authority fresh | Read succeeded | Read succeeded |
| No renewed Mac authority, old grant expired | Supervisor froze and next Read was denied | Supervisor froze and next Read was denied |

These are true first-party native two-turn traces from ONE continuing
Claude Code process per host, not unit-test-only model data. Denied
tool results did not reveal the original benign file marker.

Recovery used a **new supervisor generation** and native session
identity on each Pi. First, each machine verified that the previously
signed epoch 1 envelope was NOT valid for its new request, failing
with the expected cross-generation binding error. Mac then issued
fresh epoch 2 signatures against the two new requests. Both new
authenticated CLI304 hosts successfully performed a real Read.

No frozen epoch-1 supervisor was silently reopened. Both runs
ended with the privately persisted supervisor phase blocked.

The official native executable SHA256 on both Pi hosts was:
c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3.

## Immutable source evidence and privacy

Each Pi independently preserved original native wire/debug, actual
managed policy, root-owned state, request, signed grant, receipt,
source copy and SHA-pinned executable in an owner-private evidence
directory OUTSIDE Git. The independent auditor recomputed the actual
native tool events, exact session binding, historical Ed25519 signatures,
policy hashes, denial on expiry and old-grant replay negative control.
Both hosts produced byte-identical sanitized reports on two replays.

Mac independently compared its original epoch-1/epoch-2 signing
records and per-host generation with both Pi sanitized grant hashes;
its PRIVATE Ed25519 key remained off Git.

Public digests and bounded facts (no private identity, prompt or key):
docs/reports/2026-10-22-cli304-mac-signed-epoch-two-host-evidence.json

Deterministic tests additionally reject wrong host, policy/session,
tampered signature, stale supervisor generation, old epoch,
excessively long TTL, missing grant, invalid private permissions,
clock rollback and independent managed Hook failures.

## Important safety limitation

**This was deliberately stopping delivery of fresh Mac authority,
NOT a physical Mac-to-Pi network partition.** A valid previously
signed grant can continue authorizing this controlled Read until its
short expiry. A persisted, cross-restart Mac signer epoch ledger and
host-wide anti-rollback floor remain unimplemented; the operator explicitly
issued epoch 1 then epoch 2 in this QA run, and the old token failed solely
because it was bound to the old supervisor generation. An actual partition/reconnect of a verified transport
and distributed controller remains the next milestone.

Neither the Mac signer nor the Pi supervisors remotely discover or
protect unrelated existing Claude processes. The experiment is a
user-owned, sandboxed QA protocol, not an OS privilege boundary,
TPM-backed attestation, centrally enrolled organization managed
policy or production-wide transactional Plugin updater.

No CLI304 Claims were approved. Full P4 Chat Mode, P5 model/agent
acceptance and Stable remain HOLD. Agent Communication is not part
of this project. Issue #110 remains OPEN.

## Next step

Implement and test an isolated authenticated coordinator transport:
interrupt actual network delivery, verify short-lease timeout on BOTH
continuing Pi native sessions, then re-establish authenticated contact
and require fresh higher-epoch authorization before a new host
generation can resume. Production use further requires complete
enrolled native session inventory and mandatory managed host policy.
