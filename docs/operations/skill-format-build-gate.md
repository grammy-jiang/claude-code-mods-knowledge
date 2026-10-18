# Deterministic Skill format gate (no model or account required)

**Why:** On 2026-10-18, versions 0.4.8-beta.1 and 0.4.9-beta.1 packaged
a SKILL.md containing the invalid YAML plain scalar "Claude Code Mods: hooks".
The old validator only searched for a description line and validated ZIP
checksums. An installed/enabled Plugin did not prove that ChatGPT could
automatically discover the Skill. The earlier 0.4.7-beta.1 YAML was valid.
The corrected beta010 restored positive automatic Skill loading in a
limited real Chat Mode pilot; boundary and semantic approval remain separate.

## Required build and pre-install gate

Run these offline in the reviewed knowledge repository, targeting the
actually approved official CLI version (2.1.302 as of this report):

~~~sh
uv run --locked pytest -q tests/test_skill_format_gates.py tests/test_skill_yaml_frontmatter.py
uv run --locked mods-knowledge build \
  --api-version 2.1.302 --surface cli \
  --package-version 0.4.10-beta.1 --source-revision "$(git rev-parse HEAD)"
uv run --locked mods-knowledge skills-lint --dist dist
uv run --locked mods-knowledge package-check --dist dist
~~~

The build itself now rejects malformed YAML and damaged packages before
replacing the previous dist directory. The skills-lint command parses
the real YAML for five deployed host Skill files: common, Claude Code,
Codex, Pi Agent and ChatGPT. All five copies must be byte-identical and
the two ZIP entrypoints must match them. The full package-check also
verifies the build hashes, exact file allowlists, approved Claims and
target/source version.

The parser is PyYAML SafeLoader with duplicate-key rejection, not a
regex, string-substring search, or permissive object loader. It rejects
malformed colon-space, repeated or absent keys, unexpected fields,
incorrect name and description types, empty descriptions, unsupported
tags, and divergent or missing Skill files. Rehashing a malformed file
must never cause the artifact to pass validation.

## CI enforcement

The existing GitHub Actions workflow already executes all pytest
regression tests, then a CLI 2.1.302 build and package-check on Python
3.11 and 3.14. The enhanced build now fails before creating output if
YAML is invalid; package-check independently validates all five host
files and both ZIPs. Therefore the **existing unchanged CI workflow**
enforces the new gate without any workflow-file mutation. The local
scripts/ci_offline.sh additionally runs the named skills-lint command,
which developers can invoke directly before deploying any Plugin.

The optional extra named GitHub Actions command was not added because
the connected local GitHub credential lacks workflow-edit scope. This
does not weaken the new deterministic checks already executed in
CI; workflow scope must not be bypassed or silently elevated.
Any failed check blocks release work; no browser, account, or model
calls are needed.

When deploying a personal Plugin, download its normalized account ZIP
and compare all approved files against the locally verified source ZIP
with the offline account-archive-check command. Source ZIP validation
uses the same strict YAML parser.

This deterministic check does NOT certify ChatGPT Skill selection, model
answer semantics or generated Mod runtime correctness. Those require
separate actual Chat Mode and host inference acceptance, including
positive, unrelated-negative and version/security boundary controls.

Until P4/P5/P6 pass, keep the Stable Release HOLD. Agent Communication
is outside this project.
