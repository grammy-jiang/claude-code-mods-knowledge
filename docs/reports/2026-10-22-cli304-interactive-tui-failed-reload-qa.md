# Claude Code CLI 2.1.304: actual interactive TUI failure/recovery

**Date:** 2026-10-22 AEDT. **Result:** real interactive TUI path confirmed,
but not production-wide security acceptance. **Stable remains HOLD.**

The [previous recovery report](2026-10-22-cli304-failed-reload-recovery.md)
correctly recorded an earlier interactive attempt as **NOT VERIFIED** because
a previously blocked input remained in the TUI composer and the reload command
was not submitted independently. This new, separate experiment changed the
ordering to update and submit /reload-plugins before the first blocked prompt.
It does **not** rewrite or retroactively change that historical result.

## Real host and control scope

- Original first-party SHA-pinned Claude Code **2.1.304**, Raspberry Pi 5,
  authenticated to real Sonnet 5.5, **interactive pseudo-terminal (TUI)**.
- Local-scope Plugin was genuinely installed from a private disposable
  marketplace, with private cache and settings. The source and all version
  changes occurred only in the disposable QA directories, not in the
  user's installed production CLI, Skill or account.
- TUI supplied no model tools and selected conservative permission mode.
  Prompts were harmless sentinels, not requests to execute user-file actions.
  No approval button was selected or production permission modified.
- One running terminal/host, with the native debug timeline and visible
  terminal stream retained privately for audit.

## Exact observed sequence

| Native TUI phase | Actual observation |
| --- | --- |
| Initial original QA Plugin | Old benign prompt.submit Hook module loaded and registered |
| Update to malformed v0.0.6 | Official native strict validation **failed** (exit 1), while deliberately unchecked official Plugin update succeeded |
| First independently submitted /reload-plugins | Native debug recorded JavaScript parse error, prior Hook unloaded and zero active Hook entries |
| Harmless model request during failure window | Original Hook was absent, native turn started/completed and an actual assistant response was visible in the terminal, not just an echoed prompt |
| Update to valid v0.0.7 | Native strict validation **passed** (exit 0), official Plugin update succeeded |
| Second independently submitted /reload-plugins | Repaired Hook module loaded and registered |
| Harmless prompt after repair | Native Hook entry and short-circuit observed; original benign sentinel did not pass to the model |

The original debug events prove an ordered sequence of initial load,
failed reload, actual model turn, successful reload, registered Hook, and
final short-circuit. The terminal bytes independently include two reload
responses and a distinguishable assistant output marker during the unsafe
window. Importantly, **the old Hook was only confirmed loaded initially**:
this experiment did not claim that it had handled a prompt before the first
malformed upgrade. This is supported by the earlier independent baseline
tests, but we do not silently combine separate native turns into one.

## Independent SHA-bound evidence

The original interactive screen control bytes, native debug, original
test driver summary, candidate bytes and versioned cache were copied into
an access-controlled private Pi evidence folder. No complete transcript,
session identifier or credentials were copied to the public repository.

The independent auditor,
**scripts/audit_cli304_tui_recovery_evidence.py**, verifies:
- SHA-pinned official native executable and the exact clean source trees of
  malformed v0.0.6 and valid v0.0.7, plus native strict-validation outcomes.
- Correct original installed-cache file sets, distinguishing host-generated
  .orphaned_at metadata from the reviewed Plugin package.
- Actual source/version/update chronology and the authenticated TUI's
  parse failure, module unload, native model response, re-registration and
  subsequent short-circuit, in the correct timestamp order.
- Real assistant output marker (after stripping ANSI cursor controls), rather
  than treating the same marker in an echoed prompt as model completion.
- Exact private terminal/debug/driver fingerprints and explicit HOLD policy.

The sanitized public report is
[2026-10-22-cli304-tui-reload-host-evidence.json](2026-10-22-cli304-tui-reload-host-evidence.json),
backed by audited clean test fixtures under
**evals/fixtures/cli304-tui-recovery-20261022/**. Replay from the
persisted private Pi evidence reproduced **byte-for-byte identical** public
JSON. The separate CI test checks these source and report fingerprints,
absence of raw private data, and fail-closed approval status; it cannot
recreate live TUI interaction or attest cryptographically signed host events.

## Practical significance and unresolved scope

**The observed unsafe reload window is not confined to the --print host.**
It also arises in this tested local-scope **real interactive TUI** host.
Repairing a Plugin and reloading can reactivate the lost Hook in that host,
but this does not guarantee continuous protection during the intervening
failure period or automatically repair any other live sessions.

The earlier PR #112 preflight/postflight checker is **QA-only** and remains
unchanged by this observation. Production safety would require externally
enforced quiescence of guard-dependent operations, exact installed bytes,
per-session live Hook health attestations or restart, and fail-closed status
until every affected session is known safe. These capabilities are not yet
implemented and were not asserted by the test.

Also unverified: managed organizational permissions and precedence, successful
positive human approval, other Plugin installation scopes/hosts, command/tool
retention guarantees separate from Hook continuity, and complete high-risk
Claim approval. No CLI 2.1.304 Claim has been approved and no new stable or
Plugin release is authorized. Agent Communication is excluded from this project.

Tracking: [Issue #110](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/110).
