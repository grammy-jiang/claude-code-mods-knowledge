# P4 routing follow-up: model-effort variations and text-directed controls

**Date:** 2026-10-27, Sydney local time. **Scope:** real ordinary ChatGPT Chat Mode, Mac authenticated account, installed source-audited claude-code-mods-knowledge 0.4.12-beta.1 targeting only CLI 2.1.302. **Current status:** provider/model automatic selection **NOT FIXED**.

## Reproducible observations

The main [15-case real automatic pilot](2026-10-27-p4-beta012-mac-real-chat-routing.md) independently proved 0/9 relevant positive native Skill loads, 0/3 required boundary loads and 3/3 correct unrelated nonactivations; one same-prompt composer-selected control read four correct resources and passed its structural checks.

This follow-up changed only the original authenticated ChatGPT model selection, holding the same original POS-E-01 prompt and the exact same installed Plugin ZIP and Skill:
- GPT-6 Thinking / extended (High) — 0 automatic Skill reads, structural fail.
- GPT-6 Thinking / max (Extra High) — 0 automatic Skill reads, structural fail.
- GPT-5.6 Thinking / standard — 0 automatic Skill reads, structural fail.

The original baseline GPT-6 Thinking/standard POS-E-01 also had zero automatic Skill reads, from the independently source-locked prior pilot. Changing the model/effort alone did **not** produce a recovery in these controlled trials. Three single samples are not enough to rule out all model-dependent effects or report a universal deterministic probability.

As a non-automatic fallback, the same account ran three new genuine requests that **explicitly named the installed Plugin and Skill in the user's question** while leaving composer-selected system hints empty. For POS-E-01, POS-T-01 and POS-U-01 the actual ChatGPT event streams each contained the correct personal Plugin instance's canonical resource reads (at least three per case) and the narrow source/Claim answer structural checks passed: **3/3**. Their original replies are retained privately; this is **text-directed invocation, not automatic-selection success or native executable Mod QA**.

All six new model/origin conversations, original send receipts, full user-visible replies, tool traces, model metadata and account installation proof are independently SHA-bound by scripts/audit_p4_model_routing_controls.py. A deterministic replay was run twice and yielded identical public evidence under [2026-10-27-p4-model-routing-text-directed-evidence.json](2026-10-27-p4-model-routing-text-directed-evidence.json).

## Scope of the possible platform issue

The installed Plugin is discoverable, enabled, source-validated, and can be accessed on explicit request. The **model-mediated implicit selection** is not reliably happening in current ordinary Chat Mode, despite relevant questions and the documented Plugin/Skill description. This observation cannot independently identify product routing policy, rollout state, cache propagation or account-specific model availability as the cause.

The authenticated chooser's is_auto=false appears on all 43 advertised Plugin entries and **does not uniquely implicate this Plugin**. The portable Agent Plugin manifest format does not expose a supported global auto=true override; inventing one would not be a supported fix. Changes to the Skill body after activation cannot force a Plugin to be loaded before activation. Earlier 42-case description-only experimental metadata variations also did not establish a fix.

Official reference for expected relevant-plugin behavior and support escalation:
- https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- https://help.openai.com/en/articles/20001497-troubleshooting-plugins-and-apps-in-chatgpt
- https://developers.openai.com/plugins/concepts/skills

## Minimal support reproduction (safe to share without private data)

1. On an authorized ChatGPT account with claude-code-mods-knowledge 0.4.12-beta.1 installed and Skill enabled, open **ordinary Chat**, not Work.
2. Select GPT-6 Thinking / Standard, with **no** selected Plugin/plus-menu hint.
3. Ask one reviewed CLI 2.1.302 task from the frozen original project suite, for example the transparent tool.call observer case POS-E-01. Its exact public prompt is in evals/p4_cases_cli_2_1_302.json.
4. Inspect real api_tool.read_resource events for the canonical Skills URI. In nine different relevant original tasks, none occurred, even though answers may have been model-generated.
5. Ask the same POS-E-01 task in another new ordinary Chat with the installed Plugin **selected using the supported composer control**. That control produced four correct Plugin resource reads and structural answer PASS.
6. Repeat without a composer hint but with a direct user instruction to use the named installed Plugin/Skill. Three sampled Mods cases read the correct Plugin and passed structural citation checks.
7. Review exact selected model/surface, original case and evidence SHA, and qualified source package version. Do not send private account IDs, session cookies, downloaded account ZIPs or raw unrelated chat content to public GitHub.

**External support ticket submitted? NO.** Only this sanitized reproduction and owner-local evidence were prepared; no external support account or credential was accessed to submit the ticket.

## User-facing resolution and release boundary

The project provides a controlled, user-directed fallback, not a forced native automatic-selection implementation. For users and local Codex-mediated requests, explicitly name the installed Plugin/Skill or select the Plugin with @ in Chat Mode. The repository's opt-in private prompt helper only formats a text-directed request for exact approved CLI 2.1.302. Keep the original automatic 46-case P4 release gate unsatisfied and do not mark Stable or new CLI 2.1.310 APIs approved.
