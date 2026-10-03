# Agent Memory 开源选型与华为云 ContextDB 可行性报告

> 调研日期：2026-09-22  
> 调研方式：源码阅读 + 官方产品页/文档抽取 + GitHub API 指标 + TencentDB Agent Memory 干净 HEAD 验证  
> 适用团队：3–5 人数据库/平台团队  
> 目标：在华为云实现类似阿里云 RDS ContextDB、火山引擎 OpenViking Context、腾讯云 Agent Memory 的 Context / Agent Memory 服务。

## 1. 执行结论

### 1.1 总判断

**不建议 3–5 人团队整仓 fork 任何一个项目后直接商业化。** 更稳妥的路线是：

1. **自建产品控制面**：Workspace、Member、API Key、ACL、审计、配额、计费、实例、备份、监控必须自研，这是云产品壁垒，也是所有候选开源项目的共同缺口。
2. **Cognee 作为首选知识/图谱底座候选**：Apache-2.0、能力覆盖广、测试和 CI 较完整、活跃度高，且已有 tenant / role / permission 代码与测试。但要避免直接依赖其“Postgres 作为图存储”的 demo 特性；该能力官方标注为 demo，生产能力是商业授权项。
3. **Mem0 作为记忆 API 与记忆内核参考/可替换引擎**：社区最大、接入成本最低，OSS 能覆盖事实抽取、去重、向量检索和 `user_id / agent_id / run_id` 作用域；但 OSS 明确没有 Graph Memory，企业控制面也需要自研。
4. **Graphiti 作为时间知识图谱模块**：适合做“事实什么时候有效、何时失效、来源是什么”的图谱引擎，支持 Neo4j、FalkorDB、Kuzu、Neptune 等后端；但它不是完整 ContextDB 产品。
5. **TencentDB Agent Memory 作为最强架构参考和部分 MIT 代码来源**：开源版覆盖 L0–L3、Chat Memory / Skill / Wiki / CodeGraph、混合检索、ACL，是最接近目标产品形态的 MIT 项目之一；但当前仓库自身测试为 0，干净 HEAD 的 `MemoryProxy` typecheck 失败，且 TCVDB 适配与腾讯云绑定较深，不建议整仓直接作为生产底座。
6. **OpenViking 只做产品对标，不建议复用主项目代码**：产品形态和多租户/ACL 最完整，但主项目 AGPL-3.0；如果华为云商业服务修改后对外提供，需要承担网络服务源代码披露义务，必须先法务确认。除非明确接受 AGPL，否则应避免引入代码。

### 1.2 对 TencentDB Agent Memory 的专项回答

**TencentDB Agent Memory 能支撑我们做“类 ContextDB”的原型和大部分数据面设计，但不能直接等价于阿里 ContextDB 的完整商业产品。**

| 问题 | 结论 | 证据摘要 |
|---|---|---|
| 是否有记忆整理 | **有** | L0 Conversation → L1 Atom → L2 Scenario → L3 Persona；L1 有冲突检测与 merge，L2 有 SceneExtractor，L3 有 PersonaGenerator。 |
| 是否有知识图谱 | **有，但偏 Wiki Link Graph 与 CodeGraph，不是完整通用时间知识图谱** | Wiki 使用 FTS5 + `graph_edge` + BFS 多跳；CodeGraph 覆盖符号、调用、影响路径。缺少 Graphiti 那种事实有效期、失效时间、来源追踪模型。 |
| 是否有知识晋升 | **没有找到通用“记忆晋升”工作流** | 阿里 ContextDB 官方文档明确定义“记忆成文 + 事实校验 + 质量审核 + 知识评审”；Tencent 开源仓库检索 `知识晋升 / 晋升 / promotion` 无命中。它有 Skill 提取、Wiki/CodeGraph ingest、资产审核，但不等价于记忆自动晋升为知识文档。 |
| 是否可直接支撑华为云商业化 | **不建议直接整仓使用** | 需要补测试、修 typecheck、替换/抽象 TCVDB、补云控制面、备份/回档、配额计费、SLA 与安全合规。 |

更具体地说：

- **可以借鉴/选择性复用**：L0–L3 管线、L1 冲突检测、L2 SceneExtractor、L3 PersonaGenerator、Memory Asset 模型、permission-checker、Wiki BM25 + graph BFS、CodeGraph API 设计。
- **必须自研或替换**：华为云 IAM/租户模型、实例与配额、计费、审计、备份回档、知识晋升、知识评审、夜间整理调度、通用实体关系时间图谱、跨云存储抽象。
- **必须先修复再考虑作为底座**：补单元/集成/隔离/回归测试；修复 TypeScript 类型错误；建立迁移机制；补 SECURITY.md 与安全流程。

## 2. 目标产品基线：阿里 RDS ContextDB

阿里 ContextDB 是最清晰的验收基线。其官方快速入门将它定义为“面向 Agent 的企业级上下文数据库服务”，提供多源接入、提炼与资产化、检索与组合、治理与演进、权限控制和服务化供给。见 `official/aliyun-contextdb.txt:44`–`57`。

关键能力：

- **Context Growth Loop**：记录—组织—召回与组合—执行反馈—评估演进，见 `official/aliyun-contextdb.txt:72`–`79`。
- **图谱与夜间演进**：上下文以图谱存储，支持增量更新、关系推理，并通过夜间服务处理冗余与冲突，见 `official/aliyun-contextdb.txt:96`–`99`。
- **Workspace / API Key / 权限隔离**：不同 workspace 权限隔离，同一 API Key 的上下文可跨 Agent 共享，支持知识库级别权限，见 `official/aliyun-contextdb.txt:98`–`109`。
- **记忆整理**：自动更新实体属性、归档冲突记忆、合并重复关系、调整热度与归档状态，见 `official/aliyun-contextdb.txt:490`–`495`。
- **记忆晋升**：把 Agent 使用中沉淀的记忆整理为团队可复用知识，由多个 Agent 角色完成资料检索、事实校验、文档写作、质量审核和风险标记，见 `official/aliyun-contextdb.txt:496`–`501`。
- **知识评审**：质量评估、自矛盾检测、置信度计算、自动入库或人工审核，见 `official/aliyun-contextdb.txt:549`–`563`。
- **管理面**：成员、API Key、审计、用量，见 `official/aliyun-contextdb.txt:619`–`630`。

因此，华为云版本的最小可商用边界不应只是“向量记忆库”，而应包含：**记忆 + 知识 + 图谱 + 整理/晋升 + 租户治理 + 审计计费**。

## 3. 候选项目总体对比

### 3.1 定位与核心能力

