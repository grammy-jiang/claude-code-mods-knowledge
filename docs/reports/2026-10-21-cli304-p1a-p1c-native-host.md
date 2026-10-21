# CLI 2.1.304 P1-A/B/C: installed Plugin reload, interactive permission UI, actual read-only metadata

**Date:** 2026-10-21 Australia/Sydney. **Host:** Raspberry Pi 5, Linux ARM64.
**Publication and production compatibility: HOLD.** This is a scoped native-host
investigation, not confirmation of all host surfaces or permission policies.

## Scope and official source

The original official Claude Code 2.1.304 Linux ARM64 binary was run from an
independent private path and SHA-verified:
c487117526509ab6d2ee6013e14f181faf68d6d6afe6bb0d4b2b4a9feca5ecb3.
The model identity in actual native wires was claude-sonnet-5-5; effort was
requested as medium, not independently attested by the native wires.

Native Plugin loading and permissions were examined against the official
[Claude Code Plugin installation and scopes documentation](https://code.claude.com/docs/en/plugins/install),
[marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference),
and the earlier pinned versioned Mods sources. Reviewers must distinguish
the official release's *commands and tools* failed-reload claim from an
unproven guarantee that all previously loaded safety Hooks remain active.

The prior inline-plugin baseline is in
[PR #109](https://github.com/grammy-jiang/claude-code-mods-knowledge/pull/109),
with the open cross-version risk tracked in
[Issue #110](https://github.com/grammy-jiang/claude-code-mods-knowledge/issues/110).

## P1-A: genuine installed Plugin, versioned update and failing reload

An isolated local marketplace named mods-p1a-private-local-20261021 was
registered and the innocuous QA Mod qa-guard304-host version 0.0.1 genuinely
installed at **local** scope. CLI list readback proved it was enabled and its
versioned installed path belonged to a private temporary Plugin cache.

The correct installed-mode test **did not** use --restricted: that option
suppresses settings files and had initially yielded a false installed-plugin
coverage attempt, in which only built-in Mods loaded. Instead the valid host
used only its private local settings, strict MCP configuration, --tools "" to
disable **all model tools**, permission-mode dontAsk, a no-persistence
noninteractive stream-json session, and the bounded Sonnet model. Private
native debug explicitly attested the real installed QA Hook loading.

The following was performed within **one continuing native host process**:

1. The previously registered version 0.0.1 prompt.submit guard refused the
   benign QA input, before model inference: **0 model turns**.
2. The private marketplace source was changed to version 0.0.2 with an
   intentionally malformed JavaScript Hook module. The official CLI Plugin
   update command returned success; the installed version 0.0.2 private cache
   contained exactly the SHA-attested corrupted source.
3. /reload-plugins returned a Reloaded line reporting **zero Hooks** and
   re-reading the plugin folder. Private native diagnostics independently
   logged the parser error and that **the version loaded before is unloaded**.
4. The same benign QA input then reached the genuine model in **1 model turn**.
   The old guard did not execute a second time.
5. The marketplace source was restored to its good bytes. The invalid new
   installation remains only in the disposable private QA cache.

**Observed adverse result:** the last working safety Hook was lost during a
failed installed-Plugin version change under this specific local-scope,
noninteractive loading profile.

This does **not** demonstrate a generic bypass of built-in/managed Claude
Code permissions, nor prove that project/user/managed Plugin scopes or the
interactive TUI behave identically. It does establish that simply observing
an installed Plugin or a successful-looking reload acknowledgement is
insufficient to attest continued operation of its security Hooks.

## P1-B: real TUI human permission interface

A separate private QA TUI instance was opened under an actual pseudo-terminal.
Its first attempt reached the legitimate workspace-trust confirmation rather
than a model permission decision and was excluded from scoring. After the
private temporary test folder was trusted, a bounded Sonnet turn using only
the Write tool reached a real tool.check event whose incoming decision was
ask. Native debug confirmed the QA permission Hook had been loaded.

The terminal then visibly rendered the real host permission panel asking
whether to create a harmless temporary file and offering a once-only yes,
a broader session auto-approval choice, and no. The test did **not** choose
either approval; the temporary file was absent. The original raw TUI control
bytes and debug trace are retained privately with SHA256 fingerprints.

**Verified:** real interactive permission request and human choice UI.
**Not verified:** human approval yielding a successful permitted action, a
full refusal outcome event after choosing No, managed-policy precedence, or
positive verification that the specific person-decider result differs from
the host's default ask behavior.

## P1-C: real four-tool metadata classification

Four distinct bounded authentic native turns explicitly invoked the target
tool once. The deny-only test Mod rejected each call before its tool could
execute, including all writes.

| Actual tool | Observed tool.check e.isReadOnly | Original host decision |
| --- | --- | --- |
| Read | true | allow |
| Glob | true | allow |
| Grep | true | allow |
| Write | undefined | ask |

Every row is backed by a source-pinned native tool-use event, a matching
actual Hook debug marker, and a denied tool result. The new Write target did
not exist after the experiment.

**API guidance implication:** isReadOnly is an optional true-valued flag in
the tested target; no check for e.isReadOnly === false may be used to
recognize a Write. The absence of the property is not a universal write
indicator for every tool, and this four-case sample does not establish the
full built-in tool classification taxonomy.

## Evidence, CI and release policy

The complete private native JSONL and debug files, TUI escape sequences,
model messages and project identifiers were not committed. Only
[digest-linked sanitized factual records](2026-10-21-cli304-p1a-p1c-native-host-evidence.json)
and the harmless marketplace/Hook test-source fixtures are public.

The necessary private source, installed-version cache metadata, raw host wires,
debug and pseudo-terminal files were also preserved in a separate access-0700
evidence directory on the originating Raspberry Pi, outside Git and unrelated
production Plugin directories. Copying that 352 KiB private evidence set and
replaying the frozen auditor produced an **identical sanitized JSON report**.
The host's standalone official 304 executable remains a separately SHA-pinned
artifact. This preserves the replay inputs beyond temporary-directory cleanup.

An independent read-only auditor,
scripts/audit_cli304_p1a_p1c_live.py, verifies the true native wire/model
events, installed source/version SHA identities, UI marker, actual refusal
and negative guard-loss sequence before emitting the bounded public report.
This script fails closed on missing/mismatching private data and does not
perform a fresh model request. CI tests check the public evidence, script
fingerprint, original source bytes and negative release classification,
not a new authenticated model replay.

The Claim validator is additionally hardened for CLI 2.1.304+ so that
versioned tool.check, prior-plugin Hook skip and failed-reload guidance all
require pinned **integration-pass** evidence before becoming approved,
irrespective of whether their primary knowledge area is P, T, E or S.
This requirement does not rewrite earlier version approvals or automatically
promote any of K-0070 through K-0074.

**Still blocked:** all 31 original 302 Claims remain unapproved for 304;
K-0073 and Stable remain HOLD. P4 full Chat Mode qualification, full P5
three-agent genuine acceptance, installed scopes beyond local, TUI
successful approval and managed permission precedence are unverified.

## Next execution units

1. P1-A: check whether failed installed version recovery preserves commands
   and registered tools separately from Hooks, and repeat in a truly interactive
   TUI and another isolated install scope. Require fail-closed protection for
   security-dependent actions; do not conflate command availability with Hook
   continuity.
2. P1-B: complete a strictly bounded, harmless affirmative human approval
   control plus managed deny-overrides-allow precedence (without using
   bypassPermissions).
3. P1-C: expand the actual optional read-only metadata classification to
   Edit/Bash and other relevant tools, with explicit denial of every test
   write/command.
4. K-0072: separately test the user-visible skipped-Hook transcript in the
   interactive terminal. Only after independent approval may a reviewed
   versioned Skill be built.

Agent Communication remains a different excluded project.
