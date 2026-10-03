# Agent Memory 开源选型复核：Hindsight 优先推荐

> 复核日期：2026-09-28
> 结论状态：**本报告更新并取代 2026-09-22 / 2026-09-23 两份报告中“Mem0 + LightRAG 优先”的推荐**。
> 调研方式：GitHub API 元数据 + 仓库源码/文档阅读 + 独立多 Agent 交叉验证。
> 适用场景：华为云数据库团队，约 5 人，2–3 个月上线面向 Agent 的 ContextDB / Agent Memory 服务，优先复用 `pgvector`、PG 全文检索，后续可评估 PG AGE。

---

## 1. 执行结论

### 1.1 首选方案

**Hindsight + 华为云 RDS PostgreSQL + 自研云控制面**

| 角色 | 选型 | 说明 |
|---|---|---|
| 记忆 + 知识核心 | Hindsight | MIT License；开源版提供 Memory、Mental Models、Knowledge Base / Knowledge Pages API；PostgreSQL-first |
| 存储底座 | Huawei Cloud RDS PostgreSQL | 使用 PostgreSQL 15+、`pgvector 0.5.0+`、`tsvector`、JSONB、Recursive CTE |
| 云产品控制面 | 自研 | 补齐 IAM、租户隔离、配额、审计、计费、备份、监控、模型网关等云服务能力 |
| 图增强 | 一期不依赖 AGE | Hindsight 使用 PostgreSQL 原生能力；AGE 可作为二期图服务或独立增强，不宜阻塞 MVP |

### 1.2 备选方案

**Mem0 + LightRAG + 自研 ContextDB 控制面**

- 适合作为“双组件职责清晰”的备选：Mem0 承担记忆层，LightRAG 承担知识层。
- 但组合的主要工作量不在安装，而在统一租户、鉴权、召回、知识晋升、审计、配额和数据模型。
- 若采用该路线，建议优先使用 LightRAG 的纯 PostgreSQL 表图存储，避免直接绑定 AGE 1.7.0 之后版本。

### 1.3 不建议作为 MVP 核心

| 项目 | 原因 |
|---|---|
| Cognee | PG 图适配器源码明确标注 DEMO / not production-ready；MVP 风险偏高 |
| OpenViking | 产品方向最接近 ContextDB，但 License 是 AGPL-3.0，商用集成需谨慎法务评估 |
| Graphiti | 图记忆能力强，但主路径面向 Neo4j / FalkorDB / Neptune 等图库，不是 PG-first |
| Supermemory | Self-hosting 形态是自包含二进制与嵌入式图引擎，不符合以华为云 RDS PG 为事实源的架构 |
| Letta | 旧仓库迁移到 `letta-ai/letta-code`，当前形态更偏 Agent 平台，不适合直接作为记忆服务底座 |

---

## 2. 关键问题与结论

### 2.1 为什么 Agent Memory 会扩展到知识沉淀、知识管理与知识晋升

原始会话记忆只解决“记过什么”，但长周期 Agent 还需要解决：

1. **上下文噪声**：原始对话、工具结果、临时偏好混杂，直接塞回上下文浪费 Token 且降低准确性。
2. **冲突与过期**：用户偏好、项目约束、组织规则会变化，需要置信度、有效期、覆盖关系与版本。
3. **复用与晋升**：低层事件和会话事实需要归纳为团队知识、项目规则、领域模型，再按需召回。
4. **治理与安全**：企业服务必须处理隔离、审计、脱敏、授权、生命周期和撤销。

因此现代 ContextDB 通常从单条记忆扩展为分层上下文：

```text
Raw Interaction / Fact
        ↓
Agent Memory / Working Context
        ↓
Semantic / Episodic / Preference Memory
        ↓
Knowledge Page / Mental Model / Rule
        ↓
Governed Organizational Knowledge
```

