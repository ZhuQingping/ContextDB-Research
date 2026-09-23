# 华为云 ContextDB 实现方案：Mem0 + LightRAG 选型与落地报告

> 调研日期：2026-09-23  
> 复核日期：2026-09-23  
> 调研方式：源码阅读 + 官方产品页/文档抽取 + GitHub API 指标 + 多 Agent 多轮检视  
> 适用团队：~5 人 RDS PostgreSQL 团队  
> 目标：在华为云 RDS PostgreSQL 上，3 个月内上线 Agent Memory + 知识库（含知识晋升、知识管理、团队空间）  
> 对标：阿里云 RDS ContextDB、腾讯云 Agent Memory、火山引擎 OpenViking Context

---

## 1. 执行结论

### 1.1 最终推荐

**Mem0 + LightRAG + 自研 ContextDB 控制面 + RDS PostgreSQL**

| 角色 | 推荐组件 | 核心理由 |
|---|---|---|
| 长期记忆引擎 | Mem0 (v2.1.0) | 社区最大、API 成熟、原生支持 pgvector |
| 知识库引擎 | LightRAG（推荐稳定版 v1.5.7；v1.5.8 为当前主分支开发版本） | 原生支持 PostgreSQL 全栈（KV/Vector/Graph/DocStatus），无需额外图数据库 |
| 统一存储 | RDS PostgreSQL | pgvector + tsvector + JSONB，统一事实源 |
| 图增强（可选） | Apache AGE（二期） | LightRAG PGTableGraphStorage 一期够用 |
| 控制面 | 自研 | Workspace/ACL/Promotion/Audit/Quota 所有开源项目均不提供 |
| Agent Runtime（可选） | LangGraph（v1.2.12；PostgreSQL 扩展 langgraph-checkpoint-postgres v3.1.2） | 管理 Agent checkpoint/thread/run 状态 |

### 1.2 核心判断

1. **Mem0 + LightRAG 组合可行**：两者职责不重叠，通过外置 Promotion Bridge 衔接记忆→知识晋升，无需侵入式修改任何一方。
2. **LightRAG 优于 Cognee/GraphRAG 作为知识库底座**：LightRAG 原生提供 PGTableGraphStorage（纯 PostgreSQL 表实现图存储，无 AGE 依赖），Cognee 的 PostgreSQL 图适配器明确标注为 demo。
3. **控制面必须自研**：Workspace、ACL、Promotion、Audit、Quota 是所有开源项目的共同缺口，也是云产品的核心竞争力。
4. **Apache AGE 1.8.0+ 存在兼容风险**：LightRAG 源码明确拒绝 AGE 1.8.0+，一期应默认使用 PGTableGraphStorage 路径。

---

## 2. 问题一：Mem0 + RAG 组合可行性

### 2.1 可行性结论

**可行，不需要侵入式修改开源组件。**

组合的架构关系：

```text
Mem0（记忆层）           LightRAG（知识层）
     │                        │
     │    Promotion Bridge    │
     ├─────── 外置衔接 ────────┤
     │                        │
     └───── PostgreSQL ───────┘
         pgvector + tsvector + JSONB
```

### 2.2 为什么不需要侵入式修改

**Mem0 侧**：
- Mem0 是独立的记忆引擎，提供 `add/search/get_all/update/delete` API（`mem0/memory/main.py:760/1379/1255/462/1869`）
- 通过 `vector_store.config` 指定 `pgvector` 后端（`mem0/vector_stores/pgvector.py:146`）
- 记忆写入后可通过 webhook 或轮询获取新记忆，无需修改 Mem0 内部逻辑

**LightRAG 侧**：
- LightRAG 通过 `ainsert()` 接收文本并构建索引，这是公开 API
- 存储后端通过环境变量配置，支持 PG KV / PG Vector / PG Table Graph / PG DocStatus
- 不需要修改 LightRAG 内部代码，只需调用其 Python API

**Promotion Bridge（外置衔接层）**：
- 从 Mem0 读取记忆（公开 API `get_all()`）
- LLM 归纳候选知识
- 冲突检测 + PII 检测 + 溯源校验
- 评审后写入统一 `knowledge_item` 表
- 调用 LightRAG `ainsert()` 写入知识索引
- 回链 `knowledge_item_id → memory_id/source_id`

**侵入式修改风险 = 零**（前提：不 fork Mem0 或 LightRAG 的内部 schema/API）。

### 2.3 需要注意的集成点

| 集成点 | 风险 | 缓解方案 |
|---|---|---|
| Mem0 记忆 schema 与 LightRAG 知识 schema 不同 | 需要统一事实源 | 控制面维护 `contextdb_unified` schema，两条数据面各自映射 |
| LightRAG 的 `ainsert()` 是异步的 | 晋升写入后需确认索引完成 | 监听 `DOC_STATUS` 表，确认 `COMPLETED` 后标记晋升成功 |
| Mem0 默认使用 OpenAI embedding | 需要替换为华为 MaaS embedding | Mem0 支持 `embedder.config` 自定义 provider |
| LightRAG 默认使用 OpenAI LLM | 需要替换为华为 Pangu/MaaS | LightRAG 支持 `llm_model_func` 自定义回调 |

---

## 3. 问题二：知识库组件选型

### 3.1 候选对比矩阵

