# P4 source chronology and separate diagnostic evidence (Claude CLI 2.1.302)

Date: 2026-10-18. Candidate version: 0.4.10-beta.1 (before this patch).
Source audit: real original ChatGPT ordinary Chat Mode, not Work Mode.

## Two distinct observations

The preserved original eight-boundary cohort has six genuine Plugin
entrypoint+reference reads out of eight. The two no-read requests asked
the assistant to obey a hostile blog and upload secrets, or to blindly
install an unknown Mod with full account permissions. Both were manually
reviewed as textually safe refusals with no dangerous action reported.
This is not full security/runtime attestation. Reviews are SHA256-bound
to the exact original completed answer texts.

The original P4 strict acceptance required Plugin loading for all eight
in-scope boundaries and remains 6/8, FAIL. This report does not alter
the original rubric or rewrite historical outcomes. A separate,
nonpromoting diagnostic categories six domain-knowledge requests as
specialist routing (6/6 actual Skill reads) and two unsafe requests
as safe-refusal text observations (2/2, Plugin reading not required
to refuse). This is never a Stable release authorization.

Offline reproduction:
    uv run --locked python scripts/diagnose_p4_boundary_two_axis.py --out /tmp/mods-p4-two-axis.json
    uv run --locked pytest -q tests/test_boundary_two_axis_diagnostics.py

Grounded inputs and output:
- evals/p4_boundary_two_axis_diagnostic_302.json (classification,
  eight original answer hashes and two independently reviewed refusals)
- docs/reports/2026-10-18-cli302-boundary-two-axis-diagnostic.json
  (deterministic derived diagnostic result)
- evals/p4_boundary_semantic_rubric_cli_2_1_302.json
  (unchanged original full acceptance obligations)

## Semantic defect despite a genuine Plugin read

A naturally activated old-version CLI 2.1.220 tool.check question
correctly declined to fabricate exact unsupported fields, but added
a specific event-introduction version 2.1.269, sourced from an
unreviewed third-party historical listing. No approved first-party,
version-matched Claim or target-generated local declaration supports
that release date. An ending disclaimer does not repair the unsupported
timeline statement.

The new Skill instruction prohibits API-event introduction/removal/
deprecation version claims without approved target-matched first-party
evidence. Community version lists, even attributed and hedged, do not
qualify. Absent evidence, omit the timeline entirely and abstain on
unsupported field names or executable examples.

The deterministic answer linter also flags asserted API introduction
versions for manual first-party source review without pretending to
automatically certify all historical statements. Explicit instructions
not to claim an unsupported version are exempt from this narrow risk
signal.

Neither the source-review signal nor the two-axis diagnostic establishes
general model answer correctness or generated Mod runtime correctness.
All eight original immutable answers and private ChatGPT account
details remain private. The full 46-case Chat Mode and three-host
semantic gates remain unapproved.

Release remains STABLE HOLD. A future developer-only candidate must
be tested on genuine natural old-version questions and retain old
reference evidence. Agent Communication is out of scope.
