# P5: Local CLI and installed Mods Skill upgrade

2026-10-16, Sydney. All three agent CLIs and all three user-scoped Mods
Skills have been upgraded or independently verified current. **P5 model
inference is still incomplete.** This is installation and native-loader
acceptance, not a stable-release or full runtime API compatibility claim.

| Device | Claude Code CLI | Codex CLI | Pi Agent CLI |
| --- | --- | --- | --- |
| MacBook Pro | 2.1.296 to **2.1.301** | 0.162.1 to **0.163.0** | **1.3.0**, already latest |
| Raspberry Pi | 2.1.299 to **2.1.301** | **0.163.0**, already latest | **1.3.0**, already latest |
| sextant | 2.1.289 to **2.1.301** | 0.160.0 to **0.163.0** | **1.3.0**, already latest |

The native update commands were Claude update, Codex update and Pi
update --self. Existing long-lived Agent sessions and managed daemons were
not force-restarted. New commands resolve to the updated versions; a
running process may continue using its original process image.

## Installed Skill source, scope and readback

The reviewed source is Git SHA
6cbdc9ad6ed9f958072f9cbf4a34c4bbc2d5ef3e, matching ChatGPT developer
Plugin package **0.3.4-beta.2**. The ZIP SHA-256 is
99c1addcb68fe0fdc16dcfd60289cfb025598cebecd00912f4e653da2457ad89.
The installed Skill main file has SHA-256
03053cc81e43ca215621db048eb435d675a2685205953019744a5df1bc13530e.
Every Skill tree contains nine exact-matching files, including eight
reference files and 31 approved Claims.

Mac Codex had a local enabled marketplace Plugin at obsolete
0.1.0-rc.1. The local source was updated and retained in private rollback
storage. The official native Codex Plugin add operation refreshed the
installed/enabled Plugin entry to **0.3.4-beta.2**. That alone did not
produce any Mods Skill in a new Codex native skills/list call. Installing
the matching user-global Skill in the recognized Agent Skills directory
resolved the issue. The redundant separate Pi user copy was backed up,
so Codex and Pi Agent each discover exactly one identical Skill.

Raspberry Pi and sextant also share one user Agent Skills directory
for Codex and Pi Agent. Claude Code uses its normal user Skill location.
No unrelated user Skills, accounts, Plugins or project working trees were
replaced.

## Actual model-free native acceptance

| Verification | Mac | Raspberry Pi | sextant |
| --- | --- | --- | --- |
| Codex app-server native skills/list, actual user installation | 1 enabled, exact digest | 1 enabled, exact digest | 1 enabled, exact digest |
| Pi 1.3.0 DefaultResourceLoader, actual user installation | 1 skill, zero relevant diagnostics | 1 skill, zero relevant diagnostics | 1 skill, zero relevant diagnostics |
| Claude Code 2.1.301 interactive **native slash-command autocomplete** | Actual `/claude-code-mods-development` suggestion with Skill description | Same | Same |
| Claude 2.1.301 native strict disposable Mod validation | PASS | PASS | PASS |
| Claude 2.1.301 native mocked observer test | 1 pass, 0 fail | 1 pass, 0 fail | 1 pass, 0 fail |

**Actual Claude interactive discovery probe:** A new isolated, empty,
task-created directory was opened in a bounded pseudo-terminal. Its native
workspace trust prompt was explicitly verified before selecting trust
**for that empty directory only**. In each of the three native Claude Code
2.1.301 interactive composers, typing only the partial prefix
`/claude-code-` displayed the *full* `/claude-code-mods-development`
command suggestion and its Skill description. The complete Skill name
was **never typed or echoed by the probe** and **no model prompt was
submitted**. Test subprocesses were terminated after observation; no
existing user session/daemon was restarted. This is stronger than file
presence, native manifest validation, or Plugin-list status. The
`claude -p /skills` headless print-mode command on Mac is not available in the
noninteractive environment and must **not** be interpreted as failed native
interactive Skill loading.

Version-sensitive offline regression behavior was also checked independently:
on globally updated Claude Code 2.1.301, Python 3.11 and 3.14 each report
633 passing cases and eleven explicitly SKIPPED tests that require target
CLI 2.1.296. Those eleven tests passed using the previously preserved
2.1.296 binary through a temporary PATH wrapper. The complete suite
with that pinned CLI passed 644/644 cases under Python 3.11.
This **did not downgrade** the globally installed 2.1.301 executable.

No model tokens were consumed by these checks. Native Skills discovery,
manifest validation and a single harmless mocked tool-result case are
not equivalent to positive/negative/boundary model inference, actual
production event execution or complete API support.

**Important remaining version boundary:** the installed Skill's knowledge
revision is an internal 0.1.0 identifier, distinct from package version
0.3.4-beta.2. Its official evidence still targets **Claude Code CLI
2.1.296 only**. It does not promise that all 31 reviewed API Claims have
been independently requalified against upgraded CLI 2.1.301. That source
review and full per-agent inference must occur before P5 is marked done.

Rollback metadata, previous executable versions and the former Mac local
Codex Plugin source are stored in private, host-owned deployment state.
GitHub stores only approved hashes, source revision, machine labels and
sanitized acceptance outcomes.
