# v0.2.0-beta.1 — Claude Code Mods Knowledge（Private Beta Release）

发布日期：2026-10-14（Australia/Sydney）。**私人预发布，不是公共目录稳定版**。

这份文档记录 Beta 的发布范围。下面的七条 Chat mode 历史数据来自 **rc.2**，并不自动构成 Beta 二进制版本的运行测试证据；Beta 安装后的独立结果将在 GitHub Release 的 P5 矩阵中记录。

## 已实现的交付能力

- SSOT：91 个来源登记、43 个官方网页内容指纹、9 个章节级官方文档审阅记录。L0/L1/L2/R/C/H 独立管理，历史与社区内容不进入规范性 API 发布。
- 26 条经核验、限定目标版本的 Approved Claims（25 条工程指导，1 条 Claude Code CLI 测试工具的真实合成调用证据）；5 条 API 研究问题仍未批准。
- 六领域：事件 E、状态 S、类型 T、测试 Q、安全 P、UI U。
- Knowledge Compiler：由相同 SSOT 确定性生成 Claude Code/Codex/Pi Agent Skills 和 ChatGPT Skills-only Plugin。目标严格限定 Claude Code CLI 2.1.296。
- 46 项离线 P4 场景与跨设备 Python、Ruff、ZIP 路径、可执行内容隔离、SHA-256 证据及重放一致性测试。
- 独立的 ChatGPT 普通 Chat mode（**不是 Work**）账号插件已上传并启用。
- K-0031 解决了真实 ChatGPT 回答中误把 Mods Hook 的 `($, e, next)` 写成 `(e, next)` 的问题。

## 实际 Chat mode 质量状态

- v0.1.0-rc.2 用户账号插件：`installed=yes`、`status=ENABLED`，唯一 Skill 启用。
- 已观察到 7 个真实 Chat-mode 会话：3 个结构性通过，4 个结构性失败。通过实例包括显式请求插件后正确调用官方 Skill 和生成完整三个 Hook 参数；有实例自动路由未激活 Skill。
- 此结构性测试不是所有 46 个测试场景的实际模型执行结果，也不是全方位语义验证。**建议在普通 Chat 模式明确使用 `@claude-code-mods-knowledge`。**
- Claude Code 和 Codex 本地模型额度不足，这两个宿主的真实 LLM 验收尚未执行；所有三机器跨平台测试均为无模型的代码/包检查。

## 发布产物

`claude-code-mods-knowledge-0.2.0-beta.1.zip`：Portable Agent Plugins 1.0 清单与官方证据绑定的 Skill；不附带 MCP Server、远程认证、Hooks 或可执行组件。

`claude-code-mods-development-0.2.0-beta.1.zip`：独立 Agent Skill，可供后续 Claude Code/Codex/Pi Agent 验收。

`SOURCE-SBOM.json`、`P4-STATIC.json`、`P5-HOST-MATRIX.json`、`RELEASE.json`、`SHA256SUMS`：来源、测试、主机独立性、状态和内容哈希。

发布包由最终 Git Commit 的 SSOT 重新生成，并要求所有三台设备基于同一 Commit 独立重建得到完全相同 ZIP SHA-256；发布报告标为 `prerelease_host_runtime_unverified`，意为**部分 Chat-mode 真实测试已完成，但全套自动触发及跨平台真实验收尚未完成**。

## 重要参考

- [代码和构建历史](https://github.com/grammy-jiang/claude-code-mods-knowledge)
- [实际 P5 Chat-mode 验收报告](2026-10-14-p4-p5-evidence.md)
- [K-0031 实测代码修正的脱敏 Chat-mode 证据](p5_chat_mode_rc2_observations.json)（原始会话仅存用户私有账号）

下一阶段是扩大实际 Chat-mode 测试覆盖率，修复自动选择/引用遗漏，并在 Claude/Codex 额度恢复后进行真实 Agent Skill 启用测试。不得将本 RC 等同于通用稳定版。


此次 GitHub Beta Release 另包括适用于 `.claude/skills/` 的 Claude Code ZIP，以及适用于 `.agents/skills/` 的 Codex、Pi Agent 两个独立 ZIP，并包含可移植通用 Skill ZIP；四平台内容都由同一 SSOT 生成。默认仅可用于 Claude Code CLI 2.1.296 范围，其他版本必须重新核验。