这也是阿里云 ContextDB、火山引擎 OpenViking、腾讯云 Agent Memory 对外强调“记忆 + 知识 + 召回 + 治理”的原因。厂商页面的原始入口如下：

- 阿里云 ContextDB：<https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start>
- 火山引擎 OpenViking：<https://www.volcengine.com/product/openviking-service>
- 腾讯云 Agent Memory：<http://cloud.tencent.com/product/agm?Is=sdk-topnav>

### 2.2 业界主流开源是否也在向“记忆 + 知识 + Skill”演进

结论：**趋势存在，但成熟度和开源边界差异很大。**

| 项目 | 当前定位 | 与“记忆 + 知识 + Skill”的关系 |
|---|---|---|
| Hindsight | Agent Memory + Knowledge | 明确覆盖记忆与知识；开源版提供 Mental Models 和 Knowledge Base API |
| OpenViking | Memory + Knowledge RAG + Skills | 定位最完整，但 AGPL-3.0 带来商用风险 |
| Mem0 | Agent Memory Layer | OSS 仍以记忆层为主，v3 配置中未见到图记忆配置，需与 LightRAG 组合补知识能力 |
| Cognee | Knowledge Pipeline / Knowledge Graph | 偏知识图谱构建；PG 图适配器标记 demo |
| Graphiti | Temporal Knowledge Graph | 图知识能力强，但不是 PG-first |
| Supermemory | Memory / Context Infrastructure | 功能较完整，但 self-host 架构偏嵌入式图引擎 |

相关仓库：

- Hindsight：<https://github.com/vectorize-io/hindsight>
- OpenViking：<https://github.com/volcengine/OpenViking>
- Mem0：<https://github.com/mem0ai/mem0>
- Cognee：<https://github.com/topoteretes/cognee>
- Graphiti：<https://github.com/getzep/graphiti>
- Supermemory：<https://github.com/supermemoryai/supermemory>

### 2.3 Hindsight 为什么短时间热度很高

截至 2026-09-28，Hindsight GitHub 元数据显示约 **39,254 stars**、MIT License、近期仍在持续更新。结合仓库与文档，热度较高的合理解释是：

1. **产品切口准确**：直接针对 Agent Memory / Long-term Context，而不是泛 RAG。
2. **能力边界清楚**：不止存储文本，还提供 retain、recall、reflect、Mental Models、Knowledge Pages。
3. **PostgreSQL-first**：符合企业已有 PostgreSQL 技术栈，降低部署成本。
4. **开源协议友好**：MIT License 对快速产品化比 AGPL 更安全。
5. **增长时间短**：仓库创建时间为 2025-10-30，短时间获得数万 star，说明话题撞上了 Agent Context Infrastructure 需求。

> 注意：star 数只说明关注度和社区热度，不能直接等同于生产成熟度或性能最优。生产决策仍需要以源码能力、License、存储适配、压测和治理能力为准。

### 2.4 Hindsight 提供的是 Memory，还是 Memory + Knowledge

结论：**Hindsight 不是单纯 Memory，开源版覆盖 Memory + Knowledge。**

核心能力：

1. **Memory**：保存交互事实、语义记忆、情景记忆、偏好等，并提供召回。
2. **Reflect / Mental Models**：从记忆中归纳更稳定的判断模型或结论。
3. **Knowledge Base / Knowledge Pages**：提供知识页面能力，OpenAPI 描述其创建过程可由 mental model + tree node 组成。
4. **PostgreSQL 存储**：生产路径要求 PostgreSQL 15+ 与 pgvector 0.5.0+，使用向量、全文、JSONB、Recursive CTE 等 PG 能力。

Hindsight 论文入口：<https://arxiv.org/abs/2512.12818>

### 2.5 Hindsight 是否支持 PG 图

结论需要区分两个概念：

