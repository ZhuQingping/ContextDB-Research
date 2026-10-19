# 华为云 ContextDB 设计与两个月交付评审

日期：2026-10-07<br>
评审对象：ContextArk `main@ba328844`、agentstratum 远端 `main@d07f0c59`、本地 Hindsight `main@f7dd3f4f`<br>
结论：**REVISE。长期目标架构可继续使用；首期必须缩小产品范围，并把当前文档状态与实际实现状态分开。**

## 1. 先回答：当前设计文档到底是哪一份

当前不是三份并列的设计文档，而是四层不同用途的材料。

| 优先级 | 文档 | 身份 | 使用方式 |
|---|---|---|---|
| 1 | `agentstratum/docs/architecture/hindsight/DESIGN-V2.md` | **当前产品实施合同** | 开发、接口和实现判断以此为准。它由 ContextArk 的 V2.6 基线迁入，又增加了固定 Hindsight 版本的适用性和功能启用门。当前 SHA-256 为 `38d8d83b...` |
| 2 | `ContextArk/docs/architecture/hindsight/DESIGN-V2.md` | **架构研究源与已评审基线** | V2.6-B1 唯一可编辑架构正文。当前 SHA-256 为 `6dcd479a...`；文件明确标记为“初步评审通过”，机制、性能、业务和生产验证仍为 `NOT_RUN` |
| 3 | `ContextArk/docs/architecture/hindsight/DESIGN-V2.html` | **从 Markdown 生成的阅读版** | 便于阅读，不应单独修改，也不是新的权威来源。`v2-manifest.json` 明确把 Markdown 登记为 source |
| 4 | 在线 `.../DESIGN-V2` | **冻结的公开发布副本** | 本地发布记录说明线上仍是 version 4 的 V2.6 初评基线，未包含后续 B1 私仓增量。网页不是最新产品实施状态 |

因此，回答“现在按哪份开发”：以 **agentstratum 中的 DESIGN-V2、ADR、当前代码和执行状态共同判断**。回答“已经评审通过的原始架构是哪份”：以 **ContextArk 中的 DESIGN-V2.md** 为准。HTML 和在线页面只用于阅读。

还需注意一个状态问题：agentstratum 本地分支停在 `af80f7e`，远端 `main` 已到 `d07f0c5`；本次评审已 fetch 并读取远端最新提交，但没有改变本地分支。远端新增的是 D-GOVERNANCE、D-KNOWLEDGE 准备材料，产品源码未随这三个提交变化。

## 2. 总体判断

设计在“面向生产的长期目标”上考虑得比较完整，关键方向合理：

- 公网 Gateway、在线 Handler、后台 Worker、控制面、模型接入层各有清楚的责任和凭据边界；
- MetaPG 保存身份、授权、放置和配置，DataPG 保存运行状态与用户数据，OBS 保存原件；
- Handler 与 Worker 独立扩缩，任务以 PG 为权威，避免在 API 进程内保存耐久状态；
- 租户身份、Bank ACL、模型发送资格、撤权、恢复和升级都有明确的 fail-closed 方向；
- 固定上游版本、保留补丁来源、非作者复审和真实/替身/未运行证据分开，工程纪律较好。

但它把长期完整产品、首期适用合同、故障语义、未来强一致能力和实施准备放在同一份 1900 多行文档中。对五人团队而言，文档可以作为北极星，不能直接当作八周开发清单。当前实现状态也不支持把它描述为“即将完成的产品”：执行账本明确写着 S1 技术候选未接受，C-MODELS、C-RETAIN、C-QUERY、C-PAGES、J1/J2/J3 等关键链仍未完成。

## 3. 主要评审发现

### P0：完整 V2.6 不能由五人在两个月内交付

设计包含 G/H/W/C/L 五类运行集群、MetaPG/DataPG 双域、rt/ud 双 schema、OBS 原件先持久、模型资格与费用账本、强撤权、恢复迁移、Skill 生命周期、75 个父验收例/157 个步骤、99 条原生路由和 68 个 UI 文件。当前计划本身记录了 58 项目标、30 项能力、9 个模块和 10 项合同。

