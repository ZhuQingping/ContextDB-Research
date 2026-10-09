# ContextDB-Research

Agent Memory 与 ContextDB 技术调研仓库。当前主线是评估基于 PostgreSQL 的开源 Agent Memory / Context 服务，并沉淀可评审的设计、验证与选型证据。

## 当前结论

- **首选路线**：Hindsight + RDS PostgreSQL + 自研云控制面。Hindsight 覆盖记忆、知识、检索与多租户扩展点，许可证为 MIT。
- **备选路线**：Mem0 + LightRAG + 自研控制面。该组合职责清晰，但需要额外打通统一上下文、租户治理和知识晋升。
- **Graphiti**：时序知识图谱能力强，但主路径不是 PostgreSQL-first，适合作为后续图谱增强储备。
- **Cognee**：可作为工程与知识管线参考，但其 PostgreSQL 图后端官方标注为 demo / not production-ready。

## 报告索引

### 本次本地部署与服务化核验

2026-10-04，基于实际源码、真实 GPT 调用与官方资料重新核验。此前 Agent 报告仅作线索，不自动继承其结论。

| 文档 | 说明 |
|---|---|
| [Hindsight 本地体验与验收](deployments/hindsight-local/README.md) | UI／API／MCP 入口、启停、真实验证日志和已发现边界 |
| [华为云 ContextDB 首期服务化架构](hindsight/cloud-service-architecture.md) | 5 人 6–8 周范围、端到端职责、PG 服务单元扩展、接口开放与上线门槛 |
| [首期竞争力与投入顺序](hindsight/cloud-service-priorities.md) | 三家竞品对照、接入／成本／数据库复盘场景的投入优先级 |
| [核验依据](hindsight/cloud-service-evidence.md) | 固定源码和官方来源，纠正 Star 排名、榜单解释及历史多 PG 实验证明范围 |

### 决策与选型

| 文档 | 说明 | 更新日期 |
|---|---|---|
| [Agent Memory 选型复核：Hindsight 优先推荐](reports/agent-memory-selection-review.md) | 当前首选路线、替代路线与风险边界 | 2026-09-28 |
| [Cognee / Hindsight / Graphiti 三选一对比](reports/cognee-hindsight-graphiti-comparison.md) | 主底座选型的横向对比与决策依据 | 2026-09-29 |

### Hindsight 专项

| 文档 | 说明 |
|---|---|
| [快速熟悉 Hindsight 与 Agent Memory](hindsight/快速熟悉Hindsight与AgentMemory.md) | 概念速览、阅读路线、基础论文和 ContextDB 架构师验证问题 |
| [多 PG 实例横向扩展方案](hindsight/multi-pg-scaling-design.md) | schema 级横向扩展设计与灰度路径 |
| [多 PG 实例验证报告](hindsight/multi-pg-scaling-validation.md) | 13 项验证结果与证据 |
| [多 PG 实例评审导览](hindsight/multi-pg-scaling-review-guide.md) | 评审入口、关键决策与复核顺序 |
| [多 Bank 隔离与云化 Gateway 设计](hindsight/bank-isolation-gateway.md) | 租户内 Bank 隔离、访问模型与 Gateway 边界 |
| [后端存储格式调研](hindsight/backend-storage.md) | PG、向量、全文、图存储与租户模型 |
| [Claude Code × Hindsight 交互机制](hindsight/claude-code-integration.md) | recall / retain 链路与 ContextDB 概念映射 |

### 备选方案与专项分析

| 文档 | 说明 |
|---|---|
| [Cognee PG 后端存储与横向扩展分析](cognee/pg-backend-and-scaling.md) | Cognee PostgreSQL 存储、约束与扩展思路 |
| [TencentDB Agent Memory](tencentdb/agent-memory-internals.md) | TencentDB Agent Memory 的分层记忆、召回与去重机制 |

### 历史归档

以下文档保留为早期调研证据，不代表当前推荐结论：

| 文档 | 状态 |
|---|---|
| [Agent Memory 开源选型与 ContextDB 可行性报告](reports/archive/agent-memory-open-source-selection.md) | 已被 Hindsight 优先复核报告取代 |
| [华为云 ContextDB：Mem0 + LightRAG 选型与落地报告](reports/archive/huawei-cloud-mem0-lightrag.md) | 已调整为备选路线 |
| [ContextDB 开源组合平替方案（领导版）](reports/archive/contextdb-open-source-alternatives-leader.md) | 早期汇报材料 |

## 资产

- [RDS ContextDB 产品概览](assets/rds-contextdb-overview.pptx)
- [开源项目 Star 历史图（2026-09-22）](assets/open-source-star-history-2026-09-22.png)

## 仓库约定

- 活跃文档使用“主题优先”命名；创建/更新日期写入正文或索引。
- `reports/archive/` 只存放历史结论，引用时应注意其时效性。
- `tdai-memory/` 仅保留本地 SQLite 数据快照，用于查看关键记忆和元数据；不纳入 Git。
