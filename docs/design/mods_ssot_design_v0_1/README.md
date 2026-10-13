# Claude Code Mods SSOT / Knowledge Compiler — v0.1 设计包

**状态：架构设计与数据契约；非生产实现。** 本包不包含可以安装的 Skill / ChatGPT Plugin，也没有在目标 Agent 宿主执行加载回归测试。

阅读顺序：

1. `ARCHITECTURE.md` — 体系设计、六领域、源与 Claim 的区别、确定性编译契约、四平台适配及质量门禁。
2. `schemas/source.schema.json` — 来源登记的结构约束。
3. `schemas/claim.schema.json` — 原子知识断言的结构约束。
4. `schemas/target.schema.json` / `targets.json` — 目标主机版本档案（read-only 测得）。
5. `registry_seed_UNVERIFIED.json` — 旧目录迁移的 **91 条待核验记录**。所有 snapshots 都是 unpinned。
6. `EXAMPLE_CANDIDATE_CLAIM.json` — 用于说明数据模型的草稿断言；不得作为已批准 API 事实使用。
7. `MIGRATION_AUDIT.json` / `DESIGN_VALIDATION_REPORT.json` — 迁移审计及 11 个 JSON Schema 层面的正反样例检查。

数据源：同一会话内的 `claude_code_mods_catalog_v2_2026-10-13.json`。旧目录编号 M001–M091 原样保留。资料页“已阅读”状态不能替代具体知识条目的证据、快照、版本或运行验证。

此设计包在隔离的会话工作区生成；**未修改 MacBook Pro / Raspberry Pi 上的 Git 仓库、未安装插件、未启用任何后台任务、未执行构建器或真实 Agent Skill 测试**。
