# Claude Code Mods — P4/P5/P6 详细实施与验收计划

**版本：** 2026-10-27 v1.0
**唯一仓库：** grammy-jiang/claude-code-mods-knowledge
**起点 main：** 814bbdaf385feac5d8f022ff8615991a42038ff7（PR #122）
**状态：** 实施计划，不是已完成报告。只有实际执行、通过原生验收并合并到 main 的工作才能标记 done。

## 0. 范围、已有事实和实施原则

核心目标：维护版本限定的官方 Claude Code Mods 单一事实来源（SSOT），从同一个审查过的知识基线生成 Claude Code / Codex / Pi Agent Skills 与 ChatGPT Chat Mode Plugin，证明这些产物在真实目标宿主中可被发现、调用和准确使用，最后再发布。

严格排除：Agent Communication MCP、Agent Orchestrator Plugin、分布式宿主权限监督、Mac/Pi 签名租约、网络故障注入或系统强制 managed policy。PR #114–#118 的实验只留在原仓库 archive/cli304-security-experiments-20261023 分支；不可合并主线，也不能成为 Stable 条件。Issue #110 仅保留上游兼容性事实。

### 冻结的当前状态（检查时间：2026-10-27）

| 主题 | 已核对事实 | 未获支持的结论 |
| --- | --- | --- |
| Git | main=814bbda，PR #122 已合并，目前无开放 PR | 本地未提交工作已发布 |
| 回归 | 最近合并版本全量 1,199 passed/11 skipped，Python 3.11/3.14 CI 通过 | 三 Agent 或 Chat 模型全部合格 |
| 来源 | CLI 2.1.296、2.1.302 各有 31 项**各自版本限定** approved Claims；CLI 2.1.309 和 2.1.310 为 0 | 旧 Claim 适用于新 CLI |
| 官方 | npm latest 和 GitHub v2.1.310 一致，v2.1.309 原生证据仍是历史 | 309 验收等于 310 验收 |
| P5 WIP | Mac 分支 qa/p5-cli302-evidence-section-20261023 有 3 份未提交代码/测试 | 这些已完成 CI |
| 正式 Skill | Sextant CLI302 真正 Skill ToolUse/Read 完成；模型 Evidence 缺 K-0041、K-0067 | 答案达到全量语义验收 |
| 当前 P4 账号 | 2026-10-27 Raspberry Pi 只读 manage_plugins.py show 返回 HTTP 401 | 今天已确认安装的是 2026-10-16 的某个开发版 |
| 发布 | v0.2.0-beta.1 为最后一个 GitHub 预发布 | 已达到 Stable/GA |

所有任务状态使用 not_run / in_progress / passed / failed / blocked / inconclusive，不从结构测试推断模型行为，也不从原生 Loader 判定生成代码可靠。

## 1. 并行拓扑与共享资源

将工作划分为四条可并行的工作流：

- **Lane A：现有 P5 引用质量缺陷收尾。** P5-01 → P5-02。以 Mac 原有未提交工作分支为唯一写入口，优先合并确定性修复。
- **Lane B：P4 真实 ChatGPT Chat Mode 产品验收。** P4-00 → P4-01 → P4-02 → P4-03/P4-04。最高业务优先级，当前账号 HTTP 401 阻塞，仅该 Lane 需暂停账号读取/发送。
- **Lane C：2.1.310 官方来源和版本审批。** VER-01 → VER-02 → VER-03 → VER-04。来源收集/语义审阅与 Lane A/B 并行；不提前升级生产 CLI。
- **Lane D：P5 三 Agent 原生推理矩阵。** P5-03 → P5-04 → P5-05。Claude Code、Codex、Pi Agent 可在独立 QA 目录并行，模型额度不足时维持 blocked，不绕过配额。

共享对象只允许单写者：SSOT 审批 ledger、目标版本锁、Git main、同一个真实 ChatGPT 账号/浏览器会话。其他工作通过 Git Worktree 分支隔离；工作在一条 Lane 的 blocker 不阻塞另一条 Lane。P6 必须等待全部强制门禁独立通过。