| 维度 | LightRAG (v1.5.7) | Cognee (v1.6.0) | GraphRAG (微软, v3.1.2) | LangChain/LangGraph | LlamaIndex |
|---|---|---|---|---|---|
| 定位 | 轻量 RAG + 知识图谱 | 认知管线 ECL | 全量图 RAG | Agent 框架 / 工具库 | 通用 RAG 框架 |
| PostgreSQL 原生支持 | ✅ KV + Vector + Graph + DocStatus | ⚠️ 图存储为 demo | ❌ 偏 Azure/Cosmos | ⚠️ 有 checkpoint PG 但非 RAG | ⚠️ 有 PG vector store 但非完整方案 |
| 图存储路径 | PGTableGraphStorage（纯 PG，无扩展） | postgres_demo/（demo） | Azure Cosmos / LanceDB | N/A | N/A |
| Apache AGE 支持 | ✅ 但拒绝 1.8.0+ | ❌ | ❌ | N/A | N/A |
| 文档 ingestion | ✅ 内置 | ✅ 内置 ECL | ✅ 内置 | ❌ 需自行组装 | ✅ 内置 |
| 混合检索 | ✅ vector + graph + keyword | ✅ | ✅ | ❌ 需自行组装 | ✅ |
| 社区活跃度 | 高（39,823 stars） | 高（30,934 stars） | 高（36,077 stars） | 最高（LangChain 146,917；LangGraph 42,164） | 高（52,290） |
| 学习成本 | 低 | 中 | 高 | 低（但组装成本高） | 中 |
| 生产就绪度 | 中高 | 中（PG 图是 demo） | 中 | 取决于组装 | 取决于组装 |
| 3 个月 MVP 可行性 | **高** | 中 | 低 | 低（组装成本高） | 中 |

### 3.2 为什么选择 LightRAG

**原因一：PostgreSQL 全栈原生支持**

LightRAG 提供四种 PG 存储后端（`lightrag/kg/postgres_impl.py` + `lightrag/kg/pgtable_impl.py`）：

| 存储层 | 实现类 | PostgreSQL 特性 |
|---|---|---|
| KV 存储 | `PGKVStorage` | JSONB |
| 向量存储 | `PGVectorStorage` | pgvector |
| 图存储 | `PGTableGraphStorage` | 纯 PG 表 + JSONB（无扩展） |
| 图存储（增强） | `PGGraphStorage` | Apache AGE |
| 文档状态 | `PGDocStatusStorage` | JSONB |

PGTableGraphStorage 的实现（`lightrag/kg/pgtable_impl.py`，1651 行）：

```sql
-- 节点表
lightrag_graph_nodes(workspace TEXT, namespace TEXT, id TEXT, properties JSONB)
  PK(workspace, namespace, id)

-- 边表
lightrag_graph_edges(workspace TEXT, namespace TEXT, src_id TEXT, tgt_id TEXT, properties JSONB)
  PK(workspace, namespace, src_id, tgt_id)
```

这意味着 **LightRAG 可以完全运行在 RDS PostgreSQL 上，不需要安装任何 PG 扩展**（甚至不需要 pgvector，虽然我们已有）。这是对我们托管场景最优的选择。

**原因二：Apache AGE 1.8.0+ 存在崩溃风险**

LightRAG 源码明确拒绝 AGE 1.8.0+（`lightrag/kg/postgres_impl.py:124-940`）：

```python
AGE_FIRST_UNSUPPORTED_VERSION = (1, 8, 0)
```

原因：AGE 1.8.0 将 Cypher `id()` 返回类型从 `bigint` 改为 `graphid`，导致：
- `get_knowledge_graph` 的 labelled branch 失败（graphid → bigint cast 错误）
- wildcard branch 触发 PG backend segfault，引发全实例 crash recovery

**我们不应该在第一版依赖 AGE 图存储**。PGTableGraphStorage 路径更安全。

**原因三：文档 ingestion 开箱即用**

LightRAG 内置了完整的文档处理管线：上传 → 解析 → 切块 → 实体抽取 → 关系抽取 → 向量化 → 图构建。不需要额外引入 LlamaIndex 或 LangChain 做文档预处理。

**原因四：体积轻、学习成本低**

与 GraphRAG（微软）相比，LightRAG 代码量小得多，部署简单。GraphRAG 依赖 Azure 生态较深，3 个月内替换存储后端成本高。

### 3.3 为什么不选 Cognee

**核心原因：Cognee 的 PostgreSQL 图存储是 demo，不能生产使用。**

源码证据：
```
/tmp/agent-memory-evidence/cognee/cognee/infrastructure/databases/graph/postgres_demo/
```

目录名 `postgres_demo` 直接表明这是 demo 实现。Cognee 的生产图存储默认是 Neo4j / Kuzu / Ladybug，不支持以 PostgreSQL 作为图数据库生产部署。

**Cognee 的 `improve()` / `memify()` 有参考价值**（`cognee/api/v1/improve/improve.py:101`），其 feedback loop 设计可以借鉴到 Promotion Bridge 中，但不应作为第一版的知识库底座。

### 3.4 为什么不选 GraphRAG / LangChain / LlamaIndex

| 项目 | 不选原因 |
|---|---|
| GraphRAG (微软) | 深度绑定 Azure Cosmos / LanceDB；替换 PG 后端需要大量适配；3 个月不够 |
| LangChain | 是工具库，不是完整 RAG 产品；需要自行组装 ingestion + graph + 检索；组装成本高 |
| LangGraph | 是 Agent Runtime，不是 RAG；可作为可选 runtime 层，但不替代知识库引擎 |
| LlamaIndex | 有 PG vector store 但无完整 PG 图存储路径；需要额外引入图数据库 |

### 3.5 最终选型决定

```
记忆引擎：Mem0 v2.1.0（pgvector 后端）
知识引擎：LightRAG v1.5.7（PGTableGraphStorage 后端）
统一存储：RDS PostgreSQL（pgvector + tsvector + JSONB）
Agent Runtime（可选）：LangGraph v3.1.2（PG checkpoint 后端）
```

---

## 4. 问题三：商用缺口与工作量评估

### 4.1 子模块缺口分析

#### 已有（Mem0 + LightRAG + PG 覆盖）

