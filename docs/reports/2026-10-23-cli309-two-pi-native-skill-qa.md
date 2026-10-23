# Claude Code 2.1.309: real native Skill discovery and Mod alias QA on two Pi hosts

**Date:** 2026-10-23, Australia/Sydney.
**Project scope:** Claude Code Mods knowledge/Skills and ChatGPT Chat Mode Plugin.
**Verdict:** target-native partial PASS for synthetic Skill discovery and Mod model-alias compatibility; full SSOT Skill/model/Plugin acceptance and Stable remain HOLD.

## Objective and original first-party target

The preceding source-only PR #120 identified three directly relevant
2.1.309 changes: additional-directory same-name Skill resolution, nested
package Skill discovery, and Mod turn.step model alias resolution.

Both Raspberry Pi (rpi-a) and Sextant (rpi-b) used an **independently
SHA256-verified original official 2.1.309 Linux ARM64 executable** in
temporary private QA folders:

- Official first-party GitHub release archive SHA256:
  8ecd1f2d06ccbd3f89c8886e840e42b57a19063f3de9cfe5f7d90fe875ba99ef
- Extracted official native executable SHA256:
  9796dd26899337f687739a0b39a7353b639f062a3436a7b941fcf19a1b757a9b
- Original published version: 2.1.309.

The Sextant direct download timed out, so the exact reviewed archive
was copied from Raspberry Pi over their pre-authorized SSH connection
using a resumable local transfer, then verified independently against
the official asset hash. No production executable was overwritten.
At final collection, Pi's installed Claude was 2.1.309 (independent
of this QA) and Sextant's remained 2.1.302.

Primary current docs:
- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/plugins/mods/reference
- https://github.com/anthropics/claude-code/releases/tag/v2.1.309

## Exact source-controlled harmless fixtures

The reviewed test sources live under
evals/fixtures/cli309-skill-discovery-20261023.

- A project-root mods-qa-route Skill with a unique root marker.
- A supplemental addons directory containing a Skill with **the same
  name**, but a different source and marker.
- A nested packages/widget mods-qa-nested Skill with a third marker.
- A disposable Mod registering an async-generator turn.step Hook that
  requests the model alias haiku.

These are intentionally tiny, purely diagnostic Skill files. They
do not contain approved Claude Code Mods API knowledge and must NOT
be distributed as production Skills.

The tests used actual authenticated Sonnet and Haiku inference,
independent native Skill tool-use events, and exact source markers.
Except for benign Read of a scratch README and Skill tool invocation,
no file-edit, shell execution, or non-QA tool was authorized.

## Native result matrix

| Scenario | Raspberry Pi | Sextant |
| --- | --- | --- |
| Root project Skill source | Actual Skill(mods-qa-route); correct unique root marker | PASS, same actual Tool/marker |
| Additional-directory same-name source | Actual Skill(addons:mods-qa-route); correct separate marker | PASS, same actual Tool/marker |
| Nested-package Skill from nested working directory | Actual Skill(mods-qa-nested); correct nested marker | PASS, same actual Tool/marker |
| One continuing process reads nested README, then invokes nested Skill | PASS: Read then Skill, distinct turns, same session | Not yet run on Sextant |
| Requested relevant Skill source without giving exact Skill name, root/addons | Both source choices PASS | Not yet run on Sextant |
| Unrelated arithmetic negative control | Correct answer with **zero** Skill or other tool calls | Not yet run on Sextant |
| Mod turn.step model alias | Official strict Plugin validation passed, hook executed; actual assistant metadata was claude-haiku-5-5 | PASS, same |
| One restricted-mode diagnostic control | Skill tool returned Unknown skill and loader counted zero; model subsequently directly Read SKILL.md | Not yet run on Sextant |

Source routing was verified from the **real native Skill tool input**,
not merely by checking whether the answer contained a marker. A
source-accurate answer from an ordinary Read of SKILL.md does not prove
that the agent used the Skill system. This matters for the original
project's issue: model answers may appear plausible while capability
discovery and invocation actually fail.

The two automatic source-choice prompts still explicitly asked the
model to use the relevant available Skill; they did not name the Skill
itself. They are a useful selection test but are **not** proof of
completely spontaneous Skill activation in unrestricted user tasks.

The restricted-mode finding applies to this exact tested CLI and flag
combination. It should be investigated as an observed compatibility
boundary rather than treated as a universal defect or silently folded
into the unrestricted positive tests.

## Provenance and reproducible evidence

The bounded source and runtime auditor:
scripts/audit_cli309_native_skill_evidence.py

It verifies:
- Actual official CLI309 binary/source SHA256 and seven reviewed fixture hashes.
- Original private native stream-json, debug and empty stderr.
- Exact native CLI version, assistant model identity, Skill tool name
  and tool input, correct source-marker/negative-control behavior.
- Two-turn same-session nested Read then Skill.
- Native strict Plugin validation, actual turn.step Hook execution,
  and real Haiku model identity after the alias was requested.
- The restricted negative case as a **failure**, not a passing Skill
  invocation.

The original model prompts, full native JSONL/debug and session IDs
remain in separate mode-0700 private evidence directories on both
machines. Each host's original binary, fixture tree and raw records
were independently preserved, then the auditor recomputed byte-identical
sanitized results from those persisted copies.

Public SHA-bound results:
docs/reports/2026-10-23-cli309-two-pi-native-skill-evidence.json

CI re-verifies the public evidence, source hashes, exact scoped outcomes
and privacy boundaries. CI does NOT generate a new paid model inference
or replace the original private target-host evidence.

## Remaining product acceptance gates

These results prove only actual loading, controlled routing and
synthetic Skill source selection on reviewed native target hosts.
They do NOT prove:

- That the complete generated Claude Code Mods Skill (with 31
  approved older-version Claims) is semantically correct on 2.1.309.
- That full Mods reference citations, error identity and code output
  are correct across agent/model cases.
- That built-in /verify and /code-review invoke nested package Skills
  following shell-side file changes.
- That Codex and Pi Agent successfully discover and utilize exact
  current-version SSOT knowledge.
- That the personal ChatGPT **Chat Mode** Plugin is running the
  current approved Skill or has passed the 46-case acceptance.
- That any 2.1.309 Claim has been approved. **The count remains 0**;
  no 2.1.309 production Skill/Plugin was built or published.

Next in-scope steps: exact native nested bundled-workflow QA, followed
by product-real Skill/Claim semantic A/B tests and independent Codex/
Pi Agent acceptance once corresponding target-version knowledge
is approved. No distributed host-security project work is required
to satisfy this original Mods roadmap.