| 项目 | 实际定位 | 核心能力 | 关键缺口 |
|---|---|---|---|
| **Mem0** | 记忆 SDK / 记忆服务内核 | LLM 事实抽取、去重、更新、向量检索、实体匹配；OSS 支持 `user_id / agent_id / run_id` 作用域 | OSS 无 Graph Memory；自托管服务有用户/API Key/请求日志，但缺 workspace、ACL、配额、计费 |
| **Letta Code** | 有状态 Agent harness，不是 ContextDB 数据面底座 | memory blocks、self-improvement、sleeptime、MemFS、skills、subagents | 目标是运行 Agent，不是给多租户提供记忆数据库服务 |
| **Zep** | 当前仓库是 Zep Cloud 示例与集成仓库 | Cloud SDK 示例、集成、benchmark、ingestion 工具 | 仓库明确“不是 Zep 产品或服务”；Community Edition 已 deprecated |
| **Graphiti** | 时间知识图谱框架 | 实体、关系、事实、episode 来源追踪；事实有效期；混合检索；多图数据库后端 | 不是完整记忆产品；租户控制面、知识库治理、计费审计需自研 |
| **Cognee** | AI memory / knowledge graph platform | 文档、代码、对话转为图谱；多租户、角色、权限；多搜索类型；Docker/API/UI/MCP | 架构较宽、定制成本高；Postgres 图存储生产能力为商业授权项 |
| **MemOS** | Memory OS / 记忆调度框架 | API Key auth、MemScheduler、Dream 异步整理、图数据库抽象、中文支持 | Dream beta 且默认关闭；控制面与企业多租户治理不完整 |
| **MemoBase** | 用户画像长期记忆系统 | 用户 profile、buffer flush、中文 prompt、画像合并 | 偏画像场景；近 8 个月无提交；不适合作为完整 ContextDB 底座 |
| **LangMem** | LangGraph 记忆工具库 | hot path tools、background memory manager、prompt refinement | 库而非服务；深度绑定 LangGraph 生态 |
| **A-MEM** | 研究型动态记忆组织系统 | Zettelkasten、ChromaDB、links、memory evolution | 无服务端、无 CI、无生产多租户设计 |
| **OpenViking** | 最接近 Context Database 的开源产品 | `viking://` 统一资源/记忆/技能文件系统、L0/L1/L2、多租户 identity、ACL、API Key、商业 SaaS/BYOC | 主项目 AGPL-3.0，商业云服务复用代码有强合规约束 |
| **TencentDB Agent Memory** | 面向 Agent 团队的 Memory Hub / 记忆底座 | L0–L3、Chat Memory、Skill、Wiki、CodeGraph、BM25+向量+RRF、ACL、Proxy 接入 | 仓库无自身测试；干净 HEAD typecheck 失败；TCVDB/腾讯云耦合；无通用知识晋升 |

### 3.2 社区与工程化矩阵

数据口径：

- GitHub 指标来自 2026-09-22 GitHub API 快照；`open issues` 包含 issues + PRs。
- 测试文件数为排除 `node_modules / dist / build / target / .venv` 后的 `test_*.py / *_test.py / *.test.ts / *.test.js / *.spec.ts / *.spec.js / test_*.rs` 数量。
- `contributors` 为 GitHub API 第一页最多返回的 listed contributors，不是严格全量。

| 项目 | Stars | Forks | Open issues+PRs | 30d commits | Contributors | Last push | License | 测试文件 | CI workflows | Docker/Compose | SECURITY.md |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---|
| Mem0 | 65,781 | 7,726 | 766 | 33 | 100 | 2026-09-21 | Apache-2.0 | 299 | 34 | 2/0 | 有 |
| Letta Code | 3,394 | 415 | 394 | 100+ | 51 | 2026-09-21 | Apache-2.0 | 857 | 17 | 1/0 | 无 |
| Zep | 4,924 | 653 | 39 | 3 | 18 | 2026-09-18 | Apache-2.0 | 118 | 9 | 2/1 | 有 |
| Graphiti | 31,057 | 3,159 | 517 | 34 | 63 | 2026-09-21 | Apache-2.0 | 62 | 12 | 3/5 | 有 |
| Cognee | 30,888 | 3,079 | 490 | 100+ | 100 | 2026-09-21 | Apache-2.0 | 882 | 59 | 6/1 | 有 |
| MemOS | 11,508 | 1,052 | 88 | 87 | 100 | 2026-09-21 | Apache-2.0 | 395 | 12 | 4/2 | 有 |
| MemoBase | 2,911 | 235 | 34 | 0 | 15 | 2026-01-11 | Apache-2.0 | 10 | 1 | 2/1 | 无 |
| LangMem | 1,678 | 190 | 66 | 6 | 13 | 2026-09-09 | MIT | 3 | 2 | 0/0 | 无 |
| A-MEM | 1,182 | 123 | 20 | 0 | 6 | 2025-12-12 | MIT | 3 | 0 | 0/0 | 无 |
| OpenViking | 38,332 | 2,979 | 707 | 100+ | 100 | 2026-09-21 | AGPL-3.0 | 835 | 26 | 5/4 | 有 |
| TencentDB Agent Memory | 27,098 | 2,596 | 817 | 29 | 21 | 2026-09-21 | MIT（仓库自定义 MIT 文件，GitHub API 标记 NOASSERTION） | 0 | 1 | 6/1 | 无 |

### 3.3 加权评分

评分维度与权重：

| 维度 | 权重 | 评分含义 |
|---|---:|---|
| 核心能力 | 20% | 记忆、图谱、知识、整理、检索、资产化 |
| 产品形态契合度 | 15% | 是否像 ContextDB 数据面/服务，而非只是 SDK 或研究 demo |
| 社区生态 | 5% | Stars、贡献者、集成生态 |
| 活跃度 | 5% | 近 30 天提交、最后 push |
| 协议合规 | 15% | 商业云服务复用风险 |
| 中文支持 | 10% | 中文文档、中文 prompt、中文分词/检索适配 |
| 维护难度 | 10% | 架构复杂度、测试、CI、迁移、安全 |
| 多租户生产可行性 | 10% | 租户隔离、ACL、认证、审计、运维 |
| 后续升级 | 5% | 作为依赖/局部复用的可跟踪性 |

