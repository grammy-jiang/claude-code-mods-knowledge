# P4: Explicit, evidence-backed Mods Plugin use in ordinary ChatGPT Chat Mode

**Updated 2026-10-16 (Australia/Sydney). Chat Mode only; NOT Work Mode.** Target knowledge: Claude Code **CLI 2.1.296**. The verified installed personal package currently is published **`0.2.0-beta.1`**, which contains **26 approved Claims**. The current repository SSOT has 31 target-scoped approved Claims; this compiler change has not been installed in the user's personal account merely by merging it.

## Evidence-backed current capability

OpenAI's [Skills documentation](https://developers.openai.com/plugins/concepts/skills) confirms that the model receives Skill name/description metadata, then can load its instructions for a matching task or direct invocation. [Plugins in ChatGPT](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) describes auto-use where relevant and explicit `@` / composer selection. [Connect and test](https://developers.openai.com/plugins/deploy/connect-chatgpt) requires real positive, indirect, negative and boundary cases plus actual resources used, not just model claims. The distinct Work Mode MCP quickstart is **not evidence for Chat Mode Skill selection**.

Latest real ordinary Chat Mode [12-case explicit-use QA](../reports/2026-10-15-chat-mode-explicit-usage-qa.md): an explicit natural-language instruction mentioning the installed Plugin and Skill loaded the correct canonical Skill **4/4**, with no selected-plugin composer hint; direct composer-selected Plugin loaded it **8/8**. This is a **sample observation**, not 100% future reliability. Furthermore, **three structurally source-compliant positive answers contained independently native-rejected code/command examples**. The installed Skill must improve source-check guidance, but **a model cannot be forced to use a Skill by that Skill's own body**, because the body is only available *after loading*.

The published Beta.1 lacks later approved guardrails: `K-0032` named `register(on)` entry, `K-0033` plugin-directory testing, `K-0034` strict manifest `author`, `K-0035` required `claude plugin validate` directory and `K-0037` fail-isolated transparent-observer diagnostics. Source compilation, a new versioned account installation/content check and real Chat Mode source/native semantic QA are each necessary before promotion. The earlier private `0.3.3-beta.2` real model candidate had 4/4 intended Skill reads but still failed observer semantics, so no new package has been promoted. Do not tell the user these newer Claims are available in the currently installed Beta.1 when they are not.

## Recommended reusable **text-only** Chat Mode prompt

The following is a practical, source-scoped direct-invocation request. It **does not** itself guarantee a Plugin read or correct code:

> 请在普通 ChatGPT Chat Mode 中使用**已经安装的 `claude-code-mods-knowledge` Plugin** 及其 **`claude-code-mods-development` Skill**。
>
> **先实际读取** Skill 主文档和与本问题有关的 `references/*.md`；不要仅凭插件名称或模型记忆回答。若无法读取，请明确说明“无法确认插件知识已加载”，不要伪造已读取的来源或未经验证的 API 示例。
>
> 对每条关键技术结论写出**已批准的 K-Claim ID、其对应的 Anthropic 第一方 Mods 文档直接 URL**，并注明 Claim 适用的 CLI 版本。对于**每一条实际引用的 K-Claim**，请核对相应 reference 文件中该 Claim 的**准确 `Source:` URL，包括 `#` 后的章节锚点**；即使是同一官方网页，其他章节的锚点也不算这条 Claim 的来源。当前知识目标为 **Claude Code CLI 2.1.296**，除非已经另外核验，不要推广到其它版本或 Desktop。
>
> 若提供可执行 Mod 代码或测试命令，先检查参考中的 `K-0031`（回调）、`K-0032`（注册入口）、`K-0033`（测试目录）、`K-0034`（严格校验）、`K-0035`（validate 路径）及 `K-0037`（含异步日志 rejection 的透明观察器隔离）是否在当前**已加载**的版本中得到批准；缺失的 Claim 明确说明而不是编造。透明 `tool.call` 观察器中，**日志失败或异常不得改变原始 `next(e)` 成功结果、原始异常或事件输入**；必要时只针对诊断副作用单独 `try/catch` 保护。不得声称执行了任何未实际执行的原生验证。
>
> 最后说明所用来源及未验证事项。只有真实的 Skill 读取记录才可以证明“实际加载”；你的文字声明不是读取记录。
>
> **我的问题：** `[写入 Claude Code Mod 的具体需求]`

