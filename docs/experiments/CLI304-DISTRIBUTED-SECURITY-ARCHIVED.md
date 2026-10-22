# Archived experimental CLI304 host-security research

**Status: archived, out of scope for Claude Code Mods.**

This branch retains the experimental code and evidence introduced by
PRs #114–#118 after the compatibility/QA baseline in PRs #109–#113.

Included experimental directions:
- Opt-in transactional Plugin update coordination and rollback
- External host tool enforcement and guarded process launchers
- Managed settings sandbox experiments
- Signed three-host process observations
- Two-Pi supervisor leases and Mac-signed epoch grants

**None of this work belongs in the Claude Code Mods mainline product scope.**
It was never deployed as production CLI, user Skills, Plugin installs or
mandatory system policy. The research has partial positive QA evidence,
but is not production-safe or globally comprehensive.

Keep this branch independent. Do not merge its security-supervisor features
or corresponding release gates into main without a separate explicit
product decision and complete security review.

The Claude Code Mods mainline instead maintains:
- Versioned first-party knowledge (SSOT)
- Generation of ChatGPT Plugin and AI Agent Skills
- Accurate, reproducible target-host compatibility tests
- Genuine model/agent/tool-use acceptance and release QA

For compatibility discovery and native reproduction of the 2.1.304
failed reload issue, see original mainline PRs #109–#113 and Issue #110.
Keep the compatibility finding; do not treat development of a
distributed security manager as a release prerequisite.