| 项目 | 核心 | 产品契合 | 社区 | 活跃 | 协议 | 中文 | 维护 | 多租户 | 升级 | 加权分 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Cognee** | 5 | 4 | 5 | 5 | 5 | 3 | 3 | 3 | 4 | **3.95** |
| **TencentDB Agent Memory** | 5 | 4 | 4 | 4 | 5 | 5 | 2 | 2 | 2 | **3.75** |
| **OpenViking** | 5 | 5 | 5 | 5 | 1 | 5 | 2 | 4 | 4 | **3.70** |
| **Graphiti** | 4 | 3 | 5 | 4 | 5 | 2 | 4 | 3 | 4 | **3.55** |
| **MemOS** | 4 | 3 | 4 | 4 | 5 | 5 | 3 | 2 | 3 | **3.55** |
| **Mem0** | 4 | 3 | 5 | 5 | 5 | 2 | 4 | 2 | 4 | **3.50** |
| **Letta Code** | 3 | 2 | 3 | 5 | 5 | 2 | 3 | 1 | 3 | **2.80** |
| **MemoBase** | 3 | 2 | 2 | 1 | 5 | 5 | 2 | 2 | 1 | **2.75** |
| **LangMem** | 3 | 1 | 2 | 2 | 5 | 1 | 4 | 1 | 2 | **2.40** |
| **Zep** | 2 | 1 | 3 | 2 | 5 | 1 | 2 | 1 | 1 | **2.00** |
| **A-MEM** | 2 | 1 | 2 | 1 | 5 | 1 | 2 | 1 | 1 | **1.90** |

解读：

- **Cognee 技术与工程均衡性最好**，适合作为主底座候选。
- **Tencent 能力形态最贴近目标**，但工程质量和跨云适配拖累直接生产可行性。
- **OpenViking 产品完成度最高**，但 AGPL 是商业云服务的硬约束。
- **Mem0 / Graphiti 更适合作为可替换模块**，而不是整仓底座。

## 4. 关键候选逐项分析

## 4.1 Mem0：短期记忆 API 首选，不能承担完整 ContextDB

### 优点

- **社区最大、接入最快**：65,781 stars、299 个测试文件、34 个 workflow，近期持续提交。
- **核心记忆链路成熟**：官方文档说明写入时先查相关记忆，再由 LLM 抽取事实，去重后向量化，见 `mem0/docs/core-concepts/how-it-works.mdx:46`–`49`。
- **作用域模型简单清晰**：`add()` 接受 `user_id / agent_id / run_id`，并要求至少一个 ID；`search()` 与 `get_all()` 通过 filters 限定同一组作用域，见 `mem0/mem0/memory/main.py:760`–`802`。
- **自托管服务已有基础账号体系**：`User`、`APIKey`、`RequestLog`，见 `mem0/server/models.py:18`–`52`。

### 限制

- **OSS 无 Graph Memory**：官方文档明确，Platform 的实体信号由内置 Graph Memory 支持，OSS 只依赖向量库和 reranker，实体重叠 boost，没有 graph memory，见 `mem0/docs/core-concepts/how-it-works.mdx:49`、`:64`。
- **不是企业多租户控制面**：没有 Workspace、团队、角色、ACL、配额、计费、审计完整模型。
- **中文支持弱**：仓库内几乎没有中文文档或中文 prompt。

### 建议

采用方式：**借鉴 API 语义 + 作为可替换 Memory Engine**。短期可以引入 `mem0ai` 包快速上线记忆写入/检索，但不要把 Mem0 内部 schema 暴露成华为云产品的公开契约。公开 API 应自研，底层通过 adapter 调 Mem0、自研或 Cognee。

## 4.2 Letta Code：Agent harness，不适合作为 ContextDB 数据面

Letta Code 的 README 将其定义为“stateful agent harness”，Agent 有 memory、identity、experience，并通过重写 memory、skills、prompts 和 harness 自我进化，见 `letta-code/README.md:5`。

其核心能力是：

- self-improvement、memory blocks、sleeptime、skill learning，见 `letta-code/README.md:22`。
- MemFS 将 context 通过 git 跟踪，见 `letta-code/README.md:24`。
- Skills、subagents、channels、hooks、permissions、schedules，见 `letta-code/README.md:25`–`30`。

这些能力面向“运行一个 Agent”，而不是“给外部多租户 Agent 提供记忆数据库服务”。如果目标是 ContextDB 数据面，Letta Code 更适合作为客户端/Agent 侧集成对象，而不是服务底座。

## 4.3 Zep：当前开源仓库不能选，Graphiti 才是开源部分

当前 `getzep/zep` 仓库明确声明：“This repository is not Zep's product or service”，它只包含 Zep Cloud 示例、框架集成和工具，见 `zep/README.md:17`–`31`。

同时，Zep Community Edition 已 deprecated，代码移入 `legacy/`，不再支持，见 `zep/README.md:66`–`69`。

因此：

- 不应把当前 Zep 仓库当作自托管产品选型对象。
- 若需要 Zep 的开源时间图谱能力，应评估 **Graphiti**。
- 若评估 Zep Cloud，则是商业 SaaS 选型，不符合“借开源快速上线”的目标。

## 4.4 Graphiti：时间知识图谱引擎，建议作为可替换图谱模块

Graphiti 将自己定义为构建和查询 AI Agent temporal context graphs 的框架，跟踪事实变化、保留来源、支持 ontology，并支持增量更新与历史查询，见 `graphiti/README.md:37`–`50`。

核心价值：

- **事实有效期**：边模型包含 `expired_at / valid_at / invalid_at / reference_time`，见 `graphiti/graphiti_core/edges.py:271`–`280`。
- **多租户分区字段**：边模型包含 `group_id`，见 `graphiti/graphiti_core/edges.py:51`。
- **多数据库后端**：官方 README 列出 Neo4j、FalkorDB、Kuzu、Amazon Neptune Database / Neptune Analytics，见 `graphiti/README.md:631`–`633`。
- **服务与 MCP 生态**：仓库包含 `server/`、`mcp_server/`、Docker Compose 和相应测试 workflow。

限制：

- 不是完整记忆产品，没有云控制面、知识库治理、晋升、审计、计费。
- 中文支持弱，需要自行补中文分词、实体抽取和评测。

建议：将 Graphiti 作为 **Temporal Graph Engine adapter**，用于实体关系、事实演化、冲突与来源追踪；不要把它当唯一存储，也不要直接暴露其内部图模型。

## 4.5 Cognee：主底座首选，但注意商业版能力边界

### 优点

- **能力覆盖最均衡**：README 定义为“AI memory platform”，将文档、代码、对话转为自托管知识图谱，见 `cognee/README.md:42`–`44`；其能力表覆盖 add、cognify、search、improve、feedback，见 `cognee/README.md:168`–`184`。
- **多租户与权限有代码和测试**：测试覆盖不同用户 dataset 隔离、无权限访问抛 `PermissionDeniedError`、创建 tenant/role、跨 tenant 数据可见性，见 `cognee/cognee/tests/test_multi_tenancy.py:51`–`79`、`:81`–`110`、`:114`–`136`。
- **搜索类型丰富**：`SearchType` 包含 RAG、Hybrid、Graph、Temporal、Code 等类型，见 `cognee/cognee/modules/search/types/SearchType.py:4`。
- **部署形态较完整**：提供 Docker Compose API/UI/MCP，默认端口 API 8000、UI 3000、MCP 8001，见 `cognee/README.md:250`–`256`。
- **工程化好**：882 个测试文件、59 个 workflow、Apache-2.0、活跃度高。

