# Claude Code Mods — V2 分层可信资料库与领域映射

> 建立时间：2026-10-13（Australia/Sydney）｜原始资料：74 条｜新增已查阅资料：17 条｜共 **91 条**。
>
> **状态：文档研究与代码阅读已完成第一轮；未经目标机器实际版本测试；社区内容不具备正式规范效力。** 原资料链接全数保留，仅改变层级和引用方式。

## 0. 使用原则与禁止事项

本文件用于本项目的研究、架构评估、实现前的技术核验与测试计划。**不能**把早期设计提案、过期类型声明或社区博客复制成当前 API 定义。公开 GitHub `main` 分支的源码同样不是某个已安装版本的承诺。

1. **实现契约：** 确认目标版本，生成该安装版本的 Mods 类型声明（官方称 `/plugin-types`），并对照同版本官方文档；必要时做最小实际探针。
2. **主要文献：** L0 是 Mods 直接规范；L1 是 Mods 所依赖的现行 Claude Code 机制，L2 则是外围产品文档。每条都需要版本相容性检查。
3. **参考实现：** R 层的公开 Anthropic 示例必须区分 *Playground 教学示范* 与 *随发行版附带的内置源码*。内部 `builtin` / `prepend` / `append` 权限不可假定给普通插件。
4. **社区线索：** C 不用于推翻正式文档，除非已经在目标版本独立复现；Issue 仅证明有人报告过问题，不证明该问题今天仍存在。
5. **历史隔离：** H 只允许进入背景/架构沿革章节，禁止用其代码片段解决编译错误、设计权限控制、创建生产部署流程。
6. **支持证据：** 资料索引 ≠ 源码审查 ≠ 版本复现 ≠ CI 通过。这四种状态在研究记录中独立保存。

### 分层定义与链接统计

| 层级 | 权威范围 | 当前条目 | 使用规则 |
|---|---|---:|---|
| **L0** | 现行 Mods 官方规范 — 直接的 API 与行为契约（需版本匹配） | 10 | 同版本可作为直接规范 |
| **L1** | 一级关联：直接参与 Mods 运行的 Claude Code 官方机制文档 | 19 | 同版本可作为直接机制规范 |
| **L2** | 二级关联：对部署、兼容、维护等有用的官方文档 | 14 | 技术背景／外围约束 |
| **R** | Anthropic 官方教程／源码参考 — 验证用途，非等价 API 契约 | 17 | 参考实现，需核查 tier 和版本 |
| **C** | 社区文章／实现／Issue — 经验、假设及风险线索，需复现 | 28 | 非规范、逐项复现 |
| **H** | 历史档案或已过期版本快照 — 不得作为当前编码依据 | 3 | 不可用于当前开发 |

### 版本变更造成的关键例外

- **公开 TypeScript 声明已过期。** `anthropics/claude-code/main/mods/types/claude-code.d.ts` 顶部标有 **Claude Code 2.1.277 / Early Access**，而当前在线 Mods Reference 明确面向 **2.1.290** 及其新增 API。该声明在本索引中移入 **H**，只说明过去的类型形态；开发时须使用目标版本生成的类型，不应把 Github `main` 当作最新类型定义。
- **早期启用流程已失效。** Preview 时的 `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` 环境变量在正式版本中已不作为启用依据。要求新的开发笔记不再复制该做法。
- **官方样例也存在版本约束。** Playground 的三个示范项目说明其开发/测试使用 **2.1.280**，并在 **2.1.285** 通过过插件校验；不能直接声称在当下安装版本完整实测通过。它们又明确声明**不属于受支持的正式产品**。
- **内置源码可能有特权。** 组织层级 `next.to(...)` 的跳过能力不能由普通用户安装的 Mods 随意调用。不要把 `sec-default` 的代码直接翻译为普通插件的安全保证。

## 1. 六大工程领域映射（正向）

符号：**主**代表直接参考，*辅*代表辅助阅读；记录会在下一节按文档逐条反向标注。**H 和 C 永远是可选研究线索，不能代替 L0／L1。**

