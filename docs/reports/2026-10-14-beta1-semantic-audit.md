# ChatGPT Chat mode — 46 项实际回复与独立技术质量审查

日期：2026-10-14。ChatGPT Plugin：`0.2.0-beta.1`（账号现已回退到该已发布版并确认启用），Claude Code 目标知识版本 CLI 2.1.296。

本报告基于 Raspberry Pi 正常 ChatGPT **Chat mode** 发起的 46 次真实独立会话，以及对 30 条正向和 8 条版本/安全边界回复的独立技术复查。不是 Work mode，不包含原始账号会话 ID、完整回复或任何浏览器登录信息。仅包含哈希和归纳判断的逐项 JSON 报表：`2026-10-14-beta1-complete-semantic-qa.json`。

## 最终分级（不是仅关键词/引用统计）

| P4 类别 | 已观测 | 通过 | 失败 | 尚不能判定 |
|---|---:|---:|---:|---:|
| 30 条正向开发问答 | 30 | **7** | **17** | **6** |
| 8 条无关任务 | 8 | **8** | 0 | 0 |
| 8 条版本/权限/历史边界 | 8 | 0 | **8** | 0 |
| 合计 | 46 | **15** | **25** | **6** |

**正向答案的最终通过率 7/30。** 这不等同于单纯的静态质量测试，也不意味着其他 23 条语义全部错误：17 条失败可能来自插件未加载、官方出处/Claim 不完整或真实代码问题；6 条的精确 API/运行行为尚需更多证据，不能先标记通过。

8 条边界问题的普通模型回复不少是安全的，但**实际自动读取 Mods Plugin Skill 为 0/8**，因此插件专项验收失败。反过来，无关任务的 8 个不加载证据是真实的有效负向通过。

## 已经明确复现的代码与来源问题

1. `POS-E-02` 的建议示例出现 `export default function register({ on })`。在 MacBook 的 Claude Code **2.1.296** 中，复制同类示例到隔离 Mod 项目后，`claude plugin validate --strict` 明确报告无名为 `register` 的模块导出；正确的 `export function register(on)` 通过。
2. `POS-Q-01` 将 `claude plugin test ./tests/example.test.ts` 当作有效命令。用相同版本 CLI 实际执行时返回“no such plugin folder”；`claude plugin test ./my-mod` 使用 Mod **目录**作为参数，运行安全 Mock Test **1 pass、0 fail**。
3. `POS-T-03` 引用了 `anthropics/claude-code/main/mods/types/claude-code.d.ts` 作为当前 API 的参考。中央 Registry 已将该文件头部显示 **2.1.277 Early Access** 的版本归为历史 H，不能替代已安装 2.1.296 版本生成的 TypeScript 定义。
4. `POS-E-04` 示例涉及 `e.command`，未对当前实际 `tool.call` 输入结构做类型校验。因属工具拦截/潜在权限控制，暂记 **inconclusive**，不能当做可运行的安全 Guard。
5. `POS-E-01` 中的错误两参数示例是明确标注的反面示例，不应被简单的正则扫描误报为模型推荐。质量扫描工具已新增这种上下文判断的回归测试。

上述本机 CLI 命令只用了隔离本地测试样例，**没有模型推理/第三方源执行**。Code snippets 的类型合法性必须继续根据版本生成的声明和官方行为测试核对。尚不能由此宣称整个 46 项 QA 成功。

## 改进验收门禁

- 新增 `mods-knowledge answer-lint --case-id ID --answer-file FILE --out SANITIZED.json`。它只返回已确认的具体风险旗标、需进一步审查旗标与回复 SHA-256，**不会输出原始模型回复**；缺少旗标不代表语义正确。
- 新增真实 Chat QA 人工审查层；即使结构测试通过，也必须有独立审阅，且人工标记不能覆盖因 Skill 未加载等客观原因产生的结构失败。
- 后续的 SSOT 迭代必须给“正确模块导出”和“目录式测试调用”添加明确的、经批准的版本范围知识以及对应的回归用例，从单一事实来源生成全部平台知识，不直接手工补充四个 Skill。
- 自动触发属于 ChatGPT 模型与客户端路由，模型可能不读取 Skill；实测正确的显式调用不能代替 30/30 自动触发验收。官方 [Skills 激活说明](https://developers.openai.com/plugins/concepts/skills) 也说明完整 Skill 只有在匹配或显式调用时才加载。

## GitHub/用户环境保护

目前已发布的 `v0.2.0-beta.1` 仍为回退基线；Beta.2 前置描述 YAML 有兼容问题，Beta.3 在真实路由测试出现退步。未达到新版发布门禁以前，不应把失败实验直接合并到 main 或升级个人 ChatGPT Plugin。

所有完整回复与会话身份只保存在 Raspberry Pi 的专用本地 QA 目录；公开 GitHub 仅含 case ID、SHA 与技术审查状态。Issue #2 的语义审查范围已取得可复现进展，但 Claude Code/Codex/Pi 的实际模型使用仍待恢复额度。
