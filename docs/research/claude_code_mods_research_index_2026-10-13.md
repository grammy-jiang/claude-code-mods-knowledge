# Claude Code Mods — 官方文档、社区教程与参考实现索引

> **资料整理日期：2026-10-13（Australia/Sydney）。** 本文是可点击的资料索引、阅读优先级与工程分析，不是第三方文章全文复制，也不是对每个 Mod 的独立测试认证。

共计 **74 条独立资料链接**；其中 Mods 专题官方核心文档 **10/10 篇**（以 Anthropic 当天官方索引为准）。

## 文档目的与质量分级

- **P0**：建立实现方案前必须阅读或对比；**P1**：编码、测试、评审阶段使用；**P2**：补充和社区发现。
- **来源**：官方文档与源码为权威依据；第三方教程、GitHub 社区项目、Issue 分别是实践参考、参考实现、待验证问题。
- **覆盖限制**：社区内容快速变化，无法保证穷尽所有博客与仓库；链接可失效，作者可能更新内容。官方代码在 `main` 分支会随时间变化，项目应固定版本或 commit。
- **版本提醒**：Mods 自 Claude Code 2.1.287 起可用；API 以本机安装版本自动产生的 `.claude-plugin/types/` 及官方对应版本文档为准。

## 推荐阅读路径

1. **基础**：Mods overview → Mods reference → Create a mod → Addy Osmani 官方教程。
2. **核心技术**：React to events → Use the mods API → Draw in the interface → 官方 `claude-code.d.ts`。
3. **工程保障**：Test a mod → Plugin security and trust → Plugin CLI → Plugin loading。
4. **源码研究**：Token Weather → Blast Radius → `diff` / `sec-default` / `telemetry` 内置源码。
5. **ChatGPT 集成参考**：Codex Bridge、cdx、hamzafer 的 Codex/OpenAI Mod；比较其权限、状态、错误恢复和可移植性。

## 分类资料目录

