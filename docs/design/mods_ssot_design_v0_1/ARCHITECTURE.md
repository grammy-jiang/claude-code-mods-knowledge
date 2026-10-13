# Claude Code Mods Knowledge Infrastructure — SSOT 与 Knowledge Compiler 架构设计（v0.1）

- 日期：2026-10-13（Australia/Sydney）
- 类型：设计规范草案；**不是已部署系统，也不是对 Mods API 的重新定义**
- 输入：`claude_code_mods_catalog_v2_2026-10-13.json`（91 条资料）和官方源码审阅报告；本次核对的公开 Agent Skills、Claude Code、Codex、Pi、OpenAI Plugin 文档
- 范围：Claude Code Mods 技术知识的可信管理、多 Agent 交付及更新流水线；**不包含实际 ChatGPT→Claude Code 运行时桥接业务**
- 目标主机（只读观察）：MacBook Pro：Claude Code 2.1.296 / Codex 0.160.0 / Pi 1.0.4；Raspberry Pi：Claude Code 2.1.296 / Codex 0.162.1 / Pi 1.1.0

## 1. 问题与目标

目标不是把 91 个网址压缩成一个 Prompt，而是让 Claude Code、Codex、Pi Agent、ChatGPT 在设计／实现／审查 Mods 时，检索适用于指定 Claude Code 版本的官方证据，识别不确定性和历史内容，且每个平台使用同一份经过批准的知识版本。上游文档/API 发生变化时，只更新 SSOT，重新构建所有产物，按测试结果发布或回滚。

### 明确不做

- 不复制整站官方文档或大批第三方文章到插件中；遵守版权、许可和来源网站条款。保留 URL、不可变内容摘要、必要的短证据定位及自己编写的总结。
- 不把 Mods 的当前 API 当作 Skill 格式本身；Skill 是给 Agent 的工作说明，不是 Mods Runtime。
- 不把社区代码、GitHub main、历史 Issue/提案直接视作目标版本 API 契约。
- V1 不建设统一的在线 MCP 服务、不要求 Internet 常驻、不安装会修改 Claude Code 行为的 Mod。
- V1 不将 Knowledge Compiler 运行期调用 LLM，避免同一输入每次生成不同知识。

## 2. 选择方案与权衡

A. **四份独立 Skills / 插件**：启动快，但容易内容分叉，更新与审计成本随平台数线性增长。不采用。

B. **所有 Agent 仅使用在线检索 MCP**：知识更新快，技术依赖强；断网与授权问题影响本地开发，也不保证在所有 ChatGPT 表面启用。不采用为首期方案。

C. **版本化离线 Skill + 可选在线检索（推荐）**：单一批准知识库生成统一 Skill 内容，按平台加极薄的包；通过 URL 查原文和后续只读 MCP 获取新增信息。离线明确记录知识版本和新鲜度，不把在线更新当作发布行为。采用。

## 3. SSOT 的两个互相关联但不同的事实层

### 3.1 Source Registry（来源登记簿）

一条来源记录表示一个权威来源的固定文档身份，不等于一个技术事实。核心字段由 `schemas/source.schema.json` 定义：

- `source_id`：沿用 M001–M091，新增采用 M092…；ID 永不复用。
- `url` 与 `canonical_url`、`title`、`owner`、`source_type`：官方文档、官方源码、教程、社区或历史资料。
- `trust_layer`：`L0`, `L1`, `L2`, `R`, `C`, `H`；沿用既有分层。此字段只表示来源类别，不能单独证明适用版本。
- `areas.primary` 与 `.secondary`：六工程领域 `E/S/T/Q/P/U`，保留多对多映射。
- `snapshot`：可选固定 commit/tag、官方页面采集时间、HTTP ETag、SHA-256、许可备注。**URL 不等于不可变证据；未固定版本时须标示 unpinned。**
- `review_state`：`indexed`、`read`、`pinned`，与真实运行测试严格分开。
- `historical_reason`、`superseded_by`：保留历史演进，不自动作实现依据。