### 风险

- **Postgres 图存储生产能力不是纯开源能力**：README 明确说“run the whole memory layer on a single Postgres instance”中，Postgres 作为 graph store 是 demo feature，production ready feature 是 licensed product，见 `cognee/README.md:260`–`264`。华为云版本应使用其支持的独立图数据库后端，或自研 graph adapter，不能默认该能力免费生产可用。
- 架构宽、模块多，3–5 人团队若深度 fork，维护压力会显著上升。
- 中文支持中等，需要补中文分词、中文评测和中文 prompt。

### 建议

**将 Cognee 作为主底座候选，但采用“依赖 + adapter + 自研控制面”的方式，不做深度 fork。** 如果团队更看重快速上线简单记忆服务，可先用 Mem0；如果目标是类 ContextDB 的图谱和知识能力，Cognee 的综合契合度更高。

## 4.6 MemOS：中文与记忆调度有优势，Dream 仍偏 beta

MemOS 的 API Key 中间件从 PostgreSQL 读取 SHA-256 哈希，验证 key、scope、过期和 active 状态，并更新 last_used_at，见 `MemOS/src/memos/api/middleware/auth.py:1`–`6`、`:84`–`129`。

但需要注意：

- `AUTH_ENABLED` 默认是 `false`，见 `MemOS/src/memos/api/middleware/auth.py:25`–`28`。
- Dream 是 optional community feature，currently beta，默认关闭，见 `MemOS/src/memos/dream/README.md:3`–`12`。
- Dream 当前能力包括信号捕获、scheduler 执行、manual trigger、diary 查询、Context 合并，见 `MemOS/src/memos/dream/README.md:28`–`45`。
- Beta 限制包括信号存内存、重启丢失；触发策略简单；update/merge/archive/long-term maintenance 只是扩展方向，不是完整产品行为，见 `MemOS/src/memos/dream/README.md:106`–`114`。

建议：**借鉴 MemOS 的调度、Dream 和中文 prompt 设计，不建议作为主底座。** 其社区和工程化不错，但企业多租户治理与产品完整性仍需大量补齐。

## 4.7 MemoBase：中文画像强，但项目停滞

MemoBase 的核心是用户画像长期记忆：

- 用户数据以 blob 插入，处理后默认删除原文，可通过配置持久化，见 `memobase/README.md:228`–`247`。
- Buffer 达到阈值或空闲一段时间后 flush，也可手动 flush，见 `memobase/README.md:276`–`280`。
- `profile()` 返回结构化 topic / sub_topic / content，见 `memobase/README.md:259`–`273`。
- 中文 prompt 支持较好，例如 `zh_user_profile_topics.py`、`zh_merge_profile.py`、`zh_extract_profile.py`。

风险：

- 最后 push 为 2026-01-11，近 30 天 0 commits。
- 只有 10 个测试文件、1 个 workflow。
- 专注用户画像，不是完整 ContextDB。

建议：**借鉴中文画像主题与合并 prompt，不作为底座。**

## 4.8 LangMem：工具库，不是服务

LangMem README 明确其提供：

- 可用于任意存储系统的 functional primitives，见 `langmem/README.md:5`–`8`。
- hot path memory tools，见 `langmem/README.md:13`–`15`。
- 与 LangGraph storage 的原生集成，见 `langmem/README.md:16`。

它适合作为 LangGraph 应用的记忆工具，但不是独立多租户服务底座。若我们的公开 API 不绑定 LangGraph，不建议引入为核心依赖。

## 4.9 A-MEM：研究项目，不用于生产

A-MEM 的核心是：

- Zettelkasten 动态记忆组织、ChromaDB 索引和链接、记忆进化，见 `A-mem/README.md:23`–`30`。
- 新记忆加入时生成结构化 note、描述、tag、历史连接和动态更新，见 `A-mem/README.md:40`–`47`。

但它没有服务端、CI、Docker、多租户、安全治理，且近 30 天 0 commits。只适合研究 dynamic memory organization，不适合生产。

## 4.10 OpenViking：产品对标最强，主项目 AGPL 是硬风险

### 产品能力

OpenViking 的产品思想非常值得对标：

- **统一 `viking://` 虚拟文件系统**：资源、记忆、技能统一 URI，Agent 可 `ls / tree / read / write / grep`，见 `openviking/README_CN.md:43`–`61`。
- **L0 / L1 / L2**：摘要、概览、详情，见 `openviking/README_CN.md:88`–`105`。
- **生产部署与多租户**：README 明确服务器支持账号与用户隔离、资源 ACL、身份认证，见 `openviking/README_CN.md:252`–`256`。
- **商业版本**：SaaS 由火山引擎托管，私有化支持 BYOC / 离线部署和官方支持，见 `openviking/README_CN.md:258`–`275`。

### 源码能力

- `ResolvedIdentity` / `RequestContext` 支持 account、user、actor peer、api key，见 `openviking/openviking/server/identity.py:77`–`112`。
- API Key 插件通过 `APIKeyManager.resolve()` 解析身份，并清除不可信身份 header，见 `openviking/openviking/server/auth/plugins/api_key.py:56`–`105`。
- ACL 路由支持 set/delete/grant/revoke，见 `openviking/openviking/server/routers/acl.py:61`–`110`。

### 许可证风险

README 明确主项目是 AGPLv3，CLI crates 和 examples 是 Apache 2.0，见 `openviking/README_CN.md:329`–`335`。

对华为云商业服务而言，如果修改 AGPL 服务端并对外提供网络服务，通常需要向网络用户提供对应源代码。除非法务明确接受该义务，否则不能把主项目代码混入闭源或专有云服务实现。

### 建议

**只做产品与 API 对标，不复用主项目代码。** 可以学习：

- `viking://` 资源抽象。
- L0/L1/L2 分层读取。
- Memory / Knowledge / Skill 统一资产模型。
- 多租户 identity + ACL 设计。
- 控制台与 MCP 接入体验。

## 4.11 TencentDB Agent Memory：能力最贴近，但工程质量是硬伤

### 开源版能力

#### 4.11.1 L0–L3 记忆分层

README 明确：

- L0 Conversation：原始对话与完整上下文。
- L1 Atom：事实、偏好、约束、事件。
- L2 Scenario：围绕项目或场景组织的知识块。
- L3 Core / Persona：长期画像、稳定模式与高层认知。

见 `TencentDB-Agent-Memory/README_CN.md:250`–`257`。

异步管线实现：

