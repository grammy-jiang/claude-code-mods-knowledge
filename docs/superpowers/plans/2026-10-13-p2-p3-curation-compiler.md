# P2–P3: Curated Mods Knowledge and Deterministic Cross-Agent Compiler

**Approved scope:** finish P2 source-linked current guidance and P3 generated Skill/Plugin packages in this session. No installation/public publication or cloud credential use.

**Baseline:** Git `facd12d`, 91 sources, 43 official HTTP fingerprints, 6 unapproved candidates, 128 tests; MacBook Claude Code 2.1.296.

## P2 — curated knowledge
1. Fetch official `.md` renditions into a temporary working directory for review; record upstream URL, read sections, digest, timestamp and original current HTTP fingerprint. Re-observe official HTML and pin reviewed L0 sources at the selected snapshot digest. Do not commit original HTML/markdown.
2. Add independent source-review attestations binding official Markdown digest, source HTML digest and reviewed headings/anchors; validate their integrity as a condition for published guidance.
3. Write at least three focused guidance Claims for each E/S/T/Q/P/U area. Each Claim has bounded version 2.1.296..2.1.297, CLI surface only, official source locator, metadata pin and reviewed status. Promote through explicit audited `candidate -> reviewed -> approved` decisions. Keep six unverified API candidates untouched and unapproved; no invented production runtime reports. Test boundary, historic firewall, tamper, review ledger and query.
4. Optionally run a disposable official-style Mod in a local test harness. Separate observed CLI commands from any claim that implies live interactive runtime compatibility.

## P3 — compiler
1. TDD for deterministic `compile(verified SSOT, target profile, compiler revision)` with six references and one small Skill body; ensure only approved/target-matched non-historical Claims; content includes Claim/Source ID and official URL, not raw copied docs.
2. Output identically sourced skills at `dist/common`, `dist/claude-code/.claude/skills`, `dist/codex/.agents/skills`, `dist/pi/.agents/skills`, and `dist/chatgpt/<plugin-name>/skills` with portable root `plugin.json`; no MCP or execution hooks. Add deterministic hash manifest, input SHA, version, build repeatability, and strict no-network compilation.
3. Add tests for stale/unknown version rejection, history firewall, no candidate leakage, six-domain mapping, frontmatter/relative link integrity, consistent four skill payloads, JSON plugin validation, reproducible file SHA and traceability.
4. Run Python 3.11/3.14 regression suites and security scans, review changes and source provenance, Git commit(s), fast-forward `main` only if remote unchanged, push and verify the remote SHA.

## Scope boundaries
- P4–P5 true Agent auto-trigger and ChatGPT plugin installation remain separate; passing packaging tests is not proof of runtime loading in ChatGPT.
- Source HTTP hashes do not prove API semantics; reviewed official Markdown is a separate content form. No normative API claim is approved without actual target-version verification.
- Decision actor names and digest chains are auditable labels, not cryptographic signatures.
