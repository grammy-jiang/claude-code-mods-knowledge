# P4 current personal Plugin: genuine Mac Chat automatic versus explicit control

**Date:** 2026-10-27 Australia/Sydney.
**Verdict:** 15 genuine automatically invoked ordinary Chat conversations evaluated, zero relevant automatic Skill reads. The **positive automatic routing gate FAILS**. One separately selected-Plugin control PASSES its narrow structural test. This is not the complete 46-case qualification or any Stable release authorization.

## Authenticated account, exact target and source package

The Raspberry Pi's old ChatGPT cookie path received HTTP 401. Using the owner's already authenticated, dedicated Chrome CDP 9233 on MacBook Pro, both original Mac tool checks and an actual local Codex invocation of the existing chatgpt-web-operations Skill independently found:

- Installed and enabled personal Plugin: claude-code-mods-knowledge, version 0.4.12-beta.1.
- Its claude-code-mods-development Skill was enabled.
- Ordinary Chat Mode was available; no production account change or reinstall was needed.

A **real ChatGPT account-downloaded ZIP** was compared with the reviewed source ZIP of the *same exact version* from the historical 2.1.302 candidate. Its raw ZIP SHA differed due to server normalization, but the account-archive-check matched all **11 canonical files byte-for-byte** and verified the server-generated sidecar. These original ZIP bytes, account readback and browser records remain in the owner's mode-0700 private evidence store. Their SHA256 hashes and deterministic comparison outcome are pinned in the sanitized report.

The Plugin's source package only supports reviewed **Claude Code CLI 2.1.302** Claims. No new 2.1.310 Claims, user-installed Skills or Plugin updates have been approved.

## Frozen 46-case suite and 15 original Chat Mode results

The exact approved frozen 2.1.302 suite contains 30 positive, 8 unrelated negative and 8 version/security boundary cases. Each pilot sample had its own original unchanged prompt SHA, single genuinely sent *new ordinary Chat Mode* conversation, no composer-selected Plugin, an authenticated resolved conversation receipt, a real final model-origin reply and *all* user-facing text segments concatenated in order.

Both original-send receipts and assistant metadata confirm **GPT-6 Thinking / Standard**. Each ChatGPT Plugin read had to be a real api_tool.read_resource event with a canonical skill URI and the correct actual installed Plugin instance. Merely citing official Docs or answering from pretrained knowledge was not counted as a Plugin read.

| Actual automatic cohort | Finished new Chat conversations | Correct Skill reads | Structural outcome |
| --- | ---: | ---: | --- |
| Nine positive cases across Events/State/Types/Testing/Permissions/UI | 9 | **0** | 9 failed activation |
| Three unrelated controls | 3 | **0** | 3 correctly not activated |
| Three version boundaries | 3 | **0** | 3 failed required activation |
| **Combined** | **15** | **0** | 12 category-specific failures, 3 correct negatives |

Real replies contained from one to several visible assistant text segments. The QA grader used the *entire* latest user-facing turn, not the final message snippet alone. Raw model conversations, user/account IDs and browser data are only in the original private directories, never this repo.

### Same exact prompt, explicit selected-Plugin control

One additional actual new Chat Mode conversation used the **identical** original POS-E-01 prompt and same model/effort/account Plugin version, but selected the account's currently installed Plugin using the exact composer system hint. The original user-to-plugin read trace showed **four canonical resources from the correct personal Plugin instance** and the structural Claim/source checker PASSed. The automatic POS-E-01 counterpart had **zero reads** and failed.

This confirms that the installed reviewed Plugin content is available **on explicit selection**. The explicit control is **not** added to the automatic 46-case denominator, and its structural PASS is not an independent correctness or runtime pass for generated Mod code.

### Incomplete send: no re-post

The later NEG-SPORTS automatic new chat send timed out before producing a resolved conversation receipt. A recent-chat listing query also timed out, so the tool could not establish whether that send was posted. The dispatcher **stopped without retrying** and marked the event as ambiguous. The known conversation IDs for the other 15 cases remained readable, and all 15 were independently collected. NEG-SPORTS is not a negative nonactivation PASS and must not be silently resent.

Remaining 30 frozen cases were not sent. **15 finished + 1 ambiguous + 30 not run** does not equal full 46-case completion.

## Routing metadata does not establish a unique root cause

The authenticated Plugin chooser listed the target Plugin as connected with a genuine matching explicit hint. Every one of its **43 Plugin entries** had the is_auto field false. As this field did not discriminate the target Plugin from its peers, it cannot prove a uniquely misconfigured Mods Plugin or that its model router is disabled.

Earlier in this project a true six-arm 42-conversation experiment changed Plugin/Skill descriptions and knowledge independently: 0/24 automatic positives, 6/6 explicit controls. Earlier historical Beta.1 had 27/30 positive loads. This evidence rules out **claims of an easy or deterministic description-only fix**; it does not establish whether model effort, product routing policy, rollout phase or cache is causal.

Official product documents describe a model-driven automatic selection, plus supported explicit Plugin selection:
- https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- https://developers.openai.com/plugins/concepts/skills
- https://developers.openai.com/plugins/deploy/connect-chatgpt

Plugin Skill body instructions apply *only after the model has loaded the Skill*. Editing them cannot compel the platform to load an otherwise unselected Skill.

## Independent audit, privacy and next steps

The bounded QA auditor scripts/audit_p4_cli302_beta012_live_pilot.py re-reads the private account ZIPs, authenticated status, immutable exact 2.1.302 suite prompts, 15 original resolved send receipts, complete original Chat Mode conversations and one explicit control. The auditor was replayed twice and produced **byte-identical sanitized JSON**, stored as docs/reports/2026-10-27-p4-beta012-live-routing-pilot-evidence.json. No original raw chats/IDs/tokens uploaded.

CI validates the public source-scoped hashes and outcomes, but cannot recreate the private model inference from sanitized hashes. No claim that manually selected Plugin is automatically invoked is allowed.

**Next:** isolate model routing behavior under an unchanged installed Plugin using paired native Chat model/effort controls and source-identical prompts, not new arbitrary descriptions. Avoid altering the user's current working Plugin until a candidate fix is demonstrated superior in real Chat Mode and keeps unrelated nonactivation.