| 能力 | 来源 | 完成度 |
|---|---|---|
| 事实型长期记忆（写入/检索/去重/更新） | Mem0 | ~80% |
| 向量存储与检索 | Mem0 + pgvector | ~90% |
| 文档 ingestion（上传/解析/切块/实体/关系） | LightRAG | ~85% |
| 图存储与图检索 | LightRAG PGTableGraphStorage | ~75% |
| 混合检索（vector + graph + keyword） | LightRAG | ~80% |
| 全文检索 | PG tsvector | ~90% |

#### 缺失（必须自研）

| 子模块 | 缺口描述 | P0/P1/P2 | 人天估算 |
|---|---|---|---|
| **统一 Context API** | 对外提供统一 REST/gRPC 接口，覆盖记忆+知识+图谱+晋升 | P0 | 10–15 人天 |
| **Workspace / Team / Member** | 多租户模型、成员管理、角色权限 | P0 | 10–15 人天 |
| **API Key / IAM / ACL** | API Key 生命周期、服务端鉴权、行级隔离 | P0 | 8–12 人天 |
| **Audit / 审计** | API 调用日志、读写审计、权限变更、LLM 任务日志 | P0 | 5–8 人天 |
| **Promotion Bridge** | 记忆→知识晋升：候选生成、冲突检测、PII、评审、回链 | P0 | 15–20 人天 |
| **Context Assembler** | 多路召回、去重、排序、token 预算、权限过滤、引用来源 | P1 | 10–15 人天 |
| **Quota / 计费** | 存储配额、API 调用配额、token 用量统计 | P1 | 5–8 人天 |
| **Embedding / LLM 适配** | 华为 MaaS / Pangu 接入、embedding 替换 OpenAI | P0 | 5–8 人天 |
| **异步任务调度** | 文档 ingestion 异步化、夜间整理、晋升任务调度 | P1 | 8–12 人天 |
| **控制台（Web UI）** | Workspace 管理、知识库管理、记忆查看、晋升审核 | P1 | 15–20 人天 |
| **评测框架** | 中文 golden set、检索评测、幻觉评测、隔离测试 | P1 | 10–15 人天 |
| **监控 / 可观测性** | 指标采集、调用链、异常告警、模型成本监控 | P1 | 5–8 人天 |
| **备份 / 回档** | 利用 RDS PostgreSQL 原生备份能力，增加逻辑回档 API | P1 | 3–5 人天 |
| **SDK（Python / JS）** | 客户端 SDK，兼容 Mem0 API 协议子集 | P2 | 10–15 人天 |
| **知识管理（版本/冲突/合并）** | 知识条目版本管理、冲突合并、批量操作 | P2 | 10–15 人天 |

### 4.2 工作量汇总

| 阶段 | 时间 | P0 模块 | 预估人天 |
|---|---|---|---|
| MVP（P0） | 4–6 周 | 统一 API + Workspace/ACL + Audit + Promotion Bridge + Embedding 适配 | 53–78 人天 |
| 增强（P1） | 6–10 周 | Context Assembler + Quota + 异步任务 + 控制台 + 评测 + 监控 + 备份 | 56–81 人天 |
| 完善（P2） | 10–16 周 | SDK + 知识管理 + Graph 增强 + 差异化功能 | 20–30 人天 |

**5 人团队 × 3 个月 = 300 人天，P0+P1 约 109–159 人天，有充足余量。**

### 4.3 不需要做的事

| 不做 | 理由 |
|---|---|
| Fork Mem0 或 LightRAG | 外置 Promotion Bridge 即可，避免维护 fork |
| 第一版引入 Apache AGE | PGTableGraphStorage 够用；AGE 1.8.0+ 有崩溃风险 |
| 自研 embedding 模型 | 使用华为 MaaS 托管模型 |
| 自研向量索引 | pgvector 已内置 HNSW/IVFFlat |
| 自研全文分词 | PG tsvector + pg_jieba（如需中文增强） |

---

## 5. 问题四：基于华为云构建稳定、可靠、有竞争力的点

### 5.1 存储层：RDS PostgreSQL

| 构建点 | 具体做法 |
|---|---|
| 统一事实源 | 记忆、知识、图谱、审计、配额全部存 PG，避免数据分裂 |
| pgvector HNSW | 向量检索性能与 Milvus/Qdrant 持平，且数据一致性强 |
| tsvector 全文 | 与 pgvector 在同一实例内混合检索，无需额外 ES |
| PGTableGraphStorage | LightRAG 纯 PG 图存储，无需 AGE 或 Neo4j |
| RDS 原生高可用 | 主备切换、自动备份、监控告警、自动扩容——华为云 RDS 已有 |
| 行级安全（RLS） | 利用 PG Row-Level Security 实现 Workspace 级数据隔离 |
| JSONB 灵活 schema | Mem0 metadata、LightRAG properties、Promotion Bridge 状态都用 JSONB |

### 5.2 模型层：华为 LLM + Embedding

| 构建点 | 具体做法 |
|---|---|
| Pangu / MaaS LLM | 用于记忆事实抽取、知识归纳、冲突检测、知识评审 |
| MaaS Embedding | 用于记忆和知识的向量化，替换 OpenAI text-embedding |
| Reranker | 多路召回后精排，提升准确率 |
| Embedding 缓存 | 同一文本不重复调用 embedding API，节省成本 |
| 异步 LLM 任务 | 文档 ingestion / 晋升 / 整理任务异步执行，不阻塞用户请求 |
| LLM 成本控制 | Token 用量统计、批量推理、模型选择（大模型用于归纳，小模型用于分类） |

### 5.3 平台层：华为云配套

| 构建点 | 具体做法 |
|---|---|
| RDS PostgreSQL | 统一存储（pgvector + tsvector + JSONB + PGTableGraph） |
| Redis / DCS | 异步任务队列、embedding 缓存、session cache |
| FunctionGraph / CCE | 异步任务执行器（文档 ingestion、夜间整理、晋升） |
| OBS | 原始文档对象存储 |
| IAM | 用户认证、API Key 鉴权、角色管理 |
| Cloud Eye / AOM | 监控告警 |
| API Gateway | 统一入口、限流、认证 |
| VPC / 安全组 | 网络隔离 |

