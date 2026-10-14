# P4 ChatGPT Chat mode — 全量测试、Beta.3 回归与版本回退

日期：2026-10-14（Australia/Sydney）
项目：claude-code-mods-knowledge（GitHub 仓库为 Public）
当前 **ChatGPT 账号安装版本**：`0.2.0-beta.1`（ENABLED，已核对）
知识目标：Claude Code CLI 2.1.296

## 状态总结

**P0–P3 核心知识与编译基础设施已完成。P4/P5 的模型层端到端验收仍有阻塞，P6 只有 Beta.1 已正式发布。** 不能因为自动化测试通过就宣布完整 Chat mode 验收或稳定版发布完成。

### P4 已经做了什么

- 对 `0.2.0-beta.1` **完整执行 46/46 条真实 ChatGPT 普通 Chat mode 问题**，分别有独立会话 ID、最终回复和 Skill 资源读取检查。
- 30 条正向问题中 `27/30` 自动加载 Skill；按现行严格结构规则 `15/30` 通过、`15/30` 未达标。后者包含 3 次没有加载 Skill、12 次回答引用的 Claim/直接官方 URL 不符合预期。
- 8 条无关问题均未误触发（观察误触发 `0/8`）。
- 8 条历史／不受支持版本／安全边界问题均未自动加载 Skill（插件验收 `0/8`）；模型独立给出谨慎回答**不等于**插件触发通过。
- 以上“结构 PASS”不是 API 源码正确性的全面语义审查；例如 Beta.1 曾产生非官方的 `export default function register({ on })` 范例。
- 新增并实测了版本/宿主/许可证/可追溯性检查和 QA 报表生成器。所有正式 P4 验收均使用普通 Chat mode，不使用 Work mode。

### P4 Beta.2 → Beta.3 修复实验

| 指标 | Beta.1 | Beta.2 | Beta.3（目标子集） |
|---|---:|---:|---:|
| 原 15 条正向失败中恢复 | — | **8/15** | 没有针对全部 15 条复测 |
| Beta.2 剩余 7 条失败再次复测 | — | 7 条失败 | **1 条恢复、6 条仍失败** |
| 同一轮两个事件基础成功对照 | — | 均通过 | **两条都退步**，未自动加载 |
| 版本/安全边界触发 | 0/8 | 2/8 | **0/8** |
| Beta.3 定向测试提交 | — | — | 18/18 |
| Beta.3 已读取最终回复 | — | — | **17/18** |
| 剩余无法读取的一条 | — | — | NEG-HVAC，平台会话读取停滞；**不是模型失败** |

Beta.3 这 17 个回复包含 9 条正向和 8 条边界。正向中 `3/9` 加载 Skill，`1/9` 通过结构规则；边界中 `0/8` 加载 Skill。这是**有意挑选的失败回归子集**，不能把 `3/9` 外推为全量 30 条的触发率。确切逐项结果在 `2026-10-14-beta3-chat-qa-summary.json`，不含原始聊天内容。

两轮比较工具 `mods-knowledge chat-compare` 仅比较相同 case ID 的真实观测，不会把未复测当成恢复，也不会把普通模型的正确回答冒充 Skill 加载证据。

### 三设备代码与打包门禁

在最终 QA 工具提交 `e41c33e`：

- MacBook Pro：Python 3.11 / 3.14，共 **285 项测试各自通过**。
- sextant：Linux ARM64，**285 项通过**。
- Raspberry Pi：Beta.3 原功能提交 `3443ddf`，**276 项通过**，QA 对比工具另有 9 项通过。
- Beta.3 Plugin ZIP SHA-256：`b09c1713ff2121519904d4b575595ec465fe305c56e36d329d1b6c49eda76f2b`。
- 三设备构建同一目标 ZIP 字节一致；Skill YAML frontmatter 和 Agent Plugins 1.0 Manifest 通过结构/标准解析器校验。
- `P0` 91 条来源记录、`P2` 已批准 26 条 Claim、5 条候选继续保持可信边界；原始 14 份研究文档的 SHA-256 仍通过。

**平台模型验收的问题不是 Python 测试失败，而是 ChatGPT 自动选择插件并遵循引用规范的可靠性不足。**

## 回退判定和 GitHub 状态

- ChatGPT 账号插件先后安装测试了 Beta.1、Beta.2、Beta.3；Beta.2 的 YAML frontmatter 存在兼容性问题，不应发布为标准可移植版本。
- Beta.3 的 YAML 已修复，但真实自动路由复测有显著退步。**不将 Beta.3 发布为正式 GitHub Beta/Stable。**
- 经正常 Plugin 管理器执行 `0.2.0-beta.3 → 0.2.0-beta.1` 更新，并核验账号显示 `0.2.0-beta.1`、`installed=yes`、`ENABLED`、`claude-code-mods-development on=yes`。
- GitHub `main`／正式 Release 继续指向经过审查的 `v0.2.0-beta.1`。QA 工具及未达到发布要求的候选改动保存在独立功能分支 `feat/p4-chat-live-full-20261014`，不自动覆盖主分支。

## 还有哪些工作

1. **P4 最优先：真实 Chat mode 自动路由。** 查明为何 Mods 同一问题在不同新会话中会出现“已加载／未加载”的摇摆。需做重复采样和显式 `@claude-code-mods-knowledge` 对照，并区分插件安装、技能选路、读取、回答质量四个阶段。不能靠静态描述或手工提高评分宣布“已修复”。
2. **P4 独立语义正确性门禁。** 对返回代码验证 `register(on)`、`($, e, next)`、官方文档适用版本和当前本地 TypeScript 声明；对缺少依据或错误 API 的答案给出正式语义失败状态。
3. **P4 边界安全与历史隔离。** 八条测试必须核验 Mods 版本、UI 宿主、managed permissions、恶意第三方来源和不当安装要求；即使通用 ChatGPT 模型会拒绝，也要实际检验插件是否被触发。
4. **P5 未完成的 Agent 宿主测试。** 等 Claude Code、Codex 模型额度恢复后做真实加载与执行测试；Pi Agent 同样需要真正的运行时验收，不能用 Python/Linux 包测试替代。
5. **P6 下一版发布门禁。** 只有新的候选通过独立的 YAML、Schema、三机 SHA、Chat mode 正负向/边界和回滚检查，才能合并为新的 Beta；全面稳定版必须满足正式接受门禁。既有 Beta.1 应保持可回退。
6. **P7 可选：只读官方文档 MCP 与 SSOT 自动版本更新。** 属于后续功能，不应阻塞现有 Plugin 质量修复。

## 证据保管与审查限制

原始 46 条 Beta.1 Chat 会话、26 条 Beta.2 复测、18 条 Beta.3 复测都由 Raspberry Pi 正常登录的 Chat 浏览器创建；Beta.3 只有 17 条成功读取了最终回复，另 1 条记为平台读取阻塞。真实账号 conversation ID、完整回复、会话 Cookie 与本地浏览器登录状态**不存入公开 GitHub 仓库**。

提交到仓库的 JSON 仅包含脱敏 case ID、类别、是否调用 Skill、结构标志、已出现的 Claim ID、字节哈希和统计汇总；所有“通过”均注明是结构还是语义验收，绝不虚构缺失的模型观测。