现有实现已经有价值，但完成的是有限切片：

- K01：PG 可信路由切片，记录为 36 个纯测试和 31 个真实 PG 检查；
- K02：PG/OBS 原件与任务有限链；文档明确说不能证明 facts 或模型业务；
- A01/L01、Gateway、PG、运维等已有协议、准备或局部代码；
- 完整 C-PG 仍是“已报告待接收”；真实 C-MODELS、C-RETAIN、C-QUERY、C-PAGES 和最终 J3 均未验收；
- 五项运行启用门 G-BANK、G-DIAG、G-PARSER、G-RECOVERY、G-UPGRADE 仍为 `NOT_RUN`。

**判断：**八周可以交付定向邀请预览版，不能按当前完整 V2.6 范围承诺生产 GA。若不收缩，最可能出现的结果是接口和状态机很多，但 Retain→可召回、知识晋升、撤回、跨客户端使用等用户主链没有足够时间稳定。

### P0：当前方案不是“在 Hindsight 外面加一层服务”，核心侵入较大

设计正文自己把以下路径标为 `CORE_PATCH`：Bank 身份与配置拆分、documents、memory_units、async_operations、mental_models、Worker 发现、迁移、跨 schema FK/索引/routine、原件删除与恢复。工作包还要求覆盖 retain 分批提交、claim/recover、consolidation、page、delete 和 maintenance 的提交守卫。

现有 K01 补丁只修改五个上游文件：`config_resolver.py`、`bank_info_cache.py`、`memory_engine.py`、`retain/bank_utils.py`、`schema.py`。这证明了路由切片可行，不能证明全写路径和双 schema 改造已经完成。

**判断：**如果首期坚持 rt/ud 物理拆表、全部强 guard、所有原生 UI/管理入口和独立 L 服务同时上线，侵入会很大，长期跟随社区的成本也会很高。应把核心补丁限制在少数稳定扩展点，把产品状态机、IAM、放置、配额、OBS 原件和知识晋升尽量放在外层。

### P0：产品主链仍缺少同一候选上的端到端证据

当前证据分散在 K01、K02、A01、L01 和多个准备包中。执行状态明确要求 J3 在同一候选、环境和 oracle 下完成 75/157、99 路由、68 UI 的验收，当前仍未执行。真实身份→Gateway→Handler→PG/OBS→Worker→模型→Recall/Reflect/知识页的闭环尚未被同一版本证明。

**上线含义：**在这条链通过前，只能说“模块和局部链路已实现”，不能说“ContextDB 首期功能完备”。

### P1：Hindsight 版本策略能重放，但还不能证明可持续跟随社区

agentstratum 固定在 Hindsight `eb021da3`，通过 subtree、锁文件、不可变补丁和文件 hash 保证可重放。本机 Hindsight 当前为 `f7dd3f4f`，`eb021da3` 是其祖先，两者相差 82 个提交。设计已识别新上游的 store 边界、tag scope、诊断和 parser 变化，但 G-UPGRADE 尚未运行。

固定版本对首期稳定有利，长期必须建立月度升级流水线：导入上游候选、重放产品补丁、运行上游测试、产品合同、真实 PG/OBS 和差分行为，再决定升级。没有这条流水线，“固定版本”会逐渐变成长期 fork。

### P1：当前 CI 只能保护 K01 的一小部分

agentstratum 当前有 60 个产品 Python 源文件，约 12,552 行；测试目录静态统计有 28 个 `test_*.py` 文件、448 个测试函数定义。这个数量不能等同于通过数量。唯一 GitHub Actions 工作流只执行：

1. `ruff check src/contextdb tests/contextdb`；
2. `ty check src/contextdb`；
3. `pytest tests/contextdb/test_kernel.py -m 'not native'`。

`test_kernel.py` 只有 11 个测试函数定义，参数化后历史记录为 36 个纯检查；真实 PG 另行执行。上游 vendored 树中静态统计有 883 个测试文件、10,341 个测试函数，但产品 CI 没有运行上游回归、完整产品测试、真实 PG/OBS、客户端 E2E 或升级测试。