### 3.2 Knowledge Claim（原子知识条目）

一条 Claim 表达一条可被审查的技术断言，而不是复制一篇文档。核心结构见 `schemas/claim.schema.json`：

- `id` / `subject` / `statement` / `kind`：如一个事件调用的返回语义、一条生命周期限制、一项工程准则。
- `areas`：六领域的主要与辅助归属；`related_claims` 表示相依或冲突。
- `authority`: `normative`（要求官方同版本证据）、`guidance`（可由官方源码/经复现实践支持）、`historical`（不得成为当前实现要求）。
- `lifecycle`: `candidate` → `reviewed` → `approved`；亦可标 `deprecated` / `rejected`。状态改变需要决策证据，不以源网页发布时间自动升级。
- `applies_to.claude_code`：允许 `min_inclusive`、`max_exclusive`，空值表示尚无法证明范围，**不表示“所有版本”**；`surfaces` 仅表示已声明/验证的平台，不跨 CLI、Desktop、VS Code、无头环境自动推广。
- `evidence[]`：链接到来源 ID、不可变快照或提交、可定位段落/行号/anchor、证据角色（支持/冲突）和证据类型。
- `verification.source` 与 `verification.runtime`：独立记录是否已阅读/锁定来源以及是否在具体目标版本运行验证；“源码阅读”不能自动写成“运行成功”。
- `migration`：可选 `supersedes`、旧条目、废弃理由。

**发布门禁（不是 Schema 单独可保证）：** `authority=normative` 且 `lifecycle=approved` 时，必须存在至少一个与目标版本相容、经固定/复核的 L0（必要时 L1）直接证据；同一适用版本不可存在未裁决的直接矛盾证据。`H` 不得支持现行 normative Claim；`C` 和 `R` 仅支持 guidance，除非有独立官方契约与目标版实测补充。对涉及危险操作的关键判断要求目标版本运行验证或保守弃权。

## 4. 从资料到知识的变更状态机

`discover → snapshot → diff → candidate-claims → review → approve → compile → static-test → agent-eval → release`

- `discover`：检测官方文档索引、源代码 tag/commit 和关注的 API 变更；不把社区热度当 API 凭据。
- `snapshot`：记录可再获取的位置、源固定版本与内容摘要。遵守许可；优先存自己编写的短摘要与行号定位。
- `diff`：标明新增/修改/删除的证据片段；纯格式变化不必触发新的规范条目。
- `candidate-claims`：创建候选变更，可用模型辅助提出差异，但不能直接 `approved`。每一条都有明确受影响版本与领域。
- `review`：确定正确性、适用版本、冲突、影响范围和安全级别；如有争议，挂起相关 Claim 而非强制合并。
- `approve`：记录审查人/流程、时间、来源 hash、测试摘要，更新 SSOT。
- `compile`：纯确定性、离线执行；只读取批准的 Claim/规则和锁定的 registry，不读网络、不调用 LLM。
- `release`：经平台验证、签发版本清单、保留上版产物用于回滚。发布所需的商店审核/人工安装不属于构建成功声明。

### 冲突优先级

1. 先匹配 Claude Code 实际版本与界面环境；版本不符的事实不参与候选。
2. 相同版本的 L0 Mods 官方规范优先于非规范材料；L1 仅在 Mods 依赖的机制边界内发挥规范作用。
3. 对来源状态尚未固定或有相互矛盾的证据，阻止该 Claim 进入自动建议；提供冲突说明，而非“猜一个更可能正确的答案”。
4. R 层用于解释设计实践；C 层用于提出待验证假设；H 层仅用于史料阅读，永远不注入生产 API 参考文件。
5. 实际目标机器的可重复测试可以证明“在该安装版本观察到某行为”，但不能代替官方承诺所有其他版本同样工作。

