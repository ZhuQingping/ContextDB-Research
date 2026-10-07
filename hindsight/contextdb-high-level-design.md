# 华为云 ContextDB High Level Design

日期：2026-10-06。设计基线：Hindsight `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`。本文审查 [my_arch.drawio](my_arch.drawio) 的原始设计，并给出首期可实现的修正版。文中“原生”表示当前源码已有能力；“产品新增”表示华为云需要实现。

## 1. 结论与主要修正

总体方向合理：入口层补齐云服务能力，Hindsight复用记忆引擎，PG保存结构化记忆，OBS保存二进制文件，并通过增加服务单元横向扩展。

原设计需要做五项关键修正：

1. **不能让任意Hindsight节点连接任意PG。** 当前 `DATABASE_URL`、读库地址、OBS和模型配置都是进程级静态配置。若让每个请求动态查Metadata DB、创建到任意PG的连接，会改造连接池、迁移、Worker和维护路径，侵入Hindsight核心。应采用 **Cell架构**：先把workspace路由到Cell，再在Cell内对API实例负载均衡。
2. **API Gateway不应独自承担全部产品逻辑。** APIG负责边缘安全和粗粒度流控；ContextDB Front Door负责Bank授权、放置路由、幂等、产品配额、协议兼容和组合查询。首期可以同一部署，但代码责任应分开。
3. **Hindsight API和Worker可以拆分，但不是一一对应。** API按在线QPS和延迟扩容，Worker按队列年龄、任务类型及模型/PG容量扩容。两者只要求同Cell、同版本、同模型profile和同数据PG，不要求数量相等。
4. **“无状态”只适用于API计算实例。** PG任务队列、MCP会话、维护调度、配置缓存、本地模型、连接池、迁移与运行期DDL都会影响无状态化。API可以做到可替换、无本地持久数据，但不能把整个Hindsight系统称为无状态。
5. **首期以workspace/租户为放置和迁移单元。** 一个workspace的全部Bank放在同一数据Cell；多个workspace共享一个Cell。超大客户可以独占Cell。首期不做Bank级跨PG打散，更不拆分单个Bank。

审查建议：**REVISE**。方向可接受，但原图中“任意Hindsight访问PG1/PG2/PG3”和“网关承担全部鉴权/路由”需要按上述边界修改后再进入开发。

## 2. 修正版逻辑架构

```text
Agent / SDK / MCP / Console
              │
              ▼
华为云 APIG / WAF
TLS、外部身份、请求大小、粗粒度QPS、request_id、访问日志
              │
              ▼
ContextDB Front Door（产品数据面）
协议兼容 │ Key校验 │ Bank ACL │ 幂等 │ 配额 │ workspace→Cell路由
       │                           │
       │                           └──────────► Control Plane
       │                                        Metadata PG
       │                                        资源/授权/放置/任务/用量
       │                                        Provisioner/Coordinator
       ▼
┌────────────────────── Cell A ──────────────────────┐
│ Cell LB                                             │
│   ├─ Hindsight API Pool（WORKER_ENABLED=false）     │
│   ├─ Hindsight Worker Pool                         │
│   └─ Maintenance/Provisioner（受控DDL与周期任务）  │
│             │                │                     │
│       RDS PG A（多个workspace schema）      OBS A  │
└────────────────────────────────────────────────────┘
       │
       └──────── Cell B / Cell C …（相同结构）

所有Cell共享或按Cell部署：模型接入层（LLM / Embedding / Rerank）、
KMS/Secret、监控审计、制品与配置中心。
```

路由顺序必须是：**认证主体 → 解析资源 → 查placement → 选择Cell → Cell内负载均衡**。不能先把请求均匀发到任意Hindsight节点，再让节点寻找PG。

## 3. 模块责任

### 3.1 华为云APIG/WAF

适合放在边缘层的能力：

- TLS终止、域名和证书、WAF、防重放的基础校验；
- 云IAM或ContextDB API Key的格式/有效性初筛；
- 请求体大小、连接数、IP及租户粗粒度QPS限制；
- 生成并透传`request_id`、访问日志、基础指标；
- HTTP超时、MCP长连接或streamable HTTP策略；
- 路由到ContextDB Front Door的健康实例。

