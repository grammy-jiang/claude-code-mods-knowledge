# Claude Code 2.1.303: independently attested core type parity and native mock subset

Date: 2026-10-20, Sydney. **Compatibility scope is deliberately narrow.**
No new target-specific API Claims, Skills, ChatGPT Plugins or Stable releases
are approved by this analysis.

## First-party release identity

The official [Claude Code v2.1.303 release](https://github.com/anthropics/claude-code/releases/tag/v2.1.303)
has a Linux ARM64 tarball SHA256 of
`0c219f6d5fadf1ce5771f7976fe18d6a57a9b8267def5198b58d3e121eeb98c1`.
The archive has exactly one native executable. Its SHA256,
`f384f49826336d4ac0484ac6ac9d8d16f64d244d186ce227cbd7cc088c03315d`,
matches the installed 2.1.303 Pi executable byte for byte.
The isolated native binary itself returned `2.1.303 (Claude Code)`.

Its unique internal Zstd-encoded core Mod TypeScript declaration is 651,852
bytes and has SHA256
`8afa71883ecfa52901eb7a04cf31fef700d8ba565eaad244f4884cc620f8d56e`.
This matches the original independently reviewed CLI 2.1.302 **core declaration
exactly**. It does not prove equality of dynamically merged built-in tool
schemas, runtime hook ordering, permission precedence, state lifetime or UI.
The 2.1.304 core is different and has its own separate review.

## Real native 303 compatibility test (no account, no model)

Five source-hashed real, previously saved Codex/Sonnet observer code samples
were staged in a throwaway work directory. Some model fragments needed an
explicit TEST-ONLY register wrapper. The official 2.1.303 executable ran
inside Linux Bubblewrap with the network namespace unshared and host Home,
credentials, actual Read/Write tools and external data excluded.

- Native `claude plugin validate --strict`: **5/5 reported pass**,
  **but all five emitted `gating hook without .catch: tool.call` warnings**.
  The stronger fail-closed safety gate correctly **blocks 5/5** despite
  the native validator's zero exit status. The original model snippets
  must NOT be treated as copy-ready production hooks.
- Native `claude plugin test` with synthetic Read and denial stubs:
  **10/10 pass**.
- An intentionally wrong observer tool result: **rejected**.
- Real interactive permission/dialogue or model inference: **not run**.

The byte-pinned execution is reproduced by
`scripts/audit_cli303_official_native_parity.py`. Structured public evidence
is `docs/reports/2026-10-20-cli303-official-core-and-native-mock-parity.json`;
no original raw user answers, generated core type content, authentication or
user paths are included. Offline deterministic guards run through pytest.

## Reproduce without touching the installed CLI or account

On a Raspberry Pi ARM64 with the official 2.1.303 CLI already installed,
create a private scratch directory and fetch only its official release
archive. The script checks the official SHA256, byte identity to the
**installed** executable, core digest, native sandbox and original fixture
identities before writing its output. Use a NEW `--out` path each time:

```sh
mkdir -p -m 700 /tmp/claude303-native-review
# Obtain the v2.1.303 claude-linux-arm64.tar.gz asset via GitHub CLI:
gh release download v2.1.303 --repo anthropics/claude-code \
  --pattern 'claude-linux-arm64.tar.gz' \
  --dir /tmp/claude303-native-review --skip-existing
uv run --offline --group dev python scripts/audit_cli303_official_native_parity.py \
  --official-archive /tmp/claude303-native-review/claude-linux-arm64.tar.gz \
  --out /tmp/claude303-native-review/native-audit.json
```

This operation does NOT install/upgrade the CLI and performs no model
inference. Any missing exact binary, warning mismatch, source drift or sandbox
failure blocks the audit.

## Explicit version gate and remaining blockers

The existing 31 approved CLI 2.1.302 Claims have version range
`[2.1.302, 2.1.303)` and **remain unapproved for 2.1.303**. The actual
original generated model code still has the prior 3/5 type failures, which
mock successes must never erase. Also unverified are live host/user
permission callbacks, dynamically created tool types, all 31 Claim
semantics, a genuine native model plus current Skill, ChatGPT Chat Mode
activation, and final deployment readback.

Do not install or promote a 303 Skill from this report. Existing 302-only
Skills remain 302-only even on the Pi running 303. Stable and P5 complete
host/model acceptance remain HOLD. Agent Communication is out of scope.