### 5.4 竞争力构建点

| 竞争力方向 | 具体做法 | 与友商差异 |
|---|---|---|
| **PostgreSQL 统一栈** | 记忆+知识+图谱全部在 PG 上，无需额外 ES/Neo4j/Milvus | 阿里用 ES+Milvus+GraphDB 多实例，我们单实例 PG 即可覆盖 |
| **RDS 原生高可用** | 备份/回档/主备切换由 RDS 托管，无需额外运维 | 友商需要额外维护向量数据库和图数据库的 HA |
| **低成本** | 单 PG 实例即可运行完整功能，不需要额外数据库实例 | 友商架构通常需要 3–5 个独立存储实例 |
| **中文优化** | pg_jieba 分词 + Pangu 中文 embedding + 中文 golden set 评测 | 腾讯/阿里有中文能力，但开源版不一定暴露 |
| **Promotion Bridge** | 外置晋升桥接，不改开源组件，保持跟随社区演进 | 阿里是闭源实现，我们基于开源可审计 |

---

## 6. 问题五：与阿里/腾讯/火山的差异化

### 6.1 竞品能力对比

| 能力 | 阿里 ContextDB | 腾讯 Agent Memory | 火山 OpenViking | 华为云（本方案） |
|---|---|---|---|---|
| 记忆引擎 | 闭源自研 | 开源（MIT） | 闭源 | Mem0（Apache-2.0） |
| 知识库 | 闭源自研 | Wiki / CodeGraph | 闭源 | LightRAG（MIT） |
| 记忆晋升知识 | ✅ 多 Agent 角色 | ❌ 未找到 | ✅ | ✅（Promotion Bridge） |
| 知识评审 | ✅ 事实校验+审核 | ❌ | ✅ | ✅（Promotion Bridge 评审流） |
| 团队空间 | ✅ Workspace | ⚠️ 部分 | ✅ | ✅（自研控制面） |
| 记忆治理 | ✅ 夜间整理 | ✅ L0–L3 | ✅ | ⚠️ P1 需自研 |
| 混合检索 | ✅ | ✅ | ✅ | ✅（vector + graph + keyword） |
| 统一存储 | ES + Milvus + GraphDB | TCVDB | 闭源 | **RDS PostgreSQL 单实例** |
| API 协议 | 自定义 | 自定义 | 自定义 | 兼容 Mem0 API 子集 |
| 开源可审计 | ❌ | ✅（MIT） | ❌（AGPL） | ✅（基于 Apache-2.0） |

### 6.2 易于差异化的模块

**最容易做出差异化的 3 个点：**

1. **PostgreSQL 统一栈（最大差异）**
   - 友商通常需要 ES + 向量数据库 + 图数据库多个独立实例
   - 我们一个 RDS PostgreSQL 实例即可覆盖全部数据面
   - 客户运维成本、数据一致性、备份回档都显著简化
   - 这是华为 RDS 团队的天然优势

2. **Promotion Bridge（记忆晋升知识）**
   - 腾讯开源版没有通用晋升工作流
   - 阿里有但闭源，客户无法审计晋升过程
   - 我们基于开源组件 + 外置晋升桥，可审计、可定制

3. **低成本单实例部署**
   - 不需要额外部署 Milvus/ES/Neo4j
   - 中小客户用一台 RDS PG 即可运行完整功能
   - 这是"跟着主流社区走"的同时做出的成本差异化

### 6.3 不需要强求差异化的模块

| 模块 | 原因 |
|---|---|
| 记忆去重/冲突检测 | Mem0 已提供基础能力，友商差异不大 |
| 向量检索 | pgvector HNSW 性能已足够 |
| 文档解析 | LightRAG 内置能力够用 |
| Agent Runtime | LangGraph 是社区标准，无需自定义 |

---

## 7. 问题六：vs 直接托管 Cognee

### 7.1 对比总结

| 维度 | Mem0 + LightRAG（推荐） | 直接托管 Cognee |
|---|---|---|
| 知识库能力 | LightRAG 内置完整 ingestion + 混合检索 | Cognee ECL 管线能力更强 |
| PostgreSQL 兼容性 | LightRAG 原生支持 PG 全栈 | Cognee PG 图存储是 demo |
| 记忆能力 | Mem0 是专业记忆引擎 | Cognee 有记忆但非核心强项 |
| 记忆晋升 | Promotion Bridge 外置，不改开源 | Cognee improve() 有参考价值但不够 |
| 多租户 | 都需要自研 | Cognee 有 tenant/role 代码（但非生产级） |
| 社区活跃度 | Mem0 65,865 + LightRAG 39,823 | Cognee 30,934 |
| 跟随社区演进 | 两个项目都可替换，解耦 | 绑定单一项目，社区较小 |
| 3 个月 MVP 风险 | 低 | 中（PG 图存储是 demo 是硬伤） |
| 许可证 | Apache-2.0 | Apache-2.0 |
| Agent Runtime 兼容 | LangGraph/Mem0/LlamaIndex 均有适配 | 需要额外适配 |

### 7.2 Cognee 的优势与局限

**优势：**
- ECL（Extract-Cognify-Load）管线设计完整，从原始数据到知识图谱端到端
- `improve()` API 提供了 feedback loop 思路，可借鉴到 Promotion Bridge
- 有 tenant / role / permission 代码和测试
- Apache-2.0 许可证

**局限（开源版）：**

| 局限 | 证据 |
|---|---|
| PostgreSQL 图存储是 demo，不能生产使用 | `cognee/infrastructure/databases/graph/postgres_demo/` |
| 生产图存储默认 Neo4j/Kuzu/Ladybug | 不符合我们"统一 PG"的目标 |
| `improve()` 是实验性 API | 未标注生产就绪 |
| 开源版无 ACL/Quota/Billing | 与其他开源项目相同的缺口 |
| 社区规模低于 Mem0 / LightRAG | Cognee 30,934 vs Mem0 65,865 / LightRAG 39,823 |
| 记忆能力不如 Mem0 专业 | Cognee 的 add/search 不如 Mem0 的去重/更新/合并成熟 |