For the most direct user-side targeting, use the Chat Mode composer `@` and select **the installed plugin** before sending the task. This is a supported explicit invocation control, whereas mentioning a plugin by name in ordinary text is still interpreted by the model. Neither a text-only instruction nor an `@` selection is a deterministic guarantee of technical correctness.

## Strict validation: two independent acceptance dimensions

**1. Real knowledge retrieval (P4 invocation):** Review a *trusted Chat Mode trace* for `api_tool.read_resource`, the expected canonical URI prefix `skills://plugins/claude-code-mods-knowledge/claude-code-mods-development` and the exact installed Plugin instance. For each substantial API question, also inspect actual read resources under the relevant `references/*.md`. If no trace is available, report **`READ_NOT_VERIFIED`**, not `PASS`. The model saying "I read the Plugin" or emitting K-IDs does not establish a tool event. Missing positive read is `READ_FAILED`, not model content acceptance; version/transport restrictions are `BLOCKED`.

**2. Genuine content correctness (P4 semantics):** Read the **entire most recent visible user-facing Chat turn**, not just the last assistant text message. Check Claim IDs against the active installed version, **every cited Claim's own exact approved `Source:` URL including its `#anchor`**, exact CLI/surface, disputed/version-limited Claims and any dangerous or unsupported examples. Use the independent `mods_knowledge.claim_source_link_coverage.audit_claim_source_links` with already validated SSOT Claims for fail-closed per-Claim URL coverage; it is NOT a replacement for actual `read_resource` trace verification or semantic/native QA. For runnable code, test in a disposable Mod on **the exact target CLI** with `claude plugin validate --strict <mod-directory>` and safe mocked `claude plugin test <mod-directory>`. Distinguish `SOURCE_STRUCTURAL_PASS` from `NATIVE_CODE_PASS`; a model with a source-compliant answer has previously produced incorrect `register({ on })`, a single `.test.ts` file invocation, a pathless `claude plugin validate`, and an **unprotected observer logger that can mask downstream errors**. Always separate per-Claim correct sources from fully preserved tool result/error behavior.

Record each phase separately: `READ_NOT_VERIFIED / READ_FAILED / READ_CONFIRMED` and `SOURCE_UNVERIFIED / SOURCE_STRUCTURAL_PASS / SEMANTIC_FAILED / NATIVE_CODE_PASS`. There is no user-controlled Chat Mode setting in the documented Skills-only package that can convert an ordinary text prompt into a guaranteed enforced `read_resource` call or guaranteed correct native code. A separate trusted external QA harness can **detect** failures; it cannot make an individual ChatGPT response deterministic without a supported host enforcement mechanism.

## Qualification gate before claiming "100% reliable"

- Repeat a frozen set of prompts across Events, State, Types, Testing, Security, UI and boundary topics, with text-only direct mention and explicit `@` controls stored **separately**. Include varied wording, reused requests in new conversations and follow-ups, as OpenAI guidance requires. Collect all actual model-visible assistant segments and source-read events, not a superficial "plugin used" string.
- **Zero missing real positive Skill reads, zero false source claims, zero invalid recommended native code and zero unsafe boundaries** in the observed qualification set is necessary to report that *that set* passed. Absent full independent review, keep stable status **blocked**.
- Even a 100% score on a finite sample is **not an absolute future guarantee**. Maintain regression monitoring and an honest fallback: when a real read is absent, request the user to select the plugin with `@` or surface the limitation instead of silently giving an unverified answer.

All account IDs, original private conversations and raw reply texts remain in private local QA evidence. GitHub reports may contain only case IDs, hashed identifiers, reviewed resource URIs and bounded failure summaries. No uncontrolled Plugin installation or history rewrite is part of this procedure.
