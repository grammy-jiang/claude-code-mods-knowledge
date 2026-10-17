# P5 Skill-only reliability improvement — auto-routing and approved evidence

Date: 2026-10-17. This work deliberately does **not** change, fine-tune,
quantize, download, promote, or reconfigure any model or inference server.

## Why the old source metric was low

The native structural scorer requires the requested approved K-Claim ID
and an exact first-party `Source:` URL, including the correct fragment.
A plausible explanation, an imprecise link to the same page, or a
correct code snippet without the citation fails. This scorer is a
**source/format** check, not an independent semantic correctness score.

Previously the Skill's most detailed source-verified instructions lived
under the heading "Directly requested Plugin or Skill". Automatically
discovered Mods work could therefore be interpreted as a weaker path,
despite the shorter general citation instruction later in the Skill.
This is an instruction-scope issue we can fix without model changes.

## Change: same contract for every activated Mods task

The generated `SKILL.md` now applies the same contract to *both*
automatic and explicit activation. Its discovery-listing description
also includes the source contract, before the full Skill is opened.
For a relevant Mods question, the Agent is instructed to:

1. Establish the exact Claude Code CLI version and host. Do not
   implement unreviewed APIs using the 2.1.296 evidence.
2. Actually read the relevant detailed topic reference and the
   compact `references/claim-evidence.md` sheet. Do not fake a
   successful tool read or invent a Claim ID.
3. Begin the answer with an Evidence section, citing each selected
   approved K-Claim ID and corresponding exact official first-party URL.
   Every topic reference now lists the copy-ready pairs *above* its
   detailed guidance; the large cross-topic index remains optional.
4. Check existing approved code guardrails, and distinguish
   source evidence from actual target-CLI semantic/runtime testing.
5. Abstain from unsupported version-specific implementation claims
   rather than attach an unrelated citation.

All 31 claim-to-official-source cards are generated **deterministically**
from the existing single source of truth, never manually authored
or fetched from unrelated community sources. This index is not a new
authority. Both the detailed topic pages and source-review decisions
remain unchanged.

The change compiles byte-identically for Claude Code, Codex, Pi Agent
and the skills-only ChatGPT Plugin. Approved ZIP/Plugin member
allowlists and account/release validators explicitly admit exactly
the one additional reference file while continuing to reject
unreviewed extra resources or missing evidence.

## Verification and honest limitations

Static verification: 31 approved Claims and direct official anchor
locators, compiler/package/release/account/stable-readiness regression,
four-host byte identity and no forbidden archived or candidate Claims.
Packaging success cannot prove a real model followed the Skill.

A separate Mac Qwen3.6 isolated A/B pilot uses *identical*
frozen P4 prompts with the old installed Skill and compiled Skill
candidates. All use native Pi automatic Skill discovery, read-only
scoped tools and the same unchanged Qwen inference API. Original
raw JSONL and full model text stay in private Mac folders.

Initial pilot outcomes: the baseline and first candidate each had
**0/2** positive exact-source structural passes, despite actual Skill
reads. A second candidate with copy-ready lines buried among the
reference guidance also failed. A third candidate places citation
pairs at the TOP of topic references and primes the Skill discovery
description; its first two real positive turns both passed (2/2),
with one correctly unactivated unrelated TypeScript case and one
version-boundary case marked for manual review. This is a SMALL
observed improvement, not a universal success guarantee.

An additional frozen four-positive-case x three independent turn
cohort is used to check whether these results repeat. Never discard
its timeouts/loops or describe a source-structure PASS as native Mod
semantic correctness.

This pilot alone cannot guarantee a success rate across 120B models
or ChatGPT Chat mode. Source-card improvement must not be
interpreted as correct Mod code semantics. A future full P5 acceptance
still requires independent native CLI 2.1.296 behavior testing,
including downstream tool value/error identity.

No installed user Skill, global Pi default, ChatGPT account Plugin,
or production release is changed solely because a compiled
candidate passes static validation. Roll out only after explicit
versioned release and native host acceptance review.