1. **是否支持 PostgreSQL 图查询**：支持。Hindsight 使用 PG relational tables 表达 entity、entity co-occurrence、memory link、knowledge page tree，并使用 Recursive CTE 做图查询。
2. **是否依赖 PG AGE 扩展**：不依赖。Hindsight 的生产要求是 PostgreSQL 15+ 和 pgvector 0.5.0+，文档没有把 AGE 列为依赖。

因此，“Hindsight 不支持 PG 图”这个说法不准确。更准确的表述是：

```text
Hindsight 支持 PostgreSQL-native graph，
但不使用 Apache AGE 作为图执行引擎。
```

这与 Cognee 的关键差异在于生产成熟度：

| 维度 | Hindsight | Cognee |
|---|---|---|
| PostgreSQL 定位 | Primary backend，storage schema 与检索链路围绕 PG 设计 | PG vector 可用于生产；PG graph adapter 明确标注 DEMO / not production-ready |
| 图能力 | Entity / temporal / causal link、Recursive CTE、Knowledge Page tree | 有知识图谱 pipeline 和更通用 graph 抽象，但 PG 生产图路径要求 Kuzu 或 Neo4j |
| MVP 复杂度 | 单一 PG 事实源，部署和运维简单 | 若要生产级图，需要引入额外图库，破坏 PG-only 目标 |
| License | MIT | Apache-2.0 |
| Memory + Knowledge | Retain / Recall / Reflect / Mental Models / Knowledge Pages | 更偏 Knowledge Pipeline / KG 构建，Agent Memory 服务化能力需要额外补齐 |

**为什么仍然推荐 Hindsight：不是因为“图功能比 Cognee 更多”，而是因为在“RDS PostgreSQL 单一事实源 + 2–3 个月上线 + Memory + Knowledge 服务化”约束下，Hindsight 的完整可用路径更短。**

如果产品目标是独立的通用知识图谱平台，且愿意引入 Neo4j / Kuzu 等图库，Cognee 的图谱构建能力值得评估。但 Huawei Cloud ContextDB 的约束是优先复用 RDS PG，此时 Cognee 的 PG 图路径不能作为生产底座，Hindsight 更合适。

### 2.6 Hindsight 的付费版本与部署数据库

Hindsight 提供 **Self-hosted / Hindsight Cloud / Enterprise** 三档。官方 pricing 页明确 Self-hosted 是 MIT、免费、无限制，Cloud 按用量计费，Enterprise 面向规模化生产。

| 版本 | 定位 | 核心差异 |
|---|---|---|
| Self-hosted | 免费，MIT | 自行部署；包含 4 类 memory network、Retain / Recall / Reflect、MCP Server、embedded PostgreSQL；社区支持 |
| Hindsight Cloud | Pay-as-you-go | 包含 Self-hosted 能力，另提供托管基础设施、自动扩缩、每日备份、Dashboard、团队协作、99.9% SLA、12×5 email 支持 |
| Enterprise | 联系销售 | 包含 Cloud 能力，另提供 BYOC / on-prem、专属基础设施、自定义 SLA 最高 99.95%、最高 24×7 支持、30 分钟响应、SSO/RBAC、定制集成、培训 |

官方给出的 Cloud 计量项包括 Retain、Recall、Reflect、Iris Extract、Mental Model、Storage；例如 Retain 为 `$10.00 / million tokens`，Recall 为 `$0.75 / million tokens`。价格可能随官方页面调整，商业化评审时应当日复核。

数据库形态需要区分开发与生产：

| 环境 | 官方推荐 |
|---|---|
| 本地开发 | 默认使用 `pg0` 内嵌 PostgreSQL，并预装 pgvector |
| 生产 | 使用外部 PostgreSQL，配置 `HINDSIGHT_API_DATABASE_URL`；storage 文档给出 PostgreSQL 15+ 与 pgvector 0.5.0+ 要求 |
| 企业数据库替代 | Oracle AI Database，官方描述为 full feature parity，定位为已标准化 Oracle 的企业 |