## 2. Lane A — 当前 P5 WIP（P0，优先完成）

### P5-01：正式 Skill 引用完整性与三组原始模型证据

输入：Mac 原始 qa/p5-cli302-evidence-section-20261023 分支，Sextant 私有原生 CLI302/309 模型事件，31 项获批 302 Claims。

1. 保留原三份 WIP 文件，核对源 SHA，拒绝覆写/丢失原始本地更改。
2. 将 audit_claim_evidence_section 与既有 audit_claim_source_links 并存，严格要求开头 Evidence → Scope → Answer，所有提及的 Claim ID 必须在 Evidence 中以独立行对应**自己的**准确官方 URL，包括 #fragment。
3. 加入负例：K-0041/K-0067 出现在正文但未注册 Evidence，同一官方页面错误 anchor、未审 Claim、错误版本、不完整正文、多 Claim 共用一条引用。
4. 从原始 Sonnet JSONL 重放三组：有正式 Skill 的 CLI302、无 Skill 的 CLI302、旧 Skill 在 CLI309 上的版本错配。必要的真实工具调用与 Read 结果由原始事件支持，不凭答复措辞猜测。
5. 明确保留 no-Skill 对照的**一次 Read 错误**；这不是完全等价的变量控制，不制造“100% 模型提升”的比较。
6. 产出脱敏模型 SHA/ID/工具/判定报告、单测、Mac 全量 pytest/Ruff/source verify，正常 PR + GitHub 双 Python CI + squash merge 原仓库并更新 Issue #3。

验收：能从私有真实事件重放同一脱敏报告；旧的“官方 URL 可在任意位置”扫描虽通过，但新版 Evidence 扫描准确拒绝缺项；不新增 Claim 审批、也不修改用户全局 Skill。没有 PR merge 即不标记完成。

### P5-02：让语义门禁可以重用

1. 分别保存：原生 Skill ToolUse、reference Read、Claim target、开头 Evidence、exact URL、回答代码风险、native TypeScript 编译、原生 Mock、独立语义审核与用户宿主执行结果。
2. CI 加入确定性假阳性案例：回答看似正确但证据缺行、引用错误 Anchor、read SKILL.md 但未调用 Skill、异步工具错误被吞掉。
3. 历史报告有变化时创建新订正证据和溯源，不静默重写旧结论。

验收：严格扫描器必须 FAIL CLOSED，成功引用并不自动成为运行代码/语义合格。

## 3. Lane B — P4 ChatGPT Chat Mode（P0，主线）

Issues：#1 auto-routing 与 #2 semantic QA。只针对 ordinary Chat mode；不能用 Work 或 Codex 结果替代。

### P4-00：恢复账号可观测性（当前 blocked：HTTP 401）

1. 只读账号预检，包括浏览器环境、登录状态、个人 Plugin list/show、当前 Skill enablement 和 Chat Mode 运行条件；优先重用此前已获授权的浏览器会话。
2. 目前 Raspberry Pi 上 show claude-code-mods-knowledge 返回 HTTP 401。将其单独记录为认证/账号门禁失败，禁止推断安装版本或直接跑 46 个 Chat 用例。
3. 不收集或公开 Cookie/Access Token，不自动更换账号、凭据、网络、代理或绕过速率限制。若需要用户实际重新认证，则独立标记 blocked，不阻碍 A/C/D。
4. 授权恢复后只读下载当前账号 Plugin：记录 package name/version、enabled Skill、账号规范化 ZIP 的十个 canonical 文件及 sidecar 与已审核源 SHA 的比较；2026-10-16 的 Beta2 记录只作历史。
5. 私有保管浏览器与模型/账号证据；公开仅写匿名版本、hash、通过/失败原因。

验收：当前账号 Plugin 实际版本、enabled/Skill、源代码内容字节可可靠 read-back，且有匹配的冻结版本 QA 基线。

