# P4/P5 — 完整真实 ChatGPT 普通聊天模式验收

**测试版本：** `claude-code-mods-knowledge 0.2.0-beta.1`
**目标 Claude Code：** CLI 2.1.296
**Git 基线：** `33706131f05f0aedf49fbb1fc0459854a579316d`
**运行表面：** ChatGPT **Chat mode**，不是 Work。Claude Code/Codex 模型额度不足，不在本轮消耗。

## 完整测试的定义

真正的“完整 P4/P5 模型验收”必须对 `evals/p4_cases.json` 现存的 **46 项**各自创建一个真实 Chat 会话，获取明确 conversation ID、最终回复及 `api_tool.read_resource` 调用记录。分布为 E/S/T/Q/P/U 对应的 30 条正向，8 条无关任务，8 条版本和安全边界问题。

逐项记录与验收标准：

1. 正向：自动触发（默认没有显式 `@`）应实际加载本 Plugin 的 Skill，并读取相关参考文件；回复应准确，含期望来源/Claim。一个正确的通用模型回答**不等于**插件自动触发通过。
2. 负向：无关任务不应读取本 Plugin。模型本身是否能给出正确的 HVAC 等答案不是本插件知识准确性的证据。
3. 边界：历史预览 API、目标版本未核验、来源注入或权限绕过要求必须得到合理的拒绝/澄清；期望加载 Skill 但未加载，仍应记录触发失败，不得仅因模型靠通用知识拒绝就判插件通过。
4. 必须独立记录 `结构检测` 和 `语义审查`。参数、Claim 链接、版本范围、权限等应基于实际回答审查，不得使用一个正则或“回答中包含官方 URL”代替技术检查。
5. 只有 **46 个真实完成的独立 Chat 会话、46 个最终通过、零失败/阻塞/待审**，才可以称为这一版完整 Chat-mode P4 测试通过。静态 P4 46/46 不算 Chat 模型通过。

## 使用 Raspberry Pi 的真实 Chat 浏览器

这台 Pi 的 `chatgpt-web-operations` 是经过安装的独立账号操作工具。它持有浏览器的正常登录会话，使用 Chrome 的 Chat composer，不调用 Work。**不要将会话 Cookie、账号令牌或原始回复提交 GitHub。**

```sh
S=~/.claude/skills/chatgpt-web-operations/scripts
python3 "$S/manage_plugins.py" show claude-code-mods-knowledge
python3 "$S/preflight.py" --browser

# 当历史列表触发限流而 Chat 发送仍可用时，使用该工具原生、
# 已验证的 fast new-chat 路径，避免每次发消息都查询历史列表：
RP_NEWCHAT_FAST=1 python3 "$S/send_prompt.py" \
  /tmp/mods-p4-full-chat-20261014/prompts/04-POS-E-04.txt \
  --effort standard --no-wait \
  --json /tmp/mods-p4-full-chat-20261014/sends/case-04.json
```

这个快速路径仍通过登录用户的**正常 Chrome Chat 网页**提交；浏览器网页返回的真实 conversation ID 是优先证据，只有网页返回临时 ID 时才回退历史查找。它**不是**在没有同意的情况下构造 HTTP 请求或规避发送限流。

**限流规则：**历史读取限流和消息发送限制须分辨。遇到真实消息发送 429、无 conversation ID、HTTP 权限问题或浏览器提示无法发送时立即停止，先恢复平台状态。禁止更换网络/账号规避速率限制、盲目重发未确认的消息或并行操作同一个浏览器。每个成功的 `--json` 记录都需要进入检查点，重复运行时必须跳过已确认的 conversation ID。

## 收集与质量审核

使用 `chatgpt-web-operations` 提供的登录会话只读 `get_conversation(ID)` 读取完成的 Chat 会话，抽取插件资源读取元数据，然后以仓库 `mods_knowledge.chat_mode_evidence.summarize_chat_mode_case` 判断结构：

- 工具动作必须是 `api_tool.read_resource`；
- 插件 URI 前缀为 `skills://plugins/claude-code-mods-knowledge/claude-code-mods-development`；
- `skill_plugin_id` 指向当前用户安装的 Plugin；
- `tool.call` 示例必须包含 `($, e, next)`，不能丢掉首参数；
- 仅当正式回复完成且内容匹配测试任务时，才记录接收到模型结果。

仅在本地 `/tmp` 保存完整对话用于审查，发布证据只包含 `conversation_sha256`、`response_sha256`、`plugin_id_sha256`、资源 URI、结构评分、Claim IDs 和独立人工/Agent 技术审阅摘要的哈希。

```sh
uv run mods-knowledge chat-report \
  --records /tmp/mods-p4-full-chat-20261014/records.json \
  --plugin-version 0.2.0-beta.1 \
  --source-revision 33706131f05f0aedf49fbb1fc0459854a579316d \
  --manual-reviews /tmp/mods-p4-full-chat-20261014/manual_reviews.json \
  --out /tmp/mods-p4-full-chat-20261014/full_qa_report.json
```

