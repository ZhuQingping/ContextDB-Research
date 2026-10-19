# ContextDB-Research

Agent Memory 与 ContextDB 技术调研仓库。当前主线是评估基于 PostgreSQL 的开源 Agent Memory / Context 服务，并沉淀可评审的设计、验证与选型证据。

## 当前结论

- **首选路线**：Hindsight + RDS PostgreSQL + 自研云控制面。Hindsight 覆盖记忆、知识、检索与多租户扩展点，许可证为 MIT。
- **备选路线**：Mem0 + LightRAG + 自研控制面。该组合职责清晰，但需要额外打通统一上下文、租户治理和知识晋升。
- **Graphiti**：时序知识图谱能力强，但主路径不是 PostgreSQL-first，适合作为后续图谱增强储备。
- **Cognee**：可作为工程与知识管线参考，但其 PostgreSQL 图后端官方标注为 demo / not production-ready。

## 报告索引

当前 Hindsight v1.0.0 的部署、设计与代码评审从[服务化文档索引](hindsight/README.md)进入；下列早期报告保留作历史对照。

### Hindsight 当前文档

| 任务 | 入口 |
| --- | --- |
| 设计与代码评审 | [完整设计](hindsight/design/contextdb-release-design.md) · [代码检视](hindsight/design/code-review-guide.md) |
| 管理接口、参数、返回值、可执行用例 | [API/curl 手册](hindsight/api/contextdb-management-api-curl-guide.md) |
| 自研版本部署 | [联调指南](hindsight/deployment/contextdb-service-integration-guide.md) · [部署合同](hindsight/deployment/contextdb-deployment-contract.md) |
| 官方原生 v1.0.0 对接 | [联调指南](hindsight/deployment/native-v1.0.0/contextdb-service-integration-guide.md) · [部署合同](hindsight/deployment/native-v1.0.0/contextdb-deployment-contract.md) |
| 运维与验证 | [运维](hindsight/operations/contextdb-operations-runbook.md) · [验证摘要](hindsight/testing/contextdb-validation-summary.md) |
| 历史方案与过程材料 | [归档索引](hindsight/archive/README.md) |

当前代码和文档版本对应见代码检视指南。原生与自研的部署初始化、认证不同，不混用两套手册。

### 决策与选型

| 文档 | 说明 | 更新日期 |
|---|---|---|
| [Agent Memory 选型复核：Hindsight 优先推荐](reports/agent-memory-selection-review.md) | 当前首选路线、替代路线与风险边界 | 2026-09-28 |
| [Cognee / Hindsight / Graphiti 三选一对比](reports/cognee-hindsight-graphiti-comparison.md) | 主底座选型的横向对比与决策依据 | 2026-09-29 |

### Hindsight 专题与历史研究

[竞争力与证据](hindsight/archive/2026-10-19-before-reorganization/competitive-differentiation/ContextDB差异化竞争力.md)保留为研究资料；早期选型、静态租户、PG 扩展、多 PG、云端对比及阿里 UI 试验从[历史归档](hindsight/archive/README.md)追溯，不作为当前实现承诺或部署要求。

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