> 版本要求差异提示：当前本地快照中的 `installation.md:28-39` 写 PostgreSQL 14+，而 `storage.md:70-77` 与线上 storage 文档写 PostgreSQL 15+。华为云方案应按更严格的 PostgreSQL 15+ / pgvector 0.5.0+ 设计，POC 时确认最低版本策略。

因此，华为云 ContextDB 应采用 **Self-hosted Hindsight + Huawei Cloud RDS PostgreSQL（pgvector）**，而不是内嵌 `pg0`，也不是 Hindsight Cloud。若后续采购 Enterprise，可重点评估 BYOC/on-prem、SSO/RBAC、24×7 支持和 30 分钟响应是否能替代部分自研控制面工作量。

来源：

- Pricing：`https://vectorize.io/pricing`
- README Self-hosted / Cloud：`hindsight/README.md:113-117`
- Storage：`hindsight/hindsight-docs/docs/developer/storage.md:3-15`
- pg0 / 生产环境：`hindsight/hindsight-docs/docs/developer/storage.md:49-77`
- Installation：`hindsight/hindsight-docs/docs/developer/installation.md:28-56`

### 2.7 Hindsight 开源版能否创建团队共享知识库并支持多 Agent 共享

结论：**可以做团队共享知识库，也可以让多个 Agent 共享同一个知识空间；但共享单元是 Memory Bank，不是自动跨 Bank 复制。**

推荐三种产品化模式：

1. **共享 Team Bank**：一个团队使用一个 `bank_id`，把已有文档、wiki 页面、会议纪要、PR/commit 说明等通过 `retain` 写入；团队内多个 Agent 都指向同一 Bank。Hindsight 的 Documents API 支持按 document 跟踪来源、更新和批量删除。
2. **Knowledge Pages 作为共享 wiki**：Knowledge Pages 是 Bank 对自己整理出的“活文档”，按文件夹组织，可搜索，可镜像为 Markdown。它们由 Bank 内 observations / facts 周期性刷新，并有 provenance；适合作为“团队当前共识”，而不是原始档案。
3. **Tag-scoped shared bank**：若一个 Bank 同时服务多个用户、角色或 Agent，可用 item/document tags 做可见性过滤，并在 recall/reflect 时按 tag 过滤。这适合“共享底座 + 按需隔离”。

需要注意两个边界：

- **Bank 之间默认严格隔离**。文档明确说一个 Bank 内的 memories 对另一个 Bank 不可见；因此不能假设 Agent A 的 Bank 能自动读取 Agent B 的 Bank。跨 Bank 晋升需要自研“候选知识 → 审批 → 写入共享 Bank”的治理链路。
- **Knowledge Pages 是自动/半自动知识层，不是人工审批系统**。它适合沉淀和刷新团队共识；如果企业流程要求“知识晋升前必须人工审批、版本签名、审计留痕”，仍需要在 ContextDB 控制面补齐。

来源：

- Memory Bank 隔离：`hindsight/hindsight-docs/docs/developer/api/memory-banks.mdx:23-35`
- Documents 来源与更新：`hindsight/hindsight-docs/docs/developer/api/documents.mdx:23-41`
- Knowledge Pages wiki / Markdown / agent tools：`hindsight/hindsight-docs/docs/developer/knowledge-pages.mdx:5-47,74-79`
- Knowledge Pages 由 processed memory 刷新：`hindsight/hindsight-docs/docs/developer/knowledge-pages.mdx:60-70`
- Tag 可见性过滤：`hindsight/hindsight-docs/docs/developer/retain.md:167-175`

### 2.8 Hindsight 公布 benchmark 的评测口径

先纠正一个常见表述：**BEAM、LifeBench、LoCoMo、LongMemEval、PersonaMem、sde-bench 不是模型，而是数据集 / 基准任务**。Hindsight 是被评测的 Agent Memory System；每次评测通常还叠加一个负责生成答案或执行任务的 LLM backbone。

