# Corrected full 46-turn ChatGPT Chat Mode baseline (CLI 2.1.302)

Private original ChatGPT account test used the ordinary Chat Mode interface,
not Work. All 46 unique sends received genuine conversation IDs and 46
final responses were fetched and SHA-recorded. No extra test prompt was sent
in this source audit.

The original 0.4.7-beta.1 score of 27/30 positive structural successes
was undercounted. Two UI/state questions really read the installed skill
entrypoint at the canonical /skill.md alias plus relevant reference files.
The reviewer mistakenly required only the shorter root URI. With that root
alias recognized, 30/30 positives have observed Skill entrypoint/reference
URIs and 29/30 have complete exact first-party citations. One positive
response mentioned K-0048 without its own exact official M002 source URL.
It remains a real source-integrity failure; its required Claim itself was
otherwise present.

All eight unrelated negatives had zero Plugin resource reads (correct).
All eight unsupported-version, permission, source-injection and safety
boundary questions also had zero Plugin resource reads (not acceptable
as automatic activation), even where a general-model answer abstained.
Examples of concerning model-memory-only guidance include unsupported
precise historical Mods version timelines or claiming future-version
implementations can be tentatively sketched. A safe textual refusal without
real Plugin evidence does not clear the Plugin boundary acceptance gate.

The count correction is derived from preexisting private response hashes
and exact skill/reference resource URI metadata. Later re-fetch of at least
one old exact ChatGPT conversation returned conversation_deleted. The
report does not pretend to re-fetch original tool bodies, match a current
account Plugin ID anew, or reexecute old answers. No privacy-sensitive
original response, prompt, conversation URL or account identifier appears
in Git.

**Release status: HOLD.** Candidate changes to discovery metadata and
version/trust guardrails require a fresh versioned Plugin installation
and real positive/negative/boundary retesting; fixes to this scoring helper
alone do not alter ChatGPT's model routing.
