# P4-C: native register-parameter destructuring regression

**2026-10-16 (Australia/Sydney). Scope: Claude Code CLI 2.1.296 only.**

## Why this regression matters

The previously merged native registration matrix (K-0038, PR #45) tested five
working plain-parameter named registrations and two rejected indirect
initializers. It did **not** test destructured parameters on otherwise directly
exported named `const register` functions. The P4 answer-risk linter previously
recognized `export function register({ on })` but missed equivalent bad
`export const register = ({ on }) => ...` or
`export const register = function({ on }) ...` recommendations.

## Independent exact-version native reproduction

On Mac Claude Code CLI **2.1.296**, five assistant-authored, isolated, disposable
synthetic Mods were submitted to both `claude plugin validate --strict <mod>`
and `claude plugin test <mod>`. Their `.test.ts` used an offline stubbed
`Read` result, **not** a real tool action. No ChatGPT-generated JavaScript was
executed, no account/plugin settings were modified and no private data or
credential material were accessed.

| Register declaration (each uses the same synthetic observer) | Strict validation | Native mocked test |
| --- | --- | --- |
| `export const register = ({ on }) => { ... }` | **FAIL** | **0 pass / 1 fail** |
| `export const register = function({ on }) { ... }` | **FAIL** | **0 pass / 1 fail** |
| `const register = ({ on }) => ...; export { register };` | **FAIL** | **0 pass / 1 fail** |
| `export function register({ on }) { ... }` (existing named-declaration control) | **FAIL** | **0 pass / 1 fail** |
| `export const register = (on) => { ... }` (valid control) | **PASS** | **1 pass / 0 fail** |

All rejected variants produced the exact-version native diagnostic:
`the parameter that receives on is not a plain name`. This is **not** the
`register is exported as something other than a const function` diagnostic
seen for the previously tested factory/indirect-alias forms. The result is
limited to these source shapes and this target CLI.

## Code and test disposition

- Added three repeatable parametrized cases to the exact-version native
  registration-loader matrix; hosts missing the exact version **SKIP**, not
  PASS.
- Added red-first static answer-lint cases covering exported const arrow,
  async arrow, function expression and separately exported local const
  destructuring. The previously shipped linter failed all four cases.
- Added valid const/plain-parameter controls and a clearly marked unsafe
  counterexample: the former must remain clean and the latter requires
  manual review instead of being misrepresented as recommended executable
  advice.
- The new linter uses an existing stable risk name
  `unsupported-named-register-destructuring`, scoped only to bounded,
  directly named/exported forms. This risk scanner **does not establish**
  overall semantic correctness or replace native model-origin-artifact QA.
- Do not revise approved K-0038's historic evidence or claim that official
  docs explicitly enumerate every rejected syntax. The direct first-party
  Mods reference remains
  https://code.claude.com/docs/en/plugins/mods/reference#files .

**Acceptance:** This closes one additional known P4-C detection gap only.
P4-C semantic QA, P4-B automatic routing, P5 real host inference and P6
stable release remain **OPEN/BLOCKED**. The last published GitHub Beta remains v0.2.0-beta.1; this regression
does not install or deploy any personal ChatGPT Plugin.
