# Knowledge Claims 证据核验与审批操作指南

> 状态：2026-10-13，P1 Claim Policy / P2 candidate seed。当前 **6 个 candidate、0 个 approved**；以下机制不代表官方 API 已获核验。所有操作默认在 MacBook Pro 的项目工作树执行。

## 1. 两层事实与证据

`sources/registry.json` 保留 91 条来源，L0/L1/L2 是官方规范或机制资料，R 是官方示例，C 是社区资料，H 是历史材料。官方资料的 43 份 `sources/snapshots/` 仅保存网页响应字节的 SHA-256 与 HTTP 元数据；**不存在可还原的原始网页内容**。它们不能证明 API 语义或指定版本兼容性。

`claims/K-XXXX.json` 才是一条技术断言，其中 `subject`、`statement`、`areas.primary/secondary`、`authority`、`lifecycle`、`applies_to` 和 `evidence` 相互独立。当前登记的六条候选是研究任务/待验证判断，不是当前可用 API 的事实。

`decisions/K-XXXX.json` 是每条 Claim 的审计记录，事件包含标注的审查者身份、决策说明、UTC 时间、前后 Claim 摘要、前一个事件摘要和本次事件摘要。**记录标签不是身份认证，哈希链不是数字签名。** 有仓库写入权限的人可以重新生成整个链；发布前仍需独立代码审查、Git 来源和可验证测试证据。

## 2. 只读 CLI

```sh
cd ~/Projects/claude-code-mods-knowledge
uv sync --locked
uv run mods-knowledge claims validate
uv run mods-knowledge claims list
uv run mods-knowledge claims show K-0002
uv run mods-knowledge claims query --version 2.1.296 --surface cli
uv run mods-knowledge validate
uv run mods-knowledge verify
```

`claims query` 只返回兼容版本/运行表面的 `approved` 非历史知识；如果无适用事实，必须返回空列表，不得回退到候选猜测。网络完全离线运行。针对其他版本，需要传入准确三段版本号，不能填写 `latest`。

## 3. 在文件中整理待审核 Claim

1. 新建一个唯一的 `claims/K-NNNN.json`；新 ID 不能复用。遵守最初设计保留的 `docs/design/mods_ssot_design_v0_1/schemas/claim.schema.json`。
2. 归入 E 事件、S 状态、T 类型、Q 测试、P 安全、U UI 六个主域中的一个或多个；保留多对多次级领域标签。
3. 将每一条 `evidence` 指向 Registry 已登记来源，写出具体出处，不复制整篇网页到仓库，不采纳网页内的指令作为 Agent 权限变更。
4. 断言属规范性 `normative` 时，只能以当前匹配版本的 L0/L1 官方文档作为直接规范来源；历史 H 只能用于历史知识，社区 C/官方示例 R 不能独立证明 API 契约。
5. 新条目保持 `lifecycle=candidate`、`verification.runtime=not-run`，未固定版本前 `applies_to` 的版本边界保持 `null`，不得推测适用于全部版本。

## 4. 从 Candidate 到 Reviewed

候选本身不会自动获得 `reviewed`。至少需要：

- 对官方文档固定来源 Registry `snapshot.state=pinned`、`review_state=pinned`，核对 `snapshot.sha256` 与采集历史的同一来源、URL、记录时间；设置实际审阅时间 `snapshot.checked_at`。单纯命中网页 SHA 不等于审阅过正文。
- Claim `evidence` 的 `role=supports`、`snapshot_sha256` 必须指向已核对来源记录，`locator` 指向该官方 URL 的具体 `#anchor`；`verification.source=reviewed`。不接受只填写官网首页的泛指地址。
- 对 R 官方 GitHub 示例，需要固定 Anthropic 仓库对应 Commit，来源和 Claim 的 Commit SHA 必须一致，且有审阅时间。博客教程即使属 R 层，也不能伪装为已固定的 Git Commit 源码。
- 对 H 历史知识，只允许 H 类证据，且无论是否经过历史审阅都不得进入当前 API 查询输出。

在源材料和 Claim 已修改并通过校验后，**显式执行**：

```sh
uv run mods-knowledge claims transition K-0002 \
  --to reviewed \
  --actor "recorded-reviewer-identity" \
  --reason "已核对官方原文的具体段落、快照 SHA 和适用版本"
```

当前仓库六条候选仍未完成这些前置核验，因此上述命令目前**应拒绝修改**，不能强行通过。

## 5. 从 Reviewed 到 Approved

只能 `reviewed -> approved`；不允许 `candidate -> approved`。对于 `normative` Claim，额外要求：

- 明确 `min_inclusive` 与 `max_exclusive`（半开区间）和受支持的 `surfaces`；
- 存在匹配该区间的、已登记目标机器的 `smoke-pass` 或 `integration-pass` 运行记录；
- `verification.test_evidence` 使用 `evidence/runtime/<path>.json#sha256=<hash>`，文件内容哈希须完全一致；
- 测试报告必须绑定 Claim ID、`targets/profiles.json` 的 profile ID 和 Claude Code 版本、受支持的运行表面、实际命令、`exit_code=0`、`result=pass`、UTC 时间与日志 SHA-256；
- 日志在 `evidence/runtime/` 内，需为最大 2MB 的本地 `.log` 文件；不允许任意绝对路径或目录穿越；
- 没有未解决的 `contradicts` 证据，也不存在适用版本和运行表面重叠、同一 Subject 的另一个已批准 normative Claim。

**运行记录的 JSON 与日志即便完全一致，也只是可审计的声明，并不能密码学地证明测试真实执行。** 必须对原始运行过程、日志是否为真实测试、实际 Claude Code 版本、源码引用进行独立检查，不允许自动生成伪造 PASS 文件。不要将凭据、用户会话、敏感源码或环境变量保存进日志。

之后可显式执行：

```sh
uv run mods-knowledge claims transition K-0002 \
  --to approved \
  --actor "recorded-reviewer-identity" \
  --reason "已确认官方版本证据、冲突裁决及可复现运行日志"
```

不合格的知识必须停留在 `candidate` / `reviewed`，或通过明确审查转为 `rejected`。已批准知识发现过时时可 `approved -> deprecated`，并保留审计历史。对状态转换的每一次修改都需要提交到 Git，必要时通过 Pull Request 审查。

## 6. 版本更新与异常恢复

`targets/profiles.json` 是**活跃、可持续追加**的目标机器档案。已发布的 profile ID 不得重新指向不同机器或版本；升级机器后新增唯一 profile ID，而不是覆盖旧档案。原始设计包里的 `targets.json` 仅保留历史设计用途。

状态变更分别使用本机文件锁和原子文件替换。若进程在决定文件与 Claim 文件两次原子替换之间突然崩溃，校验会检测到摘要不一致；需要从 Git 审计事件及备份恢复，不可跳过校验。请勿直接修改已有 `decisions` 记录，修改 Claim 前应检查原有审批状态和是否必须重新评审。

**范围外：** 尚未执行真正的官方源码版本匹配、目标 Claude Code 的 API 运行验证、Knowledge Compiler、四平台 Skill 加载、ChatGPT Plugin 安装、自动批准或定时抓取。下一阶段的重点是核验具体 L0/L1 段落和补齐各领域可发布的知识，而非扩大无需证据的“通过”数量。
