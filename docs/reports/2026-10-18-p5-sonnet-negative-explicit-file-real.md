# Real native Sonnet/Medium negative TypeScript file-discovery control

This is one additional genuine native Claude Code CLI 2.1.302
Sonnet 5.5 / requested Medium turn (source Skill 0.4.12-beta.1).
It is intentionally separate from the original frozen five-case
suite and does not amend any original evidence or release verdict.

The initial unrelated NEG-TYPESCRIPT case lacked source fixtures.
A follow-up provided a src/overloads.ts fixture, but the Read-only
tool configuration gave the model no directory listing capability.
It guessed source filenames instead of discovering overloads.ts.
Those runs both established **zero Mods Skill autoactivation**, but
did not establish useful TypeScript source analysis.

For a bounded follow-up, the prompt explicitly identified the file
src/overloads.ts and requested read-only analysis, stating that it
was not a Claude Code Mod. The on-disk sample is now checked into
evals/fixtures/p5-native-negative-typescript-302/src/overloads.ts,
with SHA256 identity frozen in the auxiliary case manifest. The
additional non-Mod reminder reduces ambiguity and prevents this
from being an unbiased *natural* automatic selection test.

Actual result, one fresh native model turn and NO retries:

- claude-sonnet-5-5 completed normally; requested Medium (not provider
  independently attested) and USD0.564 estimated cost.
- Exactly one native Read tool call opened the specified overloads.ts
  file, with zero tool errors.
- The completed answer discussed the two real function signatures
  and made specific TypeScript overload recommendations.
- Zero Claude Code Mods Skill calls; zero Mods K-Claim citations.
- No code execution, no edits to project files, no Chrome or session
  persistence, and no generic host filesystem write tools.
- Native wire, prompt, original answer and fixture checksums are
  recorded in the sibling redacted JSON; raw replies and local
  account identifiers remain private.

This demonstrates usable **unrelated task isolation with actual
source material available**. The correctness of every proposed
TypeScript transformation was NOT verified by TypeScript compile tests,
and generated code semantics are NOT certified. It does not upgrade
the frozen prior five cases, current P5 native multi-host acceptance,
P4 46-case Chat Mode or Stable release. All remain HOLD.

Agent Communication project excluded.
