# Claude Code v2.1.310 — official source-only observation (P2/VER-01)

**Observation:** 2026-10-27 (Australia/Sydney). **Kind:** version-specific first-party release-note and official document *metadata*, not an approved Mods API Claim, native runtime QA, or publishing permission.

## Version/channel and first-party evidence

The official npm package latest dist-tag and official Anthropic GitHub release were **2.1.310**, distinct from npm stable=2.1.308. Original first-party release URL:
https://github.com/anthropics/claude-code/releases/tag/v2.1.310

The real v2.1.310 release was published 2026-10-23 23:39 UTC. The entire original release body is SHA256 4a2790d850518ceec4ab9ae097c315dfef5284c2765870a6d682011ae4ea9d89. Original release body stays in an owner-only private Mac archive, not Git; [public bounded hashes](2026-10-27-cli310-official-source-evidence.json) include only selected bullet hashes, authored summaries and source observation metadata.

Five relevant first-party bullet families were independently hashed:

| Release-specific topic | What the official note reports | Remaining evidence |
| --- | --- | --- |
| Monitor tool and plugin monitors | New availability on named cloud providers and special traffic/telemetry configurations | Actual model/tool discovery, exact targeted native host and provider |
| Read permission with symbolic links | Permission prompt should show the symlink target | Exact managed/interactive native permission checks |
| Windows PreToolUse / PermissionRequest | Windows Git Bash missing case has a fixed hook behavior | Windows-only case; no inference about macOS/Linux |
| Mod Image terminal support | More terminal/Multiplexer rendering paths described | Original terminal-specific native UI QA |
| Noninteractive MCP elicitation timeout | Timeout error should indicate the unanswered elicitation rather than repeat the call | Actual SDK/MCP error and retry semantics |

This is a narrow relevance selection, **not** an exhaustive changelog. A release-note phrase by itself does not prove the actual native runtime behavior or safety. The original exact bullet SHA256 for each item is in the public evidence and validated by scripts/audit_cli310_official_source_window.py against privately retained first-party bytes.

## Revisited official registry pages

The existing allowlisted Source Registry collector captured three new raw HTTP response fingerprints without storing upstream HTML text in Git:

- M003 Mods reference: 3876d8279a90afb41874830940bd0bae63ca145187b0f132ba3cb399aee07a5c.
- M004 Mods events: d5beb3abca68a424e61d94c1777e06790ab51e08bc1c5ef465a3a57278350d27.
- M033 Claude Code changelog: 70ca2e8ab711dbb97053217799ba27332936bb32fd2d16c0e95a7eece966eaa2.

All are appended metadata revisions with approval_status=not-approved and semantic_status=not-assessed. M003/M004 retain their original pinned Registry IDs; M033 is historically indexed/unpinned and is **not retroactively described as originally approved**. The complete 2.1.309 revision fingerprints remain in the immutable index even though its current pointer moved forward. This source update also repairs the earlier 309 offline audit/test assumption that 309 must be current forever; historical 309 evidence now survives subsequent 310/other versions without re-labeling an old observation as a new approval.

A changed HTML SHA alone is not evidence that Mods API meaning changed. The downloaded official source text is not committed, nor is new raw Markdown.

## Trusted SSOT, code and release boundary

- Existing separately approved CLI 2.1.296 Claims: **31**.
- Existing separately approved CLI 2.1.302 Claims: **31**.
- New CLI 2.1.309 / 2.1.310 Claims: **zero approved**.
- Nothing changes old Claim decisions, source approvals, user Skills, production CLI or personal ChatGPT Plugin.
- Official CLI 2.1.310 native type/behavior tests, current agent model QA and Chat Mode release acceptance remain **not verified**.
- Compiler targeting unsupported 2.1.310 should refuse to build production Skills. Stable stays HOLD.

**Next in-scope work:** VER-02 independently review current first-party API sections, then VER-03 on exact official 2.1.310 native binaries and harmless isolated tests. Do not promote the selective observations into the published ChatGPT Plugin without version-approved Claims and separate P4/P5 acceptance.

Current execution and dependencies: [2026-10-27 P4–P6 plan](../plans/2026-10-27-p4-p6-execution-plan.md).