不建议只由通用APIG承担的能力：

- workspace、Bank、KB和文档级资源授权；
- workspace到Cell的放置选择及迁移epoch；
- Retain幂等正文校验、Operation归属检查；
- 团队知识组合查询、晋升、撤回；
- 模型调用额度、后台任务额度及最终费用归属。

这些规则依赖ContextDB领域状态，应由产品服务实现。即使首期把它们部署在一个“自研Gateway”进程中，也应保持独立模块和接口。

### 3.2 ContextDB Front Door

这是原图缺失的关键产品数据面，建议包含：

| 子模块 | 责任 |
|---|---|
| Credential Resolver | 校验opaque API Key摘要、过期、撤销和scope；解析workspace、subject |
| Authorization | 校验成员角色、Bank/KB读写权限、资源状态；失败时默认拒绝 |
| Placement Router | 从缓存/Metadata PG解析`workspace_id → cell_id + schema + route_epoch` |
| Admission & Quota | 租户并发、请求大小、Retain/Reflect/后台任务和模型预算 |
| Compatibility Adapter | 保持Hindsight HTTP/MCP合同；限制危险配置字段和工具 |
| Idempotency Ledger | 绑定workspace、Bank、动作、幂等键和payload hash |
| Context Composer | 组合个人Bank与少量团队KB结果，执行预算分配和来源封装 |
| Usage/Audit Emitter | 记录请求、Operation、模型调用及错误归属，不记录密钥明文 |

Front Door只向Hindsight传递服务端生成的短期内部身份断言，不信任客户端提交的tenant、schema、PG地址、OBS前缀或角色。

### 3.3 Control Plane

首期可以是同一代码库中的管理API和后台Coordinator，不需要拆成多个微服务：

- workspace、成员、服务账号、API Key和授权管理；
- Cell注册、容量水位、workspace放置及迁移；
- Bank开通、删除、索引维护和schema迁移；
- 知识来源、版本、审核、发布、撤回；
- 产品级长任务、补偿、对账、用量和审计；
- 模型profile、区域、数据驻留、保留及套餐策略。

Metadata PG故障时，首期建议授权和新请求**失败关闭**。可缓存短时间placement和权限，但内部断言携带`route_epoch`，Cell必须拒绝旧epoch，避免迁移或撤权后继续访问旧位置。

### 3.4 Data Cell

Cell是横向扩展和故障隔离单元，至少固定：

- 一个数据RDS PG主库，可选只读地址；
- 一组Hindsight API实例；
- 一组Hindsight Worker实例；
- 一个受控Maintenance/Provisioner角色；
- OBS桶或桶前缀、KMS密钥引用；
- 固定Hindsight版本、schema版本、模型profile和Embedding维度；
- Cell级连接、并发、任务和容量上限。

一个Cell承载多个workspace，每个workspace首期映射一个稳定schema，schema内包含多个Bank。Cell内任意API实例可以处理本Cell任意workspace请求。

## 4. API与Worker拆分

### 4.1 API职责

- 同步Recall、读取文档/来源、受理异步Retain/Reflect等公开请求；
- 将异步任务及payload持久化到数据PG的`async_operations`；
- 不在API进程运行Worker；关闭API侧周期维护任务；
- 不持有schema owner或任意DDL权限；
- 允许实例随时替换，所有正确性状态落到PG/OBS/控制面。

### 4.2 Worker职责

- 从同一Cell PG轮询持久任务并使用数据库锁竞争领取；
- 执行事实抽取、Embedding、整合、Mental Model/Knowledge Page刷新、文件转换、导入导出、Webhook等原生任务；
- 执行前恢复持久主体并重新检查当前资源状态和授权；
- 记录attempt、模型用量、错误和完成状态；
- 优雅停机时排空或释放任务，由其他Worker重试。

Worker不需要与API对等：