- Pipeline 注释说明 L1 数据按 `(team, user, agent, session)` 隔离；L2 写 scene_blocks 共享目录；L3 写 persona，一 agent 一份；L2/L3 使用 agent 级锁，见 `MemoryCore/src/services/pipeline-worker.ts:1075`–`1085`。
- L2 完成后入队 L3，见 `MemoryCore/src/services/pipeline-worker.ts:1034`–`1065`。

#### 4.11.2 记忆整理

**结论：有，而且不是只有 README 描述，代码中有三层实现。**

1. **L1 冲突检测 / merge**：`l1-dedup.ts` 说明新记忆会与已有记录比较，优先 FTS/vector/hybrid 召回候选，再由 LLM 批量判断；输出 action 支持 `store / update / merge / skip`，见 `MemoryCore/src/core/record/l1-dedup.ts:36`–`54`、`:306`–`390`。
2. **L2 SceneExtractor**：`scene-extractor.ts` 说明由 LLM agent 读取/写 scene block 文件，流程包括备份、加载索引、组装 prompt、执行、清理 soft-delete、同步索引和解析 persona update signal，见 `MemoryCore/src/core/scene/scene-extractor.ts:1`–`17`；`extract()` 从 `:136` 开始，后续处理 soft-delete 与 merge 产物清理，见 `:202`–`308`。
3. **L3 PersonaGenerator**：`persona-generator.ts` 写入 persona 文件，记录 initial/incremental、长度变化、延迟和错误指标，见 `MemoryCore/src/core/persona/persona-generator.ts:77`–`90`、`:250`–`289`。

#### 4.11.3 混合检索

- Store 能力声明包含 `nativeHybridSearch` 与 `sparseVectors`，见 `MemoryCore/src/core/store/types.ts:252`–`258`。
- L1/L0 均提供 vector、FTS、hybrid 接口，见 `MemoryCore/src/core/store/types.ts:621`–`663`。
- TCVDB 实现说明支持 server-side dense embedding、BM25 sparse、native hybridSearch、dense+sparse+RRFRerank，见 `MemoryCore/src/core/store/tcvdb/memory-store.ts:3`–`8`。
- Sparse-only 路径使用 `match + rerank rrf`，见 `MemoryCore/src/core/store/tcvdb/memory-store.ts:1017`–`1029`。

#### 4.11.4 Wiki / CodeGraph

Wiki：

- `index-db.ts` 明确有 `wiki_fts` BM25 全文检索、`graph_edge` 有向边、BFS 多跳，写路径事务重建，读路径走 LRU 连接池，见 `MemoryKnowledge/src/engines/wiki/index-db.ts:6`–`14`。
- `graph-search.ts` 从 BM25 seed 出发，沿 `[[wikilink]]` 边做多跳 BFS，并限制访问节点数量，见 `MemoryKnowledge/src/engines/wiki/graph-search.ts:2`–`12`、`:40`–`67`。

CodeGraph：

- 路由注释说明管理接口 5 个：create/list/get/sync/delete；查询接口 8 个：search/explore/callers/callees/impact/node/status/files，见 `MemoryKnowledge/src/routes/code-graph.ts:4`–`5`。
- create 时记录 `owner_user_id`，list/count 使用 `service_id + team_id`，见 `MemoryKnowledge/src/routes/code-graph.ts:182`–`228`。

#### 4.11.5 ACL 与资产治理

README 说明资产支持 `private / team / restricted`，restricted 通过 User / Role / Agent ACL 精确授权，见 `README_CN.md:137`–`138`。

`permission-checker.ts` 实现资源 → owner → 成员 → visibility → 角色默认 → ACL → deny 的判定链；private 下非 owner 即使 admin 也拒绝；restricted 需要 user / team_role / agent ACL 匹配，见 `MemoryCore/src/metadata/service/permission-checker.ts:4`–`10`、`:43`–`137`。

#### 4.11.6 知识晋升缺口

阿里 ContextDB 的记忆晋升是：

- 将记忆自动整理为团队可复用知识。
- 不简单拼接记忆，而是由多个 Agent 角色完成资料检索、事实校验、文档写作、质量审核和风险标记，见 `official/aliyun-contextdb.txt:496`–`501`。
- 支持审批、质量分阈值、自动入库或人工审核，见 `official/aliyun-contextdb.txt:517`–`548`。

Tencent 开源仓库中：

- README 说可从对话和任务生成 Chat Memory 与 Skill，把文档和代码变成 Wiki 与 CodeGraph，再统一管理、审核和路由，见 `README_CN.md:95`。
- Skill 支持从对话和工具调用提炼，并有版本、资源文件、触发边界、执行步骤和验证规则，见 `README_CN.md:109`–`113`。
- 但全仓库检索 `知识晋升 / 晋升 / promotion`，排除 `node_modules / dist / validation-artifacts` 后没有命中。

因此，Tencent 的 **Skill 提取** 与 **Wiki/CodeGraph ingest** 不等价于阿里的 **记忆晋升**。若要在华为云实现 ContextDB，需要自研：

1. 晋升任务模型：主题、来源记忆集合、目标知识库、模板、状态机。
2. 多角色 Agent 工作流：资料检索、事实校验、文档写作、质量审核、风险标记。
3. 质量评分与阈值：置信度、自矛盾检测、证据覆盖率、事实冲突、幻觉风险。
4. 人工审核工作台：批准、拒绝、编辑、采纳重写。
5. 版本与审计：晋升文档版本、来源记忆 trace、审核人、入库时间。

### TencentDB Agent Memory 开源版与腾讯云托管版差异

公开证据能确认的差异如下：

| 维度 | 开源版 | 腾讯云托管版 |
|---|---|---|
| 定位 | 本地/自部署 Memory Hub，一键 Docker 拉起 `memory-core + memory-hub + proxy`，见 `README_CN.md:32`–`44` | 独立记忆管理底座，提供自动写入、分层沉淀、按需召回与治理增强，见官方页 `tencent-agm.txt:18`–`19` |
| 记忆架构 | README 明确 L0–L3，见 `README_CN.md:250`–`257` | 官方页明确 L0–L3 四层引擎，见 `tencent-agm.txt:22`–`23` |
| 检索 | TCVDB adapter 支持 dense+sparse+RRF，也支持本地 SQLite/FTS 等路径 | 官方页明确 Embedding + 双路检索，见 `tencent-agm.txt:24`–`25` |
| 存储 | 开源代码有 TCVDB adapter 与本地部署脚本；需要自行运维数据库、对象存储、队列、LLM | 官方页明确基于腾讯云向量数据库构建，借助云数据库基础设施提供高性能高可用，见 `tencent-agm.txt:37`–`38` |
| 备份回档 | 开源仓库未提供产品级备份/回档工作流；代码中的 BackupManager 主要面向管线文件/场景备份 | 官方页明确提供备份、回档与数据保护，支持记忆资产与运行实例解耦，见 `tencent-agm.txt:28`–`29` |
| 全局资源管理 | 开源 Memory Hub/Panel 面向团队资产，不是云实例级全局资源管理 | 官方页明确支持记忆库可视化查看、分配与回收，统一管控多应用、多实例资源，见 `tencent-agm.txt:30`–`31` |
| SLA / 支持 | 自行承担 | 官方页引导联系销售和技术支持，见 `tencent-agm.txt:43` |
| 协议 | 仓库 LICENSE 声明 MIT，见 `LICENSE:1` | 商业服务协议需商务/法务确认 |

