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

## 验收结果的状态机

- `not_run`：未创建或未核实真实对话。
- `blocked`：平台读取/发送限流或其他环境阻塞，**不能当作模型答错**。
- `inconclusive`：完成了结构检查，但尚未独立审阅语义/代码，或边界行为无法靠结构判断。
- `failed`：加载、Claim、文档引用、代码签名或语义出现实质错误。
- `passed`：真实 Chat 资源读取与要求匹配，且语义独立审查通过；无关任务需确认不误触发。

报告输出 `FULL_SUITE_LIVE_CHAT_MODE_PASS` 的前提是 46/46 `passed`。任何无法完成的部分必须保留在当前 Beta 的 P5 风险清单，不能推广为稳定版保证。

## 当前已记录的恢复检查点

测试临时目录是 `/tmp/mods-p4-full-chat-20261014`；完成的 ID 保存在 `manifest.json`，每条发送返回值分别存于 `sends/`，脱敏结果在 `collected/`。前两条 POS-E-01 和 POS-E-02 在真实 Chat mode 发送、回复和资源读取的**结构检测**上通过；剩余条目继续逐项收集。首次批量脚本曾因聊天历史读取受限卡住第三次发送，随后已使用已有工具的 fast new-chat 路径恢复。