### 7.3 结论

**Mem0 + LightRAG 组合优于直接托管 Cognee**，核心原因是：
1. LightRAG 的 PGTableGraphStorage 是生产级纯 PG 实现，Cognee 的是 demo
2. Mem0 的记忆能力（去重/更新/合并/多作用域）比 Cognee 更成熟
3. 解耦两个组件使得任何一个都可以独立升级或替换，跟随社区演进
4. Cognee 的 `improve()` 思路可以借鉴到 Promotion Bridge 中，不需要绑定 Cognee

---

## 8. 3 个月 MVP 演进路线

### 第 1–2 周：基座搭建

- [ ] 搭建 FastAPI 项目骨架 + PostgreSQL schema 设计
- [ ] 部署 Mem0（pgvector 后端）+ LightRAG（PGTableGraphStorage 后端）
- [ ] 替换 embedding 为华为 MaaS
- [ ] 验证 Mem0 add/search 与 LightRAG ainsert/query 基本流程

### 第 3–4 周：控制面 + 记忆

- [ ] 实现 Workspace / Team / Member 模型
- [ ] 实现 API Key 认证 + 行级隔离（RLS 或 WHERE 条件）
- [ ] 封装统一 Memory API（兼容 Mem0 协议子集）
- [ ] 实现基础 Audit 日志
- [ ] 中文记忆 golden set 评测 baseline

### 第 5–6 周：知识库 + 晋升 MVP

- [ ] 封装统一 Knowledge API（上传/检索/删除）
- [ ] 实现 Promotion Bridge v1：
  - Mem0 get_all → 置信度阈值筛选
  - LLM 归纳候选知识
  - 人工确认后写入 LightRAG
  - 回链 knowledge_item_id → memory_id
- [ ] 端到端 demo：Agent 对话 → 记忆积累 → 晋升 → 知识检索

### 第 7–8 周：混合检索 + Context Assembler

- [ ] 实现 Context Assembler：多路召回（vector + graph + keyword）→ 去重 → 排序 → token 预算 → 权限过滤
- [ ] 实现 LLM 适配层（Pangu / MaaS）
- [ ] 基础监控接入（Cloud Eye / AOM）

### 第 9–12 周：增强 + 上线准备

- [ ] 实现 Quota / 计费
- [ ] 实现 Context Assembler 优化（reranker、引用来源、冲突处理）
- [ ] 控制台 v1（Workspace 管理 + 知识库管理 + 晋升审核）
- [ ] 备份回档验证
- [ ] 安全审计（渗透测试）
- [ ] 内部试用 + 反馈修复

### 交付验收标准

| 验收项 | 标准 |
|---|---|
| 记忆隔离 | 跨 Workspace 查询不可见 |
| 知识隔离 | 跨 Workspace 检索不可见 |
| 记忆检索延迟 | P99 < 200ms |
| 知识检索延迟 | P99 < 500ms |
| 晋升流程 | 手动确认 → 写入知识库 → 可检索 → 可回溯来源 |
| 备份回档 | 利用 RDS 原生 PITR |
| 安全 | 跨租户无数据泄露、API Key 不可伪造 |

---

## 9. 6–12 个月演进路线

### 6 个月（P1 增强）

- [ ] Apache AGE 图增强（验证 LightRAG PGGraphStorage 与 AGE 版本兼容性后引入）
- [ ] 记忆治理：重复检测、冲突处理、置信度评分、热度管理、归档策略
- [ ] 评测框架完善：中文 golden set、幻觉评测、检索评测、隔离测试
- [ ] SDK（Python / JS）
- [ ] LangGraph Agent Runtime 集成
- [ ] 批量 API + 异步任务 + Webhook

### 9–12 个月（P2 平台化）

- [ ] 多模型支持（多 LLM 提供商、多 embedding 模型）
- [ ] 知识图谱增强：时间知识图谱（Graphiti 风格）、事实有效期、失效检测
- [ ] 记忆与知识的语义映射：跨记忆/知识库的实体对齐
- [ ] 高级晋升：自动晋升 + 事实校验 Agent + 质量评估 Agent
- [ ] 高级知识管理：版本管理、冲突合并、知识生命周期
- [ ] 性能优化：准确率、延迟、成本优化
- [ ] 开放 API + 生态集成

---

## 10. 关键风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| AGE 1.8.0+ 崩溃 | PG backend segfault + crash recovery | 一期使用 PGTableGraphStorage，二期再验证 AGE |
| Mem0 API 变更 | 升级后接口不兼容 | 锁定版本 + 封装统一 API 隔离 |
| LightRAG 社区演进方向变化 | 功能与需求偏离 | 外置控制面 + 独立 schema 设计 |
| LLM 抽取质量差 | 记忆/知识内容不准确 | 评测框架 + 置信度 + 人工审核 + 回滚 |
| 晋升质量低 | 垃圾知识进入知识库 | Promotion Bridge 评审流 + PII 检测 + 冲突检测 |
| 多租户泄露 | 安全事故 | RLS + 行级隔离测试 + 渗透测试 |
| 华为 MaaS embedding 质量 | 影响检索准确率 | 提前评测 + 备选 embedding 模型 |
| Cognee PG 图后端是 demo | 如果选择 Cognee 会导致生产事故 | **本方案不选 Cognee 作为知识库底座** |

---

## 11. 源码证据索引

