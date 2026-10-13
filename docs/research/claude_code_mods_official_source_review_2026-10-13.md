# Claude Code Mods — Anthropic 官方参考实现源码审阅

> 审阅日期：2026-10-13。审查类别：**源码静态阅读及官方说明对照**；非本地复现、运行测试或生产安全认证。版本：Playground 示例 2.1.280 构建/测试、2.1.285 校验；当前默认启用要求至少 2.1.287；内置源码公开 `main` 分支会变化且可能使用专有 tier。

## 对照规则：意图 → 实际代码 → 可借鉴模式 → 限制/缺口 → 测试需求

### R1 — Token Weather（Playground：轻量、非侵入式的实时显示）

- **官方目标：** 用天气预报式提示向开发者呈现上下文窗口使用情况，让用户无需看日志就能看懂接近压缩的趋势。原提案想在 AbovePrompt 使用 SVG；实践后改用终端可用的单宽字符和方块趋势图；这是基于环境能力修订方案的典型例子。
- **实际实现：** [源码](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/token-weather/hooks/token-weather.mjs) 的 `register(on)` 挂 `session.start`、`turn.complete`、`ui.render`；取 `$.session.usage().context` 中真实 `tokens/window/percent`，保留 12 个历史点，`$.ui.invalidate('ui.render')` 主动请求重绘。`e.agentId` 为真时不纳入主循环，UI 仅绘制 `AbovePrompt`。无模型 API 调用。
- **可复用：** 把有状态的后台观测与 UI 绘制分离；避免把数据抓取放进高频 `ui.render`；终端采用可对齐单宽字符；按目标 UI 可用宽度降级内容。
- **限制：** `readings` 是普通模块变量，重载时丢失；且其它 Mods 竞争同一 AbovePrompt。状态统计与 Claude Code 预压缩进度存在口径差异，不要误当「自动压缩倒计时」。
- **ChatGPT 适配：** 可显示 ChatGPT 连接状况、当前任务、最近响应时间，但应优先用 `$.state` 或明确的可恢复后台状态；涉及 `$.store` 持久化的跨会话任务状态需处理读改写竞态；绝不能在 `ui.render` 请求密钥或外部网络。
- **验证项：** 热重新加载、主代理/子代理区分、窗口 40/80/120 列、跨 Mod 共存、没有 Usage 数据和 API 异常的容错。
- **来源：** [设计、测试和限制](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/token-weather/README.md)。

### R2 — Blast Radius（Playground：风险工具调用拦截与人工授权）

- **官方目标：** 在 `rm -rf`、`git reset --hard`、强制推送和数据库迁移前报告预计影响，提供 Proceed/Cancel，让事件钩子具备工具调用前的交互拦截能力。
- **实际实现：** [源码](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/blast-radius/hooks/blast-radius.mjs) 中 `on('tool.call', {tool:'Bash'})` 先分类，在隔离持有状态下 `$.process.run(argv)` 探测影响范围，用 `$.ui.open` 打开 Pane 并在窄屏降级 AbovePrompt。Proceed 才 `next(e)`，Cancel/超时/异常/取消均 `{ deny: ... }`。使用 `next.signal` 判断中断并串行化多个同时保持的调用。
- **重要设计细节：** 在旧样例中，用 `await $.process.run(['sleep','0.25'])` 间歇等待交互，以避开 Hook 自身约 10 秒的计算预算；实际授权等待最多 10 分钟。**不应原样作为新产品的首选架构**；当前 Events 文档提供 `$.ui.ask` 简单交互选项，应先评估其更简单且符合现行规范的用法。
- **限制：** 分类器是实用启发式匹配，而非 Shell 的安全解析器；它不覆盖所有工具通道，更不等同于硬权限系统；插件自身不受 Bash 沙箱保护。README 也声明这是安全辅助而非权限替代，且部分后续修改未重新跑完真实会话测试。
- **ChatGPT 适配：** 外部调用、上传工作区、发送上下文必须显式授权与数据最小化；取消和失败应有确定拒绝路径，不可在 headless/UI 缺失时自动放行。
- **验证项：** 恶意 shell 引号/复合命令、子代理并发、用户取消、超时、UI 关闭、无 UI、重复调用、横向多 Mod、异常时 fail-closed。硬策略优先使用 Claude Code 权限体系和组织管理规则。
- **来源：** [设计与已知限制](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/blast-radius/README.md)。

### R3 — Replay Theater（Playground：可观测事件与交互回放）

