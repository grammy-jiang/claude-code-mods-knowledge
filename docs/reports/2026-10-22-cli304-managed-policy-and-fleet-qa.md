# CLI 2.1.304: isolated managed policy precedence and three-host signed inventory QA

**Date:** 2026-10-22 AEDT. **Issue:** #110. **Verdict:** restricted QA
evidence; all new 304 Claims unapproved and Stable release HOLD.

This work continues the one Claude Code Mods SSOT repository. Production
CLI, machine-level managed settings, Skills, ChatGPT Plugin accounts and
previously running Claude sessions have not been updated or interrupted.

## Official policy contracts

First-party documentation consulted during this implementation:

- https://code.claude.com/docs/en/managed-settings
- https://code.claude.com/docs/en/settings
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/permissions

Managed settings take precedence over ordinary user/project settings and
the per-session --settings argument, except for documented stricter lower
level settings. Linux reads file-delivered policy from
/etc/claude-code/managed-settings.json; macOS reads
/Library/Application Support/ClaudeCode/managed-settings.json.
The managed-only keys allowManagedHooksOnly and
allowManagedPermissionRulesOnly narrow lower-precedence policy sources.
Hook checks must fail closed (onFailure: block) rather than allowing tool
execution when the check executable is unavailable. Managed hooks have a
distinct source and are not meant to disappear when a reloadable Mod fails.

The project has not established that a private user can enforce immutable
organization-level settings against all Claude processes. File-based
managed settings have documented administration/delivery boundaries.
No organization Team/Enterprise admin console or MDM policy was changed.
Server-managed settings and multi-tenant policy precedence remain out of
scope for this test.

## Native CLI 304 experiment without editing the host /etc

Raspberry Pi 5 used bubblewrap to mount a temporary, QA-only managed
settings directory over /etc/claude-code INSIDE the isolated filesystem.
The real host /etc remained untouched; first-party Claude Code 2.1.304
was launched using its existing SHA-pinned ARM64 test binary. The original
authenticated Sonnet native tool events and debug traces remain in a
mode-0700 private evidence folder on the Pi.

Three original native host experiments were independently re-audited:

| Scenario | Actual native result |
| --- | --- |
| Managed deny list for Write/Edit/Bash plus CLI --allowedTools Read,Write | Real Read succeeded; real Write returned an error and created no file |
| Managed PreToolUse denies Read, while lower-priority --settings requests disableAllHooks | Real Read was denied, with exact managed-hook refusal marker |
| allowManagedHooksOnly true, with a non-managed --settings PreToolUse trying to deny Read | Real Read succeeded; marker of untrusted non-managed Hook absent |

The negative controls deliberately use harmless test files. The managed
settings and lower-priority test snippets are preserved as source-pinned
fixtures under evals/fixtures/cli304-managed-sandbox-20261022.
The original executable .py Hook fixtures are committed as .py.txt evidence
artifacts with exactly identical bytes, not as runnable or reformatted source.
The independent script scripts/audit_cli304_managed_policy.py verified
three original native JSONL/debug receipts and their source hashes twice,
with identical sanitized output:
docs/reports/2026-10-22-cli304-managed-native-sandbox-evidence.json.

**Limited interpretation:** this establishes the observed precedence on one
real 2.1.304 Linux ARM64 host in a controlled file-system namespace.
It does not prove production administrator deployment or managed policies
on the MacBook Pro/Sextant. A passing offline fixture test is not itself a
genuine host-policy attestation.

## Signed read-only fleet observations: MacBook Pro, Raspberry Pi, Sextant

Three separate machines generated independent Ed25519 QA keys (private key
restricted to the current user and NEVER committed). A single random 256-bit
challenge from the Mac was distributed to each observer. Each produced a
canonical JSON snapshot containing only host label, platform, challenge,
issued/expiry epochs, process candidate counts and strict statements of
non-coverage. No PID, argv, native session ID, home path, credentials,
repository names or prompt content were placed in these snapshots.

Mac verified all three public-key signatures and the SAME challenge within
the 180-second observation window. The historical record is at
docs/reports/2026-10-22-cli304-three-host-signed-fleet-evidence.json.
Original signed (non-secret) receipts and their public keys are under
evals/fixtures/cli304-three-host-signed-20261022.

| Signed host label | Read-only Claude process candidates | Complete managed gate coverage |
| --- | ---: | --- |
| macbook | 0 | **NOT ATTESTED** |
| rpi-a | 13 | **NOT ATTESTED** |
| rpi-b | 1 | **NOT ATTESTED** |
| **Total** | **14** | **NOT ATTESTED** |

The historical evidence was verified at 2026-10-22 18:35:13 AEDT. Its
earliest expiry was approximately 18:37:53 AEDT. It must NOT be reused as a
live online presence or current fleet coverage claim after its expiry.
The auditor allows an explicitly marked historical-as-of replay for CI;
this only validates original signature correctness, not present liveness.

Signed snapshots establish a stronger provenance and freshness claim than
unauthenticated remote self-reporting, but not a cryptographic guarantee
that an observer found EVERY running native agent or that its policy is
loaded. Every collector currently reports complete_host_session_inventory_
attested=false and production_coverage_proven=false. The all-host verifier
therefore leaves cross-machine quiescence and Stable release disallowed.

All per-host private keys are isolated in QA directories on their original
machines. The source and tests use an explicit OpenSSL executable and
Ed25519 signatures, not a shared HMAC master key. Independent signed
receipts are not TPM-backed remote attestation, and compromise of a
user-owned host can still forge that host's claims.

## Release and safety decisions

- P1 managed-settings precedence: **isolated actual-host partial PASS**
  for the three scenarios. No existing production managed policy deployed.
- Three expected host signatures: **3/3 valid in historical time window**.
  Complete session inventory: **not established**.
- Any missing host, wrong signature/key, altered counts, mismatched
  challenge, expired receipt, replay beyond the signed interval, or
  purported production-complete assertion is rejected by the QA verifier.
- New CLI304 Claims: zero approved. Stable remains HOLD.
- The Agent Communication project remains outside this work.

Next mandatory milestone for real protection is **authorized, centrally
provisioned managed settings or OS-level containment on every relevant
host**, a trustworthy full process/session inventory, authenticated
live-session policy-health reporting, and freeze/recovery tests across
actual continuously running hosts. User-changeable --settings flags and
historical read-only snapshots do not suffice for production.