Hindsight 使用 Vectorize 团队维护的 **AMB（Agent Memory Benchmark）** 作为统一入口。AMB 的流程是：Ingest 文档到 memory provider → Retrieve 上下文 → 用 Gemini 生成答案 → 用第二个 Gemini 调用评分；同时记录 retrieval time、ingestion time 和 token 成本。PrecisionMemBench 例外，只测 retrieval，不跑 answer LLM/judge。

| Benchmark | 测什么 | 关键数据形态 | 对产品选型的含义 |
|---|---|---|---|
| **BEAM** | 超长对话记忆：100k–10M tokens；缺失证据拒答、矛盾解决、事件排序、信息抽取、指令遵循、知识更新、跨 session 推理、偏好遵循、摘要、时间推理 | 100 段会话、2,000 个 probing questions；AMB split 为 `100k/500k/1m/10m` | 压测长上下文、检索成本、时间与知识更新的极限 |
| **LifeBench** | 长周期、多来源、个人化记忆：一年日常数字足迹中的事实检索、多源推理、时间演进、习惯/偏好等非陈述性记忆、不可答问题 | AMB 源码描述 10 个用户、约 2,003 个英文 QA；类别映射为 information-extraction、multi-hop、temporal-updating、nondeclarative、unanswerable | 检验个人助理类 Agent 的长期画像与生活事件记忆 |
| **LoCoMo** | 非常长的多 session 对话记忆和问答：单跳、多跳、时间、开放域 | AMB 使用 `locomo10`；10 个多 session 对话；adversarial 类别被 AMB 排除 | 经典对话记忆 benchmark；较长上下文，但比 BEAM 更接近早期 32k 时代 |
| **LongMemEval** | 聊天助手长期记忆：信息抽取、跨 session 推理、时间推理、知识更新、拒答/偏好等；AMB cleaned 数据集拆为 6 类 | AMB split `s`，每个问题有独立 haystack sessions | 更接近通用 chat assistant / enterprise assistant 场景 |
| **PersonaMem** | 长期用户画像和动态偏好：跨多轮/多 session 记住事实与偏好、识别最新偏好、迁移偏好、推荐、解释偏好演进 | AMB split `32k/128k/1M`；任务是 4 选 1 response selection | 检验推荐、用户理解、个性化回复 |
| **sde-bench** | Memory 是否提升 coding agent 修复真实 bug 的能力；正确修复必须通过 hidden test，而不是复述记忆 | Boltons 代码库 bug-fix tasks；决策来自 git history 或过去 developer conversation，另含 decoy conversations/commits | 检验工程 Agent 的跨会话项目知识、陈旧决策避免和噪声检索 |
| **PrecisionMemBench** | 检索精度：断言哪些 memory 必须返回、哪些不能返回；噪声也算失败 | retrieval-only 模式，没有 answer LLM/judge | 检验企业场景最重要的“不要乱带上下文” |

Hindsight README 的性能图称其为 LongMemEval SOTA，并说明 Hindsight 分数由 Virginia Tech Sanghani Center 与 The Washington Post 独立复现、其他厂商分数自报。Hindsight 的 `hindsight-system-evals` README 进一步确认 LoComo、LongMemEval、BEAM、PersonaMem、sde-bench 由 AMB 管理数据集、prompt、judge 和 scoring。

交叉验证结论：

1. **口径一致**：Hindsight 仓库、AMB README、AMB dataset adapters 均指向同一套数据集与任务。
2. **中性程度有限**：AMB 是 Vectorize/Hindsight 团队维护的开放 benchmark，流程开放且可复现，但不是完全第三方组织主办。
3. **分数不能跨榜乱比**：accuracy 受 dataset split、backbone LLM、judge、prompt、版本和运行时间影响。企业选型仍要用自有业务数据做同口径复测。
4. **这些基准测 memory quality，不直接证明数据库性能**：它们衡量召回、更新、拒答、精度和 Agent 任务成功率；TPS、QPS、并发、备份恢复和 RPO/RTO 需要另行压测。