本次在当前机器尝试复跑 CI 的 pytest 命令，系统 Python 缺少 pytest，返回 `No module named pytest`；未安装依赖或伪造通过。对源码和 `tests/contextdb` 的 68 个 Python 文件做了 AST 解析，均通过，这只证明语法可解析。

### P1：状态账本存在可见的滞后

远端已经合入 D-GOVERNANCE 和 D-KNOWLEDGE，`CURRENT.md` 仍显示两者“待安排”，并声明它由 revision 143 生成。说明“当前状态”没有随合并自动更新。大量准备包和收据能提高可追溯性，但状态入口滞后会让五人团队花时间核对历史，而不是确认下一项工作。

建议每次合并由 CI 重新生成并校验 `CURRENT.md`，若生成视图与任务/收据不一致就拒绝合并。首页只展示四类状态：未开始、开发中、候选已合入、同候选 E2E 已通过。

### P2：架构完整，但首期用户产品定义不够集中

设计对内部正确性投入很多，对客户第一天如何使用的定义分散在多份材料里。首期必须集中定义：资源层次、公开 API、SDK/MCP 配置、知识晋升、团队空间、操作状态和错误合同。客户不应看到 Unit、rt/ud schema、placement epoch、ProviderAttempt 等内部概念。

## 4. 建议的产品形态

产品应是一个**全托管的 Agent Memory & Knowledge Base 服务**，不是一款要求客户维护 Hindsight 或 PG schema 的数据库插件。

客户看到的资源层次建议保持四级：

```text
华为云项目 / Tenant
  └─ Workspace（团队空间、计费和成员边界）
      ├─ Memory Bank（Agent/用户的工作记忆）
      ├─ Knowledge Base（文档、知识条目和版本）
      └─ Service Credential（API Key或IAM委托）
```

首期对外提供三种入口：

- REST/SDK：Retain、Recall、Reflect、文档上传、任务查询、知识条目管理；
- MCP：让 Claude、Codex、OpenClaw 等 Agent 用少量配置接入；
- 云控制台：创建 Workspace/Bank/KB、管理成员和 Key、查看任务、来源、用量和审计。

知识晋升首期采用可解释的人审流程：从 Memory 中生成候选知识，保留来源，管理员审核后发布到团队 Knowledge Base；支持撤回与重建。不要在首期承诺全自动知识真值判断、文档级复杂 ACL 或跨 Workspace 自动共享。

## 5. 收缩后的 High Level Design

```text
Agent / SDK / MCP / Console
          |
Huawei APIG + ContextDB Gateway
认证、Workspace/Bank权限、配额、幂等、路由、审计
          |
          +-------------------- Control Plane
          |                     Workspace/Bank/Key/ACL/Placement/Job
          |                     MetaPG + KMS/Secret
          |
     Data Cell（可复制）
       |- Hindsight Runtime：API + 内置Worker + Maintenance（首期默认）
       |- Dedicated Worker Pool（达到拆分条件后启用）
       |- Provisioner 1-active：schema、索引、升级和维护任务
       |- RDS PostgreSQL：运行状态、文本、向量、全文、关系
       `- OBS：上传原件和大对象
          |
     Model Gateway / MaaS
     LLM、Embedding、Rerank的统一profile、限流、用量和超时
