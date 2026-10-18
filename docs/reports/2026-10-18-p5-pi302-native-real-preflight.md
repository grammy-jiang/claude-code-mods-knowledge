# P5 current native Pi Agent 1.3.0 CLI 2.1.302 real preflight

The source-controlled mandatory buffered native Pi runner was merged in
PR #89 from reviewed Git source 2aabca277cb947e9eb0d90e5554a03cd603c06af.
The exact merged code was independently compiled on MacBook Pro, Raspberry Pi
and sextant, and all three resulting common Skill and Plugin ZIP SHA256
digests matched byte-for-byte (5 compiled YAML Skills, 2 ZIPs, 53 artifacts).

The existing reviewed personal ChatGPT Plugin beta012 was NOT changed
because the P5 update affects only the native Pi QA runner; this was
not a new ChatGPT Plugin release.

Three real native Raspberry Pi commands executed once each, using a
private immutable report file and native installed Pi 1.3.0 / Claude
2.1.302 verification:

| Frozen QA case | Mandatory gate | Actual model calls |
| --- | --- | --- |
| BOUND-VERSION-NEW (unreviewed CLI2.1.310) | Correct abstain BEFORE backend health, safe reply hashed | 0 |
| POS-E-01 (current tool.call observer) | Blocked because pinned loopback Qwen backend returned connection reset | 0 |
| NEG-TYPESCRIPT unrelated | Correct preflight only; model not requested | 0 |

The same native subprocess uses an isolated, private Pi Agent configuration
for real model runs, with read-only tool access, no extensions/MCP and
a postflight gate that keeps all raw model events private. Red-first
synthetic tests of that integrated path confirm source omission, tool
scope error, model failure and bad CLI/Skill SHA are all rejected.
They do NOT substitute for real Qwen inference.

The Mac at about Sydney 17:34 had 6008 MiB swap in use, exceeding the
historical model-supervisor safety threshold of 512 MiB. Its Qwen backend
was offline (Pi's SSH forwarding socket was present but reset HTTP
connections). No attempt was made to change original user AI services,
start another server, disable memory protections or invoke native Qwen
under unsafe memory conditions.

This is a real native HOST PREFLIGHT result, not a native model
source-coverage or generated-code semantic PASS. Original private
reports remain outside Git. Their SHA256 fingerprints are provided
in the sibling redacted JSON; no account identities, prompts or model
answers are published.

The original ChatGPT Chat Mode 46-case gate and P4 strict boundary
activation 6/8 are unchanged. P5 and Stable remain HOLD.
Agent Communication is unrelated and outside project scope.
