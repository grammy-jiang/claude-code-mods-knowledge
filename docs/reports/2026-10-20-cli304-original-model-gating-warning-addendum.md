# CLI 2.1.304: native original-model validation warnings remain blocking

Date: 2026-10-20 Sydney. **Additional safety review only; no Claim approval.**

The first-party CLI 2.1.304 ARM64 executable was SHA-verified against the
official release archive and used only in a Linux Bubblewrap sandbox with
its network namespace disabled, no host Home, no account state and no real
user tools. Five existing source-hashed Codex/Sonnet Mod observer candidates
from the original 2.1.302 study were tested using `plugin validate --strict`.

All five validators exited zero and wrote `Validation passed`, **but each
also emitted `gating hook without .catch: tool.call`**. A zero exit code
therefore does NOT satisfy production-safe or fail-closed native Mod
validation. The same additional warning gate that protects 2.1.303 rejected
all five. The previously recorded 5 strict validator successes and 10
synthetic Read/denial mock successes still describe their respective test
operations, not safe deployability or type correctness.

A new immutable, redacted evidence record is at
`docs/reports/2026-10-20-cli304-original-model-uncaught-gating-native-review.json`.
The reproducible review tool is
`scripts/audit_cli304_original_observer_catch_warnings.py`. Both source and
stored evidence are covered by offline tests. This addendum does not rewrite
or falsify earlier evidence, does not rerun model prompts, and does not
include upstream proprietary core type declarations or private transcripts.

## Separate version and release gates

- CLI 2.1.302 and 2.1.303 embedded **core declarations match**, but that
  does not prove full behavioral compatibility or fix original type errors.
- CLI 2.1.304 has **different core types**, including changes in
  `tool.check` read-only metadata and human permission deciders.
- A separate, SHA-reviewed 2.1.304 synthetic `tool.check` fixture has
  a `.catch` and passes 4 mocked permission cases; that does not make the
  five original missing-catch observers safe.
- The 31 previously approved CLI 2.1.302 Claims remain 302-scoped. No
  2.1.304 Claim, current Skill, ChatGPT Plugin or Stable release is approved.
  Real human permission dialogs, complete generated tool types, model+Skill
  quality tests and P4/P5 release acceptance remain required.

Agent Communication is not part of this project.