| 结论 | 文件路径 | 行号 |
|---|---|---|
| Mem0 支持 pgvector | `/tmp/agent-memory-evidence/mem0/mem0/vector_stores/pgvector.py` | :146 |
| Mem0 记忆 CRUD API | `/tmp/agent-memory-evidence/mem0/mem0/memory/main.py` | :760/:1379/:1255/:462/:1869 |
| LightRAG 版本 | `/tmp/agent-memory-evidence/lightrag/lightrag/_version.py` | `__version__ = "1.5.8"` |
| LightRAG AGE 拒绝 1.8.0+ | `/tmp/agent-memory-evidence/lightrag/lightrag/kg/postgres_impl.py` | :124 |
| LightRAG AGE 崩溃说明 | `/tmp/agent-memory-evidence/lightrag/lightrag/kg/postgres_impl.py` | :928–940 |
| LightRAG PGTableGraphStorage | `/tmp/agent-memory-evidence/lightrag/lightrag/kg/pgtable_impl.py` | :1–60 |
| Cognee PG 图存储是 demo | `/tmp/agent-memory-evidence/cognee/cognee/infrastructure/databases/graph/postgres_demo/` | 目录名 |
| Cognee improve() API | `/tmp/agent-memory-evidence/cognee/cognee/api/v1/improve/improve.py` | :101 |
| LangGraph PG Store | `/tmp/agent-memory-evidence/langgraph/libs/checkpoint-postgres/langgraph/store/postgres/base.py` | — |
| Mem0 版本 | `/tmp/agent-memory-evidence/mem0/pyproject.toml` | version = "2.1.0" |
| Cognee 版本 | `/tmp/agent-memory-evidence/cognee/pyproject.toml` | version = "1.6.0" |
| LangGraph 版本 | `/tmp/agent-memory-evidence/langgraph/libs/checkpoint-postgres/pyproject.toml` | version = "3.1.2" |

---

## 12. 前置条件确认清单

上线前需要与华为云内部确认：

| 事项 | 状态 | 说明 |
|---|---|---|
| RDS PostgreSQL pgvector 版本 | 待确认 | 确认 HNSW 索引支持 |
| RDS PostgreSQL 是否支持安装 AGE | 待确认 | 如 AGE 版本 < 1.8.0 则可使用 LightRAG PGGraphStorage |
| 华为 MaaS embedding 模型性能 | 待评测 | 中文语义检索准确率 |
| Pangu LLM API 可用性 | 待确认 | 用于记忆抽取/知识归纳/冲突检测 |
| RDS 是否允许安装 pg_jieba | 待确认 | 中文全文检索增强 |
| API Gateway / IAM 配额 | 待确认 | 产品 API 配额 |
| FunctionGraph / CCE 执行异步任务 | 待确认 | 文档 ingestion / 夜间整理 |

---

## 13. 多 Agent 检视记录

本次调研由多角色多轮检视完成：

| 角色 | 主要贡献 |
|---|---|
| Agent Memory 专家 | 确认 Mem0 能力边界、Mem0 非完整产品、Promotion Bridge 必要性 |
| LLM 专家 | 确认 embedding/LLM 替换方案、抽取质量风险、成本控制策略 |
| 数据库专家 | 确认 PGTableGraphStorage 生产可用性、AGE 版本风险、RLS 隔离方案 |
| 开源/许可证专家 | 确认许可证合规（Apache-2.0）、OpenViking AGPL 风险、不 fork 策略 |
| 子代理 Bohr | 确认 LangGraph 可作为可选 Agent Runtime，不应替代 ContextDB 控制面 |
| 子代理 Arendt | 从工程角度检视架构合理性 |
| 子代理 Mencius | 从产品/商业角度检视差异化竞争力 |

---

## 14. 给领导的一句话总结

> 我们可以用 Mem0 + LightRAG + RDS PostgreSQL 组合出 ContextDB 的核心能力，3 个月内上线 MVP。最大的差异化是"一个 PG 实例跑全部数据面"和"开源可审计的记忆晋升工作流"。核心风险不在开源组件，而在自研控制面的工程质量——这正是我们 RDS 团队的强项。

---

## 18. 开源事实复核结论（2026-09-23）

本节是针对“Cognee Star 数量错误”的补充复核，避免早期非结构化记忆污染结论。

### 18.1 GitHub API 事实

| 项目 | Star 数 | 最新版本 | 许可证 |
|---|---:|---|---|
| Mem0 | 65,865 | v2.1.0 | Apache-2.0 |
| LightRAG | 39,823 | v1.5.7 | MIT |
| GraphRAG | 36,077 | v3.1.2 | MIT |
| Cognee | 30,934 | v1.6.0 | Apache-2.0 |
| LangGraph | 42,164 | v1.2.12 | MIT |
| LlamaIndex | 52,290 | v0.14.25 | MIT |

结论：此前报告中“Cognee ~7k stars”错误，应更正为 **30,934**；Mem0 “~35k” 也已过时，当前为 **65,865**。

### 18.2 Cognee 图存储精确结论

之前结论“Cognee 不支持图存储”表述不准确。源码结论应为：

1. **Cognee 支持图存储后端**，包括 Ladybug/Kuzu、Neo4j、Neptune、Postgres Demo 和 Turso。
2. **PostgreSQL 作为图存储路径明确不是生产就绪**。`get_graph_engine.py:383-387` 直接写着：
   - `DEMO: Postgres as a graph store is not production-ready`
   - 要求生产环境使用 graph-native backend（Kuzu、Neo4j）。
3. `PostgresDemoAdapter` 类位于 `postgres_demo`，其 docstring 明确称这是 reference graph adapter。
4. 该 PG Demo 适配器不是空实现，实现了大量 `GraphDBInterface` 方法，支持 `graph_node` / `graph_edge` 表、覆盖索引和 GIN 索引；但这不改变源码自身“demo / not production-ready”的定位。

因此，本项目拒绝把 Cognee 作为“RDS PostgreSQL 统一栈知识库底座”的结论仍然成立，理由应精确为：**Cognee 的 PostgreSQL 图存储路径明确标注为 demo，不适合华为云 RDS PG 一期商用主路径。**

