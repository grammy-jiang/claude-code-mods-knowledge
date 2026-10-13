# ChatGPT Chat mode — Beta.1 全量验收缺陷分类及 Beta.2 修复方案

记录日期：2026-10-14；安装插件：claude-code-mods-knowledge 0.2.0-beta.1；Claude Code 知识目标：CLI 2.1.296。

这是 **46 条已经收齐完整回复的真实 ChatGPT 普通 Chat mode 会话**，不是静态测试，更不是 Work mode。独立对话发送及浏览器实际返回的会话 ID 保存在 Raspberry Pi 的专用 QA 目录；原始账号聊天内容不得加入 GitHub。

## 原始 P4 结构判定

| 类别 | 已完成 | 实际 Skill 读取 | 结构通过 | 结构失败 |
|---|---:|---:|---:|---:|
| 正向开发及跨领域 | 30 | 27（90%） | 15 | 15 |
| 无关任务 | 8 | 0（误触发率 0%） | 8 | 0 |
| 版本、安全与历史边界 | 8 | 0 | 0 | 8 |
| 总计 | 46 | 27 | 23 | 23 |

解释：正向 15 条结构失败，包括 **3 条未加载 Skill**（POS-T-03、POS-P-04、POS-U-04），以及另外 12 条已经加载但回答缺少预期 Claim ID 或直接可打开的官方 Mods URL。失败标志重叠：14 次缺少预期 Claim、6 次缺少直接官方链接、3 次缺少真实 Skill 读取，不能相加等于 15。

具体未满足来源要求的正向测试：POS-E-03、POS-S-02、POS-S-03、POS-T-02、POS-T-04、POS-Q-03、MODS-STATE-UI、MODS-EVENT-SEC、MODS-TYPE-Q、MODS-STORE-SEC、MODS-UI-Q、MODS-SKILL-GUIDE。

边界 8 条全部未加载 Skill，其中多条通用模型回答本身采取了安全措施。因此**不能把所有 8 条判为危险回答**；它们不满足的是 P4 对 Mods 专用知识自动触发和可信出处的验收要求。对“不检查最新官方资料就使用新 API”等请求，仍需要单独检查是否做出了未经核验的 API 保证。

## 超出结构评分的代码质量问题

POS-E-02 的回答包含 `export default function register({ on })`，与已核对的官方 Mods 文档（M002/M003）示例 `export function register(on)` 不一致，至少不能直接当作官方审核通过的可执行范例。因此结构“pass”不意味着代码自动获得运行兼容性认证。

此外，原编译器的关键 API 签名段落中，部分换行被渲染成字面的 `\n`，这是文档生成格式缺陷。它虽不是所有失败的直接原因，也应当修复。

## 改动：让 Skill 的相关知识更容易被正确选中与引用

- 从已审批 SSOT 动态生成 26 条 Claim 的主题检索目录，按 E/S/T/Q/P/U 分类；不把它们作为新的独立事实来源。
- 主 Skill 明确要求同时给出相关 K ID 和对应 M ID／官方原文的直接链接；跨领域任务不得只引用一个域的 Claim。
- 官方已审批 K-0018 + K-0031 合成完整 `export function register(on)` 与 `on('tool.call', async ($, e, next))` 最小例子，避免只给内层回调而遗漏模块入口参数。
- 前置触发描述补齐旧预览开关、超出审核版本的 Mods API、VS Code Pane、managed Mods 配置、Bash sandbox 和安全权限等实际边界关键词。
- 修正关键知识段落的字面 `\n` 问题。保持 Manifest 的信任边界和“版本不适用就不作保证”原则。
- 原测试的结构/回答/实际加载标准**不放宽**，也不将未加载插件的通用回答重新算作插件通过。

以上只是修复候选；必须用更新后的真实 Chat mode 测试证明，而不是直接宣称 15 条全部修复。自动 Skill 路由由 ChatGPT 产品决定，编译器提示无法保证每次自动触发。

## 回归及后续验收

- 修复版本作为 Beta 修订版独立打包；原 Beta.1 全量结构数据保留作对照。
- 重点复测原 15 条结构失败、8 条边界、原结构通过但导出形式不符的 POS-E-02，并至少加入一个无关任务作为误触发回归。
- 真实评价要按相同标准对比 Skill `api_tool.read_resource`、Claim ID、官方 URL 和代码签名；不得将显式 `@claude-code-mods-knowledge` 的对照组混入自动触发分母。
- 如果修复版依然存在自动路由缺漏，报告为平台行为差异，不能凭提高静态分数认定问题已解决。

## Follow-up: YAML frontmatter portability defect

The interim v0.2.0-beta.2 test upload exposed a second formatting hazard: an unquoted colon in the generated Skill description made the YAML frontmatter invalid under the standard Ruby/Psych YAML parser, even though the ChatGPT account accepted the package. That provisional version must not be treated as a portable validated release.

The subsequent compiler revision quotes the entire description as a JSON/YAML-compatible string and enforces this format in the ZIP package validator. A separate regression rejects invalid unquoted scalar descriptions. Validate both the portable YAML and real Chat-mode activation before tagging a replacement Beta.