注意：公开资料没有证明开源版和云托管版功能逐项一一对应，也不应假设云上版本完全由当前开源分支构成。以上只列出公开证据可支持的差异。

### TencentDB Agent Memory 干净 HEAD 验证结果

为避免用户工作区未提交改动影响判断，我在 `/tmp/context-memory-selection/tencent-clean-head` 创建了 HEAD `41dee1f9f8cd2b7e87f3e5c073966dc58d296a16` 的 detached worktree 并复用依赖进行验证。

结果：

1. **仓库自身测试文件数为 0**：排除 `node_modules` 后，没有 `*.test.ts / *.spec.ts / test_*.py / *_test.py`。
2. **MemoryProxy `npm test` 失败**：Vitest 输出 `No test files found, exiting with code 1`。
3. **MemoryProxy `npm run typecheck` 失败，exit 2**：典型错误包括 `src/memory/memory-bridge.ts:338` 的 `agent_source` 不存在、`src/session/codebuddy/init.ts:410` 等多处 `resetFlow` 不存在、`src/storage/factory.ts:102` 找不到 `@context-proxy/cost-guard`，以及多处 `SessionInfo` 类型不兼容。
4. **CI 不跑测试**：`.github/workflows/pr-ci.yml` 的主要 job 是 install、pack、manifest、size guard、skill queue isolation guard，没有执行 `npm test` 或 typecheck，见 `.github/workflows/pr-ci.yml:17`–`158`。
5. **无 SECURITY.md、无 migration 目录**：工程化矩阵中 security 和 migrations 均为 0。

结论：**TencentDB Agent Memory 的产品设计价值很高，但当前开源分支的工程质量不足以直接作为商业生产底座。** 如果坚持采用，至少要先完成：

- 为 MemoryCore、MemoryKnowledge、MemoryProxy 建立单元测试、集成测试、隔离测试和回归测试。
- 修复 typecheck。
- CI 中强制 test + typecheck + lint + build。
- 建立数据库 schema migration。
- 补 SECURITY.md、漏洞响应、依赖扫描和权限渗透测试。
- 抽象 TCVDB 依赖，支持 PostgreSQL/pgvector、OpenSearch-compatible、图数据库等华为云可选后端。
- 补多租户压测、备份恢复演练、审计与配额。

## 5. 推荐技术路线

## 5.1 架构原则

1. **控制面自研，数据面可替换**：开源项目只作为 engine/library，不把其内部 schema、内部 API、内部错误码直接变成产品契约。
2. **先做记忆，再做知识，最后做晋升**：不要第一版就复制阿里全部能力。先保证写入、检索、隔离、审计和评测可靠，再增加图谱、Wiki、CodeGraph、晋升。
3. **租户隔离优先于功能数量**：多租户系统一旦泄露，功能再多也无法商用。Workspace → User → Agent → Session → Asset 的隔离必须进入所有查询路径。
4. **所有 LLM 产物必须可追踪**：每条 L1/L2/L3、图谱边、晋升文档都要记录来源、模型、prompt 版本、时间、置信度和审核状态。
5. **评测是产品能力，不是附属工具**：建立中文企业场景 golden set、隔离测试、回归评测、幻觉/冲突评测、延迟和成本评测。

## 5.2 推荐组合

| 层 | 推荐选择 | 理由 |
|---|---|---|
| 产品 API / 控制面 | 自研 | Workspace、Member、API Key、ACL、审计、配额、计费是云产品核心竞争力 |
| Memory Engine | Mem0 或自研 L1 pipeline，参考 Tencent L1 dedup | 快速落地，API 成熟，社区大 |
| Knowledge / Graph Engine | Cognee 为主，Graphiti 为 temporal graph adapter | Cognee 综合能力强；Graphiti 适合事实演化与来源追踪 |
| L0–L3 管线 | 自研，参考 TencentDB Agent Memory | Tencent 的分层设计最贴近目标，但直接 fork 风险高 |
| Wiki / CodeGraph | 先做 Wiki，后做 CodeGraph | Wiki 是知识库刚需；CodeGraph 可作为差异化能力分阶段实现 |
| 记忆晋升 / 知识评审 | 自研 | 所有候选均未完整提供阿里式晋升闭环 |
| 控制台 | 自研，参考 OpenViking / Tencent Memory Hub | 不复用 OpenViking 主项目代码，避免 AGPL |
| 存储 | PostgreSQL/pgvector + OpenSearch-compatible + 图数据库 + 对象存储 | 存储必须抽象，避免绑定腾讯 TCVDB |
| 队列/调度 | Kafka/Redis Stream/云队列 + 定时任务 | 支撑异步抽取、夜间整理、晋升任务 |

## 5.3 P0–P5 演进计划

### P0：产品边界与安全基线（0–2 周）

- 定义公开 API：Workspace、Member、API Key、Memory、Knowledge、Graph、Asset、Audit。
- 定义租户模型：Workspace → Team/User → Agent → Session → Asset。
- 定义 ACL：owner、team、restricted、agent、role。
- 设计存储抽象：MemoryStore、GraphStore、ObjectStore、Queue。
- 建立隔离测试：任何查询必须带 tenant/user/agent/session scope。
- 建立审计表：API 调用、读写、权限变更、LLM 任务、审核动作。

### P1：记忆 MVP（2–6 周）

- L0 原始对话保存。
- L1 事实抽取、去重、更新、merge。
- 向量 + BM25 混合检索，RRF 融合。
- `user_id / agent_id / run_id` 作用域过滤。
- 基础 API Key 认证和速率限制。
- 中文分词与中文检索评测。

交付验收：

- 相同 user/agent/run 查询可见，跨租户不可见。
- L1 冲突能 update/merge/skip，而不是无限新增。
- 检索延迟、召回率、误召回率有 baseline。

### P2：图谱与知识库（6–12 周）

