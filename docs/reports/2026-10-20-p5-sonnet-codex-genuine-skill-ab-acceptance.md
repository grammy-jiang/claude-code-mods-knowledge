# P5: original Sonnet/Codex Skill A/B and native CLI302 code acceptance

Date: 2026-10-20 (Australia/Sydney). **Positive, narrowly scoped result.
Neither full model reliability nor Stable approval is established.**

## Matched, genuine native-agent experiment

The old Skill checkout is Git `1531e8d` (before PR #102); the new Skill
checkout is `45dcf52` (after PR #102). Both Skills were independently
compiled from their own immutable source revision for **Claude Code CLI
2.1.302 only** and deployed to private, isolated per-arm project folders
on the MacBook Pro. The original public 302 `POS-E-01` question was extended
with the identical experimental instruction to explicitly read the local
Skill, both `references/events.md` and `references/claim-evidence.md`,
provide exact first-party Claim links and a Mod observer code example.

Four successful, new, native model turns were captured:

| Agent | Engine/version requested | A/B results |
| --- | --- | --- |
| Claude Code | CLI 2.1.302, `claude-sonnet-5-5`, medium effort | Original: missing `on(...).catch`; updated: attached registration `.catch` |
| Codex CLI | 0.163.0, `gpt-6.1-sol`, medium effort, read-only | Original: missing `on(...).catch`; updated: attached registration `.catch` |

Exact model identity for Sonnet is supported by native wire `modelUsage`.
For Codex, the CLI options requested `gpt-6.1-sol`; the private JSONL does
not independently attest the model identity or server-applied effort.
The sample is one prompt per model and Skill arm, NOT a 100% reliability test.

For all four valid turns, the original model output and full wire bytes are
SHA-pinned in the adjoining redacted report. Exact project-local Skill and
relevant reference reads were observed (no read errors), and all four
final answers passed per-Claim first-party URL source-structure review.
The private raw replies and prompts remain on the MacBook Pro and are NOT
published or copied into this repository.

### Invalid preflight excluded from scored A/B

Before the corrected run, two Sonnet attempts loaded the globally installed
Skill, and default `dontAsk` mode denied all reference reads. Both models
abstained, so these attempts were correctly EXCLUDED rather than counted as
failures or successful model-generated code. The valid Sonnet trials used
`--tools Read --allowedTools Read --permission-mode dontAsk`, explicitly
reading only their own project-local Skill files. No permission bypass or
model-generated file modification was performed.

## Actual generated-code checks

Four independently extracted code examples (only source-hashed JavaScript,
not raw prompts/answers) were transferred to a private Raspberry Pi folder.
The original installed Claude Code CLI 2.1.302 binary was SHA-pinned.
Tests ran the actual generated source inside networkless Linux Bubblewrap,
without host Home, credentials, network or real tools mounted:

| Validation | Old Skill code (2) | New Skill code (2) |
| --- | ---: | ---: |
| Native strict validator process exits zero | 2/2 | 2/2 |
| `gating hook without .catch` warning | 2/2 | **0/2** |
| Native mocked Read result/denial + exactly one downstream call | 4/4 | 4/4 |
| TypeScript 6.0.3 `--noEmit`, pinned CLI302 core declarations | 2/2 | 2/2 |
| Source/link quality checker | 2/2 | 2/2 |

`claude plugin validate --strict` returning zero WITH a gating warning is
insufficient for release; the source-bound fail-closed gate catches the
old code and accepts the corrected registration shape. A read-only native
stub passing is NOT a genuine user permission or real downstream exception
object identity test. The typecheck adds only an `On` annotation to the
original module's `register(on)` parameter and does not verify dynamic
built-in tool declarations merged during real plugin loading.

## Repeatable evidence and security boundaries

- Private-model replay scorer:
  `scripts/audit_p5_real_model_skill_ab.py`.
- Private source-hashed native code, official CLI302 and type verifier:
  `scripts/audit_p5_real_model_native_302.py`.
- Sanitized, immutable model evidence:
  `docs/reports/2026-10-20-p5-real-sonnet-codex-skill-ab.json`.
- Sanitized native safety/type evidence:
  `docs/reports/2026-10-20-p5-real-sonnet-codex-native-code-qa.json`.
- Offline CI checks the cross-file SHA linkage, exact source revision, target
  scope, source-link structure, flags, warning counts, test counts, and
  prohibited private text. It does not refetch or replay paid models.

The valid Sonnet A/B calls reported approximate combined model cost of
USD 0.96. Previous invalid Sonnet preflight calls are excluded from the
quality comparison, not retroactively relabeled as model acceptance. Codex
reported token usage but not a directly comparable cost figure.

## Remaining release constraints

P5 genuine-model quality is improved for one 302 `tool.call` task, but
complete host semantics, other prompts, real permission precedence, full
model/Skill acceptance, installed host compatibility, 2.1.303/2.1.304
new-Claim approvals, P4 Chat Mode 46-case completion, account Plugin
readback and Stable remain **HOLD**. No production Skill or Plugin was
installed/upgraded in this experiment. Agent Communication is out of scope.