## 5. Knowledge Compiler 契约

编译是一个纯函数：

`compile(approved_ssot_revision, target_profile, compiler_revision) -> artifacts + build_manifest`

相同输入（包括模板、Schema、目标配置、排序和源码提交）必须生成同一组文件哈希。禁止构建阶段访问网络、调用模型、根据当前时间改写 Markdown、掺入未经审查的索引；构建时间写入独立 release attestation，不应影响产物可重现性。

### 5.1 输入

- 经 Schema 与跨文件引用验证的 Source Registry 和 Claim 集；
- 以 Git SHA 或版本号锁定的编辑性知识与规则模板；
- `targets/*.json`：Agent 宿主（Claude/Codex/Pi/ChatGPT）、当前软件版本、目标 Claude Code API 版本、支持的加载路径、联网/工具依赖；
- 模板版本、引用清单、已批准的源码示例注释。

### 5.2 内部处理

- 基于 `authority/lifecycle/version/surface` 过滤不适用 Claim；未标范围不得凭空默认“最新”可用。
- 对不同平台输出**内容等价**的主 Skill 和 `references/`；只有包目录、少量宿主说明和命令引用不同。
- 每条生成的 API 描述可追溯到 Claim ID → Source ID → 原始 URL/提交/定位器。
- 主 `SKILL.md` 仅包含触发条件、决策工作流、知识查找规则、引用与失败回退；不把 91 篇资料塞进正文。`references/{events,state,types,testing,security,interface}.md` 按需读取。
- 资料冲突、未知版本、网页无法访问、测试未运行时，产物明确要求 Agent 报告不确定性。
- 将 `historical` / `deprecated` Claims 输出至**隔离的**可选历史附录，永不在当前 API、可复制代码或默认检索结果中推荐其做法。

### 5.3 输出路径

```
dist/
  common/claude-code-mods-development/{SKILL.md,references/*}
  claude-code/.claude/skills/claude-code-mods-development/...
  codex/.agents/skills/claude-code-mods-development/...
  pi/.agents/skills/claude-code-mods-development/...
  chatgpt/claude-code-mods-knowledge/{plugin.json,skills/claude-code-mods-development/...}
  manifests/{build-manifest.json,checksums.sha256}
```

V1 建议先输出一个主 Skill `claude-code-mods-development`，避免六个互相竞争的入口 Skill；六领域是按需加载的参考文件。必要时再经触发测试评估拆分。

### 5.4 平台差异

- **Claude Code**：项目 `.claude/skills/`，个人 `~/.claude/skills/`；额外字段如 `disable-model-invocation` 属 Claude 专有，不能污染通用 Skill。可另行封装 Claude Plugin，但 V1 不强制。
- **Codex**：使用项目/个人 `.agents/skills/`，独立验证自动触发与 `$skill-name` 调用。
- **Pi Agent**：支持项目 `.agents/skills/` 与 `.pi/skills/`；采用标准目录式 `SKILL.md`，在 Pi 1.0.4 与 1.1.0 分别做加载验收。
- **ChatGPT**：优先 Agent Plugins v1 根目录 `plugin.json` 与 `skills/`；若需要兼容旧版，**另生成** `.codex-plugin/plugin.json`，不得出现两套互相矛盾的配置。首次仅 Skill，无 MCP 工具与账户授权。
- **在线检索**：Agent 若支持浏览器/官方 docs 阅读则遵守当前来源路由；第二阶段可添加只读 Docs MCP，Skill 将工具作为可选依赖。技能打包快照不等于服务器自动更新。

## 6. 版本策略与发布锁

同时独立维护：

1. `schema_version`：SSOT 数据契约的版本；
2. `knowledge_version`：知识内容的版本（如 0.1.0）；
3. `compiler_version`：生成器代码版本或 Git SHA；
4. `package_version`：各平台发布产物的版本；
5. `target_versions`：Claude Code、Codex、Pi 以及支持的 UI 运行表面。

