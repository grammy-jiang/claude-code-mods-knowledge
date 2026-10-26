# P4: current verified way to use Claude Code Mods Knowledge in ChatGPT Chat Mode

**Updated:** 2026-10-27. **Installed personal Plugin at last real readback:** claude-code-mods-knowledge 0.4.12-beta.1, enabled; its single claude-code-mods-development Skill enabled. **Approved target of this package:** Claude Code CLI 2.1.302 only (31 reviewed Claims). This is NOT approval for current Claude Code 2.1.310.

## The critical distinction: native automatic selection vs reliable user-directed selection

The product documentation says ChatGPT *may* automatically select a relevant installed Plugin. The model makes that routing decision from metadata; the Skill body cannot force loading because the body is not available until after selection. A user may also directly select a Plugin through the composer. The supported portable plugin manifest has no forced global auto=true setting.

The real 2026-10-27 0.4.12-beta.1 pilot on Mac Chat Mode / GPT-6 Thinking Standard independently confirmed:
- **9/9 relevant positive tasks:** no native automatic Skill load.
- **3/3 version boundary tasks:** no native automatic Skill load (a routing failure; correct prose alone is insufficient).
- **3/3 unrelated negative tasks:** correctly did not load the Skill.
- **One same-prompt composer-selected Plugin control:** 4 genuine canonical reads, scoped structural PASS.
- **One NEG-SPORTS send:** ambiguous timeout. Never resend it without proving the previous post did not occur.

All 15 resolved original chats and the current account-downloaded Plugin ZIP were saved privately; the sanitized deterministic report is under docs/reports/2026-10-27-p4-beta012-live-routing-pilot-evidence.json. That account package was matched byte-for-byte against **11** canonical source files and the verified server sidecar.

Separate same-account real model/effort controls on POS-E-01 did not repair automatic loading: GPT-6 Thinking extended/high and max/extra-high plus GPT-5.6 Thinking standard all gave zero automatic Skill reads. These are single real attempts, not a universal statement about those models.

**Practical positive control:** three real separate Chat Mode requests across Events, Types and UI *without a composer system hint* explicitly asked in the text to use the installed Plugin and named Skill. All **3/3** genuinely loaded the correct Plugin and passed scoped Claim/source structural checks. Because the prompt itself explicitly requested that Plugin, these are **user-directed text requests**, NOT unbiased automatic-routing successes, and this finite sample does not guarantee every future response.

## Immediate user-facing fallback (no plugin reinstall or UI changes)

For the most dependable supported selection, open a normal Chat Mode chat, type @ and select the already installed Claude Code Mods Knowledge Plugin in the composer. You can also place the following at the start of a new Mods-only question (tested, but not a deterministic guarantee):

> For this Claude Code Mods task, use my installed claude-code-mods-knowledge Plugin and its claude-code-mods-development Skill. Actually read the applicable official reference pages before citing any K-Claim. Do not infer CLI 2.1.310 compatibility from older Claims. The technical task is:
>
> [Insert a specific Claude Code Mods / CLI 2.1.302 question.]

Do not add this prefix to unrelated TypeScript/Python/HVAC or general IT questions. Do not rely on a model simply *claiming* it loaded the Plugin; verify original api_tool.read_resource with the correct installed Plugin instance and canonical Skill resource URI before scoring technical acceptance. For generated Mods code, independently test the output on the actual reviewed CLI version.

## Safe local Codex/QA helper

For the user's MacBook Pro Codex workflow, the original Mods repository now has an **opt-in, deterministic text-directed prompt preparer**. It does not send any ChatGPT requests, change account settings, update Plugins or convert user-directed invocation into model auto-routing:

1. Create an original Mods question as a UTF-8 file in a private directory.
2. Run the helper with explicit reviewed target version 2.1.302:
   python scripts/prepare_p4_explicit_mods_request.py --input /private/task.txt --out /private/scoped-task.txt --target-version 2.1.302