```

首期部署上不需要把每个逻辑模块做成微服务：

- Gateway 与 Control API 可来自同一代码库、分别部署；
- 首期沿用Hindsight默认联合部署，不建设API和Worker两套集群；达到吞吐、资源隔离或独立扩缩条件后，再启用官方Dedicated Worker形态；
- Maintenance首期不独立成第三套服务，沿用上游进程内MaintenanceLoop并监控重复扫描成本；Provisioner仍作为受控管理Job，不进入普通请求进程；
- Model Gateway 首期可以是内部适配模块或现有 MaaS 网关能力，保持接口边界即可，不必自研完整计费系统；
- 一个 Workspace 的全部 Bank 首期放在同一 Data Cell；多个 Workspace 共享 Cell；超大客户可独占 Cell；不拆分单 Bank。

MetaPG 保存 PG/OBS 的资源 ID、地址引用、Cell 和 Workspace 放置关系；密钥只保存 KMS/Secret 引用。Handler/Worker 不应每个请求动态连接任意 PG，而是按 Cell 使用受控连接池。

### 5.1 Gateway怎样选择API实例

API副本只在**同一个Runtime Pool**内对等，不是所有Data Cell中的API全局对等。Pool至少固定`cell_id/shard_id、profile_id、code_version、schema_version、model_profile`；配置不同就属于不同Pool。

请求路由分两步：

1. Gateway根据已认证的Tenant、Workspace和Bank查询placement，得到目标`cell_id + handler_pool_id + route_epoch`；
2. Gateway把请求发到该Pool的稳定Service地址，由Service/LB在健康的N个Runtime副本间按least-request或round-robin分发。

Gateway不应保存每个Pod的地址，也不应先随机选择API再让API寻找PG。API副本启动时只连接自己Pool对应的DataPG/OBS/model profile，请求携带的可信Unit上下文与本实例绑定不一致时必须拒绝。

当前agentstratum的有限实现还不是上述N副本模型：`Unit`快照保存单个`handler_id + handler_origin`，`Forwarder`按`unit_id`查到唯一地址并直接转发，还要求不同Unit使用不同固定Handler实例。因此当前代码只能证明“固定Unit到固定Handler”的路由合同，不能证明Handler Pool负载均衡。首期需要把该合同改为`handler_pool_id + service_endpoint`；Pod列表和健康摘除交给服务发现/LB。

同步Recall/Reflect在选中的API副本内执行。异步Retain/文档任务由任一API副本在DataPG写入`async_operations`后返回operation ID。后续查询operation状态仍走Gateway→任一同Pool API→PG。

### 5.2 首期是否拆分API和Worker

**不默认拆分。** Hindsight官方文档明确把API内置Worker推荐给开发和小型生产，把Dedicated Worker推荐给高吞吐或长任务场景。官方Helm默认`api.replicaCount=1`、`worker.enabled=false`；只有显式开启worker后，才关闭API内置Worker，并以StatefulSet运行独立Worker。

首期每个Data Cell部署一个Hindsight Runtime Pool，每个副本都运行API、内置Worker和MaintenanceLoop，共享同一个DataPG。Kubernetes负责副本、健康检查和服务发现，产品不另做一套“API集群管理”和“Worker集群管理”。需要特别保证worker_id稳定，或者具备明确的decommission/recovery流程；官方文档说明不稳定的容器hostname会留下已claim任务。

出现以下任一条件再拆分：API延迟受后台CPU/内存影响；任务最老等待超过SLO；API和后台任务的扩容比例明显不同；本地Embedding/Rerank抢占在线资源；Worker需要更高模型/PG权限；长任务故障频繁影响API发布。拆分使用同一镜像的`hindsight-api`和`hindsight-worker`两个入口，不重写调度系统。

Maintenance也不应因为逻辑上可识别就立即建设第三套集群。当前上游的MaintenanceLoop会随每个MemoryEngine启动，官方源码明确承认每个API/Worker进程都会运行、依靠启动jitter和数据库侧去重降低冲突，并没有leader election。首期沿用并监控；只有跨租户扫描或重复维护已形成实际瓶颈时，再把维护interval从普通Runtime/Worker关闭，交给单独的leader实例。

### 5.3 Gateway是否与Worker交互

**业务数据面不直接交互。** 正常链路只有：

```text
Gateway -> API -> DataPG中的pending operation
                         ^
                         | PG claim
                    Worker Pool