### P4-01：冻结版本、用例与配对比较

- 原始 published baseline：v0.2.0-beta.1，CLI 2.1.296，冻结的 evals/p4_cases.json。
- 后续候选：只使用真实启用且匹配自身 reviewed SSOT scope 的候选；CLI302 用 evals/p4_cases_cli_2_1_302.json；310 先审批并创建自己版本的 frozen suite。
- 记录目标 Git SHA/Plugin version/Source SHA/case_id/prompt SHA/model effort；显式 @plugin 仅作阳性控制，不能计入 automatic PASS。

验收：比较对象及版本一致，账号当时真实读回版本已核实；不拼接不同候选版本的用例结果。

### P4-02：真正的 46-case 自动 Chat Mode 验收

冻结的 suite 由 **30 positive + 8 unrelated negative + 8 version/security boundary** 构成；每例独立新普通 Chat 会话、真实发送确认、最终完整用户可见回合（所有 assistant 文本片段合并），并记录 api_tool.read_resource 与正确的 Skills URI。所有原始对话、conversation IDs、账户资源与下载 ZIP 仅留私有目录。

- Positive：真正确认 Plugin 的 Skill 与相关引用被自动读取，回答来源/Claim 与预期及独立语义审核一致；通用模型碰巧答对不算自动触发。
- Negative：不读取 Mods Plugin；回答别的主题再好也不能证明这个插件“有用”。
- Boundary：不匹配版本/旧文档/注入/权限边界按规定拒绝或澄清，同时该调用是否自动激活单独判断。模型自行拒绝但 Skill 未加载仍是路由失败。
- 错误状态：401、429、conversation ID 不确定、模型未完成、浏览器失败为 blocked，绝不盲目补发。复跑必须读取并去重已经完成的原始 ID。

验收：**46 个完成且 46/46 真正符合其独立标准，零 irrelevant false activation**。静态 46/46 和显式 @plugin 成功不代替自动模式真实通过。

### P4-03：可重复的路由诊断

- 对自动路由失败/高风险代表用例至少 3 次新的配对会话，保持同 prompt SHA、账号 build、模型/effort、运行模式；对时段/缓存效应记录而非挑选有利样本。
- 原因分类：未安装/版本不同/Skill disabled/未选中/资源地址错误/读取失败/等待中/权限阻塞/429/语义失败。
- 一次只改变 Plugin Skill name、description、触发关键词之一，配备未变更对照；发布前严格检验 unrelated 和 boundary 没有回归。
- 如果平台自动路由不能达到标准，如实保留失败，不通过减小样本或只用显式 @plugin 规避自动路由门禁。

验收：能够解释失败属于真实账号状态、选取问题还是模型语义；重复样本仍不合格则 P4 维持 blocked/failed。

### P4-04：完整语义、代码、来源验收

- 对 P4-02 所有真实最终回答逐项审核官方 Source ID、正确 #anchor、准确 Claim、CLI 版本和 E/S/T/Q/P/U 对应领域。
- 检查典型代码风险：具名 register(on)、tool.call 三参数 ($, e, next)、strict author、Mod 目录验证参数、异步 .catch/日志错误隔离、误报未验证兼容性。
- 可执行代码需独立 TypeScript noEmit、目标原生 plugin validate --strict、安全隔离的 .test.ts mocks 和语义 review；静态 PASS ≠ 原生运行成功 ≠ 用户权限语义得到证明。
- 独立审核所有 8 项边界；绝不从 answer_lint 0 warning 推论源码安全。

验收：每个 case 分离 routing / Claim URL / 语义 / code native verdict，不足证据为 inconclusive。

## 4. Lane C — 2.1.310 官方知识更新（P1，可并行）

### VER-01：原始官方来源观察

