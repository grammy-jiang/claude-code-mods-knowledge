# Real Chat Mode QA: factory-assigned `register` rejected; bad-example scoring

**2026-10-16, Australia/Sydney. Only ordinary ChatGPT Chat Mode, not Work.**
This is a *bounded* summary of the private Mac Codex + Agent Communication
`0.3.3-beta.3` candidate experiment, source-matched to SSOT main
`2c5afd0852bf2ed95f1b367d45238e544e44cfeb` (31 then-approved Claims).

## Source- and tool-matched Chat Mode observations

- The account-installed temporary candidate had ten canonical files and
  sidecar matching the independently Mac/Pi-built source package. The real
  GPT-6 Thinking / Standard Chat Mode test conversations used **textual direct
  invocation** of the installed `claude-code-mods-knowledge` Plugin and its
  `claude-code-mods-development` Skill, not Work Mode or a forced undocumented
  system hint.
- **POS-E-01**, original `tool.call` observer task: `FINAL_VERIFIED` with **four**
  genuine scoped Plugin Skill/reference `api_tool.read_resource` events;
  **9/9** cited approved Claim `Source:` URLs matched their exact first-party
  anchor. The model included one suitable async-awaited fail-isolated
  observer example and also deliberately labeled an *unsafe anti-example*.
  The old regex risk scanner flagged the unsafe snippet as if recommended,
  despite the explicit wrong-example heading. Correct response-level status
  remains **REVIEW_NEEDED**, never an unconditional full code/native PASS.
- **POS-E-ASYNC-LOGGER**, a fresh task explicitly covering sync throws and
  async rejected diagnostics: `FINAL_VERIFIED`, **five** scoped resource reads,
  all expected Claim IDs present, **11/11** exact first-party source locators
  matched, and known-risk regexes found zero risks. The inline examples
  properly isolated logging, according to the independent review. But an
  *additional advertised complete executable Mod artifact* exported
  `register` via a factory-assigned constant rather than the reviewed named
  declaration — **semantic FAIL**, despite sources, Skill reads and lint.
- **BOUND-INJECTION** was **not sent**: the experiment correctly stopped after
  the blocking second-case semantic failure. Its status is **NOT_TESTED**, not
  a model pass or refusal. These are two independent completed Chat Mode
  conversations, not evidence for 100% future success.

The outer account owner restored the **published `0.2.0-beta.1`** from the
original GitHub release ZIP after stopping and independently downloaded it:
**10/10 canonical files and server sidecar matched**. All other ten personal
Plugin states were identical before and after. No duplicated send and no
HTTP401/403/429 bypass occurred. Personal conversation/project/Plugin IDs,
raw replies, screenshots, cookies, tokens, and account artifacts are
intentionally not part of the public report.

## Target-native reproduction — *independent synthetic code*, not model code

The approved M003 [Mods reference, files](https://code.claude.com/docs/en/plugins/mods/reference#files)
documents the named `export function register(on)` entry. To challenge the
observed factory-shape discrepancy, a **new assistant-authored disposable
synthetic Mod** makes `createRegister()` genuinely return a JavaScript
function, then uses `export const register = createRegister()` as its only
entry. On the user's Mac with **actual Claude Code CLI 2.1.296**:

| Native operation | Result |
| --- | --- |
| `claude plugin validate --strict <synthetic-mod-dir>` | **exit 1**, `register is exported as something other than a function` |
| `claude plugin test <synthetic-mod-dir>` with mocked Read | **exit 1**, Hooks module load failure; 0 pass, 1 fail |
| Existing `export function register(on)` positive control | **strict/pass**, native mock positive PASS in PR #44 |

This demonstrates that an exported constant containing a function is **not
interchangeable with the function declaration** for this version's Mod loader.
It does **not** prove every other export form fails on every CLI build or that
the user's model-origin artifact was independently installed/executed on Mac.

## Approved, version-scoped SSOT correction and fail-closed linter

- New **K-0038** (`mods.types.factory-assigned-register-export-rejected`),
  pinned to first-party **M003**, target **Claude Code CLI `[2.1.296,
  2.1.297)`**, CLI surface only; candidate → reviewed → approved via two
  SHA-linked AI-attributed decisions. Its statement explicitly rejects the
  reproduced factory-assigned export and recommends the version-scoped
  named `export function register(on)` declaration, without claiming future
  compatibility. The portable generator selects the Claim by subject, not
  an independent API fact maintained in source-code literals.
- `answer_lint` adds the narrowly supported `unsupported-factory-register-export`
  known-risk flag for **recommended** `export const register = createRegister()`
  and equivalent direct factory-call assignments. An explicitly labeled
  unsafe comparison remains **manual review**, not a false hard-code failure.
  The new `错误写法` / `Incorrect example` detection looks only at the last two
  nonempty pre-code heading lines; an explicitly *recommended correct
  implementation* heading still triggers a hard risk if its code is unsafe.
  No absence of static flags grants semantic/runtime PASS.
- The exact fixture is source-controlled under
  `tests/fixtures/mods-const-register-rejected/`; optional native
  regression `tests/test_native_register_factory_rejection.py` runs only on
  CLI `2.1.296` and **SKIPS** on mismatching/unavailable hosts rather than
  pretending an acceptance test ran.

With K-0038 approved, central knowledge has **32 active approved Claims,
5 unapproved candidates and one deprecated K-0036**. The currently installed
published Beta.1 still contains its historical 26 approved Claims: a compiler
merge does **not** install K-0038 into ChatGPT. Real QA of a *separately*
versioned, safely backed-up candidate must still test whether model answers
follow the new rule. Stable release and P4-C semantic correctness remain
**BLOCKED**.
