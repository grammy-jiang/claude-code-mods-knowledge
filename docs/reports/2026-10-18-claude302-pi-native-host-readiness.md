# P5 Pi Agent 1.3.0: genuine native model inference, boundary failure

The native Pi Agent local-model provider was unavailable at the
existing developer-configured loopback port 18080: two original model
attempts previously exited Pi with code 0 and agent_end even as all
model requests stopped in Connection error and native auto-retries
exhausted. The native result scorer now requires a true terminal model
stop reason and refuses to count those process exits as model inference.
The original two failure traces remain unchanged and SHA-bound.

For independent recovery testing, a **temporary, loopback-only oMLX
server** was started on alternate port 18081, using previously downloaded
Qwen 3.6 weights, isolated test-state and a private, isolated
PI_CODING_AGENT_DIR. The global Pi model registry, installed Skills and
production model-service configuration were unchanged. The test used
native Pi 1.3.0 JSON event streaming, explicit provider/model flags,
a read-only tool allowlist (read/grep/find/ls), no extensions/MCP,
and three distinct task IDs. No model-generated code or real user
shell tool was executed. After the three original results were
captured, the temporary server was stopped and its listening socket
verified gone.

| Original independent Pi trial | Observed native model and Tool evidence | Gate |
|---|---|---|
| Positive native Mods request | Genuine mac-qwen model end; two actual Skill/reference reads | **Fail:** K-0041 and K-0042 cited without precise approved official URLs |
| Unrelated negative request | Genuine model end; zero Mods reference reads | **Pass** for Skill nonactivation |
| Unsupported version 2.1.310 boundary | Genuine model end; four Mods reference reads | **Fail:** despite the task targeting unreviewed 2.1.310 without allowed source lookup, it produced executable 2.1.302 hooks/register.js code with disclaimers |

The exact original wire and answer SHA256 identifiers are preserved in
the separately committed metadata-only report. User prompt text, model
answers, local paths, identities, credentials and logs stay private.

**Conclusion:** The Pi Agent client and installed Skill can run real
native model turns when the backend is present; however neither
positive exact-source quality nor unsupported-version behavior met
the agreed strict acceptance criteria. The task is NOT a production
Pi Agent host pass and does NOT unblock the Stable Release. Current
state remains beta HOLD.

This report deliberately does not certify arbitrary host runtime
semantics or the full answer. Tested snippets would still require
independent CLI 2.1.302 strict validation and mocked native Mod tests.
