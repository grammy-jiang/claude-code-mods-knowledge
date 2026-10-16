# P5 bounded native Claude Code CLI test — K-0037 asynchronous observer

**2026-10-16, Australia/Sydney.** This is an exact target-version, model-free,
network-free **synthetic** Mod Hook smoke. It is **not** ChatGPT Chat Mode
model-answer acceptance, production compatibility, or a P5 issue closeout.

The previously approved source-scoped K-0037 supersedes deprecated K-0036 for
transparent `tool.call` diagnostic exception isolation. Its advice is grounded
in first-party [M004: observe an event](https://code.claude.com/docs/en/plugins/mods/events#observe-an-event)
plus independent safe JavaScript tests, not a promise of actual model behavior.

A version-pinned disposable plugin now lives under
`tests/fixtures/mods-async-observer/`. It exports a named `register(on)`,
registers `on('tool.call', async ($, e, next) => ...)`, calls `next(e)` exactly
once, and catches a deliberately rejecting, awaited diagnostic Promise in
`finally`. The offline `.test.ts` provides a **mocked** Read tool response,
checks that the intended result survives that rejected diagnostic, and does
**not** touch a real file, network, account, or arbitrary user data.

| Host | Observed installed Claude CLI | Strict CLI validation | Native offline test | Result |
| --- | --- | --- | --- | --- |
| MacBook Pro | **2.1.296** | `claude plugin validate --strict tests/fixtures/mods-async-observer`: exit **0** | `claude plugin test tests/fixtures/mods-async-observer`: **1 pass, 0 fail** | **PASS, scoped mock success case** |
| Raspberry Pi 5 | **2.1.299** | Not admitted for the exact target | Not run as target evidence; Python regression explicitly **skipped** | **VERSION_MISMATCH — NOT PASS** |

The staged fixture hashes matched exactly between the two machines:

- `hooks/register.js`: SHA-256 `58a704537e45d2a0b4d05c821644a3e046b6f4c016187c9e3955442614a58509`
- `tests/observer.test.ts`: SHA-256 `1e11160fb4155760b053b1e6080a8b80245cc290c3536f56a8edb4f9d1d671d0`

The new `tests/test_native_async_observer.py` refuses to count a pass on
machines lacking exact CLI **2.1.296**. It checks the real binary's version,
strict Mod manifest/hook validation, native offline plugin mock test exit and
one correct tool-result assertion. CI builders without an exact native CLI
report an honest **SKIP**; neither a skip nor a Python wrapper can prove an
actual model turn.

**Important error-case limitation:** A separate private Mac disposable probe
made its mocked `tool.call` callback throw a deliberate synthetic downstream
Error. The Claude CLI 2.1.296 **test harness** returned
`HooksError: no implementation for tool.call`, reporting the mock hook was
skipped because it threw. The test fixture therefore deliberately does **not**
claim that the native harness preserved the original thrown Error identity;
that precise failure-path behavior was reproduced only by the repository's
**seven offline Node synthetic control-flow tests** in PR #43. Treat the native
error identity check as **NOT_VERIFIED**, not as a native code failure or PASS.

No ChatGPT Plugin was installed, no quota/model inference was consumed and no
personal Chat session was touched by this isolated native fixture. P5-A and
P5-D remain open pending true model inference and version/surface-specific
end-to-end checks, while P4 semantic QA and stable release gates remain blocked.
