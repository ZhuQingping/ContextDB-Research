# Hindsight Solution 3 与 AgentStratum 的定位和长期价值

日期：2026-10-08

> **范围更新（2026-10-09）**：本文记录方案比较时的演进关系，不是当前首期范围批准。当前首期已明确为独享版：每租户一个 Hindsight 计算节点和一个 PG 实例。方案三中的共享Cell只作为已完成原型的拓扑验证；不要据本文将共享版列为首期交付。后续是否建设共享版仍需容量、成本和隔离目标支持。

## 1. 结论

Hindsight Solution 3 和 AgentStratum 不是同一层级的替代方案。

- Hindsight Solution 3 是短期服务化方案，重点证明多个租户可以共享 Data Cell，Gateway 可以完成租户到 Cell 的路由，Hindsight API 与 Worker 可以分离部署，租户数据可以通过 PostgreSQL schema 和独立 Cell 隔离。
- AgentStratum 是长期产品架构，目标是在 Hindsight 原生能力之上建立完整的多租产品边界，包括身份授权、业务处理、控制面、原件与任务恢复、模型治理、运维、升级退出和长期产品资产。

长期方向不是放弃 Solution 3 后重做一套系统，而是以 Solution 3 已验证的 Cell、API、Worker 和 PostgreSQL 拓扑为运行基础，逐步演进到 AgentStratum 的 Gateway、Handler、Worker、Control、LLM Adapter 和产品数据模型。

如果目标只是让多个租户安全共享 Hindsight，Solution 3 已经具备很高的短期价值。如果目标是形成能够长期商用、持续演进和运营的 ContextDB 产品，AgentStratum 的核心方向值得继续建设。

## 2. 两种方案解决的问题

| 维度 | Hindsight Solution 3 | AgentStratum | 长期收益 |
|---|---|---|---|
| 主要目标 | 验证共享型与独享型 Cell 的可运行拓扑 | 建设完整多租 Agent 数据与记忆产品 | 从服务部署提升为产品能力 |
| 租户身份 | API Key 映射 tenant 和 schema | Tenant、Subtenant、Principal、Agent、Bank Grant | 支持团队、成员、服务账号和共享授权 |
| Gateway | 选择 Cell，并在 Cell 内轮询 Hindsight API | 身份、会话、动作授权、限流、背压、审计和私有签名转发 | 建立真正的公共安全边界 |
| 在线业务 | Hindsight API 同时处理协议和 MemoryEngine 业务 | 独立 Handler 处理 Retain、Recall、Reflect 和业务管理 | 协议层与业务计算可独立扩缩和发布 |
| Worker | 复用原生 PostgreSQL 任务表和 Worker | 增加任务委托、UNKNOWN、hold、Attempt 和恢复边界 | 故障后避免盲目重发和旧执行者迟到写 |
| 元数据 | 单 Gateway SQLite placement | MetaPG 管理身份、Grant、配置版本、placement 和开通状态 | 支持多 Gateway 和可信配置发布 |
| 用户数据 | Cell 内 tenant schema，独享租户使用独立 Cell | DataPG 方案 B，运行域和用户数据域按 schema、角色和 Unit 分离 | 更清晰的事务、权限和恢复边界 |
| 原件 | 主要沿用 Hindsight 当前输入和存储行为 | 原件先进入对象存储，校验完成后再登记耐久任务 | 支持重建、恢复和原件追踪 |
| 模型 | Hindsight 进程直接配置 provider | 独立 LLM Adapter 管理 generate、embed、rerank、凭据和使用量 | 支持模型治理、费用观察和供应商演进 |
| 扩展 | 固定 Cell 内扩 API 和 Worker | Gateway、Handler、Worker、Control、Model 和 DataPG 分别扩展 | 避免把所有瓶颈绑定到同一种进程 |
| 产品资产 | Bank、Memory、Document 等原生对象 | Knowledge、Memory、Session、Skill、Trial、Release 等长期对象 | 支持 Agent 经验资产和更完整生命周期 |