- 官方 npm latest 与 GitHub release target=2.1.310，按发布事实保存完整原始 source 的私有 SHA、公开 release bullet SHA、checked_at、版本和链接。
- 按注册 Allowlist 采集 M003/M004/M033 及受影响 Mods/Skills 文档，追加 immutable snapshot；不篡改历史元数据。HTML 字节差异 ≠ 语义变更。
- 首先关注新 Monitor 工具、Mod UI Image、权限/Hook 和 MCP 影响；其余变化列为独立后续审核主题。

验收：原始 URL 与 exact version、来源散列有完整记录；mods-knowledge verify PASS，新增内容保持 unapproved。

### VER-02：限定范围的 Claim 审批

- 仅独立审阅当前官方文档明确支持且有目标版本类型/语义证据的 Claim。
- 用 candidate → reviewed → approved 记录出处和审查，不向 310 隐式扩展 302/309 审批，也不修改旧已审批范围。
- 为兼容性不确定的主题保留 pending；没有 Claim 不构建正式 310 Plugin。

验收：针对 310 每条 approved Claim 都能追溯官方位置、精确目标类型和原生 QA。

### VER-03：官方 2.1.310 原生测试

- 官方原版 SHA 验证后在各 host 独立 scratch 目录测试，保护 Mac 7x24 常驻会话、Pi/Sextant 生产 CLI 及个人 Skills。
- 重新验证被 release delta 触及的 Skills/Mod hooks、Model Alias、嵌套 Skill、Monitor/权限等，不复用 309 ToolUse 来证明 310。
- 目标机器、模型、真实输出、权限拒绝及未测项分别保留，原始记录不上 Git。

验收：官方 binary SHA、真实 target、types/native QA、失败分类可审查。

### VER-04：冻结 target 后生成四类产物

- 在同一 reviewed SSOT Git SHA 下重新构建 Claude Code、Codex、Pi Agent Skills 和 ChatGPT Plugin，校验 manifest、Source Index、SBOM、可重现 ZIP/hashes。
- 发布前重查在线 npm latest 并要求当前 approved Claims、完整 P4/P5 资格；latest 若再次更新，本轮 310 作为历史证据保留，不谎称仍最新，也不反复重置独立的 P4 历史对照。

验收：不能出现“CLI310 文件名，却包含 CLI302 的旧 Claims”的假兼容包。

## 5. Lane D — 真实 P5 三 Agent 模型矩阵（P1，可并行）

### P5-03：冻结相同的跨模型样本

每个 Agent、宿主、模型真实测试 representative positive（E/S/T/Q/P/U）、negative、version/security boundary。每例记录源 SHA/模型真实 provider、模型 ID/Skill ToolUse/引用 Read/response SHA/工具错误/输出完成与否。

不得将 Codex app-server skills/list、Pi loadSkillsFromDir 或 Claude plugin manifest validate 直接当作模型使用知识通过。

### P5-04：技术答案与 runnable Mod QA

- 同时保留有 Skill 与无 Skill 对照的真实答案，并明确对照工具错误/限流等不对称条件。
- 严格检查 Evidence、版本、官方来源与 Claim；生成代码在目标本机做 TypeScript 类型检查、strict native Mod validation、safe .test.ts mock。
- 另行测试正常/拒绝/失败/异常返回，保持 downstream exactly once、错误不被日志覆盖。不从模拟 stub 推断真实权限成功。
- 新发现的确定性缺陷先写 FAIL 单测，再回 SSOT/compiler 源头修；不直接编辑个人安装的 Skill。

### P5-05：三 Agent 独立验收报告

独立保留 Claude Code/Codex/Pi Agent 的 real-host positive/negative/boundary 结论、对应版本、样本规模、模型 ID 和每项 Code QA。不同模型不互相借用 PASS；任何缺失或不稳定标 inconclusive/failed，Issue #3 保持开放。

## 6. P6 Stable 的统一门禁（必须等待上游完成）