```

Gateway不选择Worker、不向Worker发送Retain正文、不等待某个Worker，也不维护任务队列。这样API和Worker才能独立扩缩，Gateway重启也不会丢已受理任务。

Control Plane会分别向Gateway/API/Worker发布placement、版本、能力和assigned Unit配置；这是管理关系。Maintenance调度器可以向DataPG创建维护任务；它也不通过Gateway调用普通Worker。

### 5.4 拆分后M个Worker是否对等、分别执行什么

Worker与API一样，只在同一个Worker Pool内对等。一个Pool固定：

- Data Cell和可访问的assigned Unit集合；
- Hindsight代码、schema/payload版本和模型profile；
- capability/task class，例如普通Retain、知识构建或维护；
- PG角色、最大并发槽位和模型调用额度。

首期建议只保留两种角色：

| Pool/角色 | 职责 | 副本关系 |
|---|---|---|
| General Worker Pool | Retain抽取、Embedding、整合、知识页构建等已开放的异步任务 | M个副本对等，谁先从PG成功claim谁执行 |
| Maintenance Scheduler（后续可选） | 周期扫描、清理发现、需要产生维护任务的调度 | 重复维护成为实际瓶颈后再引入leader；不属于首期必选部署 |

首期不要为每种operation建立一个Worker服务。Hindsight原生Worker已有`max_slots`、按operation type预留槽位和共享槽位的机制，可以避免整合任务占满全部并发。当某类任务形成独立瓶颈后，再建立带task-class过滤的专用Pool，例如`retain-heavy`或`page-build`。

### 5.5 Worker任务如何调度

调度权威是DataPG，不是Gateway、API内存或Kubernetes调度器：

1. API在短事务中写入`async_operations(status=pending, operation_type, bank_id, payload/ref)`；
2. 每个Worker只扫描Control Plane分给自己的Unit和允许的task class；
3. Worker在PG事务中使用`SELECT ... FOR UPDATE SKIP LOCKED`领取最早/最高优先级的pending任务；
4. 成功领取后写`status=processing、worker_id、claimed_at、attempt/lease`；其他Worker因行锁和状态变化无法领取同一任务；
5. Worker执行模型和数据处理，提交前重新检查Unit/Bank授权、storage epoch和attempt所有权；
6. 成功或失败状态写回PG，API从PG查询结果；
7. Worker缩容时先停止claim再排空。执行效果未知或模型可能已发送的任务进入hold，不能直接改回pending重做。

Hindsight原生Poller已经使用`FOR UPDATE SKIP LOCKED`支持多个Worker竞争领取，也支持任务类型的reserved/shared slots。V2.6提出的assigned Unit、跨实例Attempt fence、租户公平调度和UNKNOWN hold更强，其中只有有限K02链已经实现；完整原生任务链尚未通过J3。因此首期必须先完成同一Cell中“2个API+2个Worker”的真实并发、强杀和恢复试验，再宣传独立横向扩展。

## 6. 八周首期范围

### 必须交付

1. Workspace、成员、Service Credential、Bank/KB 和 Bank 级 ACL；
2. 单区域、多 Cell 的静态放置；首期迁移可用维护窗口离线完成；
3. Hindsight 核心 Retain、Recall、Reflect；默认联合Runtime可用，并验证可切换到官方Dedicated Worker模式；
4. 文本和文件入库，OBS 原件、PG 任务和来源引用可追踪；
5. Memory→候选知识→人工审核→团队 KB 发布/撤回；
6. REST、一个官方 Python SDK、MCP 配置样例；
7. 模型 profile、租户级并发/速率限制、超时和用量统计；
8. 备份、删除、审计、告警和最小运维手册；
9. 至少两个真实 Agent 客户端与一个业务场景的端到端验收。

### 首期延后

- 单 Bank 跨 PG、在线无损 Cell 迁移和自动再均衡；
- 文档级/Chunk 级 ACL、个人域与团队域任意混合查询；
- 完整 single-send、供应商费用强一致和跨库原子发布；
- 多 provider 自动故障切换、BYOM/BYO endpoint；
- Skill 自动学习、Trial、Release 全生命周期；
- 全量原生 UI 兼容和 99 路由全部公开；
- 全自动知识晋升、严格不可变历史和任意时点知识视图；
- 生产级跨 Region 双活。

首期需要清楚标为 Preview，并明确原生可见性、撤回生效时间、任务重试和恢复限制。延后不等于不设计；接口保留 capability 和 version，不能先返回空成功。

## 7. 五人并行开发方式

当前设计已经提供任务卡、固定输入、写集、收据和非作者复审，具备多人协作基础。问题是流程颗粒过细、共享内核仍是单写瓶颈。建议把 40 多张细卡收敛成五条可独立验收的主线：

| 人员主责 | 八周主线 | 独占写区 |
|---|---|---|
| A：Hindsight 内核 | API/Worker role、可信上下文、模型端口、上游补丁 | `vendor/hindsight` 和唯一 patch 队列 |
| B：控制与网关 | Workspace、Key、ACL、placement、quota、审计 | `gateway/`、`control/`、Meta schema |
| C：数据与运维 | DataPG/OBS、Provisioner、备份恢复、Cell 部署 | `storage/`、`k02/`、部署与迁移 |
| D：产品能力 | KB、知识晋升、公开 API、SDK/MCP、控制台 | 产品 API、KB workflow、客户端 |
| E：质量与发布 | CI、E2E、故障注入、性能、安全、发布候选 | 测试框架、流水线、验收环境 |

共享合同在第一周冻结；每条主线每天可独立合入，涉及 `vendor/hindsight` 的修改统一由 A 集成。E 不应等到第七周才开始，第一周就建立同一候选的 E2E 环境。作者不能批准自己的上线门，但无需为每个小提交创建庞大收据；高风险边界保留严格证据，普通实现使用常规 PR、CI 和 code owner。

## 8. 可落地的八周计划

| 周 | 交付物 | 退出条件 |
|---|---|---|
| 第1周 | 冻结 Preview 范围、资源/API 合同、固定上游基线；CI 扩到产品测试；搭建一键 Cell 环境 | 干净环境可启动Gateway、联合Hindsight Runtime、PG和OBS stub；一条冒烟链通过 |
| 第2周 | Workspace/Key/Bank ACL、MetaPG、可信内部信封、静态 placement | 伪造 tenant/schema 被拒；Key 撤销生效；两租户隔离 |
| 第3周 | 联合Runtime的Retain受理、PG任务、OBS原件；保留官方Dedicated Worker切换能力 | 两副本联合运行不重复处理；停内置Worker并启动Dedicated Worker后积压任务可继续完成 |
| 第4周 | Recall/Reflect、模型 profile、Embedding/Rerank/LLM 接入和限流 | 同一模型空间可稳定写读；超时/429/失败可解释；无跨租候选 |
| 第5周 | KB 文档、来源、候选知识、人工审核、发布/撤回 | 文档→可检索→晋升→团队召回→撤回全链通过 |
| 第6周 | Python SDK、MCP、控制台最小页面；Claude/Codex 等真实客户端 | 两类客户端无需理解内部拓扑即可完成核心用例 |
| 第7周 | 删除、备份恢复、升级演练、故障注入、容量与成本基线 | 备份恢复与一版上游重放成功；关键故障无静默数据越权 |
| 第8周 | 固定候选回归、性能压测、安全审查、灰度发布和运维交接 | 同一候选的 E2E/回归/运维门通过，失败项有明确阻断或降级说明 |

如果第 4 周末 Retain/Recall 的真实链仍未稳定，应继续缩减控制台和高级知识功能，不能削减隔离、来源、删除和回归验证。

## 9. 跟随 Hindsight 社区的工程方案

建议把修改分成三类并设硬约束：

1. **外层 Adapter**：IAM、Gateway、MetaPG、placement、quota、KB 审核、OBS 生命周期。完全不修改上游；
2. **稳定扩展接口**：可信请求上下文、StorageContext/table resolver、任务 claim/commit guard、模型端口、role 启动开关。尽量推动上游接受；
3. **不可避免的补丁**：少量核心写路径。每个补丁必须有上游原文件 hash、行为测试和升级冲突责任人。

为避免长期 fork，设置三条指标：

- 产品补丁修改的上游文件数和净增行数；
- 上游更新重放补丁的冲突数与人时；
- 新旧版本在 Retain/Recall/Reflect/后台任务上的差分结果。

每月选择一个上游候选执行 G-UPGRADE，不要求每次升级，但必须知道升级成本。连续两个候选无法在一周内重放时，停止新增核心补丁，优先收敛扩展接口或向上游贡献。

## 10. 首期上线门

| 门 | 最低证据 |
|---|---|
| 功能 | Retain、Recall、Reflect、文件 KB、知识晋升/审核/撤回在同一候选通过 |
| 隔离 | 两 Tenant、多个 Workspace/Bank 的正负例；伪造身份、Bank、schema、Cell 全部拒绝 |
| 任务 | 联合Runtime多副本的进程强杀、重启、重复请求和积压恢复；Dedicated Worker切换路径可重放 |
| 模型 | LLM/Embedding/Rerank 真实 MaaS 的成功、超时、429、错误、用量和限流 |
| 数据 | PG/OBS 引用一致、删除与保留、备份恢复、Embedding 模型/version 记录 |
| 客户端 | 至少两种真实 Agent 客户端和官方 SDK/MCP 文档 |
| 升级 | 从固定 `eb021da3` 至一个较新候选的补丁重放、schema 升级和回退演练 |
| 运维 | Cell 容量、PG 连接、队列年龄、模型并发、错误率、告警和 runbook |

现有 75/157 验收体系可以保留为长期完整分母；Preview 应另建 20–30 个不可删的发布级用户旅程。测试清单与真实执行结果必须分开，`NOT_RUN` 不能因为映射完整而变为通过。

## 11. 证据索引与本次核验

| 结论 | 本地证据 |
|---|---|
| ContextArk Markdown 是架构源，HTML 是派生物 | `ContextArk/docs/architecture/hindsight/v2-manifest.json`；`build-v2.py:96,332,362,373` |
| 线上仍为冻结 version 4，B1 增量未发布 | `ContextArk/docs/architecture/hindsight/online/README.md` |
| 产品代码和接口以 agentstratum 为权威 | `ContextArk/README.md:7`；`agentstratum/docs/provenance/contextark-source-map.json:4` |
| 完整设计仍是初评，产品/生产未验 | `ContextArk/docs/architecture/hindsight/DESIGN-V2.md:3`；`build-v2.py:332` |
| G/H/W/C/L 目标边界 | `ContextArk/docs/architecture/hindsight/DESIGN-V2.md:220-313` |
| 多处需要核心补丁 | 同文件 `610-617`、`1376-1388` |
| S1 和关键业务链未接受 | `agentstratum/docs/architecture/hindsight/execution-workflow/CURRENT.md:55-66,90-95` |
| 固定基线及五文件 K01 patch | `agentstratum/src/contextdb/upstream/hindsight/manifest.json`；`upstream/hindsight.lock.json` |
| 五项运行门未执行 | `agentstratum/docs/provenance/contextark-source-map.json:6-19` |
| CI 只跑 K01 pure 子集 | `agentstratum/.github/workflows/k01.yml` |

本次还完成了以下只读核验：三个仓库分支和远端提交比对；两份 DESIGN-V2 的 hash 和文本差异；在线 URL 访问尝试（网页工具不可访问，本机 HTTP 返回 403，因此以仓内发布收据判断版本）；agentstratum 60 个产品源文件及测试清单静态统计；68 个 `src/contextdb` 与 `tests/contextdb` Python 文件 AST 解析通过；当前系统 Python 不能运行 pytest，失败原因为未安装 pytest。

## 12. 最终建议

保留 V2.6 作为长期架构基线，但立即建立一份不超过 15 页的 `PREVIEW-SCOPE.md`，只包含本报告第 4–10 节的产品合同、部署边界、八周任务和上线门。开发入口只指向 agentstratum；ContextArk 和在线页面继续作为研究基线与阅读副本。

两个月目标应定义为：**单区域、Bank级权限、可横向增加Data Cell、支持Memory与团队KB、人审知识晋升、默认联合Runtime并保留Dedicated Worker切换能力、真实Agent易接入的邀请预览版。** 这个范围对五人团队有挑战但可执行。完整V2.6、强一致费用/撤权/恢复、Skill生命周期和生产GA应按后续阶段推进。