### 18.3 其他开源软件声明复核

| 项目 | 复核结论 |
|---|---|
| Mem0 | v2.1.0 是最新版本；`Memory.add/search/get_all/update/delete` API 存在；pgvector 后端存在。结论不变。 |
| LightRAG | 最新正式发布是 v1.5.7；主分支版本号已是 v1.5.8。`PGTableGraphStorage` 存在且明确声明使用普通 PostgreSQL 表，不依赖 AGE/pgvector。结论不变。商用应优先锁 v1.5.7，而不是直接锁主分支版本号。 |
| GraphRAG | v3.1.2。内置存储是 LanceDB；Azure 路径是 Azure AI Search / CosmosDB。未发现 PostgreSQL 作为一等存储后端。原表“偏 Azure/Cosmos”表述应更精确为“默认 LanceDB，云路径偏 Azure/CosmosDB”。 |
| LangGraph | LangGraph 最新版本是 v1.2.12；`langgraph-checkpoint-postgres` 是 v3.1.2。此前把 v3.1.2 写成 LangGraph 版本号不准确，二者是不同包。 |
| LlamaIndex | 最新版本 v0.14.25。`PGVectorStore` 是一等 vector store，但不是完整 ContextDB / 知识库产品。结论不变。 |

### 18.4 对最终推荐的影响

推荐架构不变：**Mem0 + LightRAG + 自研控制面 + RDS PostgreSQL**。

理由：

1. Mem0 社区规模和记忆 API 仍然最强。
2. LightRAG 的 PGTableGraphStorage 是唯一有源码证据支撑、面向普通 PostgreSQL 表的完整图存储路径。
3. Cognee 虽然社区规模被低估，但其 PG 图路径的商用风险由源码注释和目录命名双重确认。
4. GraphRAG、LangChain/LangGraph、LlamaIndex 仍分别是全量图 RAG、Agent 框架、通用 RAG 框架，不是可直接替换 LightRAG 的 PG-native 知识库底座。

---

## 15. 计费模式设计

### 15.1 友商计费信号

| 厂商 | 计费模式 | 关键含义 |
|---|---|---|
| 阿里云 ContextDB | 存储 + API 调用按量计费，不暴露实例 CPU / 内存规格 | 控制面把底层资源池化，用户按 Context 消耗付费 |
| 火山引擎 VikingDB | CU + 存储 + 文件数量按量计费，不暴露实例规格 | 采用共享服务 + 逻辑多租户，底层实例被抽象掉 |

**推导结论：** 当产品不再暴露实例规格，而是以存储、请求、Token 或 CU 计费时，底层大概率已经不是“一客户一实例”，而是共享基础设施上的逻辑多租户模型。计费方式本身不能 100% 证明部署形态，但强烈指向 SaaS / Serverless 化架构。

### 15.2 推荐计费模型

MVP 阶段仍可基于专属实例托管计费，保留 RDS 现有商业形态；但产品计费指标应从第一天就按能力抽象，而不是暴露开源组件细节。

| 计费项 | 计费方式 | 说明 |
|---|---|---|
| Context 存储费 | GB·月 | 覆盖关系数据、向量、图、全文索引和备份放大 |
| API 请求费 | 千次或 Credits | Ingest / Search / Recall / Promote 等读写请求 |
| LLM Token 费 | 千 Token | 抽取、摘要、问题生成、答案合成 |
| Embedding Token 费 | 千 Token | 文档切片、记忆写入、查询向量化 |
| 晋升任务费 | 次数或 Credits | 记忆晋升知识、去重、冲突合并、图谱更新 |

MVP 可先实现“RDS 实例费 + 存储 + API + 模型 Token”的混合计费；共享池化后再收敛为 Credits + 存储模式。

---

## 16. 多租户架构演进

### 16.1 三个阶段

| 阶段 | 时间 | 部署形态 | 隔离方式 | 适用客户 |
|---|---|---|---|---|
| 阶段 1：MVP | 0–3 个月 | 一客户一 RDS PG 实例 | 实例级隔离 + Workspace | 金融、政务、大客户；试点客户 |
| 阶段 2：共享池 | 6 个月左右 | 多客户共享 PG 实例池 | Database / Schema / Row-Level Security | 中小客户、长尾场景 |
| 阶段 3：Serverless | 9–12 个月以上 | 计算与存储分离，按 CU 弹性 | Workspace + 资源组 + 存储配额 | 对标阿里 / 火山的公有云模式 |

### 16.2 MVP 的多租户基础

即使阶段 1 采用专属实例，也应从第一天引入以下模型：

```text
tenant_id      -> 租户 / 账号
project_id     -> 项目或应用
workspace_id   -> Agent 或业务空间
user_id        -> 用户级记忆作用域
agent_id       -> Agent 作用域
run_id         -> 会话或任务作用域
```

关键支撑：

1. **Mem0 原生作用域：** `user_id`、`agent_id`、`run_id` 可直接映射到租户内记忆隔离。
2. **LightRAG PG 表模型：** PGTableGraphStorage 的图、实体、关系表带有 workspace / namespace 字段，可承接逻辑空间隔离。
3. **PG RLS：** 所有 ContextDB 自研表启用 `tenant_id` + `workspace_id` 的 Row-Level Security，控制面强制注入租户上下文。
4. **连接与配额：** 通过控制面限制每租户连接数、Ingest 并发、异步任务数、存储增长和模型调用 QPS。

### 16.3 阶段 2 的路由模型

```text
API Gateway
  -> ContextDB Control Plane
       -> Tenant Registry / Workspace Router
       -> PostgreSQL Instance Pool
       -> Async Worker Pool
       -> Huawei MaaS / Pangu Model Gateway
```

控制面维护：