| 工程领域 | 必读 L0 | 直接关联 L1 | 官方源码参考 R | 实施/测试重点 |
|---|---|---|---|---|
| **E 事件／中间件** | M001 M003 M004 M005 | M013 M029 M030 M031 M032 M075 M079 | M039 M040 M042 M044 M089 M091 | `next(e)` 原样转发；改写拷贝；拒绝/替换行为与链路；子代理与重入 |
| **S 状态／生命周期** | M003 M005 M006 | M017 M019 M032 M079 | M038 M040 M041 M043 M087 M091 | 热重载、`/clear`、`/resume`、`classic.SessionStart` 补偿恢复、`$.state` vs `$.store` |
| **T 类型／质量门禁** | M002 M003 M005 M008 M009 | M012 M013 M014 M015 M017 M019 M078 | M041 M084 M085 | 本地 `/plugin-types`、`tsc --noEmit`、plugin validate/test、用户 tier 范围 |
| **Q 测试／诊断** | M002 M003 M008 M009 | M015 M017 M075 | M041 M084 M085 | Mock、错误/超时/取消、CLI 真机、Desktop/VS Code 分别验证 |
| **P 权限／安全** | M001 M003 M004 M005 M010 | M016 M027 M030 M031 M076 M077 M078 | M039 M042 M043 M088 M089 | 全权限 Mod、不受 Bash sandbox 约束、策略优先级、fail-closed |
| **U UI／跨平台** | M001 M003 M006 M007 | M011 M013 | M038 M039 M040 M041 M087 M089 M091 | Pane/AbovePrompt、热键与视图冲突、终端/桌面/VS Code/无头降级 |

注意：这是研究导航矩阵，而非每条资料唯一职责。各资料在机器索引里有 `core` 和 `support` 的**多对多**标签。

## 2. 全部 91 条文档清单：层级 → 六领域（反向）

每条记录格式为：编号、资料、重要领域（**主** / *辅*）、初步阅读情况。对于未逐项阅读正文的第三方链接，标记为「已编目」，而不是声称已经独立验证其全部内容。

### L0 — 现行 Mods 官方规范 — 直接的 API 与行为契约（需版本匹配）（10 条）

