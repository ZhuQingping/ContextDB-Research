# ContextDB-Research

Agent Memory 与 ContextDB 技术调研仓库。当前主线是评估基于 PostgreSQL 的开源 Agent Memory / Context 服务，并沉淀可评审的设计、验证与选型证据。

## 当前结论

- **首选路线**：Hindsight + RDS PostgreSQL + 自研云控制面。Hindsight 覆盖记忆、知识、检索与多租户扩展点，许可证为 MIT。
- **备选路线**：Mem0 + LightRAG + 自研控制面。该组合职责清晰，但需要额外打通统一上下文、租户治理和知识晋升。
- **Graphiti**：时序知识图谱能力强，但主路径不是 PostgreSQL-first，适合作为后续图谱增强储备。
- **Cognee**：可作为工程与知识管线参考，但其 PostgreSQL 图后端官方标注为 demo / not production-ready。

## 报告索引

当前 Hindsight v1.0.0 的部署、设计与代码评审从[服务化文档索引](hindsight/README.md)进入；下列早期报告保留作历史对照。

### 本次本地部署与服务化核验

2026-10-04，基于实际源码、真实 GPT 调用与官方资料重新核验。此前 Agent 报告仅作线索，不自动继承其结论。

| 文档 | 说明 |
|---|---|
| [Hindsight 本地体验与验收](deployments/hindsight-local/README.md) | UI／API／MCP 入口、启停、真实验证日志和已发现边界 |
| [Hindsight Cloud 与开源版实测及部署建议](hindsight/hindsight-cloud-open-source-comparison.md) | 商业版与开源版真实差异、Cloud 部署证据边界、控制面/数据面拆分和华为云 Data Cell 方案 |
| [ContextDB 成员与 API Key 管理设计](hindsight/member-and-apikey-management-design.md) | 阿里云控制台实测、成员与 Key 关系、Hindsight Organization 的产品原因，以及华为云首期是否需要组织层 |
| [ContextDB 首发完整设计（当前优化版）](hindsight/member-apikey-bank-service-design-first-release.md) | 按实例管理、UI 管理、应用访问组织，保留完整接口、PG 约束、认证及恢复细节 |
| [ContextDB 首发优化与验收](hindsight/contextdb-optimization-backlog.md) | 当前决策、实现状态和四领域复核入口 |
| [ContextDB 首发部署与 API 验证](hindsight/implementation/contextdb-optimized-guide.md) / [curl 用例](hindsight/implementation/contextdb-management-api-curl-guide.md) | 离线初始化、启动升级及多空间、多用户验证 |
| [ContextDB 服务化设计 v1（历史详细版）](hindsight/member-apikey-bank-service-design.md) | 工作空间内成员、单空间 Key；恢复原架构图、9 张 PG 表、16 个管理操作及实现说明 |
| [ContextDB 服务化设计 v2（当前实现）](hindsight/member-apikey-bank-service-design-v2.md) | 实例级用户、多空间 Key、管理员 UI；含架构流程、8 张表、18 个管理操作及实现入口 |
| [ContextDB V2 总体架构](hindsight/contextdb-v2-architecture.md) | 业务访问、云管控、UI 管理三个场景，以及 API/Worker 与 PG 元数据、用户数据的关系 |
| [ContextDB V2 管控联调](hindsight/contextdb-v2-control-plane-integration.md) | PG 插件与配置、实例初始化/服务启停、空间创建/删除/轮询的具体命令与脚本；节点 Agent 调度边界 |
| [ContextDB V2 管控命令审核](hindsight/implementation/contextdb-v2-control-plane-executable-review-2026-10-15.md) | 16 项模拟验证、架构师与资料审核结论；真实部署与云端联调尚未执行 |
| [ContextDB 管理 REST 合同 v1](hindsight/api/contextdb-control-plane-v1.openapi.yaml) | 原 16 个内部管控操作的历史合同，配套 v1 设计 |
| [ContextDB 管理 REST 合同 v2](hindsight/api/contextdb-control-plane.openapi.yaml) | 当前实际路由生成的 18 个操作；区分 Console 管控与 admin/all 管理认证 |
| [ContextDB PG 表设计 v1](hindsight/member-apikey-bank-service-design.md#pg-表设计) / [v2](hindsight/member-apikey-bank-service-design-v2.md#pg-表设计) | 两版字段、约束、索引及事务规则，不能混用 DDL |
| [ContextDB 租户用户与管理员 UI 审阅记录](hindsight/implementation/contextdb-tenant-admin-review-2026-10-15.md) | 夜间开发阶段的专家评审、已修缺陷与历史验证记录 |
| [ContextDB V2 本地自测与验收记录](hindsight/implementation/contextdb-v2-self-test-acceptance-2026-10-15.md) | 正式提交的自测结果、本机体验检查、待完成的模型与云管控验收 |
| [ContextDB 首期实现验收记录](hindsight/implementation/contextdb-service-verification-2026-10-13.md) | 本地测试、接口覆盖、专家交叉检视及未完成的生产联调 |
| [ContextDB v2 本地验证与演示手册](hindsight/implementation/contextdb-v2-local-validation-guide.md) | 代码仓随版验证与演示手册；此处保留入口 |
| [ContextDB v2 部署配置清单](hindsight/implementation/contextdb-v2-deployment-environment.md) | 代码仓随版配置清单；此处保留入口 |
| [ContextDB v2 部署与使用手册](hindsight/implementation/contextdb-v2-deployment-usage-guide.md) | 已迁入代码仓并随 V2 提交维护；此处保留文档入口 |
| [ContextDB 首期设计五专家局部复核](hindsight/implementation/contextdb-design-five-expert-review-2026-10-13.md) | 保留已实现架构，仅校准事实与阅读提示；资料/文档/memory/PG/开发者五视角复核，用户验收未完成 |
| [ContextDB 开发问题与设计差异](hindsight/implementation/contextdb-service-night-task-2026-10-13.md) | 本次实现过程中发现的问题、修复依据与后续优化项 |
| [同 Bank 用户记忆隔离后续研究](hindsight/member-memory-isolation-future-notes.md) | SMIC 跨 Key 证据、tag scope 思路与派生/Worker 风险；非本期实现 |
| [华为云 ContextDB 首期服务化架构](hindsight/cloud-service-architecture.md) | 5 人 6–8 周范围、端到端职责、PG 服务单元扩展、接口开放与上线门槛 |
| [ContextDB 设计与两个月交付专家评审](hindsight/contextdb-design-expert-review.md) | 当前设计权威、实现成熟度、Hindsight 侵入度、产品形态、五人八周计划与上线门 |
| [AgentStratum 长期演进与 AI 工程收敛建议](hindsight/agentstratum-long-term-evolution-and-ai-convergence.md) | 固定代码基线下的产品主链缺口、AI任务合同、CI与团队并行工作建议 |
| [Hindsight Solution 3 与 AgentStratum 定位](hindsight/hindsight-solution3-and-agentstratum.md) | 方案三原型验证与长期产品架构的关系；含当前首期范围提示 |
| [Hindsight Cloud/开源差异实测证据](hindsight/evidence/cloud-vs-local-2026-10-07/cloud-vs-local-summary.json) | 2026-10-07 OpenAPI、运行状态、存储后端可见性和网络探测摘要 |
| [首期竞争力与投入顺序](hindsight/cloud-service-priorities.md) | 三家竞品对照、接入／成本／数据库复盘场景的投入优先级 |
| [ContextDB 差异化竞争力建议](hindsight/competitive-differentiation/ContextDB差异化竞争力.md) | 加密、导出、中文场景等候选能力及验收要求；属于规划建议，不代表当前承诺 |
| [竞争力证据与决策记录](hindsight/competitive-differentiation/ContextDB竞争力证据与决策记录.md) | 竞品/论文来源、历史结论修订、证据等级和未关闭问题 |
| [核验依据](hindsight/cloud-service-evidence.md) | 固定源码和官方来源，纠正 Star 排名、榜单解释及历史多 PG 实验证明范围 |

以上评审和竞争力材料均标注了检查日期与代码/资料基线。竞品价格、版本、社区数据和 AgentStratum 实现状态会变化，引用时应按文内日期理解；当前首期选择以最新明确的产品决策为准。

### 决策与选型

| 文档 | 说明 | 更新日期 |
|---|---|---|
| [Agent Memory 选型复核：Hindsight 优先推荐](reports/agent-memory-selection-review.md) | 当前首选路线、替代路线与风险边界 | 2026-09-28 |
| [Cognee / Hindsight / Graphiti 三选一对比](reports/cognee-hindsight-graphiti-comparison.md) | 主底座选型的横向对比与决策依据 | 2026-09-29 |

### Hindsight 专项

| 文档 | 说明 |
|---|---|
| [快速熟悉 Hindsight 与 Agent Memory](hindsight/快速熟悉Hindsight与AgentMemory.md) | 概念速览、阅读路线、基础论文和 ContextDB 架构师验证问题 |
| [Hindsight 开源版多人记忆隔离与知识共享讨论](hindsight/hindsight-opensource-multiuser-isolation-issues.md) | GitHub issue 与维护者结论、Bank/tag/API Key 权限边界，以及 ContextDB 设计建议 |
| [Hindsight 静态租户、API Key 与数据隔离](hindsight/static-tenant-api-key-isolation.md) | TENANT_EXTENSION/TENANT_USERS 配置、组织与多 Key 映射、schema/bank 隔离及原生 UI 凭据 |
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