### P6-01：证据汇合与资格判定
输入同一个 source Git SHA 的 approved exact-version SSOT、四种包/manifest、46/46 Chat Mode 自动验收、三 Agent 原生模型报告和个人账号实际下载/回滚证明。运行 stable-readiness --require-ready，缺任何关键证据返回 STABLE_RELEASE_BLOCKED。

### P6-02：候选构建
冻结目标版本、生成四端技能/Plugin，验证 YAML/JSON Schema、manifest/allowlist、内容 SHA256、三机可重建、GitHub Actions Python 3.11/3.14、元数据/版本正确性。

### P6-03：账号安装及回滚
账号恢复且 P4 PASS 后，在授权下先备份原版、上传候选、实际 read-back enabled 与 canonical plugin ZIP、做真实 Chat测试与回滚演习。上传成功不等于运行成功；不影响无关的个人 Plugins。

### P6-04：Stable 发布
只有 P6-01/02/03 全部 PASS 才创建正式 Tag 和 GitHub Stable Release，独立下载比对资产 SHA 与 release notes。若未通过，维持历史 Beta.1，不标记 GA。

## 7. 开发与并行执行契约

1. **唯一原仓库、不 fork。** 工作流各自 Git branch/Worktree，提交 PR → 完整 Mac offline pytest、Ruff、source verify → GitHub Python 3.11/3.14 CI → squash merge main → 原 Issue 更新；并行期间避免两个分支同时改同一个审批 ledger。
2. **真实证据分层。** static lint、source URL、model ToolUse、原生 Mod test、真实 Chat resource read、账号 ZIP download 分别记录；某一维度 PASS 不转化为其他维度 PASS。
3. **隐私。** 保存原始 conversations、model JSONL、session ID、凭据、个人路径、浏览器缓存于各 host 0700 私有目录。GitHub 仅提交 sanitized Case/URL/Claim ID、散列和审查结果。
4. **失败处理。** HTTP 401/429 或平台受限停止该 Lane 的账号操作，不改网络/账号绕过、不重复发送可能成功的消息。不能因为测试环境不足就删掉失败的 Case。
5. **资源。** 浏览器单实例串行排队；独立 CPU/Host/agent 可以并行，配额耗尽时先做确定性验证，不隐性切换到付费 API。
6. **变更范围。** 不修改正在运行的正式 Claude Code 进程、系统 managed settings、个人 Skills、不发布或安装未经审批的新 Plugin。Issue #110 的官方兼容性问题与独立安全研究始终分离。

## 8. 启动顺序和验收检查点

| 顺序 | WBS | 初始状态 | 不得越过的退出条件 |
| --- | --- | --- | --- |
| 0 | 本计划合并 main | in_progress | 文档评审 + 双 Python CI |
| 1 | P5-01 当前 WIP 收尾 | in_progress | 私有 3-arm 原生证据可重放，单测与 PR/CI 通过 |
| 2 | P4-00 当前账号只读核验 | **blocked: HTTP 401** | 真正认证/版本/Plugin enablement 可以独立 read-back |
| 3 | VER-01 2.1.310 原始官方来源 | not_run | 源 SHA 与 append-only 快照一致、无自动 Claim 审批 |
| 4 | P4-01/02 新真实 46-case | blocked by P4-00 | 46 个独立实际 Chat 回合完整通过 |
| 5 | P4-03/04 重复路由与语义审核 | not_run | 真实 trace+完整回答+每个 Claim URL 与 Native code 审查 |
| 6 | P5-02/03/04/05 三 Agent 实际模型 | partial historical | 独立的版本/模型/运行与语义验收 |
| 7 | VER-02/03/04 审批、新 CLI 原生与构建 | 310 仍 0 approved | 所有新批准 Claims 经过官方和原生核验 |
| 8 | P6-01/02/03/04 Stable | HOLD | 前述独立 PASS + 真实账号安装与回滚通过 |

**最终定义：** 工作项只有在明确产物存在、原始证据可核、测试通过且已合并 main 后才视为 done。完成某次测试而发现 FAIL，是“测试已执行”，不是该产品能力已通过。