| 维度 | API Pool | Worker Pool |
|---|---|---|
| 扩容信号 | 在线QPS、p95/p99、连接数 | 队列深度、最老任务年龄、模型并发、PG负载 |
| 负载特点 | 短请求、延迟敏感 | 长任务、成本敏感、可重试 |
| 对外暴露 | 经Front Door访问 | 仅健康、指标和内部管理 |
| 数量关系 | 至少跨故障域高可用 | 可为0到N，但有异步能力时至少1；无需1:1 |
| DDL权限 | 无 | 普通Worker无；Provisioner单独持有 |

API、Worker、Provisioner必须使用相同Hindsight版本和数据schema版本。API与Worker的模型profile也必须兼容，否则同一Bank可能被不同Embedding模型写入不一致向量空间。

## 5. 后台调度与知识晋升

后台任务分为两类，不能全部交给一种Worker：

### 5.1 Hindsight原生数据任务

Retain、事实抽取、Embedding、自动整合、Mental Model刷新、文件转换和导入导出继续使用Hindsight `async_operations`队列，由本Cell Hindsight Worker领取。PG是任务broker和状态源，不需要另外部署Kafka才能完成首期。

原生MaintenanceLoop会发现未调度的整合、定时Mental Model、日志保留和Operation清理。当前实现会在每个MemoryEngine进程启动，且没有leader election。建议：

- API部署把所有维护interval设为0；
- 普通Worker也关闭周期发现；
- 每Cell保留一个或少量“Maintenance Worker”开启周期发现；
- 发现器只负责幂等地产生任务，实际任务仍由Worker池竞争执行；
- 监控发现器最后成功时间，故障后允许另一实例接管。

### 5.2 ContextDB产品工作流

知识晋升、人工审核、版本发布、撤回、workspace迁移和Bank开通属于华为云产品状态机，由Control Plane Coordinator调度：

1. 在Metadata PG事务中写产品job和资源状态；
2. 以确定性document/operation ID调用目标Cell的Hindsight API；
3. 轮询或订阅原生Operation状态；
4. 校验目标内容可读、epoch和授权仍有效；
5. 原子发布为`READY`，失败保持`FAILED_CLOSED`；
6. Coordinator崩溃后从Metadata PG恢复并继续补偿。

Hindsight Worker不应直接决定“谁批准知识、向哪个团队发布”。它负责执行数据动作，产品Coordinator负责业务状态机。

## 6. 无状态化的完整条件

Hindsight API可以称为“无本地持久状态、可替换”，前提是以下状态已有明确归属：

| 状态 | 所有者/处理方式 |
|---|---|
| PG/OBS/模型地址 | Cell部署配置，不能按客户端请求动态指定 |
| 租户schema和Bank ACL | Metadata PG为权威；内部断言传递；Cell扩展复核 |
| 异步任务 | 数据PG `async_operations`，Worker竞争领取 |
| 产品job和幂等账本 | Metadata PG，Coordinator恢复 |
| MCP会话 | 首期启用stateless HTTP；若保留SSE会话则网关粘滞并限定失效语义 |
| 配置/权限/placement缓存 | 只作加速；带TTL、版本/epoch和主动失效，不能成为权威状态 |
| 本地Embedding/Rerank模型 | 镜像或只读共享缓存；各实例固定相同权重/版本/维度 |
| 进程内并发信号量 | 仅限制单进程；集群配额由Front Door/模型接入层控制 |
| 周期维护 | 专责Maintenance Worker；不能随API副本数线性放大 |
| 数据库迁移和Bank索引DDL | 独立Migrator/Provisioner；API和普通Worker无DDL权限 |
| Webhook/外部回调 | 持久任务、重试、SSRF策略、租户费用归属 |
| 日志和trace | 集中观测系统；敏感正文按策略脱敏与保留 |

此外要固定制品SHA、配置hash、schema版本、模型ID、Embedding维度、扩展版本和OBS key格式。实例重建后这些值不一致，虽然进程“无状态”，数据仍可能被破坏。

## 7. Metadata PG最小数据模型

### 7.1 身份和资源

