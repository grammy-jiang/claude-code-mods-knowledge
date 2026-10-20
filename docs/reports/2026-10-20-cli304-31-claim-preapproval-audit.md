# CLI 2.1.304: 31-Claim preapproval and 302 type-conflict mitigation

Date: 2026-10-20 Sydney. **Publication NOT AUTHORIZED.**

The latest first-party Claude Code v2.1.304 release is the review
target, not an approved Mods knowledge version. The installed Mac CLI
remains 2.1.302; Raspberry Pi currently runs 2.1.303. An official
Linux ARM64 2.1.304 release asset and native binary were SHA-verified
and evaluated inside an OS sandbox without installing, changing account
settings or calling models. The source review is in PR #98.

## All 31 original 302 Claims accounted for

Every currently approved CLI-scoped 2.1.302 Knowledge Claim
(K-0039 through K-0069) has its own row in the adjoining JSON:
immutable original Claim and decision SHA256s, version scope,
English subject, exact official source URLs, affected area, priority
review lane and a specific unanswered 304 verification question.

First-party release notes and the native core types prove relevant
API changes rather than full compatibility: tool.check gains
read-only metadata and human decider behavior; skip-hook transcript
diagnostics and failed-reload recovery also changed.

Every one of the 31 rows remains explicitly UNAPPROVED under 304.
Native mock successes cover only specific scenarios. No 304 Claim
has been approved by the SSOT validator, no 304 Skill can be compiled,
and no 304 ChatGPT Plugin was published. Generic 2.1.303 release
notes cannot prove identical behavior to 302.

## K-0068: approved 302 source contradicts reviewed core types

The immutable approved original K-0068 statement includes a
console.log inline observer illustration. Genuine Codex/Sonnet
CLI302 original examples and the FIRST-PARTY embedded native core
TypeScript declaration show TS2584 failures for this global in
three of five original snippets. A TEST-ONLY replacement using
$.ui.log(text, { to: "debug" }) satisfied the narrow core typing
test but is not the actual generated model output.

The compiler now emits a visible, source-attested P5 type caution
adjacent to K-0068 in BOTH references/events.md and
references/claim-evidence.md. It retains the exact original
approved text and official anchor for audit, while warning
that the console-based illustration is NOT copy-ready runnable
Mod code. The 2.1.296 output remains unchanged.

This is a MITIGATION, not a replacement normative Claim. A new
approved Claim ID and decision history with real CLI-specific
proof are required before marking it corrected for 304. No
historical source or approval event was modified.

## New release and permission checks required

- Verify tool.check decider person with actual host/user callback,
  including refusal when nobody can be asked, catch and managed guard
  precedence, not only synthetic native tests.
- Verify when isReadOnly metadata is present and whether event
  immutability and Mod order assertions still hold.
- Verify transcript diagnostics for prior-plugin hook skipping and
  failed Mod reload recovery/state lifetime across sessions.
- Re-pin each other original 302 Claim to 304 official documentation
  plus target-matched native tests; preserve distinct source revisions.
- Generate dynamic full built-in tool types only from an authorized
  genuine plugin load, never from older 2.1.277 declarations.

The original P4 eight-boundary strict Plugin autoactivation result
remains 6/8 FAIL, current full 46-case Chat Mode qualification
is incomplete, ChatGPT Plugin account management earlier returned
HTTP 401, genuine current Pi Agent Qwen inference is resource blocked,
and Stable release remains HOLD.

Agent Communication is a separate excluded project.