`build-manifest.json` 须包含以上版本、完整源/Claim 哈希、输入 Git SHA、每个产物的 SHA-256、构建环境说明和门禁测试证据路径。对于某个 host 的发布，必须验证该 host 实际版本；不能因为 Mac 与 Raspberry Pi 的 Claude Code 版本相同，就推断 Codex/Pi 宿主行为相同。

版本变化流程：新增知识只影响 `knowledge_version`；结构变化提升 schema；适配生成器变化提升 compiler；下游每次发布都递增 package，且能定位回相应知识清单。旧包与旧知识快照保留可回滚版本。

## 7. 质量门禁和测试矩阵

| 门禁 | 通过条件 | 必须拒绝的例子 |
|---|---|---|
| `source-schema` | ID 唯一、URL 合法、层级与领域合法、历史属性完整 | 重复 ID；H 声称规范 |
| `claim-schema` | 原子 Claim 有稳定 ID、版本字段、领域、证据、状态 | 使用一个 Blob 存整篇无来源文章 |
| `normative-evidence` | 所有发布到当前规范的事实均有固定且版本相容的官方证据 | 社区文章单独证明 API 返回类型 |
| `history-firewall` | 旧 API 只在可选历史区；当前代码与参考不出现 | 早期 preview 开关重新变成安装步骤 |
| `reproducibility` | 两次离线构建产物 SHA-256 完全一致 | 生成中出现抓取时刻或随机排序 |
| `portability` | 通用 YAML frontmatter、相对路径、无宿主专有 API | 通用 Skill 使用 Claude 专用参数 |
| `prompt-injection` | 来源内容中的“忽略规则”不提升为 Agent 指令 | 第三方 README 指挥插件上传凭据 |
| `retrieval-eval` | 六领域核心问答能找到同版本官方引证 | UI API 问题只给历史参考 |
| `negative-eval` | 版本不明、官方证据冲突时明确弃权/核验 | 猜测当前 API 或臆造字段 |
| `host-smoke` | Claude/Codex/Pi/ChatGPT 每种宿主都能发现、加载、引用技能 | 一个目录可见但实际 Skill 未触发 |
| `security` | 没有默认网络上报、密钥读取、危险权限授权 | 新插件安装即打开执行通道 |
| `supply-chain` | 记录 source hash、构建 hash、包校验、已批准审查 | 无法重现此前发布包 |

自动化测试明确区分 `static_pass`、`simulated_pass`、`host_runtime_pass`；不能用前两个代替最后一个。能力评估要覆盖正常触发、无关任务不触发、目标版本匹配、过期 API 拒绝、证据缺失、官方与社区冲突、离线降级、跨宿主路径及与其他 Skills 共存。

## 8. 推荐仓库结构

```
claude-code-mods-knowledge/
  README.md
  docs/{architecture,decisions,operations}/
  schemas/{source.schema.json,claim.schema.json,release.schema.json}
  sources/{registry.json,snapshots/metadata/,history/}
  claims/{events/,state/,types/,testing/,security/,interface/}
  examples/{playground/,builtins/}              # 分析与指针，不复制受限源码
  knowledge/{glossary.md,source-routing.md,review-rules.md}
  templates/{skill/,platforms/}
  targets/{macbook.json,raspberry-pi.json,chatgpt.json}
  compiler/{...}                                 # 独立 Python 包；待实施
  tests/{schema/,policy/,golden/,retrieval/,platform/}
  scripts/{...}
  migration/{catalog-v2-input.json,import-report.json}
  dist/                                          # 构建产物（建议不纳入主源码）
```

注意：本会话只读扫描 `~/Projects` 后，尚未确定一个现存专门的 Mods 知识仓库；不得为省事在 `binnacle`、`android-mcp` 或别人的进行中工作树里直接落地。新仓库的 Git 地址/归属是部署决策，不影响本设计评审。

## 9. 分阶段执行与验收

