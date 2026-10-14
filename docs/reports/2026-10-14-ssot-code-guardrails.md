# SSOT 新增的两个已验证 Mods 工程约束（2026-10-14）

## 真实 Chat mode 发现的问题

本项目在 ChatGPT 普通聊天模式中按完整 P4 套件审核了实际 Claude Code Mods 开发回答。两条本来被表面源码引用检查放过的建议，经 Claude Code CLI 2.1.296 本地模拟工程验证为**不能作为有效的可运行范例**：

- **POS-E-02**：给出 `export default function register({ on })`。它不提供官方约定的具名 `register` 导出。
- **POS-Q-01**：建议 `claude plugin test ./tests/example.test.ts`。本机 CLI 的参数实际上是 Mod 插件目录，而非测试文件路径。

## 单一事实来源更新

已在中央 `claims/` 中新增、审阅并审批两条细粒度知识，完整保留 Claim 原子 ID、L0 官方出处、版本适用区间和决策链：

| ID | 作用 | 官方资料 |
|---|---|---|
| **K-0032** | 使用具名 `export function register(on)`，不要把默认导出/解构签名当作等价入口 | M003 — [Mods reference — Files](https://code.claude.com/docs/en/plugins/mods/reference#files) |
| **K-0033** | `claude plugin test` 使用 Mod 插件**目录**，如 `claude plugin test ./my-mod`；不能直接传入单个 `.test.ts` 文件 | M008 — [Test a mod — Write a test](https://code.claude.com/docs/en/plugins/mods/test#write-a-test) |

审批范围严格限定 Claude Code **CLI 2.1.296**（半开区间 `[2.1.296, 2.1.297)`）。这是当前安装版本的 CLI 静态检查与离线测试证据，**不是**模型实际生成答案已改善的证据，也不是 Desktop/VS Code 等宿主的 API 通用保证。

## 本机复现实验

实验在 MacBook Pro 的**临时隔离插件目录**中进行，没有 Claude Code/Codex 模型推理或外部插件安装。

1. 正确导出 `export function register(on)` 的安全本地测试 Mod 执行 `claude plugin validate --strict`：`success=true`，无 manifest/hook 错误。
2. 改写为 `export default function register({ on })` 但不改变其他文件：同一验证器 `success=false`，明确报告缺失名为 `register` 的导出。
3. 运行 `claude plugin test ./my-mod/tests/basic.test.ts`：CLI 返回 `no such plugin folder`，退出码为 1。
4. 运行 `claude plugin test ./my-mod`：模拟工具调用隔离测试结果为 **1 pass，0 fail**。

这四条只支持准确的 CLI 模块导出与命令参数结论，不能证明运行时权限控制、UI 绘制或交互会话的所有行为。

## P3 编译器与验收

两条约束从已批准 SSOT 动态加入主 `SKILL.md` 的高优先级技术核验章节，并同时出现在 TypeScript/Testing 对应的 `references/types.md` 与 `references/testing.md`。Claude Code、Codex、Pi Agent、ChatGPT 四平台仍使用同一份生成数据，而不是人工分别维护独立说明。

变更后的已批准 Claim 总数 **28**，原有 5 条未审查的 API Candidate 仍不被编译为活跃规范。自动化测试覆盖版本边界、批准记录校验、两条知识传递、四平台文件一致性、官方文档出处和 ZIP SHA-256。

## 后续真实插件质量验收

现有 GitHub 正式 Beta.1 不受本分支实验影响。只有重新生成新版本、验证 ZIP/YAML/三台机器哈希，并在**新的普通 Chat mode 会话**中对原 POS-E-02/POS-Q-01 等失败场景取得真实读 Skill 和正确可执行示例，才能将这些修复视为通过端到端验收。缺乏 Chat mode 结果时应将其标记为“SSOT 修复待分发”，不能升级正式稳定版。