- `accounts/projects/workspaces`：云账号、项目、工作空间、区域和生命周期状态；
- `subjects/memberships/service_principals`：用户、服务账号、角色和成员状态；
- `banks`：产品Bank ID、类型（个人记忆/团队KB）、workspace归属、状态；
- `grants`：主体对Bank/KB的动作权限；
- `api_keys`：key ID、HMAC摘要、主体、scope、Bank约束、过期、撤销、pepper版本；
- `client_bindings`：Agent/仓库/会话映射到稳定个人Bank，不能用客户端路径直接作为权限依据。

### 7.2 放置和版本

- `cells`：区域、状态、容量、RDS/OBS/模型profile引用、制品和schema版本；
- `placements`：workspace、cell、schema、`route_epoch`、迁移状态；
- `model_profiles`：LLM/Embedding/Rerank标识、Embedding维度、提示词/config版本；
- `resource_versions`：Bank/KB内容epoch、配置版本和删除tombstone。

Metadata PG保存RDS/OBS的**资源ID和Secret/KMS引用**，不保存PG密码、OBS SK或模型密钥明文。实际凭据由部署系统/KMS注入Cell。

### 7.3 工作流、可靠性和治理

- `request_ledger`：幂等键、payload hash、原生operation ID、状态及过期；
- `jobs/job_attempts`：开通、发布、撤回、迁移、删除和补偿；
- `sources/source_revisions/publications`：来源版本、审核、目标KB和发布epoch；
- `usage_ledger`：请求、Token、Embedding文本量、Rerank候选、存储字节、供应商request ID；
- `audit_events`：谁在何时对哪个资源执行什么动作；
- `quotas/policies`：套餐、并发、速率、任务、保留和数据驻留规则。

不在Metadata PG重复保存记忆正文、Chunk、向量、图关系或附件字节。它保存控制状态和指针，数据PG/OBS保存客户内容。

## 8. PG横向扩展粒度

### 8.1 首期选择：workspace/租户级放置

推荐规则：**多个workspace共享一个Cell；一个workspace的所有Bank位于一个Cell；单个Bank永不跨PG。**

优点：

- 与Hindsight“一个数据库连接、一个租户schema包含多个Bank”的原生模型一致；
- Worker可在本Cell发现并轮询所有workspace schema；
- 团队个人记忆与KB组合查询无需跨PG扇出；
- workspace备份、恢复、迁移、删除和数据驻留边界清晰；
- Placement缓存只需按workspace路由，网关和运维复杂度最低。

不足是超大workspace受单个PG上限约束。首期解决方式是让大客户独占Cell，并通过容量水位提前迁移，而不是立即实现Bank级分片。

### 8.2 为什么首期不选Bank级打散

Bank级放置会让一个workspace跨多个Cell，额外引入：

- 列出Bank、权限修改、团队组合Recall和用量查询的跨PG扇出；
- Worker、schema迁移、导入导出、删除与恢复的多Cell协调；
- 同一租户配置、模型profile和OBS生命周期的一致性问题；
- placement缓存失效和部分Cell故障时的结果完整性语义；
- 上游租户扩展只返回schema，而连接池仍是进程级，无法原生在一个进程内按Bank切PG。

这些成本与五人团队、1–2个月上线目标不匹配。

### 8.3 后续扩展路径

当真实数据证明单workspace会超过一个Cell容量时，引入`bank_group`作为第二级放置单元：个人Bank组、团队KB组可以迁移到不同Cell，但仍不拆单个Bank。产品组合查询负责有限扇出，并明确部分失败语义。只有单个Bank本身超过PG能力时，才评估修改Hindsight的分片存储；这不属于首期服务化。

## 9. 关键请求流程

### 9.1 Recall

1. APIG认证并执行边缘限制；
2. Front Door解析key/云身份，检查Bank读权限和产品预算；
3. Placement Router读取workspace的Cell和route epoch；
4. 请求发送到该Cell任一Hindsight API；
5. Hindsight从本Cell PG执行向量、全文、图和时序检索；只有返回附件字节时才访问OBS；
6. Front Door复核资源状态/epoch，记录用量并返回。

### 9.2 Retain