3. Local Codex can use its already-installed chatgpt-web-operations Skill to send the generated file through the Mac adapter into an ordinary Chat Mode conversation. Use the same model/effort and record the real send ID and tool trace privately.
4. The helper refuses current unapproved target 2.1.310 and never overwrites an existing private prompt. The output is expressly flagged as **user-directed**, not an automatic-routing QA case.

This is a practical *controlled invocation* workaround in Codex-mediated requests; it does **not** change what native ChatGPT does for an arbitrary user question.

## CLI 2.1.302 approved guardrails to check after the Skill is actually loaded

当前已安装的 2.1.302 知识不能把旧版 2.1.296 Claims 直接复制成适用于最新版的事实。CLI 2.1.302 中实际使用的相关版本限定 Claims 包括：

- K-0040：透明事件观察器须让下游 next(e) 执行并保留原始结果。
- K-0041：Mod 事件输入按不可变数据处理，改写时复制字段。
- K-0048：以实际目标 CLI 的本地 TypeScript declarations 核对 API。
- K-0064：tool.call 回调参数顺序应为 ($, e, next)。
- K-0067：真实校验命令需要提供 Mod 目录，如 claude plugin validate --strict <mod-directory>。
- K-0068：诊断日志中的失败不得替代或破坏下游原始结果或异常，也不能导致 next(e) 被意外执行多次。
- K-0069：注册入口使用静态可发现的具名 register(on)。

只有在实际读取对应 references/claim-evidence.md，并核对每条 Claim 自己的官方精确 URL 后才能引用。这个要求适用于普通 ChatGPT Chat Mode，而不是把日志、原始调用结果或异常处理视作预训练知识就能保证的事情。这里提到的 Claims 不是针对 2.1.310 的批准。

### 历史 2.1.296-only guardrails（不能迁移成 302 审批）

此前针对 2.1.296 的 K-0038、K-0033、K-0034、K-0035 和 K-0037 等 guardrails 仍保留为历史版本知识；它们不因这篇用户操作说明而变成 2.1.302 / 2.1.310 的新的 approved Claims。

## Independent evidence / answer gate

The P4 acceptance dimensions remain independent:
- **Install/account:** exact Plugin version, enabled Skill, downloaded package SHA/sidecar/canonical file digest verified.
- **Routing:** genuine authenticated ordinary Chat Mode resource read, correct Plugin instance, canonical Skill URI; explicit selection and explicit text request are separate from unbiased automatic use.
- **Complete answer:** assemble all user-facing text segments after the most recent user request, not only the last assistant text message.
- **Sources:** each version-scoped approved K-Claim used anywhere in the answer must appear in opening Evidence with its own direct first-party Mods URL including exact section fragment; Scope then Answer.
- **Native code and semantics:** target-matched TypeScript declarations, native strict Mod validation and safe isolated tests; citation structure is not a runtime PASS.
- **Release:** real 46-case automatic Chat Mode evaluation, cross-Agent QA, approved latest target, account readback/rollback and release integrity must all pass. A workaround does not loosen P6.

Previous historical 2026-10-15 Beta.1 explicit-use pilot: 4/4 explicit natural-language requests and 8/8 composer-selected requests loaded the Plugin, but some answers carried native-invalid examples. This historical CLI 2.1.296 evidence must not be misrepresented as the 2026-10-27 CLI 2.1.302 account state or quality.

### Sources and further review

- OpenAI Plugins in ChatGPT: https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- Official Skills selection and description contract: https://developers.openai.com/plugins/concepts/skills
- Official testing guidance for Plugin packages: https://developers.openai.com/plugins/deploy/connect-chatgpt
- Agent Plugins portable manifest: https://agent-plugins.org/plugin-authors/manifest
- Project original routing factorial: docs/operations/p4-routing-factorial-evidence.md
- Real 2026-10-27 pilot: docs/reports/2026-10-27-p4-beta012-mac-real-chat-routing.md

**P4 native automatic selection remains FAIL and P6 Stable remains HOLD.** If the installed Plugin is enabled, has byte-identical reviewed Skill content, and remains unused on relevant automatic requests across controlled models, do not repeatedly reinstall or guess an undocumented auto setting. Use the reproducible evidence to raise a routing issue with OpenAI Support while retaining the user-directed fallback.