| ID | 文档 | 主领域 | 辅助领域 | 已检查程度 |
|---|---|---|---|---|
| `M001` | [Mods overview](https://code.claude.com/docs/en/plugins/mods/overview) | **E** **S** **P** **U** | T Q | 已查阅关键原文 |
| `M002` | [Create a mod](https://code.claude.com/docs/en/plugins/mods/create) | **T** **S** **Q** | E P U | 已查阅关键原文 |
| `M003` | [Mods reference](https://code.claude.com/docs/en/plugins/mods/reference) | **E** **S** **T** **Q** **P** **U** | — | 已查阅关键原文 |
| `M004` | [React to events with a mod](https://code.claude.com/docs/en/plugins/mods/events) | **E** **P** | S T Q | 已查阅关键原文 |
| `M005` | [Use the mods API](https://code.claude.com/docs/en/plugins/mods/api) | **E** **S** **T** | Q P U | 已查阅关键原文 |
| `M006` | [Draw in the interface with a mod](https://code.claude.com/docs/en/plugins/mods/interface) | **U** **S** | E T Q | 已查阅关键原文 |
| `M007` | [Interface gallery for mods](https://code.claude.com/docs/en/plugins/mods/gallery) | **U** | Q | 已查阅关键原文 |
| `M008` | [Test a mod](https://code.claude.com/docs/en/plugins/mods/test) | **Q** **T** | E S U | 已查阅关键原文 |
| `M009` | [Troubleshoot a mod](https://code.claude.com/docs/en/plugins/mods/troubleshoot) | **Q** **T** | E S P U | 已查阅关键原文 |
| `M010` | [Manage mods for your organization](https://code.claude.com/docs/en/plugins/mods/admin) | **P** | T Q | 已查阅关键原文 |

### L1 — 一级关联：直接参与 Mods 运行的 Claude Code 官方机制文档（19 条）

| ID | 文档 | 主领域 | 辅助领域 | 已检查程度 |
|---|---|---|---|---|
| `M011` | [Plugins overview](https://code.claude.com/docs/en/plugins/overview) | **T** | E S P | 已查阅关键原文 |
| `M012` | [Create a Claude Code plugin](https://code.claude.com/docs/en/plugins/create) | **T** **Q** | E S | 已查阅关键原文 |
| `M013` | [Add components to a plugin](https://code.claude.com/docs/en/plugins/components) | **T** **E** | S P U | 已查阅关键原文 |
| `M014` | [Plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference) | **T** | S P | 已查阅关键原文 |
| `M015` | [Plugin commands reference](https://code.claude.com/docs/en/plugins/cli-reference) | **Q** **T** | S | 已查阅关键原文 |
| `M016` | [Plugin security and trust](https://code.claude.com/docs/en/plugins/security) | **P** | T Q | 已查阅关键原文 |
| `M017` | [Plugin loading reference](https://code.claude.com/docs/en/plugins/loading) | **T** **S** | E Q | 已查阅关键原文 |
| `M018` | [Install and manage plugins](https://code.claude.com/docs/en/plugins/install) | **T** **S** | P | 已查阅关键原文 |
| `M019` | [Plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies) | **T** | S | 已查阅关键原文 |
| `M027` | [Manage Claude Code plugins for your organization](https://code.claude.com/docs/en/plugins/org) | **P** | T | 已查阅关键原文 |
| `M029` | [Extend Claude Code](https://code.claude.com/docs/en/features-overview) | **E** **T** | P U | 已查阅关键原文 |
| `M030` | [Automate actions with hooks](https://code.claude.com/docs/en/hooks-guide) | **E** **P** | T | 已查阅关键原文 |
| `M031` | [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp) | **E** **T** | S P | 已查阅关键原文 |
| `M032` | [Message your other Claude Code sessions](https://code.claude.com/docs/en/cross-session-messaging) | **E** **S** | P | 已查阅关键原文 |
| `M075` | [Hooks reference](https://code.claude.com/docs/en/hooks) | **E** **P** | T Q | 已查阅关键原文 |
| `M076` | [Configure permissions](https://code.claude.com/docs/en/permissions) | **P** | E T | 已查阅关键原文 |
| `M077` | [Configure the sandboxed Bash tool](https://code.claude.com/docs/en/sandboxing) | **P** | E T | 已查阅关键原文 |
| `M078` | [Settings files and precedence](https://code.claude.com/docs/en/settings) | **P** **T** | S | 已查阅关键原文 |
| `M079` | [Create custom subagents](https://code.claude.com/docs/en/sub-agents) | **E** **S** | P T | 已查阅关键原文 |

### L2 — 二级关联：对部署、兼容、维护等有用的官方文档（14 条）

| ID | 文档 | 主领域 | 辅助领域 | 已检查程度 |
|---|---|---|---|---|
| `M020` | [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals) | **Q** | T | 已查阅关键原文 |
| `M021` | [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish) | **T** | Q P | 已查阅关键原文 |
| `M022` | [Create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace) | **T** | P | 已编目／未逐项复现实验 |
| `M023` | [Host and maintain a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace) | **T** | Q P | 已编目／未逐项复现实验 |
| `M024` | [Marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) | **T** | P | 已编目／未逐项复现实验 |
| `M025` | [Anthropic marketplaces](https://code.claude.com/docs/en/plugins/anthropic-marketplaces) | **T** | — | 已编目／未逐项复现实验 |
| `M026` | [Measure plugin cost and usage](https://code.claude.com/docs/en/plugins/measure) | **S** | Q T P | 已查阅关键原文 |
| `M028` | [Troubleshoot plugins](https://code.claude.com/docs/en/plugins/troubleshooting) | **Q** | T | 已编目／未逐项复现实验 |
| `M033` | [Claude Code changelog](https://code.claude.com/docs/en/changelog) | **T** | S Q | 已编目／未逐项复现实验 |
| `M034` | [Claude Code docs official index](https://code.claude.com/docs/llms.txt) | **T** | — | 已查阅关键原文 |
| `M080` | [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) | **T** | Q | 已查阅关键原文 |
| `M081` | [Customize keyboard shortcuts](https://code.claude.com/docs/en/keybindings) | **U** | T | 已查阅关键原文 |
| `M082` | [Claude Code desktop application](https://code.claude.com/docs/en/desktop) | **U** | T | 已查阅关键原文 |
| `M083` | [Use Claude Code in VS Code](https://code.claude.com/docs/en/vs-code) | **U** | T | 已查阅关键原文 |

### R — Anthropic 官方教程／源码参考 — 验证用途，非等价 API 契约（17 条）

| ID | 文档 | 主领域 | 辅助领域 | 已检查程度 |
|---|---|---|---|---|
| `M036` | [Getting started with Claude Code mods — Addy Osmani](https://claude.dev/blog/getting-started-with-claude-code-mods/) | **E** **S** **T** **Q** **U** | P | 已查阅关键原文 |
| `M037` | [Claude Code Playground Mods — index](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/README.md) | **E** **T** **U** | S Q | 源码/原文已研究 |
| `M038` | [Token Weather](https://github.com/anthropics/claude-code-playground/tree/main/claude-code/mods/token-weather) | **S** **U** | E Q | 源码/原文已研究 |
| `M039` | [Blast Radius](https://github.com/anthropics/claude-code-playground/tree/main/claude-code/mods/blast-radius) | **E** **P** | S Q U | 源码/原文已研究 |
| `M040` | [Replay Theater](https://github.com/anthropics/claude-code-playground/tree/main/claude-code/mods/replay-theater) | **E** **S** **U** | Q | 源码/原文已研究 |
| `M041` | [Built-in diff Mod](https://github.com/anthropics/claude-code/blob/main/mods/diff/hooks/register.ts) | **S** **U** **T** **Q** | E | 源码/原文已研究 |
| `M042` | [Built-in sec-default Mod](https://github.com/anthropics/claude-code/blob/main/mods/sec-default/hooks/register.ts) | **E** **P** | T Q | 源码/原文已研究 |
| `M043` | [Built-in telemetry Mod](https://github.com/anthropics/claude-code/blob/main/mods/telemetry/hooks/register.ts) | **S** **P** | E T Q | 源码/原文已研究 |
| `M044` | [Built-in agents-md Mod](https://github.com/anthropics/claude-code/blob/main/mods/agents-md/hooks/register.ts) | **E** **S** | P T | 源码/原文已研究 |
| `M084` | [Built-in Mods — source index and test patterns](https://github.com/anthropics/claude-code/blob/main/mods/README.md) | **T** **Q** | E S P | 源码/原文已研究 |
| `M085` | [Built-in Mods — TypeScript project configuration](https://github.com/anthropics/claude-code/blob/main/mods/tsconfig.json) | **T** **Q** | — | 源码/原文已研究 |
| `M086` | [Token Weather — design and limitations](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/token-weather/README.md) | **S** **U** | E Q | 源码/原文已研究 |
| `M087` | [Token Weather — actual hooks module](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/token-weather/hooks/token-weather.mjs) | **S** **U** | E | 源码/原文已研究 |
| `M088` | [Blast Radius — design and limitations](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/blast-radius/README.md) | **E** **P** | Q U | 源码/原文已研究 |
| `M089` | [Blast Radius — actual hooks module](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/blast-radius/hooks/blast-radius.mjs) | **E** **P** | S U | 源码/原文已研究 |
| `M090` | [Replay Theater — design and limitations](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/replay-theater/README.md) | **E** **S** **U** | Q | 源码/原文已研究 |
| `M091` | [Replay Theater — actual hooks module](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/replay-theater/hooks/replay-theater.mjs) | **E** **S** **U** | Q | 源码/原文已研究 |

### C — 社区文章／实现／Issue — 经验、假设及风险线索，需复现（28 条）

| ID | 文档 | 主领域 | 辅助领域 | 已检查程度 |
|---|---|---|---|---|
| `M046` | [Better Stack — Building Custom UI and Behavior from Inside the Agent](https://betterstack.com/community/guides/ai/claude-code-mods/) | **E** **U** | S Q | 已编目／未逐项复现实验 |
| `M047` | [Kanaries — Build and Test Your First Mod, Plus 15 Community Examples](https://docs.kanaries.net/topics/AICoding/claude-code-mods) | **T** **Q** | E | 已编目／未逐项复现实验 |
| `M048` | [Digital Applied — How to Build Your First Claude Code Mod](https://www.digitalapplied.com/blog/build-first-claude-code-mod-tutorial) | **P** **Q** | E T | 已查阅关键原文 |
| `M049` | [Digital Applied — Security Checklist](https://www.digitalapplied.com/blog/claude-code-mod-security-review-checklist) | **P** | Q | 已编目／未逐项复现实验 |
| `M050` | [Digital Applied — Function Hooks Explained](https://www.digitalapplied.com/blog/claude-code-mods-function-hooks-explained) | **E** | P T | 已编目／未逐项复现实验 |
| `M051` | [Digital Applied — Coding Agent Tool Interception Comparison](https://www.digitalapplied.com/blog/ai-coding-agent-hooks-compared-tool-interception) | **E** | T | 已编目／未逐项复现实验 |
| `M052` | [mods.guide — Testing and Debugging Mods](https://mods.guide/en/articles/testing-and-debugging/) | **Q** | T S | 已编目／未逐项复现实验 |
| `M053` | [mods.guide — Build Your First Mod](https://mods.guide/en/guide/build-your-first-mod/) | **E** **T** | Q | 已编目／未逐项复现实验 |
| `M054` | [mods.guide — Troubleshooting](https://mods.guide/en/guide/troubleshooting/) | **Q** | E T | 已编目／未逐项复现实验 |
| `M055` | [Agrici Daniel — Claude Code Mods Complete Guide](https://agricidaniel.com/blog/claude-code-mods-guide) | **E** **P** | T | 已编目／未逐项复现实验 |
| `M056` | [explainx.ai — TypeScript Plugin Guide](https://www.explainx.ai/blog/claude-code-mods-typescript-plugins-guide-2026) | **T** **E** | Q | 已编目／未逐项复现实验 |
| `M057` | [explainx.ai — Awesome Claude Code Mods](https://www.explainx.ai/blog/awesome-claude-code-mods-50-open-source-mods-install-guide-2026) | **E** **T** **U** | Q | 已编目／未逐项复现实验 |
| `M058` | [explainx.ai — Desktop Mods Install and Build Guide](https://www.explainx.ai/blog/claude-code-desktop-app-mods-how-to-install-and-build-guide-2026) | **U** | T | 已编目／未逐项复现实验 |
| `M059` | [ClaudeCodeMods.com — Build Your First Mod](https://claudecodemods.com/learn/getting-started/) | **E** **T** | Q | 已编目／未逐项复现实验 |
| `M060` | [pjfp.com — Install, Build and Secure Mods](https://pjfp.com/claude-code-mods/) | **P** **T** | Q | 已编目／未逐项复现实验 |
| `M061` | [claudcod.com — What They Are and How to Install One](https://claudcod.com/blog/claude-code-mods/) | **E** **T** | — | 已编目／未逐项复现实验 |
| `M062` | [promptadvisers — Codex Computer-Use Bridge and Threads](https://github.com/promptadvisers/claude-mods-computer-use-threads) | **E** **S** | P U | 已编目／未逐项复现实验 |
| `M063` | [RedesignedRobot — cdx execution lanes](https://github.com/RedesignedRobot/cdx) | **E** **S** | Q U | 已编目／未逐项复现实验 |
| `M064` | [hamzafer/claude-code-mods](https://github.com/hamzafer/claude-code-mods) | **E** **S** **T** **U** | Q | 已编目／未逐项复现实验 |
| `M065` | [karanb192/claude-code-mods — builder skill](https://github.com/karanb192/claude-code-mods) | **T** **Q** | P | 已编目／未逐项复现实验 |
| `M066` | [whyashthakker/awesome-claude-code-mods](https://github.com/whyashthakker/awesome-claude-code-mods) | **E** **U** | T | 已编目／未逐项复现实验 |
| `M067` | [karanb192/awesome-claude-code-mods](https://github.com/karanb192/awesome-claude-code-mods) | **P** | T Q | 已编目／未逐项复现实验 |
| `M068` | [GitHub Claude Code Mods topic](https://github.com/topics/claude-code-mods) | **E** | U | 已编目／未逐项复现实验 |
| `M069` | [Claude Mods community directory](https://claudemods.chat/) | **E** **U** | — | 已编目／未逐项复现实验 |
| `M071` | [TypeScript checking gap — issue #99771](https://github.com/anthropics/claude-code/issues/99771) | **Q** **T** | — | 已查阅关键原文 |
| `M072` | [VS Code Mod UI availability — issue #99045](https://github.com/anthropics/claude-code/issues/99045) | **U** | T | 已查阅关键原文 |
| `M073` | [Pane Input truncation — issue #100299](https://github.com/anthropics/claude-code/issues/100299) | **U** | Q | 已查阅关键原文 |
| `M074` | [Built-in diff notifications interaction — issue #99026](https://github.com/anthropics/claude-code/issues/99026) | **U** | S | 已查阅关键原文 |

### H — 历史档案或已过期版本快照 — 不得作为当前编码依据（3 条）

| ID | 文档 | 主领域 | 辅助领域 | 已检查程度 |
|---|---|---|---|---|
| `M035` | [Customize Claude Code with mods in TypeScript](https://claude.com/resources/articles/claude-code-mods) | **E** | P U | 已查阅关键原文 |
| `M045` | [Published Mods TypeScript API declarations](https://github.com/anthropics/claude-code/blob/main/mods/types/claude-code.d.ts) | **T** | E S | 源码/原文已研究 |
| `M070` | [Original proposal — Mods make Claude 10x more extensible #91870](https://github.com/anthropics/claude-code/issues/91870) | **E** | P U | 已查阅关键原文 |


### 生命周期中尤其需要注意的非直观约束

当前 [Mods Interface](https://code.claude.com/docs/en/plugins/mods/interface) 明确区分三层状态：**module 变量**在模块重载后丢失；**`$.state`** 在同一会话内跨热重载但在 `/clear`、`/resume`、`/branch` 后重置；**`$.store`** 是多会话持久化 JSON 存储。并且 `session.start` **不会**因为 `/clear`、`/resume`、`/branch` 重发，使用持久值回填 state 还应监听 `classic.SessionStart` 的 `clear/resume/fork` 来源。`$.store` 也是非事务性共享存储，`get → set` 会发生竞态和更新丢失。对连接 ChatGPT 多任务、多会话的本项目，应使用明确的会话 ID 和并发策略，而不能把 store 当作原子数据库。

## 3. 六大工程领域的最低开发质量门禁

| 领域 | 最低可接受证据 | 针对 ChatGPT 集成的失败情形 |
|---|---|---|
| E | 工具与 Prompt 事件的「观察不变性」黄金测试、多个 Mods 组合、拒绝/返回值/异常/取消全分支测试 | 意外吞掉 Claude Code 工具调用、改变系统工具结果、重复触发回调 |
| S | 热重载、会话结束、`/clear`、`/resume`、`/branch`、`classic.SessionStart` 回填、`$.store` 并发竞态与幂等测试 | 过期会话发消息给错误 ChatGPT 任务、重复命令注册、状态意外泄漏 |
| T | `claude plugin validate`、`claude plugin test`、真实本地 `claude-code` `.d.ts` 生成、独立 `tsc --noEmit`、锁定 CLI 版本 | 通过测试但接口类型错误，或依赖仅内置插件才拥有的特权 API |
| Q | 细粒度 Mock、真实 CLI 集成、桌面 UI 交互、错误日志与负向测试，留存版本与复现命令 | Mock 模型没有实际工具返回形状、真实 UI 不渲染、超时行为不同 |
| P | 数据流与认证材料威胁模型、默认拒绝与撤销路径、运行工具/外部网络/文件访问审计；保护性功能故障时拒绝 | 误将 Mod 视为沙箱、未经授权将会话发往外部服务、Bash Hook 绕过 |
| U | CLI 和 Desktop 分别实测，VS Code / headless 明确降级，窄屏、共享 AbovePrompt、焦点和快捷键冲突测试 | 无头环境等待永远不存在的用户确认、Pane 抢焦点、组件覆盖 |

**默认设计倾向：** ChatGPT 集成以「可观察、可取消、可审计、显式授权、对 Claude Code 默认行为零侵入」作为基础目标。可选管理面板放在 UI；后台运行逻辑不得依赖 UI 一定存在。

## 4. 版本有效性和证据升级流程

任何准备用于代码实现的记录需要有一份 evidence manifest：

```yaml
source_id: M004
source_revision: <文档抓取日期及可复核的 URL/commit>
target_claude_code_version: <目标 CLI 或 Desktop 实际版本>
api_symbol: <例如 tool.call / next(e)>
reference: <L0 文档章节 + 本地生成的类型定义>
platforms_tested: [terminal, desktop, vscode, headless]
validation: <mock 测试 ID + 真实集成测试 ID>
result: confirmed | limited | mismatch | blocked
reviewer: <执行者及日期>
```

审批规则：

- `H` → 永远不直接升级；要使用某个思想，先在 L0/L1 找到当前正式对应点，创建新的有版本依据的记录。
- `C` → 必须用当前目标版本的官方规范核查；只可升级**经过复现的事实**，不能因为作者热门而成为标准。
- `R` → 只有一般工程模式可借鉴；涉及 `builtin`/managed tier 的操作按特权功能处理，先证明我们可调用。
- `L0`/`L1`/`L2` → 改版后也需重新对齐本地声明与关键测试，不能把一次验证视为永久保证。

## 5. 研究局限与下一批需要机器执行的验证

- 本轮已阅读 Mods 规范、重要 L1 机制和 3+4 个官方参考实现的入口模块与说明；**尚未执行** `claude plugin test`、`tsc`、真实 CLI 或 Desktop 上的现场测试。
- 官方内置 `diff` 的大模块通过主注册入口、README、官方 TypeScript 编译配置研究；未声称已经逐个完成其全部辅助文件和测试案例的覆盖式代码审计。
- 现行参考页标为 2.1.290，但个别字段要求 2.1.292+。**逐 API 版本门禁**不可仅按该页标题判断。
- 其他 16 个社区教程/8 个社区项目已归类；并非全部源码经过同等深度审查。
- 下一批验证应在用户选择的实际目标 Claude Code 安装实例上读取版本和 `/plugin-types` 生成物，并以独立 worktree/插件目录做低风险重放测试，不改变其他开发工作。

## 6. 关联资料

- [V2 官方源码审阅报告](./claude_code_mods_official_source_review_2026-10-13.md)
- [V2 机器可读 JSON 资料目录](./claude_code_mods_catalog_v2_2026-10-13.json)
- [V1 原始 74 条链接索引](./claude_code_mods_research_index_2026-10-13.md)
- [官方 Mods Reference](https://code.claude.com/docs/en/plugins/mods/reference)
- [Anthropic 内置 Mods 源码索引](https://github.com/anthropics/claude-code/blob/main/mods/README.md)