来源：

- AMB 机制与指标：`https://github.com/vectorize-io/agent-memory-benchmark/blob/main/README.md:3-28`，AMB latest commit `03c1d0f1d27da63034f0931121c858faba512383`
- BEAM 适配器：`agent-memory-benchmark/src/memory_bench/dataset/beam.py:1-112`
- LifeBench 适配器：`agent-memory-benchmark/src/memory_bench/dataset/lifebench.py:1-89`
- LoCoMo 适配器：`agent-memory-benchmark/src/memory_bench/dataset/locomo.py:1-70`
- LongMemEval 适配器：`agent-memory-benchmark/src/memory_bench/dataset/longmemeval.py:1-71`
- PersonaMem 适配器：`agent-memory-benchmark/src/memory_bench/dataset/personamem.py:1-58`
- sde-bench 适配器：`agent-memory-benchmark/src/memory_bench/dataset/sdebench.py:62-110`
- Hindsight 使用 AMB：`hindsight/hindsight-system-evals/README.md:229-258`
- Hindsight 独立复现声明：`hindsight/README.md:42-52`

---

## 3. 选型对比

### 3.1 2026-09-28 GitHub 元数据快照

| 仓库 | Stars | License | 最近 Push | 选型判断 |
|---|---:|---|---|---|
| `mem0ai/mem0` | 66,171 | Apache-2.0 | 2026-09-25 | 记忆层强；知识层需组合 |
| `HKUDS/LightRAG` | 39,896 | MIT | 2026-09-27 | 知识层强；支持 PG 全栈 |
| `vectorize-io/hindsight` | 39,254 | MIT | 2026-09-28 | **首选**；Memory + Knowledge，PG-first |
| `volcengine/OpenViking` | 38,853 | AGPL-3.0 | 2026-09-28 | 方向相关；License 风险高 |
| `getzep/graphiti` | 31,242 | Apache-2.0 | 2026-09-27 | KG 强；非 PG-first |
| `topoteretes/cognee` | 31,107 | Apache-2.0 | 2026-09-27 | PG 图为 demo，不宜作 MVP 核心 |
| `supermemoryai/supermemory` | 30,965 | MIT | 2026-09-25 | 嵌入式 self-host，非 RDS PG-central |
| `letta-ai/letta` | 24,937 | Apache-2.0 | 2026-09-10 | 源码迁移至 `letta-code`；平台属性强 |

### 3.2 综合评分

评分 1–5，5 表示对当前目标最合适。该评分反映华为云 5 人团队、2–3 个月 MVP、PG-first、Memory + Knowledge、商用可控五个约束，不是通用排行榜。

| 项目 | PG 适配 | Memory + Knowledge | MVP 工作量 | 商用 License | 社区活跃 | 综合建议 |
|---|---:|---:|---:|---:|---:|---|
| Hindsight | 5 | 5 | 3 | 5 | 5 | 首选 |
| Mem0 + LightRAG | 4 | 4 | 2 | 5 | 5 | 备选 |
| Cognee | 3 | 4 | 2 | 5 | 4 | 不建议 MVP |
| OpenViking | 需复核 | 5 | 3 | 2 | 5 | 只作参考 |
| Graphiti | 2 | 3 | 2 | 5 | 4 | 参考 |
| Supermemory | 2 | 4 | 2 | 5 | 4 | 参考 |

---

## 4. 关键证据索引

> 以下行号基于 2026-09-28 本地快照。上游代码更新后，请按文件路径重新核对。

### 4.1 Hindsight

本地快照 commit：`ccfe85b4851957ac2adf88b4a9ddf9668b2882f1`

