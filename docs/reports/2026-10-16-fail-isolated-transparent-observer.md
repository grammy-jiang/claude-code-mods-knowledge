# K-0036: fail-isolated transparent observer diagnostics — evidence and guardrail

**Target:** Claude Code CLI 2.1.296, `tool.call` observation. **Result:** native synthetic success/error identity reproduction; original real Chat Mode model-output logging advice was semantically invalid.

The first-party Mods official Events page [M004 / observe an event](https://code.claude.com/docs/en/plugins/mods/events#observe-an-event) supports continuing middleware with `next(e)` and preserving downstream behavior, as already captured by approved K-0007. A real ordinary ChatGPT Chat Mode candidate reply cited valid Claims and official sources but recommended unisolated `console.log` after `await next(e)`, and `console.error` in the downstream-error catch path. Those diagnostic side effects can fail and override the original downstream result or error; see the [five-case account trial](2026-10-16-agent-communication-chatmode-beta2-qa.md).

We reproduced this with **safe assistant-authored synthetic code only**, never executed the ChatGPT response itself. On Mac Node **v24.21.0**, an unsafe synthetic Hook:

1. Replaced an original successful `next(e)` return with a logger failure when `console.log()` threw.
2. Masked the original rejected `next(e)` Error when an unprotected `console.error()` inside its catch block also threw.
3. A safe synthetic handler with `try { return await next(e) } finally { try { await diagnostics(); } catch {} }` kept the exact result identity, exact original thrown Error identity and exactly one `next(e)` invocation, including when a diagnostic returned a rejected Promise. The repository carries the network-free Node fixtures under `tests/fixtures/observer_logging_safety/` and an optional Node-backed Python regression test.

The safe synthetic named `register(on)` hook was **strictly accepted by actual Mac Claude Code CLI 2.1.296**, with a verified `.claude-plugin/plugin.json`, `hooks/hooks.json` and `hooks/register.js`. This is *not* a production-host test, and cannot certify model-origin code or arbitrary logging APIs.

New K-0036 (`mods.events.fail-isolated-transparent-observer-diagnostics`) is approved, scoped only to CLI `[2.1.296,2.1.297)`, with reviewed official M004 source pin and a two-event **AI-attributed** SHA-linked native decision ledger `decisions/K-0036.json`. It is a conservative best-practice derived from the official transparent-observer contract plus reproduced JavaScript control-flow behavior; do not misrepresent the official page as asserting a particular logger implementation. Its `statement`/exact official source locator are rendered from the SSOT into the four portable Skills and `references/events.md`.

`answer_lint` now flags a **bounded subset of provable unsafe patterns** (`observer-post-next-diagnostics-not-isolated`, `observer-catch-diagnostics-can-mask-error`) in runnable TypeScript examples. A deliberately labeled wrong snippet is marked for manual review. Full language-level semantic correctness is not determined by regular expressions, a passed disposable Mod strict validator, or matching K-Claim URLs. No Plugin installation or new Chat Mode model invocation was performed by this source-only correction.

**Release disposition:** Keep the published account baseline `0.2.0-beta.1` and P4/P5/P6 gates open. Targeted synthetic verification passes are a prerequisite for, not a replacement for, a future versioned ordinary Chat Mode acceptance test. Historical Git private-links remediation requires separate coordination and is not part of this fix.