- 引入 Cognee 或 Graphiti adapter。
- 文档 ingestion → chunk → entity/relation → graph。
- 支持 graph search、hybrid search、RAG search。
- Wiki 页面与链接图谱。
- 知识资产与记忆资产统一登记。
- 图谱边记录来源、置信度、创建时间、失效时间。

### P3：L2/L3 与夜间整理（12–20 周）

- L2 Scenario 聚合，参考 Tencent SceneExtractor。
- L3 Persona / Core Profile 生成。
- 夜间任务：实体属性更新、冲突归档、重复关系合并、热度调整。
- 记忆 TTL、保护规则、归档策略。
- 增量与全量重建任务。

### P4：记忆晋升与知识评审（20–30 周）

- 晋升任务：主题、来源记忆、模板、目标知识库、状态机。
- Agent 角色：资料检索、事实校验、写作、质量审核、风险标记。
- 质量分：置信度、自矛盾、证据覆盖、幻觉风险、重复度。
- 人工审核：批准、拒绝、编辑、采纳重写。
- 入库版本与来源 trace。

### P5：商业化平台能力（30 周以上）

- 实例生命周期、创建、升级、删除。
- 配额、计费、账单、成本看板。
- 备份、恢复、跨可用区容灾。
- 监控、告警、tracing、审计导出。
- MCP / SDK / CLI / 控制台。
- SLA、安全合规、渗透测试、数据驻留策略。

## 6. 多租户生产可行性判断

| 项目 | 多租户能力 | 生产可行性 |
|---|---|---|
| Mem0 | `user_id / agent_id / run_id` 作用域；自托管服务有 User/APIKey/RequestLog | 可做单产品记忆内核；云多租户控制面需自研 |
| Letta Code | Agent runtime 内部状态，多租户治理不是核心目标 | 不建议作为数据面底座 |
| Zep | 当前仓库不是产品；CE deprecated | 不可选 |
| Graphiti | `group_id` 图分区 | 适合作为模块；需自建租户认证与控制面 |
| Cognee | tenant、role、permission 有实现与测试 | 可作为主底座候选，需补云控制面和安全运维 |
| MemOS | API Key 中间件，但默认关闭；用户上下文较基础 | 可参考，不建议直接商业化 |
| MemoBase | 用户 profile 体系 | 偏 C 端画像，不适合企业多租户 ContextDB |
| LangMem | 存储抽象，无租户服务 | 只适合客户端/框架集成 |
| A-MEM | 无 | 不适合 |
| OpenViking | account/user identity、ACL、API Key | 技术可行，但 AGPL 限制商业复用 |
| TencentDB Agent Memory | team/user/agent/session 隔离、资产 ACL、TCVDB filter | 原型可行；生产需补测试、迁移、云控制面和存储抽象 |

## 7. 中文支持评估

| 等级 | 项目 | 证据与判断 |
|---|---|---|
| 强 | TencentDB Agent Memory、OpenViking、MemOS、MemoBase | 有中文 README / 中文 prompt / 中文场景设计；Tencent Wiki 明确中文 bigram 逻辑 |
| 中 | Cognee | 有中文社区材料，但核心 README 和 prompt 仍以英文为主，需要补中文评测 |
| 弱 | Mem0、Letta Code、Graphiti、Zep、LangMem、A-MEM | 缺少系统化中文文档和中文 prompt；需要自行补中文分词、实体抽取、评测 |

中文场景不能只看 README。至少要验证：

- 中文分词与 BM25。
- 中文实体识别与别名。
- 中文人名/组织/项目消歧。
- 中文时间表达解析。
- 中文长文档 chunking。
- 中文幻觉与冲突评测。
- 中文 prompt 的输出稳定性。

## 8. 风险清单

### 8.1 技术风险

1. **LLM 抽取质量不稳定**：同一对话可能抽出不同事实，必须有版本、置信度和人工审核。
2. **图谱冲突与幻觉**：实体关系错误比无图谱更危险，需要来源 trace 和审核。
3. **检索混合策略调参难**：BM25、向量、图遍历、RRF 的权重必须按中文场景评测。
4. **异步管线一致性**：L1/L2/L3 之间可能滞后或重复，需要幂等键、锁、checkpoint、重放。
5. **多租户泄露**：任何查询绕过 scope 都是 P0 事故。
6. **成本失控**：抽取、图谱构建、晋升、重写都会显著放大 LLM 调用。

### 8.2 工程风险

1. **整仓 fork 维护成本高**：上游越活跃，fork 后 rebase 越痛苦。
2. **Tencent 当前无测试且 typecheck 失败**：直接采用需要先投入修复。
3. **OpenViking AGPL**：商业云服务必须法务确认，不能默认可复用。
4. **Cognee Postgres graph demo**：不能把 demo 特性当生产能力。
5. **MemoBase 停滞**：不适合作为长期依赖。

### 8.3 商业风险

1. **与云厂商数据库能力绑定**：华为云版本应抽象存储，避免复制 TCVDB 专属实现。
2. **数据导出与迁移**：阿里文档明确当前记忆/知识库暂不支持导出；我们应把导出/迁移作为差异化能力。
3. **计费模型复杂**：写入、检索、LLM 演进、存储、图谱重建都应可计量。
4. **合规审计**：企业客户会要求审计、数据驻留、删除、备份和恢复演练。

## 9. 最终选型建议

### 采用

1. **Cognee：主底座候选**：用于知识图谱、多租户 dataset、搜索与 ingestion。采用依赖/adapter 方式，避免深度 fork；Postgres graph 生产能力另行商务确认。
2. **Graphiti：Temporal Graph Engine**：用于实体关系演化、事实有效期、来源追踪。作为可替换模块，不承担完整产品控制面。
3. **Mem0：Memory Engine / API 参考**：短期快速上线记忆写入与检索；公开 API 自研，底层可替换。

### 借鉴

1. **TencentDB Agent Memory**：借鉴 L0–L3、L1 dedup、L2 Scene、L3 Persona、Asset/ACL、Wiki graph、CodeGraph API。MIT 许可允许选择性复用，但必须先补测试和存储抽象。
2. **OpenViking**：借鉴 `viking://` 统一资源模型、L0/L1/L2、多租户 identity/ACL、控制台体验。主项目代码不建议复用。
3. **阿里 RDS ContextDB**：作为产品验收基线，尤其是记忆晋升、知识评审、夜间演进、Workspace/API Key/审计。

### 替换

1. **Zep Community Edition → Graphiti / Zep Cloud**：CE 已 deprecated，不应继续作为自托管路线。
2. **通用 Wiki 检索 → Wiki + Link Graph + Entity Graph 分层**：不要用单一 RAG chunk 检索替代结构化知识图谱。

### 不用