| 结论 | 证据 |
|---|---|
| PostgreSQL-first；企业版另有 Oracle | `hindsight-docs/docs/developer/storage.md:3` |
| 使用 pgvector、tsvector、JSONB、Recursive CTE | `hindsight-docs/docs/developer/storage.md:9-15` |
| 明确避免通用存储抽象 | `hindsight-docs/docs/developer/storage.md:27-39` |
| 生产要求 PostgreSQL 15+、pgvector 0.5.0+ | `hindsight-docs/docs/developer/storage.md:70-77` |
| Mental Models REST API | `hindsight-docs/static/openapi.json:1668,1875,2100,2166,2234,2302` |
| Knowledge Base REST API | `hindsight-docs/static/openapi.json:2370,2432,2501,2570,2632,2720,2788` |
| Knowledge Page 创建与 mental model + tree node 相关 | `hindsight-docs/static/openapi.json:2507` |
| 管理操作主要通过 `hindsight-admin` CLI | `hindsight-docs/docs/developer/admin-cli.md:520-526` |
| 多租户属于扩展点，不是开箱企业控制台 | `hindsight-docs/docs/developer/extensions.md:9-15` |

仓库：<https://github.com/vectorize-io/hindsight>

### 4.2 Cognee

| 结论 | 证据 |
|---|---|
| PG 图适配器明确为 DEMO / not production-ready | `cognee/cognee/infrastructure/databases/graph/postgres_demo/adapter.py:1-10` |
| pgvector 适配器存在 | `cognee/cognee/infrastructure/databases/vector/pgvector/PGVectorAdapter.py:70` |

仓库：<https://github.com/topoteretes/cognee>

### 4.3 Mem0 与 LightRAG

| 结论 | 证据 |
|---|---|
| Mem0 当前 `MemoryConfig` 未见 graph 配置 | `mem0/mem0/configs/base.py:29-58` |
| Mem0 v3 迁移说明 graph memory 行为变化 | `mem0/docs/migration/oss-v2-to-v3.mdx:26-29` |
| LightRAG README 推荐生产使用 PostgreSQL，可承担 KV / Vector / DocStatus / Graph | `LightRAG/README.md:359-366` |
| LightRAG PG 向量索引用 HNSW 等 | `LightRAG/lightrag/kg/postgres_impl.py:2636-2674` |
| LightRAG 对 AGE 1.7.0 有版本门禁，并提示更高版本存在 crash/SIGSEGV 风险 | `LightRAG/lightrag/kg/postgres_impl.py:1144-1160` |
| LightRAG 提供纯 PG 表图存储 | `LightRAG/lightrag/kg/pgtable_impl.py:267` |

仓库：

- Mem0：<https://github.com/mem0ai/mem0>
- LightRAG：<https://github.com/HKUDS/LightRAG>

### 4.4 其他项目

| 结论 | 证据 |
|---|---|
| Graphiti 支持后端包括 Neo4j / FalkorDB / Neptune / OpenSearch / Kuzu | `graphiti/README.md:159,280,632` |
| Supermemory self-hosting 为单个自包含二进制 | `supermemory/apps/docs/self-hosting/overview.mdx:5` |
| Supermemory 描述无需外置数据库并使用嵌入式图引擎 | `supermemory/apps/docs/self-hosting/overview.mdx:23-31` |
| Letta README 指向 `letta-ai/letta-code` | `letta/README.md:5-7` |
| Letta 旧仓库提醒不要使用 archive/old server 做生产或基准 | `letta/AGENTS.md:7-33` |
| OpenViking License 为 AGPL-3.0 | `OpenViking/LICENSE:637-644` |

---

## 5. 华为云 ContextDB MVP 方案

### 5.1 架构

```text
Agent / SDK / MCP Client
          │
          ▼
Huawei Cloud API Gateway / IAM
          │
          ▼
ContextDB Service Plane
┌──────────────────────────────────────────────┐
│  Session / Tenant Router                     │
│  Memory API: retain / recall / update        │
│  Reflect API: summarize / mental model       │
│  Knowledge API: pages / tree / promotion     │
│  Governance: ACL / audit / quota / redaction │
└──────────────────────────────────────────────┘
          │
          ▼
Huawei Cloud RDS PostgreSQL
  pgvector + tsvector + JSONB + Recursive CTE
          │
          ▼
Model Gateway
  Pangu / OpenAI-compatible Embedding & LLM
```