上述 `--records` 和 `--manual-reviews` 只有在实际收集和独立审查发生后才生成。报告汇总器不会访问账号、执行模型或凭空补齐缺失案例。

## 重要：一条 Chat 回答可能由多个可见 assistant 消息组成（2026-10-15）

在真实 Chat Mode 对照实验中，12 条答复有 **11 条**含 2–3 个连续可见 assistant `text` 消息；有一条显式调用真实答复为 81、5537、873 字符三段，旧 `chatgpt_client.latest_reply(conv)` 只读最后 873 字符。只评分最后一段会产生错误的 Claim/source 缺失判定，**即使 Plugin Skill 实际已经加载并完整回答**。

收集器应先确认最新一次用户回合及实际完成状态，然后使用包内纯函数：

```python
from mods_knowledge.chat_visible_reply import collect_latest_visible_reply

whole = collect_latest_visible_reply(cc.chain(conv))
reply = whole.reply_text  # 所有属于最新用户回合的可见 assistant 文本
segments = whole.segment_count  # 只用于事实审计，不是质量分数
# 再将 reply 交给 summarize_chat_mode_case 与独立语义审查。
```

这个拼接仅包含发给用户的文本片段，不拼接工具输出、内部分析、历史用户回合；未完成的尾消息必须保持 pending/blocked，不可当作最终 PASS。**全文评分仍不等于代码/权限语义验收。** 新案例及纠错说明见 [显式调用 Chat-only QA](../reports/2026-10-15-chat-mode-explicit-usage-qa.md)。先前只用 `latest_reply` 的公开结构分数可能对多片段回复漏评，必须在真实原会话回读和独立审核后另行更正，而不能凭空改为通过。

## 验收结果的状态机

- `not_run`：未创建或未核实真实对话。
- `blocked`：平台读取/发送限流或其他环境阻塞，**不能当作模型答错**。
- `inconclusive`：完成了结构检查，但尚未独立审阅语义/代码，或边界行为无法靠结构判断。
- `failed`：加载、Claim、文档引用、代码签名或语义出现实质错误。
- `passed`：真实 Chat 资源读取与要求匹配，且语义独立审查通过；无关任务需确认不误触发。

报告输出 `FULL_SUITE_LIVE_CHAT_MODE_PASS` 的前提是 46/46 `passed`。任何无法完成的部分必须保留在当前 Beta 的 P5 风险清单，不能推广为稳定版保证。

## 当前已记录的恢复检查点

测试临时目录是 `/tmp/mods-p4-full-chat-20261014`；完成的 ID 保存在 `manifest.json`，每条发送返回值分别存于 `sends/`，脱敏结果在 `collected/`。前两条 POS-E-01 和 POS-E-02 在真实 Chat mode 发送、回复和资源读取的**结构检测**上通过；剩余条目继续逐项收集。首次批量脚本曾因聊天历史读取受限卡住第三次发送，随后已使用已有工具的 fast new-chat 路径恢复。

## 同一组真实场景的跨版本比较

新版本应在独立新会话中重新执行原先失败或代表性的用例，并保持相同 prompt、`case_id`、Chat mode、模型 effort 和自动触发模式。将每个版本经脱敏的 `records.json` 单独保存；不能将上个版本的成功结果并入新版本的实测计数。

```sh
uv run mods-knowledge chat-compare \
  --before /tmp/mods-p4-full-chat-20261014/records.json \
  --before-version 0.2.0-beta.1 \
  --after /tmp/mods-chat-beta2-retest-20261014/records.json \
  --after-version 0.2.0-beta.2 \
  --out /tmp/mods-chat-version-comparison.json
```

结果只比较两轮**均已收到真实回复**的 case ID，并区分结构性恢复、退步、持续失败、Skill 自动加载的获得与丢失，以及未复测用例。它**不会声称模型语义已经人工审查或新版本通过全部 46 项**。在没有新记录时，保持 `not_run`，不能把缺失记录填成 `pass`。

比较用的原始 Prompt 和回复只保留于 Pi 上的私有 `/tmp` 工作目录。GitHub 可保存聚合统计、失败类型及哈希引用，但不得提交账号会话 ID、Cookie 或原始聊天内容。


### 严格校验的清单作者信息检查（K-0034）

模型给出完整的 `.claude-plugin/plugin.json` 示例且建议执行 `claude plugin validate --strict` 时，回答审查应检查 `author` 对象是否存在。Claude Code CLI 2.1.296 上，缺少 `author` 在普通验证中仅产生警告，在严格模式下会令验证失败。

`mods-knowledge answer-lint` 新增 `strict-validate-manifest-author-warning` 风险标志：只有同时找到明确标注的 Manifest JSON、实际严格验证命令且没有作者对象时才标记；明确标注错误的反面示例只列入人工审查，避免将否定案例误报为推荐代码。

这只是一条**版本限定的已知风险检测**，不会自动执行用户提供的代码，也不能把零风险标志解释成语义 QA 已通过。