1. **Letta Code**：Agent harness，不是 ContextDB 数据面。
2. **LangMem**：库，深度绑定 LangGraph。
3. **A-MEM**：研究项目，无生产工程。
4. **MemoBase**：画像专用且停滞。
5. **Zep 当前仓库**：不是产品或服务。

## 10. 证据索引

### 10.1 代码快照

| 项目 | Commit |
|---|---|
| Mem0 | `a39a802bbc93e85b820078cd3c4dbaf53af25dbe` |
| Letta Code | `b69da0ee2aa2afa348e6975055ed804cb127f172` |
| Zep | `495bf72880d13f0b81696ec4f88a9817ed85ca73` |
| Graphiti | `0de2993c5199ebd4c1efcf09ea9984ec4e53e86f` |
| Cognee | `663a2dc15d04bc0d7ec2733a2dd604b7ed1b8c8e` |
| MemOS | `12acdad694d0a6b01437111fc885d60a1f3fa2d5` |
| MemoBase | `358c16bbc6d687937d79bc2f984a11c3be8da901` |
| LangMem | `9d033b47d9ce53e37e92c92241b0496c0278932e` |
| A-MEM | `ceffb860f0712bbae97b184d440df62bc910ca8d` |
| OpenViking | `172c1050716f63339f4001292d58c830e6b7a315` |
| TencentDB Agent Memory | `41dee1f9f8cd2b7e87f3e5c073966dc58d296a16` |

### 10.2 官方链接

- 阿里云 RDS ContextDB 快速入门：https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start
- 腾讯云 Agent Memory：https://cloud.tencent.com/product/agm
- 火山引擎 OpenViking Service：https://www.volcengine.com/product/openviking-service
- OpenViking GitHub：https://github.com/volcengine/OpenViking

### 10.3 关键源码证据

- Mem0 作用域与写入：`/tmp/context-memory-selection/mem0/mem0/memory/main.py:760`
- Mem0 OSS 无 Graph Memory：`/tmp/context-memory-selection/mem0/docs/core-concepts/how-it-works.mdx:64`
- Mem0 服务用户/APIKey/日志：`/tmp/context-memory-selection/mem0/server/models.py:18`
- Letta 定位：`/tmp/context-memory-selection/letta-code/README.md:5`
- Zep 当前仓库非产品：`/tmp/context-memory-selection/zep/README.md:19`
- Zep CE deprecated：`/tmp/context-memory-selection/zep/README.md:66`
- Graphiti 定位：`/tmp/context-memory-selection/graphiti/README.md:37`
- Graphiti 时间字段：`/tmp/context-memory-selection/graphiti/graphiti_core/edges.py:271`
- Graphiti 数据库后端：`/tmp/context-memory-selection/graphiti/README.md:632`
- Cognee 定位：`/tmp/context-memory-selection/cognee/README.md:42`
- Cognee 多租户测试：`/tmp/context-memory-selection/cognee/cognee/tests/test_multi_tenancy.py:63`
- Cognee 部署：`/tmp/context-memory-selection/cognee/README.md:250`
- Cognee Postgres graph demo 边界：`/tmp/context-memory-selection/cognee/README.md:260`
- MemOS auth：`/tmp/context-memory-selection/MemOS/src/memos/api/middleware/auth.py:1`
- MemOS Dream beta：`/tmp/context-memory-selection/MemOS/src/memos/dream/README.md:3`
- MemoBase 用户与画像：`/tmp/context-memory-selection/memobase/README.md:259`
- LangMem 定位：`/tmp/context-memory-selection/langmem/README.md:13`
- A-MEM 定位：`/tmp/context-memory-selection/A-mem/README.md:23`
- OpenViking `viking://`：`/tmp/context-memory-selection/openviking/README_CN.md:43`
- OpenViking L0/L1/L2：`/tmp/context-memory-selection/openviking/README_CN.md:88`
- OpenViking 生产部署：`/tmp/context-memory-selection/openviking/README_CN.md:252`
- OpenViking 商业版本：`/tmp/context-memory-selection/openviking/README_CN.md:258`
- OpenViking AGPL：`/tmp/context-memory-selection/openviking/README_CN.md:329`
- Tencent L0–L3：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/README_CN.md:250`
- Tencent L1 dedup：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore/src/core/record/l1-dedup.ts:36`
- Tencent L2 SceneExtractor：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore/src/core/scene/scene-extractor.ts:1`
- Tencent L3 PersonaGenerator：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore/src/core/persona/persona-generator.ts:77`
- Tencent TCVDB hybrid：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore/src/core/store/tcvdb/memory-store.ts:3`
- Tencent Wiki graph：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryKnowledge/src/engines/wiki/index-db.ts:6`
- Tencent CodeGraph 路由：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryKnowledge/src/routes/code-graph.ts:4`
- Tencent 权限判定：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/MemoryCore/src/metadata/service/permission-checker.ts:43`
- Tencent CI：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/.github/workflows/pr-ci.yml:17`
- Tencent MIT：`/Users/zhuqingping/Work/Database/ContextDB_TencentDB/TencentDB-Agent-Memory/LICENSE:1`

### 10.4 官方文本快照

- 阿里 ContextDB：`/tmp/context-memory-selection/official/aliyun-contextdb.txt`
- 腾讯 Agent Memory：`/tmp/context-memory-selection/official/tencent-agm.txt`
- 火山 OpenViking Service HTML：`/tmp/context-memory-selection/official/volcengine-openviking-service.html`

### 10.5 数据快照

- GitHub 指标：`/tmp/context-memory-selection/github_metrics_2026-09-22.json`
- 既有活动快照：`/tmp/context-memory-selection/github_metrics.json`
- Tencent 干净 HEAD：`/tmp/context-memory-selection/tencent-clean-head`

## 11. 一页决策摘要

如果只能选一条路线：

> **自研云产品控制面，Cognee 作为知识/图谱主底座候选，Mem0 作为短期记忆引擎，Graphiti 作为时间图谱模块，TencentDB Agent Memory 作为 L0–L3 与资产治理架构参考，OpenViking 作为产品体验对标；不整仓 fork，不使用 AGPL 主项目代码，知识晋升和知识评审自研。**

如果必须在 6 周内上线最小版本：

1. 自研 API Gateway + API Key + Workspace/User/Agent scope。
2. PostgreSQL/pgvector + BM25/FTS 混合检索。
3. 引入 Mem0 或自研 L1 抽取/去重。
4. 接入审计、配额、监控。
5. 暂缓图谱和晋升，先保证记忆可靠。

如果目标是 6 个月内接近阿里 ContextDB：

1. P0–P1 记忆服务。
2. P2 Cognee/Graphiti 图谱与知识库。
3. P3 Tencent 式 L2/L3 与夜间整理。
4. P4 记忆晋升与知识评审。
5. P5 商业化平台能力。
