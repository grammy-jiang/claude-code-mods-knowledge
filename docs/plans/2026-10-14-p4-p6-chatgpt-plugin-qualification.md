# P4–P6 ChatGPT Plugin Qualification and Private Release Plan

Date: 2026-10-14 (Australia/Sydney).
Owner authorization: implement ordinary engineering decisions autonomously, do not call Claude Code/Codex models while quota exhausted, use MacBook, Raspberry Pi and sextant.

## Scope and gates

**P4**: Curated test scenarios across six domains, source lookup, unsupported versions, historical isolation, malicious document instructions, and unrelated-topic false activation. Provide deterministic executable package/content checks and explicit ChatGPT-Work manual evaluations. Never label static checks as model behavior.

**P5**: Validate on macOS ARM64 and two independent Raspberry Pi ARM64 Linux hosts, including Python version and strict bundle extraction tests, per-file SHA-256, source link integrity, and safe path handling. Prepare a ChatGPT personal local Marketplace. Attempt install via the supported non-inference plugin package manager and verify on-disk cache. Do not call Claude Code/Codex LLMs or manipulate their sessions. If ChatGPT Desktop UI/Work cannot be exercised, record `host_runtime_not_verified`.

**P6**: Create a reproducible release wrapper with checksums, metadata, supported version/surface, provenance commit, tests matrix and remaining host gaps. Generate tested ZIP, install-source local marketplace, Git tag/private GitHub Release when safe. No public directory submission without identity verification. If actual ChatGPT runtime evaluation remains impossible, mark release a **candidate** rather than mislabel it fully accepted.

### Deliverables

- `evals/p4_cases.json` and `src/mods_knowledge/evaluator.py`, `tests/test_evaluator.py`.
- `scripts/validate_release.py`: bounded ZIP safety and reproducibility/security validation.
- `scripts/personal_marketplace.py`: safe personal Marketplace install/update with dry-run, no overwrite other plugins and tracked test assertions.
- `docs/reports/p4-p5-2026-10-14.md`, `docs/operations/personal-plugin-install.md`.
- Versioned package and release manifest from release builder. Repo branch, quality checks, remote fast-forward and private GitHub Release.

### Completion vs evidence

The following are **not equivalent**: generated plugin package, source installed in personal Marketplace, cache marked installed, UI plugin available, ChatGPT Work automatically selected the Skill, ChatGPT model gave a correct answer. Record each separately; never invent a Work result.

## Implementation order

1. Inspect official marketplace format and current local files, establish clean worktree and baseline. Check all three hosts, no LLM use.
2. Write failing eval tests, implement conservative offline evaluator and positive/negative scenario library. P4 static `passed`/model `not_run` split.
3. Write failing release and marketplace tests, implement package ZIP and site metadata checks. Preserve user settings with atomic writes, no secrets or open hooks. Install only after final reviewed package ready.
4. Clone private repo onto Raspberry Pi, clone via SSH from Pi to sextant, run independent Python/test/bundle scans. Compare exact source and artifact hashes.
5. Attempt local Plugin Marketplace installation through documented host/package tools; try real ChatGPT Work UI if available. Do not claim success if unavailable.
6. Release with full caveats/verification report and rollback instructions, commit to independent branch, merge/push after fresh tests. Generate release package from clean commit, tag and upload private GitHub Release. Rebuild/check all three devices and finalize status.