### A. 官方 Mods 核心文档（完整专题目录）

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [Mods overview](https://code.claude.com/docs/en/plugins/mods/overview) | 官方核心 | 架构、能力边界、环境兼容性与安全模型 |
| P0 | [Create a mod](https://code.claude.com/docs/en/plugins/mods/create) | 官方核心 | 目录布局、hooks.json、开发、重载与验证 |
| P0 | [Mods reference](https://code.claude.com/docs/en/plugins/mods/reference) | 官方核心 | 完整事件、API、UI、兼容性与资源限制索引 |
| P0 | [React to events with a mod](https://code.claude.com/docs/en/plugins/mods/events) | 官方核心 | 工具/Prompt/会话事件，中间件 next(e) 与拒绝处理 |
| P0 | [Use the mods API](https://code.claude.com/docs/en/plugins/mods/api) | 官方核心 | 命令、工具、模型、文件、HTTP、进程、计时器、跨会话消息 |
| P0 | [Draw in the interface with a mod](https://code.claude.com/docs/en/plugins/mods/interface) | 官方核心 | 自定义 Pane、AbovePrompt、用户输入、UI 状态 |
| P1 | [Interface gallery for mods](https://code.claude.com/docs/en/plugins/mods/gallery) | 官方核心 | UI 组件、终端效果与示例 |
| P0 | [Test a mod](https://code.claude.com/docs/en/plugins/mods/test) | 官方核心 | 无登录/模型/网络的事件模拟、API stub、交互测试 |
| P1 | [Troubleshoot a mod](https://code.claude.com/docs/en/plugins/mods/troubleshoot) | 官方核心 | 日志、加载失败、事件匹配和工具兼容性 |
| P1 | [Manage mods for your organization](https://code.claude.com/docs/en/plugins/mods/admin) | 官方核心 | 企业权限、控制与安全策略 |

### B. 官方配套 Plugin、MCP、Hooks 文档

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [Plugins overview](https://code.claude.com/docs/en/plugins/overview) | 官方配套 | 插件容器与组件模型 |
| P0 | [Create a Claude Code plugin](https://code.claude.com/docs/en/plugins/create) | 官方配套 | 建立插件工程与本地测试 |
| P0 | [Add components to a plugin](https://code.claude.com/docs/en/plugins/components) | 官方配套 | Mod 与 MCP、Skills、Hooks 的组合方法 |
| P0 | [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference) | 官方配套 | plugin.json 的字段、约束和环境变量 |
| P0 | [Plugin commands reference](https://code.claude.com/docs/en/plugins/cli-reference) | 官方配套 | plugin validate/test、--plugin-dir、热重新加载 |
| P0 | [Plugin security and trust](https://code.claude.com/docs/en/plugins/security) | 官方配套 | 安装第三方代码前的信任与代码审计要求 |
| P0 | [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading) | 官方配套 | 加载次序、路径和更新行为 |
| P1 | [Install and manage plugins](https://code.claude.com/docs/en/plugins/install) | 官方配套 | 插件安装、启用、停用和更新 |
| P1 | [Plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies) | 官方配套 | 版本要求、依赖解析 |
| P1 | [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) | 官方配套 | 端到端质量评价及 CI 质量门禁 |
| P1 | [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish) | 官方配套 | 发布前检查与版本管理 |
| P2 | [Create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace) | 官方配套 | 创建分发仓库 |
| P2 | [Host and maintain a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace) | 官方配套 | 托管及持续维护插件目录 |
| P2 | [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) | 官方配套 | marketplace.json 规范 |
| P2 | [Anthropic marketplaces](https://code.claude.com/docs/en/plugins/anthropic-marketplaces) | 官方配套 | 官方和社区目录 |
| P1 | [Measure plugin cost and usage](https://code.claude.com/docs/en/plugins/measure) | 官方配套 | 性能、token 成本及产品遥测 |
| P1 | [Manage Claude Code plugins for your organization](https://code.claude.com/docs/en/plugins/org) | 官方配套 | 组织部署、插件准入和集中管理 |
| P2 | [Troubleshoot plugins](https://code.claude.com/docs/en/plugins/troubleshooting) | 官方配套 | 插件加载和安装排障 |
| P0 | [Extend Claude Code](https://code.claude.com/docs/en/features-overview) | 官方配套 | Mods、MCP、Skills、Hooks 能力分工 |
| P1 | [Automate actions with hooks](https://code.claude.com/docs/en/hooks-guide) | 官方配套 | 现有 Shell Hooks 与 Mods 的边界 |
| P0 | [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) | 官方配套 | 工具服务与插件内部事件的正确架构分层 |
| P1 | [Message your other Claude Code sessions](https://code.claude.com/docs/en/cross-session-messaging) | 官方配套 | 跨会话交互方案对照 |
| P0 | [Claude Code changelog](https://code.claude.com/docs/en/changelog) | 官方配套 | 跟踪版本兼容、修复与破坏性变更 |
| P0 | [Claude Code docs official index](https://code.claude.com/docs/llms.txt) | 官方配套 | 权威目录，可用于定期发现新文档 |

### C. Anthropic 官方发布资料

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [Customize Claude Code with mods in TypeScript](https://claude.com/resources/articles/claude-code-mods) | 官方发布 | 2026-10-01 产品正式发布背景 |
| P0 | [Getting started with Claude Code mods — Addy Osmani](https://claude.dev/blog/getting-started-with-claude-code-mods/) | 官方发布 | 2026-10-01 可运行的创建、状态、测试和分发教程 |

### D. Anthropic 源码与参考样例

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [Claude Code Playground Mods — index](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/README.md) | 官方源码 | 官方三个完整示例的入口和安装说明 |
| P0 | [Token Weather](https://github.com/anthropics/claude-code-playground/tree/main/claude-code/mods/token-weather) | 官方源码 | 轻量状态指示 UI、session.start 与 turn.complete |
| P0 | [Blast Radius](https://github.com/anthropics/claude-code-playground/tree/main/claude-code/mods/blast-radius) | 官方源码 | 危险命令拦截、用户确认与权限边界 |
| P1 | [Replay Theater](https://github.com/anthropics/claude-code-playground/tree/main/claude-code/mods/replay-theater) | 官方源码 | 文件更改历史与交互式 Diff 组件 |
| P0 | [Built-in diff Mod](https://github.com/anthropics/claude-code/blob/main/mods/diff/hooks/register.ts) | 官方源码 | 成熟 Pane 实现及文件变更视图 |
| P0 | [Built-in sec-default Mod](https://github.com/anthropics/claude-code/blob/main/mods/sec-default/hooks/register.ts) | 官方源码 | 权限拦截和安全策略实现 |
| P1 | [Built-in telemetry Mod](https://github.com/anthropics/claude-code/blob/main/mods/telemetry/hooks/register.ts) | 官方源码 | 观察、事件采样、遥测模式 |
| P1 | [Built-in agents-md Mod](https://github.com/anthropics/claude-code/blob/main/mods/agents-md/hooks/register.ts) | 官方源码 | 上下文指令与 Prompt 集成 |
| P0 | [Published Mods TypeScript API declarations](https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts) | 官方源码 | 源码版声明；真实开发优先使用运行时生成的本地声明 |

### E. 第三方教程与实践文章（经过筛选，非官方）

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [Better Stack — Building Custom UI and Behavior from Inside the Agent](https://betterstack.com/community/guides/ai/claude-code-mods/) | 社区文章 | 架构和实现综述；较完整的外部技术讲解 |
| P0 | [Kanaries — Build and Test Your First Mod, Plus 15 Community Examples](https://docs.kanaries.net/topics/AICoding/claude-code-mods) | 社区文章 | 多示例、编写与测试流程；部分实践为作者自述 |
| P0 | [Digital Applied — How to Build Your First Claude Code Mod](https://www.digitalapplied.com/blog/build-first-claude-code-mod-tutorial) | 社区文章 | 真实运行 Secret-redaction 案例，发现 mock 与实测数据结构不一致 |
| P0 | [Digital Applied — Security Checklist](https://www.digitalapplied.com/blog/claude-code-mod-security-review-checklist) | 社区文章 | 第三方代码安装前的权限和攻击面审计 |
| P1 | [Digital Applied — Function Hooks Explained](https://www.digitalapplied.com/blog/claude-code-mods-function-hooks-explained) | 社区文章 | Mods 与传统 Hook 行为差异 |
| P1 | [Digital Applied — Coding Agent Tool Interception Comparison](https://www.digitalapplied.com/blog/ai-coding-agent-hooks-compared-tool-interception) | 社区文章 | 与 Codex/Cursor 等开发助手的事件/工具拦截能力比较 |
| P0 | [mods.guide — Testing and Debugging Mods](https://mods.guide/en/articles/testing-and-debugging/) | 社区文章 | 测试、调试、热重载与常见实现错误 |
| P1 | [mods.guide — Build Your First Mod](https://mods.guide/en/guide/build-your-first-mod/) | 社区文章 | 实操建模和目录结构 |
| P1 | [mods.guide — Troubleshooting](https://mods.guide/en/guide/troubleshooting/) | 社区文章 | 加载、调试与修复建议 |
| P1 | [Agrici Daniel — Claude Code Mods Complete Guide](https://agricidaniel.com/blog/claude-code-mods-guide) | 社区文章 | 行为拦截、故障处理及安全工程 |
| P1 | [explainx.ai — TypeScript Plugin Guide](https://www.explainx.ai/blog/claude-code-mods-typescript-plugins-guide-2026) | 社区文章 | 早期预览与 GA 差别；虽标题含 Official，但不是官方资料 |
| P1 | [explainx.ai — Awesome Claude Code Mods](https://www.explainx.ai/blog/awesome-claude-code-mods-50-open-source-mods-install-guide-2026) | 社区文章 | 作者建立的示例集索引，测试覆盖需独立复核 |
| P2 | [explainx.ai — Desktop Mods Install and Build Guide](https://www.explainx.ai/blog/claude-code-desktop-app-mods-how-to-install-and-build-guide-2026) | 社区文章 | 桌面 UI 和安装步骤，桌面实测程度需单独核验 |
| P1 | [ClaudeCodeMods.com — Build Your First Mod](https://claudecodemods.com/learn/getting-started/) | 社区文章 | 独立入门代码与版本检查 |
| P2 | [pjfp.com — Install, Build and Secure Mods](https://pjfp.com/claude-code-mods/) | 社区文章 | 摘要性安全与入门文章，不能代替正式 API |
| P2 | [claudcod.com — What They Are and How to Install One](https://claudcod.com/blog/claude-code-mods/) | 社区文章 | 面向初学者的安装简介 |

### F. 社区实现、资源目录与 OpenAI/Codex 案例

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [promptadvisers — Codex Computer-Use Bridge and Threads](https://github.com/promptadvisers/claude-mods-computer-use-threads) | 社区源码 | 跨 ChatGPT/Codex 桥接与会话通信；注意非官方支持方案 |
| P0 | [RedesignedRobot — cdx execution lanes](https://github.com/RedesignedRobot/cdx) | 社区源码 | Codex/Antigravity 任务通道、进度、后台调度及 UI |
| P0 | [hamzafer/claude-code-mods](https://github.com/hamzafer/claude-code-mods) | 社区源码 | Codex review / OpenAI balance / 多种 UI 的较丰富代码 |
| P0 | [karanb192/claude-code-mods — builder skill](https://github.com/karanb192/claude-code-mods) | 社区源码 | 面向 Mod 开发的类型检查、隔离测试和 review 流程 |
| P1 | [whyashthakker/awesome-claude-code-mods](https://github.com/whyashthakker/awesome-claude-code-mods) | 社区源码 | 大规模示例合集；示例运行状态、版本适配逐项确认 |
| P1 | [karanb192/awesome-claude-code-mods](https://github.com/karanb192/awesome-claude-code-mods) | 社区源码 | 扫描公开插件的工具、文件和网络访问；部分快照来自早期版本 |
| P2 | [GitHub Claude Code Mods topic](https://github.com/topics/claude-code-mods) | 社区源码 | 发现新 Mod 项目；没有官方质量保证 |
| P2 | [Claude Mods community directory](https://claudemods.chat/) | 社区源码 | 社区插件目录与能力标签；注意分类混合 |

### G. 架构提案、问题及兼容性信息

| 优先级 | 资料 | 来源 | 阅读/复核重点 |
|---|---|---|---|
| P0 | [Original proposal — Mods make Claude 10x more extensible #91870](https://github.com/anthropics/claude-code/issues/91870) | 问题与设计 | 2026-09-03 原始提案，2026-10-01 上线说明；历史接口不可作为当前规范 |
| P0 | [TypeScript checking gap — issue #99771](https://github.com/anthropics/claude-code/issues/99771) | 问题与设计 | 报告 plugin validate/test 未执行真正的 TypeScript 静态类型检查 |
| P1 | [VS Code Mod UI availability — issue #99045](https://github.com/anthropics/claude-code/issues/99045) | 问题与设计 | VS Code 模型和 UI 渲染能力差异；以正式兼容矩阵优先 |
| P1 | [Pane Input truncation — issue #100299](https://github.com/anthropics/claude-code/issues/100299) | 问题与设计 | 单行输入框在窄 Pane 中可能隐藏长文本末尾 |
| P2 | [Built-in diff notifications interaction — issue #99026](https://github.com/anthropics/claude-code/issues/99026) | 问题与设计 | 其他 Pane 和 toast 的交互问题，留意 UI 组合 |

## 从资料归纳的开发最佳实践（需以目标运行版本复核）

| 工作项 | 推荐做法 | 依据 |
|---|---|---|
| TypeScript 类型 | 使用当前版本生成的 `.claude-plugin/types/`，CI 增加独立 `tsc --noEmit`；不能把 `plugin test` 通过理解成类型全部正确。 | 官方 Mod Reference、issue #99771 |
| 中间件组合 | 纯观察类 hook 调用 `next(e)` 并尽量保持原始结果；覆写结果时构造新对象，避免修改冻结参数；多个插件共同挂载时验证组合顺序。 | 官方 Events、Addy Osmani 教程 |
| 安全失败策略 | 明确监控类功能是否允许 fail-open；权限/脱敏/保密类策略要求显式处理异常、超时和覆盖范围，不可默认认为捕获一个工具等于覆盖所有内容通道。 | 官方 Security、Digital Applied 实操、原始设计提案 |
| 测试层次 | 三道门禁：插件校验与类型检查 → Mock 单元/界面交互测试 → 隔离环境真实 CLI/桌面端集成测试。 | 官方 Test、Digital Applied 的脱敏 bug |
| 状态生命周期 | 区分 JS 模块变量、`$.state`（同会话及热重载）和持久 `$.store`（跨会话）；加入重入、重复注册、卸载和恢复测试。 | 官方 API/Interface、Addy Osmani 教程 |
| UI 兼容 | CLI/桌面分别测试；不要假定 VS Code 或无头模式均支持自定义 Pane；处理窄屏输入、渲染冲突和不可用时的纯文本降级。 | 官方 Mods Overview、issues #99045、#100299 |
| 资源上限 | 明确事件处理耗时、请求上限、重试与取消，不要把高频网络请求放入 UI 渲染路径；敏感内容、密钥和会话信息默认最小化采集。 | 官方 Mods API/Reference、安全指南 |
| 第三方复用 | 只使用已审计、可复现、固定 commit 的社区源码；把示例改写为最小授权的适配层，而非直接加载未知 Mod。 | 官方插件安全指南 |

## 对 ChatGPT Plugin For Claude Code Mods 的具体启示

优先研究两个架构方向：**(A) Mods 直接嵌入事件与 UI，MCP 提供外部工具与服务**；**(B) Mods 通过受控本地桥接进程调用 Codex/ChatGPT 对应的正式公开接口**。对于跨平台能力、代理授权、用户确认、日志与会话恢复，必须建立显式测试矩阵。

关键开放问题：能否在不依赖非公开 ChatGPT 客户端接口的前提下，实现稳定双向交互？对 Codex/ChatGPT 应使用什么正式支持的 API/本地程序？插件怎么管理用户权限、可取消任务、错误重试和敏感数据边界？这些均不能仅凭社区样例视为已解决。

## 源文档追踪

- Anthropic 权威全文目录：<https://code.claude.com/docs/llms.txt>。
- Claude Code release notes：<https://code.claude.com/docs/en/changelog>。
- 官方设计及反馈：<https://github.com/anthropics/claude-code/issues/91870>。
- 若未来文档 API 发生冲突：本地目标版本类型声明 > 匹配版本的官方规范 > 当前官方在线文档 > 第三方文章 > 早期设计提案。