- **官方目标：** 按时间线逐步查看 Claude 刚进行的文件编辑。早期概念提出自动弹窗，实际改为显示提示、按需打开面板，以降低中断性并控制 UI 焦点。
- **实际实现：** [源码](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/replay-theater/hooks/replay-theater.mjs) 观察 `tool.call` 的 Edit/Write/MultiEdit，透明 `next(e)`；通过 `turn.start`/`turn.complete` 区分任务；在 `session.start` 注册 `/replay` 并处理 `command.run`；显示 Pane、Prev/Next/Close 和窄屏降级。Diff 有限流保护（部分操作只保留 12 行，超过 400 行退化）。
- **限制（极重要）：** `tool.call` 记录的是**意图**，不是工具运行成功的**结果**。用户拒绝或执行失败的编辑也进入回放；用户不能仅凭回放判断文件已变更。模块内存遇热重载丢失；MultiEdit 和部分窄屏 fallback 在 README 中承认未经实测。
- **ChatGPT 适配：** 适合设计任务流/工具链审计显示，但必须把 `requested/approved/started/succeeded/failed/cancelled` 分层记录，避免用户误认为外部操作已成功。
- **验证项：** 拒绝执行、失败、局部成功、子代理、用户焦点、键盘、热重载、多个文件编辑、重复事件与状态折叠。
- **来源：** [设计、迭代和测试限制](https://github.com/anthropics/claude-code-playground/blob/main/claude-code/mods/replay-theater/README.md)。

### R4 — Built-in diff（内部工程化 UI 和复杂状态）

- **官方目标：** 在 Claude Code UI 中通过 `/diff` 展示当前 Git 工作区的未提交变化，刷新、分组并逐文件浏览。
- **实际实现：** [主注册入口](https://github.com/anthropics/claude-code/blob/main/mods/diff/hooks/register.ts) 导入多个模块分离 Git backend、pane state、view、host adapter 和 limits；含 `session.start` 初始化、`command.run`、`ui.render`、`ui.close`、焦点和滚动事件；具备刷新排队、debounce、防重入与请求代际检验，避免旧结果覆盖新结果。
- **可复用：** API 接口适配层隔离引擎、Git、计时器与 UI；把「是否有有效数据」和「哪次刷新更新」建成显式状态；设计后端故障与非 Git 工作区降级；界面尺寸来自渲染容器实际宽高而非硬编码。
- **约束：** 内置源码可能与发布中的发行版不同；大型文件需要配合其辅助模块与测试阅读，不能仅复制 1000 行入口脚本。
- **ChatGPT 适配：** 会话列表、任务进度和外部响应的流式刷新可使用 generation token / abort / coalescing 等模式，但必须保证不会把一个旧任务的结果写入新任务界面。
- **验证项：** 请求竞态、旧结果、超时、无 Git 工作区、UI 关闭及窗口变化、重载、真实端到端版本。

### R5 — Built-in sec-default（组织安全边界：不是普通插件模板）

- **官方目标：** 保证组织设定的策略、经典 Hooks、Prompt 内容与管理级设置不会被用户安装的 Mods 轻易削弱；该 Mod 自己并非设定新的安全策略。
- **实际实现：** [主注册入口](https://github.com/anthropics/claude-code/blob/main/mods/sec-default/hooks/register.ts) 在组织管理 tier 上对若干事件 `next.to(e, 'append')` 绕开用户级扩展链；通过 `plugin.register` 检查插件准入；通过 `tool.check` 复核判定，`.catch` 遇问题采取保护性回退；审查来源 `next.origin.tier` 和组织 policy。
- **不可直接复用：** **`next.to` 依赖管理级优先权**，普通用户 Mod 不能获取等同权力；复制代码逻辑不会改变权限 tier。任何保护机制必须考虑工具调用之外的会话附加、环境与外部 API 直接调用。
- **ChatGPT 适配：** 最小权限和显式授权采用官方权限控制 + 独立服务侧限制；不能依赖单个 user-tier Mod 实现对整个 Claude Code 的强制安全网关。
- **验证项：** 插件绕过、不同来源 tier、策略读取失败、权限冲突、会话级策略变更、MCP/网络独立通道等。

### R6 — Built-in telemetry（批量日志和最小隐私暴露）

- **官方目标：** 在允许分析的环境中收集符合规范的产品事件并批量处理；对用户安装扩展限制内部发送途径。
- **实际实现：** [主注册入口](https://github.com/anthropics/claude-code/blob/main/mods/telemetry/hooks/register.ts) 注册 `telemetry.log`, `telemetry.mark`, `engine.create`，提供可组合的 `$.telemetry` 命名空间，将 sender 绑定到官方 API，事件队列以阈值、定时和 `session.end` 触发 flush，并检查隐私/遥测禁用环境。依赖模块负责具体过滤与发送。
- **可复用：** 隔离 transport、批量发送、遵守系统级隐私配置、超时/退出 flush 和脱敏。**不要复用第一方遥测的发送端点或身份机制**。
- **ChatGPT 适配：** 以本地诊断为默认；外部上报必须单独明示并适用最小数据收集；对任何 token/认证信息只记录存在性而非内容。
- **验证项：** 断网、重启、缓冲上限、重复发送、日志泄露、禁用遥测、卸载和多会话竞争。

### R7 — Built-in agents-md（Prompt 上下文与旧配置兼容）

- **官方目标：** 支持读取 AGENTS.md 作为项目指令，并与 CLAUDE.md 共存或替代的多种模式，尽量复用原有上下文建构流程。
- **实际实现：** [主注册入口](https://github.com/anthropics/claude-code/blob/main/mods/agents-md/hooks/register.ts) 为 `instructionFiles` 提供模式化处理，兼容 `projectInstructions` 的历史设置，并在变更时提示迁移；使用 `prompt.context`、`agent.spawn`、Read 事件相关处理来装载及去重指令。
- **可复用：** 迁移配置时提供兼容期限与用户提示；注入系统/会话上下文应尊重原有格式和去重机制；不要把所有指令重复注入父代理、子代理或所有轮次。
- **ChatGPT 适配：** 如果需要向 Claude 提供 ChatGPT 任务摘要，必须控制作用域、同意范围和去重，不应悄悄篡改用户 Prompt。
- **验证项：** 旧配置、新配置、多根目录、祖先目录、嵌套 Read、subagent、会话恢复、跨用户权限。

## 官方工程说明中的测试模式

[随发行源码的官方 README](https://github.com/anthropics/claude-code/blob/main/mods/README.md) 提供了与三个 Playground 示例不同的工程门槛：

- 测试采用 `claude-code/testing`，通过 `mock.clock`、`mock.store`、特定 tier 和 `on` 注册的引擎下层模拟器测试事件链。
- 每个内置 Mod 带有 `tests/` 目录、分层配置和接口契约；单独运行如 `claude plugin test mods/diff`。
- [tsconfig.json](https://github.com/anthropics/claude-code/blob/main/mods/tsconfig.json) 使用 `strict`、`noUncheckedIndexedAccess`、`noEmit`，覆盖 `types`、`*/hooks`、`*/tests`；**类型检查不是 `plugin validate` 自动替代品**。
- 这些规则是官方随发源码的工程方法，并不承诺内部测试配置或 `tier('builtin')` 可由所有普通插件获得。

## 官方示例支持程度和冲突处理

| 证据 | 能说明什么 | 不能说明什么 |
|---|---|---|
| L0 Mods Reference | 当前公开的事件和 API 定义（页标题指向 CLI/Desktop v2.1.290） | 所有字段都在 v2.1.290 可用；部分特性注明 v2.1.292+ |
| Playground README | 官方作者实际期望验证的功能、源代码示意、部分真实环境实验 | 无漏洞、生产级安全、全部新版本通过测试 |
| 内置 `mods/README.md` | Anthropic 在源码仓库中组织类型、测试和内置层级的方法 | 公开 `main` 一定等于用户安装的二进制版本 |
| `mods/types/claude-code.d.ts` | v2.1.277 Early Access 时的 API 快照 | 当前运行版本的完整类型定义 |
| Anthropic 博客教程 | 发布时的使用意图、动手教程 | 未来每一个 API 行为都有版本保证 |

## 对本项目最先建议提炼的复用组件（仅设计方向）

1. **透明事件观察器**（参考 Replay）：事件记录与工具成功状态分离，默认 `next(e)`。
2. **任务上下文状态机**（参考 diff）：用于远端任务的取消、重连、代际标识、过期结果屏蔽。
3. **能力感知 UI**（参考 Token Weather、Replay）：主 UI 与无 UI 环境分离，弱环境下纯文本可降级。
4. **用户授权闸门**（参考 Blast Radius 但不用其 Shell 分类器当权限引擎）：显式确认、错误拒绝、可审核授权范围；优先评估官方 `$.ui.ask` 和权限规则。
5. **安全策略边界**（参考 sec-default）：不同来源 tier、插件准入与硬控制要分开建模；不复制内部特权 API。
6. **版本化工程门禁**（参考内置 Mods README）：动态生成本地声明、独立 tsc、mock/真机两级回归、源版本固化。

## 待现场核验项

本次未在目标 MacBook/树莓派安装目录运行代码。下一步在独立环境采集 `claude --version`、生成 `/plugin-types` 输出、记录构建目标平台，并以只读/无危险命令的官方 Token Weather 作为最低风险烟雾测试；通过后再测试具有阻断行为的 Mod。历史与社区仓库不参与默认安装。