AgentStratum 的三类运行职责已经由 [ADR-0002](https://github.com/RSIXDB/agentstratum/blob/main/docs/decisions/ADR-0002-functional-cluster-separation.md) 固定：Gateway 只承担公共协议和治理，Handler 承担在线业务，Worker 承担异步处理。团队多租、MetaPG、DataPG、模型适配和原件顺序由 [ADR-0003](https://github.com/RSIXDB/agentstratum/blob/main/docs/decisions/ADR-0003-tenant-stateless-pg-model-goals.md) 与 [ADR-0004](https://github.com/RSIXDB/agentstratum/blob/main/docs/decisions/ADR-0004-initial-design-baseline.md) 进一步明确。

## 3. AgentStratum 工作量大的根本原因

AgentStratum 的工作量大，不是因为把 Solution 3 的 Gateway 写得更复杂，而是因为它把一个可运行的 Hindsight 服务扩展成完整产品。

主要新增责任包括：

1. 建立团队、成员、服务账号、Bank 和 Grant 的产品身份模型。
2. 把公共接入、在线业务和后台任务拆为独立功能集群。
3. 建立 MetaPG 控制权威以及 Unit、DataPG 和计算实例之间的 placement。
4. 将原件、受理、任务、模型调用、提交和最终状态组成可恢复链路。
5. 处理模型调用已经发生但结果未知、费用未知或本地提交失败的情况。
6. 支持权限撤销、配置变更、凭据轮换、任务停用和历史责任保留。
7. 建立部署、诊断、备份恢复、升级、退出和非作者接手能力。
8. 为 Knowledge、Memory、Session 和 Skill 等长期产品资产保留演进空间。

这些内容大量属于客户看不到的内部能力，但决定系统是否能长期安全运营。它们不能简单用“接口能成功返回”或“存在多个副本”来替代。

## 4. 完整产品蓝图不等于短期交付清单

可以将你的理解表述为：

> AgentStratum 描述的是整个产品服务化和长期持续建设的目标形态。其中一部分能力不是短期客户直接需要的，应随着客户规模、运营要求和产品承诺逐步建设，而不是在第一版一次性完成。

这个理解是正确的，但需要补充一个重要边界：客户暂时看不到，不代表所有内部能力都可以后置。部分能力虽然不是客户功能，却是短期服务成立的正确性前提。

### 4.1 短期必须守住的内部正确性

这些能力不一定出现在客户界面上，但多租服务一旦开放就必须成立：

- 可信身份不能由客户端伪造 tenant、schema 或内部路由头。
- Bank 和数据必须有明确租户归属，不能跨租读取。
- Gateway、Handler 和 Worker 的服务身份与凭据边界必须清楚。
- 非幂等写请求不能在结果未知时隐藏重试。
- API 返回 operation 不等于任务已经完成，任务状态必须可查询。
- Worker 停止、恢复和重新领取不能静默制造重复外部效果。
- 模型与数据库秘密不能进入日志或由公共 Gateway 持有。
- 配置、模型空间和 schema 不兼容时必须拒绝启动或接流量。

Solution 3 已经验证其中一部分基础能力；AgentStratum 需要把这些能力固化为产品合同。

### 4.2 短期客户可见能力

短期版本可以优先交付：

- 稳定的 Retain、Recall、Reflect 和 operation 查询。
- 共享型与独享型租户。
- 基础团队、成员和 Bank 授权。
- 支持范围明确的 HTTP、UI 或 SDK 入口。
- 固定模型组合和可解释错误。
- 基础管理、健康检查、日志和人工故障处置。

这些能力应复用 Hindsight 原生实现，避免等待所有长期治理机制完成后才让客户使用。

### 4.3 随产品运营逐步建设的能力

当客户数量、在线变更和运维要求增长后，再逐步建设：

- 权限和配置在线发布、生效确认与撤权传播。
- 完整 Request Ledger、Attempt、checkpoint 和全部写点保护。
- 持久模型结果、费用 UNKNOWN 对账和父子预算。
- 自动 Worker 接管、公平调度和跨副本额度守恒。
- 完整备份恢复、离线迁移、升级和退出往返。
- 更完善的来源支持、撤源、冲突、时间和人工页协作。

### 4.4 由明确业务需求触发的远期能力

即使研发 Token 和团队能力充足，也不应因为“能够实现”就默认全部建设：

- 完整不可变 Publication 和所有历史投影。
- 多 home 控制面和自动在线迁移。
- 文档级 ACL 和独立个人资产域。
- 多 provider 自动切换和完整客户计费平台。
- Session 到 Skill、Trial、Release 的完整自动化生命周期。
- 通用连接器平台、多宿主强采用证明和自动学习。
- 自动弹性、跨 Unit 分布式查询和生产级全局硬配额。

这些能力需要由客户场景、风险、规模、法规或商业模式触发。研发资源充足可以降低实现成本，但不能消除运行复杂度、故障组合、写放大、延迟和长期维护成本。

## 5. Solution 3 如何成为 AgentStratum 的基础

Solution 3 已有成果不应被丢弃，可以按以下关系进入长期方案：

| Solution 3 能力 | AgentStratum 中的承接位置 |
|---|---|
| Cell | Unit 和 DataPG placement |
| 共享型与独享型 | 一个 Tenant 放入共享 Unit 或专属 Unit |
| Gateway 选择 Cell | Gateway 消费 Control Snapshot 后选择 Handler/Unit |
| Cell 内多个 Hindsight API | 私有 Handler/Business Runtime 实例池 |
| 独立 Hindsight Worker | Worker 实例池及后续受控任务协议 |
| PostgreSQL tenant schema | DataPG 内的租户、运行域和用户数据域隔离基础 |
| 原生 async_operations | 长期 operation、Attempt、hold 和恢复协议的基础 |
| Hindsight HTTP 合同 | 对外兼容入口与 Handler 内部原生能力适配基础 |
| T01 至 T08 验收 | AgentStratum 多实例拓扑和隔离测试的低层基线 |

因此，推荐的演进关系是：

```text
短期：Client -> Solution 3 Gateway -> Hindsight API/Worker Cell

长期：Client -> Gateway -> Handler -> DataPG/OBS
                            |          |
                            +-------> Worker
                 Control 提供身份、授权、配置和 placement
                 LLM Adapter 提供模型调用与治理
```

## 6. 当前实现成熟度边界

Solution 3 已经通过真实多进程和真实 PostgreSQL 的拓扑、分发、隔离、Worker 和重启验证，但真实模型 Recall 唯一标识检查尚未通过。它证明了短期架构可行，不证明生产治理已经完成。

AgentStratum 当前已经存在 Gateway 会话和流控、PG/Unit 内核、原件任务链、模型与查询接缝等有限实现和测试，不只是设计文档。但完整 MetaPG、DataPG、OBS、Gateway、Handler、Worker、LLM Adapter 与真实 provider 的组合验收尚未完成，S1 技术候选仍未接受。当前阶段应把它视为正在形成的长期产品，而不是可以立即替换 Solution 3 的已完成系统。

AgentStratum 当前固定 Hindsight `eb021da3b2501911e4b57c82b3de1123572a200e`，Solution 3 原型使用较新的 `a77c1f3412a7b82f36588dffce1a8d7480e99cc7`。长期合流前需要单独处理版本、接口和 Worker 恢复行为差异，不能直接假设两套实现等价。

## 7. 最终判断

在不考虑研发工作量和核心侵入性的前提下，AgentStratum 的长期产品方向值得做。它解决的是 Solution 3 有意没有解决的产品级问题，而不是重复实现同一套 Cell 路由。

推荐坚持以下原则：

1. Solution 3 继续承担短期客户落地和运行基线。
2. AgentStratum 吸收 Solution 3 的已验证拓扑，而不是平行重造部署底座。
3. 多租隔离、身份授权、非幂等失败语义、秘密边界和配置兼容属于短期正确性，不能因客户暂时看不到而删除。
4. 在线治理、自动恢复、完整计费、高阶知识语义、Skill 和规模能力按产品阶段逐步启用。
5. 每项长期能力都应由具体产品承诺和验收反例驱动，不能仅因 Token 足够就默认全部实现。

这使 AgentStratum 成为一条持续构筑的产品路线，而不是要求一次性交付全部长期蓝图的超大项目。