1. Front Door完成写权限、大小、幂等和额度校验；
2. API把任务和主体上下文持久化到本Cell PG后返回Operation；
3. 本Cell任一Worker领取任务，调用模型并写PG；附件/原文件按策略写OBS；
4. 执行前和发布结果前检查资源未撤权、未迁移、未删除；
5. 客户通过Operation查询“已受理/处理中/可检索/失败”。

### 9.3 workspace迁移

冻结新写和产品job → 排空API/Worker在途任务 → 复制并校验schema及必要OBS对象 → 目标Cell以同版本恢复 → Recall抽样校验 → CAS更新placement和route epoch → 开放请求 → 旧Cell拒绝旧epoch并延迟清理。

## 10. 扩容与故障原则

- API扩容只能增加在线计算能力，不能增加PG、模型或OBS吞吐；
- Worker扩容前检查PG连接/IO和模型配额，避免队列更快地压垮下游；
- 新增Cell增加总容量；workspace迁移解决Cell水位不均；
- 控制面故障时拒绝新授权和新路由，不能相信客户端自报位置；
- 数据Cell故障只影响该Cell的workspace，其他Cell继续服务；
- OBS故障不应阻断纯文本Recall，但附件读取、文件Retain及导入导出应明确失败；
- 模型故障不应阻断不需要LLM的基础Recall，Retain/Reflect进入可解释的失败或重试状态；
- 路由、权限、任务、模型和存储的指标必须以workspace/Cell维度可观测。

## 11. 开发验收条件

- 同一workspace请求只进入其placement指定Cell；伪造tenant/schema/cell头无效；
- Cell内任意API实例的Recall/Retain结果一致，实例重启不丢已受理任务；
- API关闭内置Worker和周期维护，独立Worker可停止、扩容和恢复积压；
- API数量与Worker数量独立变化，不出现任务重复发布或跨workspace处理；
- Bank由特权Provisioner创建，普通API/Worker账号无任意DDL权限；
- workspace迁移时旧epoch写入被拒绝，切换失败可以恢复到明确状态；
- API Key撤销、成员移除、Bank删除覆盖HTTP、MCP、附件、导出和Operation查询；
- 目标RDS、OBS、LLM/Embedding/Rerank完成真实协议、故障、恢复、容量和成本验证；
- 未执行或失败的门禁明确标记，不能由本地PG或S3兼容性推导为云上通过。

## 12. 结论证据与边界

| 结论 | 证据 | 证据类型 |
|---|---|---|
| 数据库连接是进程配置，不是请求级路由参数 | [`config.py`定义及装载`DATABASE_URL`](../../hindsight/hindsight-api-slim/hindsight_api/config.py#L153) | 源码确认 |
| API可关闭内置Worker；独立Worker不执行迁移 | [`DEFAULT_WORKER_ENABLED`](../../hindsight/hindsight-api-slim/hindsight_api/config.py#L1855)、[`worker/main.py`](../../hindsight/hindsight-api-slim/hindsight_api/worker/main.py#L283) | 源码确认 |
| 多Worker通过PG安全竞争任务，并跨tenant schema轮询 | [`worker/poller.py`](../../hindsight/hindsight-api-slim/hindsight_api/worker/poller.py#L290)、[`TenantExtension.list_tenants`](../../hindsight/hindsight-api-slim/hindsight_api/extensions/tenant.py#L99) | 源码确认 |
| 周期维护在每个API/Worker运行且没有leader election | [`engine/maintenance.py`](../../hindsight/hindsight-api-slim/hindsight_api/engine/maintenance.py#L30) | 源码确认 |
| MCP默认是有状态模式 | [`DEFAULT_MCP_STATELESS=False`](../../hindsight/hindsight-api-slim/hindsight_api/config.py#L1517) | 源码确认 |
| API与独立Worker拆分链路可运行 | [12项拆分验证结果](../deployments/hindsight-local/round2/evidence/split-worker-probe.json) | 本地实测 |

本轮没有目标华为云RDS、OBS、IAM、APIG和MaaS账号，因此Cell故障切换、OBS兼容性、云IAM撤权延迟、目标模型容量与费用仍是**待云环境验证项**。本文对这些部分给出设计和验收条件，不把它们写成已验证能力。