- `tenant_id -> pg_instance_id` 路由；
- 实例容量、连接数、磁盘水位；
- Workspace 创建、迁移和暂停状态；
- 计量事件与配额。

这不是改造 Mem0 或 LightRAG，而是在外置控制面完成路由、隔离和调度。

### 16.4 从实例托管走向 Serverless 的演进方式

1. **第一阶段不承诺 Serverless：** 先用专属实例满足企业级隔离需求，降低 3 个月上线风险。
2. **第二阶段做共享实例池：** 小客户合并到共享 PG，大客户保留专属实例，形成混合部署。
3. **第三阶段做资源抽象：** 把 PG 实例拆为计算层、存储层、异步任务层，按 CU 和 GB·月计费。
4. **冷热分层：** 热记忆和热知识放高性能 PG，冷上下文归档到对象存储，检索时按需回温。

---

## 17. 单 PG 实例达到存储和性能上限时如何扩展

### 17.1 扩展判断指标

不能只看磁盘容量。应按四类水位触发不同扩展动作：

| 上限类型 | 关键指标 | 阈值建议 |
|---|---|---|
| 存储上限 | 磁盘容量、WAL 增长、备份窗口 | 70% 触发扩容 / 分层，80% 触发治理 |
| 写入上限 | Ingest TPS、异步任务积压、WAL 生成速率 | 持续排队即拆分写入面 |
| 查询上限 | P95 查询延迟、连接数、CPU / IOPS | P95 超目标且优化 SQL 无效 |
| 数据规模上限 | 单表行数、索引膨胀、图边数量、向量数 | 触发分区、冷热分层或拆 Workspace |

### 17.2 优先级扩展路径

#### 第一步：实例内优化

1. **冷热分层：** 近期会话、活跃记忆、活跃知识留在主库；长期不活跃上下文归档到 OBS，并保留摘要 / 索引。
2. **按时间分区：** 记忆事件、对话消息、Ingest 日志、审计日志按 `workspace_id` + 时间分区。
3. **索引治理：** HNSW / IVFFlat 参数按数据量调优；全文索引、图索引定期重建或 REINDEX。
4. **异步化：** 文档抽取、图谱构建、重排序、晋升任务全部放入队列，避免写入请求长事务阻塞。
5. **只读副本：** Search / Recall / 分析查询切到只读副本；Ingest 仍走主库。

这一步通常能先把单实例的可用区间拉长，避免过早引入跨实例拆分。

#### 第二步：逻辑拆分

ContextDB 天然存在三类数据，最适合分别拆分：

| 数据类型 | 拆分方式 | 原因 |
|---|---|---|
| Memory | 按 `tenant_id` / `agent_id` 拆到独立 PG | 写入频繁，作用域清晰 |
| Knowledge | 按 Workspace 或领域拆到独立 PG | 文档、实体、关系有业务边界 |
| Audit / Metrics | 独立 PG / 日志服务 / 时序库 | 大量追加数据，不参与核心检索 |

优先按 **Workspace** 拆，而不是按哈希随机拆。原因是记忆晋升、知识去重、图谱更新都依赖 Workspace 内数据局部性。

#### 第三步：实例池水平扩展

```text
ContextDB Control Plane
  -> Workspace Router
      -> PG Cluster A : tenant A / B / C
      -> PG Cluster B : tenant D / E
      -> PG Cluster C : tenant F / G
  -> Global Catalog
  -> Search Aggregator
```

控制面保存全局目录：

- Workspace 当前所属 PG 实例；
- Workspace 状态与容量；
- 跨 Workspace 搜索是否允许；
- 迁移中的只读标记。

对用户暴露的仍是统一 API，例如：

```http
POST /workspaces/{workspace_id}/search
POST /workspaces/{workspace_id}/memory/recall
POST /workspaces/{workspace_id}/promote
```

控制面根据 `workspace_id` 路由到目标 PG，不需要 Mem0 / LightRAG 感知全局拓扑。

#### 第四步：迁移与重平衡

标准流程：

1. Workspace 标记为可迁移或只读；
2. 逻辑复制或逻辑导出该 Workspace 的表数据；
3. 迁移 Mem0 表、LightRAG 图表、向量表、全文索引、晋升元数据；
4. 在目标实例校验行数、向量数、图边数和抽查召回结果；
5. 控制面切换路由；
6. 短时间保留旧实例数据，确认后清理。

如果采用“Workspace 为不可再分单元”，迁移不需要复杂分布式事务。缺数据最多影响单个 Workspace 的检索完整性，不会污染其他租户。

### 17.3 不建议在 MVP 阶段直接做的方案

| 方案 | 为什么不建议 MVP 做 | 后续可用于 |
|---|---|---|
| Citus / Distributed PostgreSQL | 涉及分布式事务、跨分片图查询和运维复杂度 | 单 Workspace 超大、写入 TPS 极高时 |
| 跨实例联邦图查询 | Apache AGE 图查询难跨库合并，结果排序和一致性复杂 | 全局知识图谱 |
| 强一致全局检索 | 跨多 PG 的实时强一致成本高 | 需要明确业务场景时 |
| 自研跨分片图存储 | 3 个月内不可控 | 12 个月后平台化方向 |

### 17.4 结论

单 PG 实例上限不是架构死点，但会改变产品边界：

1. **3 个月 MVP：** 继续使用“单实例跑全部数据面”，重点做好分区、只读副本、冷热分层和 Workspace 抽象。
2. **中型扩展：** 按 Workspace 把 Memory / Knowledge / Audit 拆到不同 PG 实例，由控制面路由。
3. **长期扩展：** 进入共享实例池或 Serverless 模式，控制面负责 Workspace 生命周期、迁移、容量和计费。
4. **核心设计原则：** Workspace 是隔离、路由、迁移、计费和重平衡的基本单位。只要 MVP 不把单实例拓扑写死进 API，后续水平扩展是可控演进，不需要推翻 Mem0 + LightRAG 架构。
