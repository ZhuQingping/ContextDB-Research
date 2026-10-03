# ContextDB 开源组合平替方案（领导版）

## 1. 结论

可以用开源组件组合出 **ContextDB 约 70% 的核心能力**，但剩下约 **30% 属于平台工程能力**，需要自研补齐。

ContextDB 的核心价值不是某个单一算法，而是把以下能力做成一个统一服务：

- 长期记忆
- 知识库
- 实体与关系图谱
- 混合检索
- 权限与租户隔离
- 审计与配额
- Agent 自动上下文注入

因此，开源替代路线应采用：

> **开源组件组合 + 自研薄平台层**

---

## 2. 推荐开源组合

| 能力 | 推荐组件 | 作用说明 |
|---|---|---|
| 长期记忆 | Mem0 + PostgreSQL/pgvector | 用户偏好、事实抽取、跨会话记忆、记忆更新 |
| 知识库 / RAG | LightRAG + LlamaIndex + MinerU | 文档解析、切块、向量化、知识召回 |
| 图谱增强 | GraphRAG + Apache AGE / Neo4j | 实体、关系、多跳推理；构建成本高于 LightRAG |
| 统一存储 | PostgreSQL | 业务表、记忆、知识、权限、审计、事件的事实源 |
| 向量检索 | pgvector | 初期够用，规模扩大后可替换为 Qdrant / Milvus |
| 关键词检索 | PostgreSQL FTS / OpenSearch | 补足向量检索在精确匹配上的短板 |
| 文件存储 | MinIO / S3 | 存储原始文档、解析结果、版本快照 |
| API 服务 | FastAPI + LiteLLM | 统一 Context API 和模型网关 |
| 异步任务 | Redis + Celery / Temporal | 记忆提取、文档入库、图谱构建、夜间整理 |
| 治理与观测 | Keycloak + Langfuse + Grafana | 权限、调用追踪、质量评估、监控 |

---

## 3. 建议架构（文字版）

```text
Agent / 应用
   ↓
统一 Context API（自研）
   ├─ Mem0：长期记忆
   ├─ LightRAG / GraphRAG：知识库与图谱
   ├─ PostgreSQL：事实源 + 权限 + 审计
   │   ├─ pgvector：向量检索
   │   ├─ FTS：关键词检索
   │   └─ Apache AGE：实体关系
   ├─ MinIO：原始文件
   └─ Redis + Celery：异步任务
   ↓
LLM Gateway + Reranker
```

---

## 4. 与 ContextDB 的能力映射

| ContextDB 能力 | 开源替代方案 | 自研程度 |
|---|---|---|
| 短期记忆 / 会话上下文 | PostgreSQL + 自研 Session 管理 | 中 |
| 长期记忆 | Mem0 + pgvector | 低 |
| 知识库 | LightRAG / GraphRAG + LlamaIndex + MinIO | 中 |
| 实体卡 | PostgreSQL + Apache AGE | 中 |
| 实体关系图谱 | Apache AGE / Neo4j + GraphRAG | 中高 |
| 混合检索 | pgvector + FTS + Reranker | 中 |
| 记忆演进 / Dream | Celery / Temporal + LLM + 自研策略 | 高 |
| 记忆晋升为知识 | 自研工作流 + 人工审核 | 高 |
| 权限与租户 | PostgreSQL + Keycloak | 中 |
| API Key 与审计 | FastAPI + PostgreSQL | 中 |
| Agent 自动注入 | 自研 CLI / Hook | 高 |
| 控制台 | React / Next.js | 高 |

---

## 5. 必须自研补齐的能力

### 5.1 统一 Context API

对外提供统一接口，覆盖：

- 记忆写入
- 记忆检索
- 知识库上传
- 知识检索
- 实体查询
- 会话上下文获取

建议兼容 **Mem0 API 协议子集**，降低客户端接入成本。

### 5.2 Agent 自动注入

实现两个关键链路：

```text
用户提问前：检索相关记忆和知识，注入上下文
Agent 回答后：提取有价值信息，写入长期记忆
```

这部分是 ContextDB 使用体验的关键，开源组件不会自动提供完整能力。

### 5.3 租户与权限

需要支持：

- Workspace
- Group
- Member
- API Key
- 知识库 ACL
- 记忆隔离

核心原则：

> API Key 服务端解析租户，客户端不能伪造身份。

### 5.4 上下文组装器

决定最终给模型注入哪些内容，需要处理：

- 多路召回
- 去重
- 排序
- token 预算
- 权限过滤
- 引用来源
- 冲突处理

这是开源组合和商业 ContextDB 之间最大的差距之一。

### 5.5 记忆治理

长期记忆不能只写入，不治理。需要实现：

- 重复检测
- 冲突处理
- 置信度
- 重要度
- 过期策略
- 记忆晋升为知识

对应 ContextDB 的 Dream / 夜间演进能力。

### 5.6 文档接入管道

需要补齐：

- 多数据源连接器
- OCR
- 文档解析
- 分块
- 增量更新
- 版本管理

可用 MinerU、LlamaIndex 降低开发成本，但流程编排需要自研。

### 5.7 审计、配额与观测

需要记录：

- 谁读写了什么记忆
- 谁访问了什么知识库
- 调用了多少 token
- 存储了多少数据
- 检索命中率
- 延迟和失败率

可用 Langfuse + Grafana + PostgreSQL 组合实现。

---

## 6. 分阶段实施建议

### 一期：MVP

目标：先跑通“长期记忆 + 知识召回”闭环。

组件：

- PostgreSQL
- pgvector
- Mem0
- LightRAG
- MinIO
- FastAPI
- Redis + Celery

交付：

- 记忆写入与检索
- 文档上传与知识检索
- 基础 API
- 基础权限

### 二期：增强检索与图谱

目标：提升召回质量，补齐实体关系能力。

新增：

- Apache AGE / Neo4j
- GraphRAG
- Reranker
- OpenSearch
- 更完整的租户权限

### 三期：平台化

目标：接近 ContextDB 的产品体验。

新增：

- Dream 记忆演进
- 记忆晋升
- 审计与配额
- Web 控制台
- 质量评测体系

---

## 7. 风险与取舍

| 风险 | 说明 | 应对 |
|---|---|---|
| GraphRAG 构建成本高 | 实体抽取和图谱构建消耗较多 token | 一期先用 LightRAG，二期再引入 GraphRAG |
| pgvector 规模上限 | 超大规模向量检索性能可能不足 | 预留 Qdrant / Milvus 替换路径 |
| 多组件运维复杂 | PostgreSQL、Redis、MinIO、RAG 服务都需要维护 | 先用 Docker Compose，再逐步上 Kubernetes |
| 开源组件能力不完整 | 治理、审计、Agent 注入、记忆晋升需自研 | 明确自研边界，避免误认为拼装即可完成 |
| 数据迁移风险 | 各组件 schema 不统一 | PostgreSQL 作为唯一事实源，其他组件只做索引和投影 |

---

## 8. 给领导的一句话总结

> 我们可以用 Mem0、LightRAG、GraphRAG 和 PostgreSQL 组合出 ContextDB 的核心能力，但真正决定成败的是自研的统一 API、权限治理和上下文组装层。建议先做记忆 + 知识库 MVP，再逐步补齐图谱和平台治理能力。