### 5.2 分阶段落地

| 阶段 | 目标 | 关键动作 |
|---|---|---|
| 第 1–2 周 | 技术验证 | 部署 Hindsight；验证 RDS PG 版本、`pgvector`、`tsvector`、JSONB、Recursive CTE；跑通 retain / recall / reflect / Knowledge Page |
| 第 3–6 周 | 云服务最小闭环 | 对接 IAM；实现租户隔离、审计、配额、限流、模型网关；确定数据模型和 API 契约 |
| 第 7–10 周 | 治理与质量 | 完成备份恢复、监控告警、KMS、PII / 密敏信息处理、知识晋升审批、多租户压测与安全测试 |
| 第 11–12 周 | Beta | 输出 REST / SDK / MCP 文档；完成成本模型、SLA、灰度与典型业务评测 |

### 5.3 技术边界与风险

| 风险 | 判断 | 缓解 |
|---|---|---|
| Hindsight 无开箱企业管理控制台 | 属实，多租户主要是扩展点 | 自研控制面，使用其 TenantExtension 集成华为云 IAM |
| Hindsight 无原生 AGE | 属实 | 一期不依赖 AGE；用 PG Recursive CTE / relational graph 满足 MVP |
| 社区增长快但项目较新 | 属实 | 锁定 release/tag，建立兼容性与回归测试，必要时维护内部分支 |
| “支持 PG 图”容易被误解为 AGE | 需明确 | 对内明确：Hindsight 使用 PG relational graph + Recursive CTE，不依赖 AGE |
| 性能基准多为项目论文/厂商叙事 | 未经本团队复现 | 用真实业务负载和 LongMemEval 等数据集做独立评测 |
| Mem0 + LightRAG 组合成本被低估 | 常见风险 | 若选择该路线，先做统一数据模型与治理面原型，不先写业务功能 |
| OpenViking AGPL | 商用受限 | 只做能力参考，不复制代码；如需集成先法务评审 |

---

## 6. 最终建议

1. **立即启动 Hindsight POC**，验证其 Memory + Knowledge 能力在华为云 RDS PG 上的部署、召回质量和多租户扩展点。
2. **不要把 AGE 作为 MVP 阻塞项**。Hindsight 的核心路径是 PostgreSQL-first，不要求 AGE。
3. **把云产品投入放在控制面**：租户、IAM、审计、配额、计费、备份恢复、监控、模型网关、知识治理。
4. **保留 Mem0 + LightRAG 作为备选**，但不要因为组件流行就默认组合成本低。
5. **OpenViking 只做能力对标，不直接商用集成**，除非完成 AGPL 合规评审。
6. **在两周内完成三项硬验证**：
   - Huawei Cloud RDS PG 是否满足 PostgreSQL 15+ 与 `pgvector 0.5.0+`；
   - Hindsight Knowledge Pages 是否满足目标知识管理场景；
   - Hindsight TenantExtension 是否能承接华为云租户与 IAM 模型。

---

## 7. 后续可继续深化的工作

1. 输出 Hindsight 在华为云上的部署拓扑图与容量模型。
2. 核对华为云 RDS PG 当前可用的扩展、版本与参数白名单。
3. 基于 LongMemEval 与真实业务数据，对 Hindsight、Mem0 + LightRAG 做同口径压测。
4. 阅读 Hindsight `TenantExtension` 源码，设计华为云 IAM / 项目 / 企业子账号映射。
5. 设计知识晋升状态机：候选、评审、生效、版本化、失效、撤销。
6. 准备正式安全与合规评审，特别是 License、数据跨境、PII 和企业隔离。
