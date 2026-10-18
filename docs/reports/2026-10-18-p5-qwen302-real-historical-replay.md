# P5: current CLI 2.1.302 buffered gate replays TRUE historical Qwen errors

Date: 2026-10-18, Sydney.
Source: three previous actual, fully completed native Pi Agent 1.3.0 /
mac-qwen/qwen36-35b-a3b-mtp model turns.

**IMPORTANT:** This is OFFLINE HISTORICAL REPLAY, not a new model completion
on the current Skill. The Qwen server was not started; there were zero
inference/browser/network requests from the independent audit script.
Old original beta-era P5 records remain immutable.

The original full native event stream and final answer SHA256 were
independently compared with the already-published factual baseline
docs/reports/2026-10-18-claude302-pi-local-native-recovered.json.
All THREE native model wires matched the historical original report
EXACTLY, including each full assistant final output fingerprint and
final stopReason=stop. Native model provider/model identity was also
checked from the original message events, and each original prompt
fingerprint was unique.

Each original event sequence was then fed into the **current**
reviewed CLI2.1.302 Pi preflight/postflight and approved first-party
Claim/URL checks. These scores describe how the present delivery
GATE would judge the ORIGINAL Qwen model behavior.

| Original real Qwen case | Current preflight | Current buffered postflight |
| --- | --- | --- |
| POS-E-01 | Run reviewed in-scope model | BLOCK: exact Claim/first-party source incomplete; executable example needs independent semantic validation; structural conditions fail |
| NEG-TYPESCRIPT | Run unrelated model without Mods source requirements | ALLOW_STRUCTURAL_ONLY, no Mods Skill activation, NOT a runtime-model correctness pass |
| BOUND-VERSION-NEW | ABSTAIN BEFORE MODEL for unreviewed 2.1.310 | BLOCK historical answer: model was launched without the required preflight |

For POS-E-01 the current gate additionally noted an unreviewed
version reference. This is not fixed by a general-model disclaimer
or by successful Skill activation. The earlier actual Qwen answer
had cited K-0041/K-0042 without each exact first-party approved URL.

The historical future-version 2.1.310 answer had generated unreviewed
runnable old-version Mod code; the new preflight would have prevented
starting that model at all. Its historical completed text is marked
preflight-not-enforced and withheld. A later use of the new runner
cannot "undo" that previous output; this audit only establishes that
current gate logic rejects the original known failure.

The unrelated negative was correctly outside Mods Skill scope and is
approved for structural isolation alone. Although the underlying
postflight has a flag for allowing an unrelated answer, this
READ-ONLY replay script never emits raw historical replies and does
not itself authorize user-visible delivery.

No original raw prompts, actual account IDs, model replies, local
private paths, authentication data, or model-generated code are in
the public files. The JSON includes only bounded case identifiers,
SHA256 fingerprints and tool gate reason codes. The verifier source
SHA256 and the previously reviewed Claim pack Git source SHA are
recorded. The verifier does NOT claim to independently refetch
tool event bodies from the original model provider: it reads the
exact original private native wire whose digest matches the prior
immutable real model report.

## What is still NOT proven

- Real Qwen inference using the latest installed 0.4.12 Skill;
- runtime execution/compilation and semantic correctness of generated
  Mods code from any model;
- any current complete three-host model acceptance result;
- the full current ChatGPT Chat Mode 46-question acceptance;
- original P4 strict 8/8 boundary activation (still 6/8);
- release approval.

The Qwen server was offline at 23:31 Sydney; Mac Swap still used
about 5.99 GiB, above the earlier supervisor 512 MiB condition.
Do not bypass resource protection or confuse an SSH forwarding
listener with a working model backend.

**Stable remains HOLD.** Agent Communication is a different project
and intentionally excluded.