- **P0 Source ingestion**：导入 91 条旧 Source ID，保留原层级和领域；生成重复/遗漏/历史隔离审计。验收：条目数一致、引用稳定、无重复 URL；导入后全部仍是 `indexed/read`，不能被默认为 `pinned`。
- **P1 Schemas & policy**：实现 schema、跨字段/跨来源约束、候选/批准状态机。验收：故意投放社区单证据 normative、无版本 Claim、H 注入当前 API 等反例全部失败。
- **P2 Claim curation**：从官方 L0/L1 提炼最小核心 Claim；每一项可回溯证据和版本。验收：六领域至少各有一个经过引用审核的 Claim，且官方示例明确只作为 guidance。
- **P3 Deterministic compiler**：输出一份通用 Skill 和四个平台包。验收：连续两次 SHA 相同，通用 Skill 通过 Agent Skills 官方格式检验。
- **P4 Evaluation**：启动无害的 Docs 查找/回答测试和目标版本识别测试；加入旧 API、冲突、离线、提示注入反例。验收：所有关键用例通过；必要时调整 Skill 触发描述而不改事实。
- **P5 Host smoke**：Mac/Pi 上 Claude Code、Codex、Pi 分别进行独立加载验证，ChatGPT 中验证 Plugin 安装后的 Skill 触发。验收：每个平台输出可核查的调用日志/测试证据；没有获得安装证明的包标记 `NOT_TESTED`。
- **P6 Release**：固定 Git SHA/知识版本、生成 SBOM 式来源目录和哈希清单、发布到选定渠道。验收：全平台标明“已验证/未验证”，可回滚一版。
- **P7 Optional docs MCP**：只读检索 `find_sources`, `search_claims`, `get_claim`, `check_version`；返回来源与版本，不提供写文件或运行 Shell 能力。验收：单独断网/拒绝权限时 Skill 保持离线降级。

## 10. 已识别风险与决策记录

- **文档漂移**：当前网页不能代表旧安装版本；用固定 source 版本、目标版本检测和冲突门禁阻断过度推断。
- **版权与许可**：默认发布原创总结+链接+最少必要引文；大规模原文抓取必须先确认许可。
- **提示注入**：上游文章与仓库内容作为数据，不允许改变技能内的工具权限和系统行为。
- **官方示例误用**：Playground 演示非生产安全保证；内置 Mods 有特殊权限，不能直接复制。
- **宿主支持差异**：Mac Pi 1.0.4 vs Raspberry Pi 1.1.0；Codex 0.160.0 vs 0.162.1，要分版本测试。
- **发布原子性**：ChatGPT 插件包升级不等于 MCP 运行时实时变更；本地 Skill 文件变更是否热生效也依赖宿主，应以实际检测为准。
- **静态验证假阳性**：Schema 能检查形状，不能证明实际 API 正确；需要一条事实到一条官方证据再到版本的闭环。

## 11. 设计阶段完成定义

本设计达到可进入实现评审的标准，当且仅当：已有稳定 schema、原有 91 项的迁移策略、纯函数编译契约、完整质量门禁、清晰的四宿主产物和目标版本矩阵。**当前文件属于设计产物；没有声称已经实现 Knowledge Compiler、完成四宿主自动测试或发布 ChatGPT Plugin。**

## 12. 关键官方技术依据（2026-10-13 已核对）

- Mods 官方概览：https://code.claude.com/docs/en/plugins/mods/overview
- Claude Code Skills：https://code.claude.com/docs/en/skills
- Codex / ChatGPT Skills：https://learn.chatgpt.com/docs/build-skills
- Pi Skills：https://pi.dev/docs/latest/skills
- Agent Skills 规范：https://agentskills.io/specification
- OpenAI Agent Plugins 打包：https://developers.openai.com/plugins/build/plugins
- ChatGPT Plugin 发布：https://developers.openai.com/plugins/deploy/submission

