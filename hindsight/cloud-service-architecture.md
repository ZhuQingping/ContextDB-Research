# 华为云 ContextDB 首期服务化架构

2026-10-04。面向约 5 人、6–8 周的工程决策。下文“建议”是待落地设计；源码事实基于 `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`，不能替代华为云生产验证。证据见 [核验依据](cloud-service-evidence.md)，实际安装见 [本地验收](../deployments/hindsight-local/README.md)。

**建议继续选择 Hindsight，但把一期定义为面向研发／数据库运维团队的受控试用服务。复用记忆引擎，补齐薄产品层和云运维；不要在一期重写存储、图引擎或做通用分布式数据库。** 6–8 周实现这一范围有机会；面向任意规模客户的完整商业 GA 不能只由时间表保证，必须通过隔离、恢复、成本与容量门槛。

**开发版阅读入口：** §9为具体HLD/LLD，§10为12个任务包及8周计划，§11为发布门禁；§1–8保留背景与取舍。本轮新增本地验证均有脚本/结果链接。

**针对 `my_arch.drawio` 的专项审查与修正版HLD：** [ContextDB High Level Design](contextdb-high-level-design.md)。核心修正是先按workspace路由到固定Cell，再在Cell内负载均衡；当前Hindsight的PG连接是进程级配置，不应改造成任意节点按请求动态连接任意PG。

## 1 商用判断

Hindsight 不是只有单机个人用途的 Demo。当前代码已有 HTTP/MCP、独立 Worker、租户扩展、任务持久化、知识页面、文档导入导出、监控与审计接口。根许可证为 MIT，允许商业使用、修改及分发，但须保留许可声明。管理 UI 的 package.json 标注 ISC；完整发行物还包括依赖、模型权重和第三方服务，须按实际构建清单检查，不能用根目录一个 MIT 文件替代全部审查。[S1、S2](cloud-service-evidence.md#s1-版本与许可证)

**可作为商业产品底座，不等于开源默认配置已是可直接售卖的多租户云服务。** 默认 TenantExtension 不鉴权；内置 API Key 模式把有效请求映射到同一 schema。工作空间、成员、Bank 授权、凭据吊销、服务配额、客户账单、工单支持与 SLA 是华为云产品职责。已有授权／标签扩展点可以复用，但必须验证所有暴露路径。[S3](cloud-service-evidence.md#s3-隔离与授权)

本机 GPT 登录只用于这次合成数据体验。上线应使用获准的商用模型服务与区域内数据处理链路，明确留存、调用限额和费用责任；不能把个人订阅接入方式变成生产模型供给方案。

## 2 大模块和责任

```text
Agent／SDK／MCP／控制台
          ↓
华为云网关：认证、入口限流、请求观测
          ↓
ContextDB 产品服务：资源授权、稳定 API、路由、查询组合、晋升流程
          ↓                              ↓
服务单元 A                          服务单元 B …
Hindsight API + Worker               Hindsight API + Worker
          ↓                              ↓
RDS PG A 主备                       RDS PG B 主备

共用配套：控制元数据 PG、OBS 原件、模型接入层、密钥管理、监控审计
```

这是逻辑边界，不是要求 5 人自研七个微服务。首期产品控制面与业务编排可以是同一代码库；网关复用云配套；模型接入先做小型适配层。API 与 Worker 独立部署，使用同版 Hindsight 制品，便于分别控制在线延迟与后台费用。[S2](cloud-service-evidence.md#s2-现成服务能力)

| 模块 | 首期承担什么 | 不要混淆的边界 |
|---|---|---|
| Agent 接入 | 一个端点、一个作用域凭据、项目绑定、诊断命令；会话开始召回、结束异步写入 | 配好 MCP 只意味着工具可用，不保证宿主会自动调用 |
| 华为云网关 | TLS、验证外部身份、字节／请求限额、request_id、访问日志 | 验证 API Key 不等于验证某个 Bank 的读写权限 |
| 产品服务 | 工作空间／成员／角色、服务端资源归属、API 参数白名单、幂等受理、PG 单元路由、晋升和用量 | 不信任客户端传来的 tenant/schema/DSN，也不把 tenant_id 当身份凭证 |
| Hindsight API | 同步 recall、受理 retain、受控 reflect、原生文档／知识能力 | 保持上游可升级，不把云账号／计费硬编码进内核 |
| Worker 与维护进程 | 持久任务、提取、整合、刷新、重试、清理；按租户／单元限并发 | 入口 QPS 限流不能限制一个请求产生的后台模型调用量 |
| RDS PG／OBS | PG 保存事实、向量、关联边、任务与状态；OBS 保存原文件与导出物 | 原件移到 OBS 不会移走 PG 里的文本块、事实和索引 |
| 模型与观测 | 模型白名单、超时、并发、费用预算、Token 用量、trace、失败降级 | LLM、Embedding、Reranker 是不同依赖；切 Embedding 要考虑重建索引 |

PG 原生图路径使用关系表及检索算法，不要求 AGE。首期保留 pgvector 和 native 全文路径；不为用上既有 AGE 能力而改图存储。当前文件存储默认是 PG BYTEA，另有 S3 与 FileStorage 扩展；OBS 接入须测上传、下载、删除、签名和租户前缀，不能仅凭“兼容 S3”宣布完成。[S4](cloud-service-evidence.md#s4-pg-和文件存储)

两个容易漏掉的部署点：`WORKER_ENABLED=false` 只关闭内置任务处理，不自动关闭 MaintenanceLoop；需关闭在线 API 的相应维护间隔，并保留承担维护职责的进程。MCP 默认是有会话状态的 HTTP 模式；做任意实例路由前，应验证 stateless 模式与客户端兼容，或明确会话粘滞和断线重连策略。[S5](cloud-service-evidence.md#s5-无状态部署的条件)

## 3 资源和权限模型

建议对外采用 **云项目 → 工作空间 → 个人记忆库／团队知识库**。成员与服务账号通过角色和资源授权访问。内部初期一个工作空间对应一个租户 schema；每个人的私有记忆、每个共享知识库对应独立 Bank。schema 名使用稳定内部 ID，不以用户名命名，不因成员离职改名。对外隐藏 schema 与 PG 地址。

Bank 是数据范围，**不是自动生效的用户 ACL**。用户 A 能否读取用户 B 的 Bank，必须由产品服务在每次请求中判断；内网 Hindsight 也用扩展校验可信身份，避免绕过网关。标签优先用于项目／来源筛选，不把客户自报标签当权限。若使用标签授权，只能由服务端强制作用域，并测试 strict 模式、无标签、分页、图、原文、导出及后台派生结果。[S3](cloud-service-evidence.md#s3-隔离与授权)

一期只承诺“个人库私有、团队 KB 按库授权”；不承诺任意文档／段落级 ACL。跨团队分享通过复制已审核文档到目标 KB 完成，不引入全局共享 Bank。撤权要使新请求失效，并限制在途任务发布；已经交付给客户端的内容无法远程收回。

## 4 三条端到端链路

**写记忆：** Agent 发送会话摘要或选定片段、来源 ID 和幂等键 → 网关认证 → 产品服务校验库归属与预算、找到服务单元 → Hindsight 异步 retain → PG 保存任务 → Worker 调用模型并写事实／向量／关联 → 客户查询 operation。界面区分“已接收、可检索、整合中、失败”。原生异步 retain 支持客户端 operation_id；云层仍须绑定租户、动作和请求摘要，不能将它泛化为所有 API 的 exactly-once 保证。[S6](cloud-service-evidence.md#s6-接口与受理语义)

**读上下文：** Agent 带问题和项目绑定 → 服务端先求出有权访问的个人库与 KB → 对少量目标 Bank 并行 recall → 产品层去重、按预算组装并保留来源 → Agent 使用上下文回答。默认不追加 reflect；它会引入额外 LLM 推理。多 Bank 不同分数不可直接混排，首期用固定库配额或排名融合并分别标出“个人经验、团队规范”。返回前复核撤权／文档下线状态；不得先给 LLM 看无权原文再只过滤最终回答。

**晋升知识：** 成员选定有权发布的记忆／原文 → 固定来源版本 → 模板生成草稿，附来源及不确定点 → 人工编辑审批 → 写入目标 KB 并等索引完成 → 发布该版本 → 新成员可召回。未经批准的草稿只进入暂存区，不进入在线共享召回。后台重整合不得悄悄覆盖已发布知识。[S7](cloud-service-evidence.md#s7-知识能力)

知识管理一期保留原文、版本、状态、来源、作者／审批人、删除／撤回。先提供文本和 Markdown，其他格式按实际验收追加。可复用 Hindsight 的 `chunks` 模式保存 KB 文本，省去不必要的事实提取；其不会自动带来企业文档治理。合成 Knowledge Pages 可以作为草稿生成能力，不视为审批后的权威规范。

**本次发现一个必须由产品定义的删除边界：** 在克隆测试库删除唯一源文档后，recall 已无结果，但原先合成的 Knowledge Page 仍能读取完整旧内容。因而不能把原生“删除文档”包装成“彻底忘记”。普通源文档归档与隐私清除是两种操作；后者必须追踪并阻断相关页面、导出、缓存和后台任务，再清除或重建派生物。首期可先暂停受影响 Bank 的派生页面访问，直到重建完成。[实测记录](../deployments/hindsight-local/evidence/source-delete-check.json)

为压缩实现量，首期同一 KB 的发布／替换／删除串行执行；版本切换期间暂停该 KB 查询并显式返回短暂不可用，完成索引与校验后再打开。读、发布、撤回都走同一服务端状态检查，在途查询返回前再次检查。只有把可见性过滤做到检索前、派生链和返回前，才演进为不中断的多版本发布；不要以“最终一致”为理由让未审核文档可见。以上为建议方案，尚未实现。

## 5 PG 横向扩展

**先扩服务单元，后考虑单 Bank 分片。** 每个单元固定连接一个数据 PG 主库及可选只读地址；控制元数据保存 `workspace_id → cell_id + route_epoch + state`。新工作空间落到有余量的单元；大工作空间可迁入专属单元。API、Worker、迁移和维护只处理本单元租户。这样无需在 MemoryEngine 内维护跨 PG 连接池，也无需一个 Worker 遍历所有 PG。[S8](cloud-service-evidence.md#s8-扩展与历史实验)

| 瓶颈 | 首先采取的动作 | 能解决／不能解决什么 |
|---|---|---|
| 用户总量、总写入、总存储增长 | 新增 PG 服务单元，分配或迁移工作空间 | 扩总容量；单个 Bank 仍受一个 PG 限制 |
| 同一 PG 的在线查询慢 | 看 CPU／IO／锁／执行计划／连接与模型阶段；再决定调优或拆热租户 | 多加 API Pod 可能只会放大 PG 压力 |
| 可容忍延迟的 recall 读量大 | 验证 `READ_DATABASE_URL`，用只读副本分担 | 不扩主库写入能力；新写可见与权限变更要处理复制延迟 |
| 大量导入／整合挤占在线资源 | Worker 并发和每租户预算，分批导入、低峰维护 | 控制竞争；不是零成本提高吞吐 |
| 单租户特别大 | 先专属实例／升配，再按项目或知识库拆成多个 Bank／工作空间 | 拆后由产品层做有限扇出，不保留“跨分片完整图推理”承诺 |
| 一个 Bank 超出单机能力 | 明确容量上限；后续评估按业务边界拆分、分布式 PG 或新存储扩展 | 需要适配事务、图、索引、任务与评测，不是加 Citus 即完成 |

 迁移首期建议用可控维护窗口：**标记迁移并阻止新写 → 排空该租户 Worker／维护作业 → 导出 schema 及必要外部对象清单 → 在已预置同版本基础函数的目标 PG 恢复 → 校验表、索引、任务和召回 → 原子切换路由版本 → 开放读写**。源端必须拒绝旧路由的写，不能只改缓存；失败留在源端，目标不可被静默当作新库。目标已接受新写后，不允许仅改路由倒回旧库。schema 名保持不变可避免原生对象存储前缀随迁移变化。RDS PITR 是整实例恢复，单租户恢复通常需临时实例再抽取租户数据。

容量触发按实测的 recall p95、最老排队年龄、IO／连接余量、索引增长、迁移耗时制定。不要先许诺“每库百万租户”：schema／表／索引数量、按 Bank 索引和维护发现成本都需压测。既有多 PG 报告的 `schema_router.py` 在当前源码中未找到，不能作为现成上线能力。[S8](cloud-service-evidence.md#s8-扩展与历史实验)

## 6 首期开放范围

当前源码 OpenAPI 有 **99 个 method/path 组合**，其中含运维和已退役接口；数字不代表 99 项可用客户能力。完整清单见 [接口证据](../deployments/hindsight-local/evidence/source-api-inventory.txt)。建议公共 API 使用华为云稳定契约，再适配原生接口。[S6](cloud-service-evidence.md#s6-接口与受理语义)

| 能力 | 原生接口概要 | 一期建议 |
|---|---|---|
| Bank 管理 | `PUT/GET/DELETE .../banks` 及资源路径 | 通过产品资源管理，受限开放；创建参数也必须白名单 |
| 记忆写入 | `POST /v1/default/banks/{b}/memories` | 核心开放；默认异步，提供幂等键和任务状态 |
| 记忆召回 | `POST .../memories/recall` | 核心开放；限制预算、返回长度和目标库数 |
| 来源／记忆管理 | `documents`、`memories/list`、单条读取／修改 | 开放查证、纠错、删除及受控导出；删除覆盖派生与恢复流程 |
| 任务 | `operations` 查询／取消／重试 | 开放，区分受理与成功；重试仍计入执行预算 |
| reflect | `POST .../reflect` | 试用可选、高成本限额；不作为每次检索的默认路径 |
| 知识页面／Mental Models | `knowledge-base/*`、`mental-models/*` | 后端复用；只开放简单页面或草稿操作，不暴露全部自动刷新策略 |
| 文件入库 | `files/retain` | 先 TXT／MD；PDF 等经解析质量和资源限额验证后追加 |
| 晋升／团队协作 | 无完整云审批与组织模型 | 自研最小草稿—审核—发布—撤回闭环 |
| MCP／SDK | 原生 MCP、多语言 SDK | 先一种 Coding Agent + HTTP SDK 验收；MCP 只发布少量允许工具 |
| 配置／提示词／导出恢复 | `config`、`prompts/preview`、`transfer`、模板 | 管理面专用；模型地址、凭据、策略、跨库转移不直接透传 |
| 图、webhook、原始 LLM trace | `graph`、`entities`、`webhooks`、`llm-requests` | 初期内部运维；敏感原文、外呼地址、Token 消耗都需单独治理 |

`/v1/default` 不是客户指定 schema 的入口。不同租户由认证扩展解析到 schema。MCP 工具清单、原文下载、管理 UI 代理和异步导出都必须过同一授权模型；隐藏 UI 按钮不能替代服务端拒绝。[S3、S6](cloud-service-evidence.md#s3-隔离与授权)

## 7 五人排期和上线门槛

以下是工作量规划，不是完成事实。人员可按强项交叉承担。

| 角色 | 主责任 | 6–8 周产出 |
|---|---|---|
| 1 服务负责人 | 契约、网关适配、资源 ACL、审计 | 正确的租户／成员／Bank 边界，公开接口白名单 |
| 2 Hindsight 工程 | 固定版本、扩展、任务与模型控制 | retain/recall/reflect、重试与费用上限，升级回归集 |
| 3 PG／SRE | RDS 适配、连接／DDL、备份恢复、服务单元 | 两单元分配演练、维护窗口迁移、恢复报告 |
| 4 产品体验 | 简单控制台、客户端接入、知识晋升 | 5 分钟接入路径、来源查看、审批发布闭环 |
| 5 验证工程 | 跨租户矩阵、中文场景、故障与费用 | 可重复验收、发布门禁；与前四人共建自动化 |

第 1–2 周锁定版本与模型、打通真实 RDS／OBS、小样本体验；第 3–4 周完成权限、配额、客户端和文本 KB；第 5–6 周完成晋升、恢复与双服务单元演练；第 7–8 周仅做试点反馈、容量标定与上线补洞。若仅有 4 周，收缩为少数客户专属部署／邀请试用，不压缩隔离和恢复验收。

上线必须通过：跨用户／跨租户所有公开入口拒绝越权；重试不重复受理／不重复客户扣费；Worker 中断可恢复；PG 故障与恢复后原文、索引、派生状态一致；删除／撤权不被后台任务或恢复重新公开；中文实例名、SQL 错误码和版本号能正确查证；用量超过预算能停止后台工作；新用户按文档完成一次跨会话回忆。性能与费用的数值承诺在目标华为云规格压测后填写，不由本机样例推导。

## 8 持续跟随社区

将云资源、审批、账单和路由放在外层，将确需内核感知的身份／配额放在正式扩展点。固定 **源码 SHA + 依赖锁 + PG 扩展版本 + 模型版本 + 配置**；禁止生产追随 `latest`。每次升级检查 OpenAPI 差异、schema 迁移、权限边界、任务恢复和一组中文金标，再按服务单元灰度。数据库迁移不保证可逆；旧镜像回滚不等于数据回滚。

已有大型候选架构中的“网关／在线业务／Worker 分开”“原件先持久化”“授权覆盖派生结果”值得保留；成对 rt/ud schema、统一重写运行时、全链路强一致账本与大范围内核改造不应在首期一并实施。用户提供的在线稿明确写着产品／生产验证 NOT_RUN，本报告把它作为待审设计，不把其中“已确认”的表述当作本轮授权或事实。[S9](cloud-service-evidence.md#s9-用户提供的待审材料)

## 9 可开工的设计基线（本轮新增）

本节把前面的概览落实为 HLD、LLD 和任务板。**下面是拟实现设计，不是已部署的华为云产品。** 本轮本地验证支持其中部分机制，不代表 IAM、APIG、RDS、OBS、MaaS 生产联调已经通过。与前文概览冲突时，以本节收敛后的首期范围为准。

### 9.1 首期范围与明确取舍

交付目标：一个区域、邀请试用、文本/Markdown、个人记忆与按库授权的团队 KB；支持原生客户端的经验证子集。实现创建空间、发放 key、写入/召回、任务诊断、来源查看、审核晋升和撤回。先用一个数据单元，发布前完成第二单元的新租户分配与维护窗口迁移演练。

- 一个 workspace 对应一个 Hindsight tenant schema；每个个人库或团队 KB 对应 Bank。workspace 与云账号、成员、项目的映射由控制层持有。
- 团队内 Bank ACL 是产品层新增能力，不能用 schema 隔离代替。客户不提交 schema、DSN 或可信 tenant_id。
- 模型 profile 固定在服务单元；同一单元不允许客户任意切 Embedding/维度。要提供不同模型套餐，先按 profile 分单元，避免改写 Hindsight 模型实例生命周期。
- 默认直接 Recall；Reflect 受限开放。KB 用 `chunks` 模式、关闭自动 observations，避免审核后的规范被后台自由改写。
- 原文首期可以保持 PG 原生存储；接入 OBS 只用于不可变上传原件/导出，不以“必须先迁走全部文件”为上线前提。需要文件存储扩展时再验证 S3/OBS 协议。
- 不承诺透明单 Bank 分片、零中断版本切换、任意历史快照、全套原生 API 对外兼容或四种客户端全部自动记忆。

### 9.2 HLD：部署单元与所有权

```text
客户 Agent / HTTP SDK / 云控制台
                │ TLS + 外部凭据
         华为云入口（APIG/已有网关）
                │
     ContextDB 服务（一个代码库，两种运行角色）
     ├─ API角色：鉴权、Bank授权、兼容路由、管理接口、MCP适配
     └─ 协调角色：开通、幂等派发、发布/删除、用量对账、迁移
          │                    │
          │                    └─ 控制PG：资源、权限、任务意图、用量
          │ 可信内部请求
     ┌────┴────────────────────────────────┐
     │ Cell：Hindsight API + Worker + PG   │
     │ API副本 / Worker副本 / 维护职责      │
     │ 一个固定PG写地址和一个模型profile    │
     └────┬────────────────────────────────┘
          ├─ 模型服务（获准MaaS或自部署）
          └─ 原件/导出存储（按需OBS）
```

控制 PG 和数据 PG 生产上独立实例。控制层没有复制 Hindsight 的任务队列：它只记录产品意图与跨服务补偿；抽取、整合、刷新继续由 `async_operations` 执行。协调角色可与 API 共用代码和镜像，以独立进程启动，不再建立多个小微服务。

| 组件 | 要开发什么 | 复用什么 | 运行/故障边界 |
|---|---|---|---|
| ContextDB API | 凭据、授权、路由、参数白名单、管理API、客户错误码 | 原生HTTP SDK响应模型，已验收的插件协议 | 无法确认授权时拒绝；不缓存正文 |
| ContextDB coordinator | 持久工作项、幂等派发、开通/发布/删除状态机、对账 | 控制PG行锁与事务 | 进程重启从未完成工作项恢复 |
| Hindsight tenant extension | 校验内部身份，返回schema；列举本Cell租户；配置白名单 | `TenantExtension` | 不能默认匿名；不能接受客户伪造内部头 |
| Hindsight validator | retain/recall/reflect等关键路径补充授权与用量 | `OperationValidatorExtension` | 不是所有管理API都自动覆盖；外层精确路由白名单仍必要 |
| Hindsight API/Worker | 不改核心算法；分进程部署 | 上游API、持久任务、检索与模型适配 | 版本相同；并发与连接数分别限制 |
| PG/维护 | 迁移预置、备份恢复、schema容量、慢SQL | RDS PG及上游migration/maintenance | 扩容按Cell；DDL不在客户首个请求中临时执行 |
| 客户连接页 | endpoint/key/bank配置、诊断、最近调用与任务状态 | 上游插件配置格式 | 不以“连接成功”替代“实际写入召回成功” |

建议目录（待创建，不表示当前已有）：`contextdb/api/`、`auth/`、`resources/`、`routing/`、`jobs/`、`knowledge/`、`metering/`、`compat/`；扩展独立包 `contextdb_hindsight_ext/`；契约测试 `tests/contracts/`；云清单 `deploy/`。不得把云账号逻辑直接写进上游 `memory_engine.py`。

本轮已实际启动API-only与独立Worker，用新schema完成12项检查：无Worker任务排队、启动后处理、停止Worker时API召回继续、重启后排空积压、健康/指标读取。[实测](../deployments/hindsight-local/round2/evidence/split-worker-probe.json)。未覆盖执行中强杀或PG断电。

### 9.3 LLD：控制数据模型

下表给出最小表合同；DDL、索引与迁移属于任务 D02 的交付，不是上游现成表。所有关系包含 workspace 归属校验，不能仅凭全局对象 ID 判定授权。

| 表 | 核心字段与唯一约束 | 用途 |
|---|---|---|
| `workspaces` | `id, cloud_project_id, region, state, auth_epoch` | 产品归属与冻结 |
| `memberships` | `(workspace_id, subject_id)` PK；`role, state` | 成员/服务账号身份 |
| `model_profiles` | `id, version, llm_model, embedding_model, embedding_dimension, reranker_model, config_hash` | 发布后不可原位修改，变更新建profile |
| `cells` | `id, region, model_profile_id, internal_endpoint, state, upstream_sha, image_digest, schema_version` | 可放置的服务单元；密钥仅保存引用 |
| `placements` | `workspace_id` PK；`cell_id, schema_name, route_epoch, state` | 唯一当前放置；迁移时冻结 |
| `banks` | `id` PK；`(workspace_id, public_bank_id)` unique；`native_bank_id, kind, owner_subject, state, content_epoch` | 私有记忆/团队KB资源 |
| `bank_grants` | `(workspace_id, bank_id, subject_id)` PK；`actions` | read/write/manage/publish权限 |
| `api_keys` | `key_id` PK；`digest, pepper_version, workspace_id, subject_id, scopes, bank_constraints, expires_at, revoked_at` | 客户凭据验证；不存明文secret |
| `request_ledger` | `(workspace_id, bank_id, action, idempotency_key)` unique；`payload_hash, operation_id, subject_id, key_id, state, created_at` | 幂等与派发恢复 |
| `jobs` | `job_id` PK；`kind, resource_id, phase, attempt, next_retry_at, payload_ref` | 产品开通/发布/删除/迁移意图 |
| `source_revisions` | `(workspace_id, source_id, revision)` unique；`content_hash, raw_ref, author, state` | 来源可追溯；原件引用不可随迁PG改变 |
| `publications` | `id, workspace_id, kb_id, source_id, source_revision, reviewer, native_document_id, job_id, state` | 草稿审核和发布状态 |
| `usage_events` | `event_id` unique；`workspace_id, operation_id, attempt_id, provider, units, status` | 可去重用量与供应商对账；未知不记成零 |

控制库不保存所有事实/向量，也不复制 `async_operations` 的执行细节。来源文本可以存在受控原件存储，控制表保存引用与hash。删除控制对象需先完成下游清理，不直接用级联删除把恢复线索删掉。

参考DDL已落地为 [control_schema_reference.sql](../deployments/hindsight-local/round2/scripts/control_schema_reference.sql)，在真实PG独立schema执行了约束验证。[结果](../deployments/hindsight-local/round2/evidence/control-schema-results.json)。它验证复合FK/唯一性和事务等局部合同，不是可直接投产的migration；角色/RLS、JSON权限条件、跨region放置、模型profile不可变性与完整索引仍需D02/D03实现。

### 9.4 LLD：API与客户端兼容合同

分开两类接口：产品管理路径（拟定）`/v1/contextdb/...`；原生兼容路径保留 `/v1/default/banks/...`。`default` 是协议固定段，不是客户可指定的 PG schema。兼容层应有请求/响应契约测试，不承诺透传全部原生接口。

| 外部接口/动作 | 关键输入输出 | 校验与映射 |
|---|---|---|
| `POST /v1/contextdb/workspaces` | 名称 → workspace及开通job | 云身份校验；placement ready前不可用 |
| `POST .../api-keys` / `DELETE .../api-keys/{id}` | 作用域/有效期 → 一次性完整key；撤销返回状态 | 管理权限；创建不赋予超出主体的权限 |
| `PUT /v1/default/banks/{bank}` | 插件首次建库 → 兼容Bank响应 | 只允许主体创建自己的个人Bank；禁止借同名请求接管他人库 |
| `POST .../{bank}/memories` | items、document_id、async、operation_id → 原生响应 | 请求摘要、授权、大小限额；不悄悄改变插件期待的同步/异步语义 |
| `POST .../{bank}/memories/recall` | query、budget、max_tokens、tags → 原生结果 | 只读授权；对预算与返回附件分别限额 |
| `POST .../{bank}/reflect` | query → 生成回答 | 独立额度；默认不让插件每轮隐式触发 |
| `GET .../{bank}/operations/{id}` | → 运行状态与安全错误摘要 | operation必须属于当前Bank/租户 |
| `GET/DELETE .../{bank}/documents/{id}` | 来源查证/撤回 | 文档归属；派生处理；删除不是只删一张表 |
| `POST /v1/contextdb/promotions` / `.../{id}/approve` | 来源版本/目标KB → 发布job | 发布权限、审核人、来源读取权限 |
| `/mcp/{bank}/` | tools/list、tools/call | 同一身份与授权；仅开放验收工具；HTTP与MCP不能各有一套宽松权限 |

客户端必需的 `bank/config` GET/PATCH（重置为DELETE）、能力探测等由实际插件HTTP记录确定白名单；不直接封死后再宣称兼容。只允许经验证的配置字段，禁止任意URL、webhook、provider和凭据下发。注意当前 `ConfigResolver` 对 `get_allowed_config_fields` 的部分异常会退回允许全部可配置字段；云扩展应将权限查询失败转为明确拒绝或空允许集合，外层同时拒绝该配置请求，不能依赖抛出网络异常自动关闭权限。此行为已用真实ConfigResolver+记录后端fixture复现，TimeoutError/RuntimeError会继续写，空集合/ValueError拒绝；需纳入D03负向测试。[证据](../deployments/hindsight-local/round2/evidence/parameters-failopen.json)

MCP首期应通过产品MCP工具层转入相同业务函数，或在原生MCP扩展上完成等价授权后再放行；不能只检查URL Bank就允许所有工具调用。选择哪条路径由 D06 的兼容测试决定，当前不宣称透明MCP代理已经实现。会话模式、反向代理超时、重连、取消和撤权必须一起测。

错误合同：401凭据无效/过期；403无权；404资源不可见；409幂等正文冲突或资源正在变更；413输入过大；429超过产品额度；503授权依赖不可用/KB维护中。保留原生SDK所需错误结构，HTTP状态语义与业务码通过兼容测试固定。

### 9.4.1 首期客户端与团队查询的具体约定

连接页生成个人Bank的稳定产品ID，首期官方配置使用显式 `bankId`，关闭插件自动按仓库创建Bank的模式；先避免同一团队两位成员在同名仓库中发生资源命名碰撞。Bank ID由产品生成，不以客户端路径或仓库名直接决定归属。后续支持动态每仓库Bank时，应增加“主体+仓库标识→Bank”映射并单独验收，不复用团队共享ID作为私有库ID。

原生兼容Recall先保持单Bank语义，避免把团队KB结果混入个人库响应后，客户端再用个人Bank路径读取来源却得到404。团队组合查询采用新增产品接口（拟定）`POST /v1/contextdb/context/query` 及对应MCP工具 `recall_context`：

- 输入：`query`、可选个人Bank和KB选择、总 `max_tokens`。服务端重新计算可访问集合，客户端选择只缩小范围。
- 首期限制最多1个个人Bank+2个KB，超出返回明确错误；这是产品范围建议，非原生限制或压测结论。
- 输出：`items[{bank_id, kind, memory_id/document_id, source_revision, text, citation_url}]`、`truncated`、`request_id`；来源链接回到产品权限入口。
- 按固定库配额分配总上下文预算，不直接比较不同Bank的原生相关性分数；返回前复核各资源状态与epoch。任一必选来源失败则明确失败，不静默给出貌似完整的团队答案。
- 云连接配置额外注册团队查询MCP工具；原生插件的自动个人记忆继续复用。**首期不宣称未经修改的原生自动hook已经自动合并团队KB。** 若后续希望每轮自动融合，修改薄客户端适配层并重新做真实会话/预算/来源读取验收。

该接口和工具是D06/D08交付的一部分，当前只是明确合同。它使“原生兼容”和“新增团队查询”各自可测试，不以不兼容的混合响应破坏已有客户端。

### 9.5 LLD：凭据与可信身份

授权取主体权限、key scopes/Bank约束、资源状态三者交集；key只能缩小主体权限，不能扩权。key不保存明文密钥或客户端自报的schema。

客户 key 建议为 `ctx_<key_id>_<256-bit随机secret>`，使用安全随机数，创建时显示一次。tenant、subject、Bank权限和Cell位置在控制库中查询，不把全部租户资料或下游模型密钥塞进key。key自身就是Bearer secret；可含非敏感版本/查找标识，但不以可解码字段作为可信身份。

服务端可保存 HMAC-SHA256 摘要，pepper 由密钥管理服务注入并版本化；比较使用恒定时间比较。轮换生成新key，短期双key并存，确认切换后撤旧key。首期每请求查当前有效性与授权，不用长TTL权限缓存换取性能；后续缓存必须验证撤权上限。

向 Hindsight 传递独立内部凭据及短期签名身份断言：包含 workspace、subject、bank/action、cell、route_epoch、request_id、过期时间和audience。入口移除同名客户头；扩展仅接受可信服务身份/签名，校验bank/action与实际请求一致。`list_tenants()`仅返回本Cell当前可处理的placement，不能让每个Worker遍历全平台租户。异步任务不保存短期断言当作未来授权，执行时用服务身份和持久主体标识重新解析当前策略。原生Retain子任务已携带 `_tenant_id` 与 `_api_key_id`，Worker可重建这两项context；云扩展可由key_id查主体/当前scope，撤销记录必须保留到任务与审计保留期结束。产品账本另存subject_id/key_id，不假定上游已持久化完整ACL。后台整合等无客户key的任务使用显式系统主体，只处理仍有效的Bank并计入所属workspace，不能把“缺少key”当成匿名授权。这一内部协议尚待实现与测试；本轮原型只验证外层opaque-key和Bank ACL。

**本地验证：** [auth_probe.py](../deployments/hindsight-local/round2/scripts/auth_probe.py) 用真实控制PG database和Cell B HTTP执行27项检查，包括同名跨租户隔离、私有库拒绝、只读key拒写、伪造tenant头、过期、轮换与撤销、数据库不存明文key。该原型不包含生产网关、IAM/KMS、MCP、缓存和分布式撤权；控制/数据database位于同一本地实例，不能证明独立实例HA。[结果](../deployments/hindsight-local/round2/evidence/auth-probe.json)

### 9.6 LLD：写入受理与重试

1. 验证主体、Bank写权限、资源状态和输入；生成规范化正文hash。由 `(workspace,bank,action,idem_key)` 找到请求记录。
2. 首次请求在控制PG事务中记录 `PREPARED` 与稳定UUID `operation_id`；相同key相同hash返回原记录，不同hash返回409。
3. 调用原生异步Retain，显式传同一个 `operation_id`。收到上游持久受理响应后更新 `SUBMITTED` 并返回operation。
4. 若请求超时，保持 `PREPARED/UNKNOWN`；协调器重试相同operation，不生成新UUID。客户用同一幂等键重试，不把超时当“肯定没执行”。
5. 上游完成/失败后同步可查询状态；来源内容/任务记录按约定保留。原生operation过期清理前必须完成对账；过期后的旧幂等键不能当作新请求重新派发。

这里不用控制PG与数据PG两阶段提交。重复请求安全依赖原生operation幂等，加控制层正文摘要和恢复记录。对同步原生请求不能直接套用此保证：首期推荐异步接入；同步兼容路径单独验收、单独说明重试语义。

**本地验证：** 8个并发原生请求得到同一operation，跨Bank复用返回409；同operation改变正文仍返回旧任务，并未写入新正文。控制PG摘要账本在并发下只产生一行，并对不同正文返回409。11项检查通过。[脚本](../deployments/hindsight-local/round2/scripts/idempotency_probe.py)、[结果](../deployments/hindsight-local/round2/evidence/idempotency-probe.json)。这不是模型调用“恰好一次”的证明。

### 9.7 LLD：团队知识发布与删除

首期选成本较低的“按KB串行、变更时暂停查询”，不做全量不可变事实版本系统：

- 草稿与审批记录在控制层；草稿不写入公开KB。来源用固定revision，避免审核期间原文变化。
- 审核通过后，在控制PG同一事务中将KB设为 `PUBLISHING`、递增 `content_epoch`、写发布job。
- 协调器按确定性document_id将已审核文本写入KB（chunks模式）；等待operation完成并校验来源可读，再将KB改为 `READY`。
- 查询前必须看到 `READY` 并取得epoch；返回内容前再次检查授权、状态与epoch。期间发生发布/撤回则不返回旧结果。初期KB禁用流式Reflect，避免检查前正文已泄露给客户。
- 发布失败或进程中断保持 `FAILED_CLOSED/PUBLISHING`，恢复任务重试/修复后才开放；不得让部分新旧内容混杂返回。
- 撤回先置 `DELETING` 并递增epoch，随后清理原文、记忆及受影响派生物；清理完成再开放其余资料。备份恢复后重放撤回记录，避免旧数据复活。

**本地验证：** [publication_probe.py](../deployments/hindsight-local/round2/scripts/publication_probe.py) 的14项真实PG事务检查覆盖并发发布仅一胜者、状态与job同事务、连接重建后的持久状态、失败保持关闭、epoch阻止旧查询结果、回滚无孤立job。[结果](../deployments/hindsight-local/round2/evidence/publication-probe.json)。它模拟“索引已完成”的通知，没有实现完整的Hindsight知识发布服务，也没有验证全部读取路径；这些属于D08/D10上线门禁。

### 9.8 LLD：成本、扩展、恢复

**成本。** 先记录每次operation/attempt的输入输出token、Embedding文本量、Rerank候选数和供应商请求ID；用量缺失标记unknown，不记成免费。`OperationValidator` 的post hooks提供部分统计，但不能假设已覆盖所有后台模型重试或供应商实际扣费。首期以产品输入/频率/并发/后台任务上限控制风险，试用不承诺精确预付扣款。若要硬人民币预算，必须在所有模型出站路径做逐次预留与结算，单列D07验收，不能仅在入口QPS限流。

**扩展。** 新workspace按PG剩余容量、连接余量和任务积压分配Cell。模型profile/Embedding空间固定；不允许把不同向量维度数据直接混入同一索引。扩API不等于扩PG吞吐；扩Worker前检查数据库和模型限额。首次压测输出每Cell推荐工作空间/Bank上限，不能预写百万租户承诺。

**迁移。** 首期维护窗口迁移：冻结workspace读写/新任务→排空worker和维护→备份schema及控制引用→目标同版本恢复→校验记录/索引/召回→CAS切换placement的route_epoch→开放。源端扩展必须拒绝旧epoch/冻结状态；目标接受新写后不得简单回指旧库。需分别演练切换前失败和切换后失败。

**恢复与发布。** 先在目标RDS版本演练DDL权限、扩展、连接、备份和PITR。发布制品记录上游SHA、依赖锁、扩展包、配置hash、模型ID与向量维度；迁移由受控job先执行；普通API尽量仅持DML权限，运行期DDL由受控开通/维护身份承担，必须逐路径验证。回滚镜像不代表数据迁移可逆；破坏性迁移必须采用前后兼容或恢复方案。当前本地PG体验实例不能用于推导RDS持久性/SLA。实测两套pg0实例均为 `fsync=off`（启动参数 `-F`），因此本轮事务/重试验证不证明断电耐久性；云配置必须启用fsync并在目标RDS上验证复制与恢复。[PG实测](../deployments/hindsight-local/round2/evidence/pg-runtime.json)

### 9.9 Bank开通权限与控制台身份

本地权限探针发现：关闭启动迁移并预迁移schema后，DML-only运行账号能健康启动，但原生建Bank因同步CREATE INDEX返回500（必须是memory_units表owner）。用特权身份先建Bank，再切换DML账号，配置/chunks Retain/Recall通过。证据：[失败](../deployments/hindsight-local/round2/evidence/parameters-privilege-results.json)、[预建方案](../deployments/hindsight-local/round2/evidence/parameters-privilege-prebank.json)。此结果仅覆盖上述链路，未覆盖全部维护/删除/LLM任务。

D02/D04落实流程：客户Bank创建请求经授权后生成唯一开通job → 受控特权执行器在已分配schema中调用原生开通逻辑 → 校验Bank和索引 → 控制表标记READY → 放行普通数据请求。原生客户端首次PUT Bank由产品层接管；幂等重放返回已有资源；连接页优先预开通后发配置。兼容PUT只在READY后返回原生200响应，等待超出服务端上限则返回503及Retry-After（须验收插件重试/诊断），不把产品202 job响应冒充原生成功；不能透传给DML-only API。特权凭据仅提供给开通/维护执行器；列出并验收删除Bank、索引重建及维护DDL所需权限，不通过赋给所有API表owner来掩盖分工缺失。

原生UI使用共用后端key，可选CP_ACCESS_KEY只提供共享登录口令。本轮隔离UI的匿名拒绝/正确口令登录5项检查通过，但没有逐客户权限能力。D06的客户连接页和来源查看必须走产品服务的成员身份；原生UI首期仅限内部运维。[UI验证](../deployments/hindsight-local/round2/evidence/ui-access-probe.json)

## 10 五人可执行任务板

以下为**计划估算**：5人×8周×5工作日＝200人日；开发/验证任务160人日，余40人日用于集成、试点反馈和缺陷。现有APIG/IAM/RDS/模型服务需可复用；若需新建这些平台，应延长排期或缩小范围，不以压缩安全验收换日期。

角色：A产品服务/鉴权；B Hindsight扩展与兼容；C PG/部署运维；D客户端/UI/知识流程；E测试与质量。每人仍需参与自己模块的测试，不把全部测试留给E。

| ID | 任务与具体交付 | 负责人；估算 | 依赖 | 完成判据 |
|---|---|---|---|---|
| D01 | 固定源码/依赖/制品；导入上游CI；失败分类清单 | E+B；8人日 | 无 | 可复现测试，失败有证据和处理结论，不把skip计pass |
| D02 | 控制表DDL/API骨架、workspace/成员/placement、受控Bank开通job | A+C；12人日 | D01基线 | 并发开通唯一；中断后可恢复；未ready不可访问 |
| D03 | key创建/过期/轮换/撤销及scope、Bank ACL、内部身份扩展、授权依赖故障拒绝 | A+B；18人日 | D02 | HTTP/MCP/下载/任务/配置公开路径无越权；吊销生效界限有测试 |
| D04 | API/Worker制品与部署、目标RDS迁移/备份/监控 | C+B；15人日 | D01 | 特权开通与DML运行分离；维护权限逐项验收；恢复与配额可观测 |
| D05 | 原生HTTP兼容、字段白名单、幂等账本与协调恢复、异步主体持久化及执行/返回前复核 | B+A；16人日 | D02/D03 | 同key同正文重放、异正文409、超时丢ACK恢复；SDK契约通过 |
| D06 | 带成员身份的客户连接页、诊断、MCP及首个真实Agent hooks | D+B；14人日 | D03/D05 | 两独立会话自动写入召回；断线、权限失效可解释 |
| D07 | 模型profile、获准MaaS实测、用量与任务额度 | B+C；14人日 | D01/D04 | LLM/Embedding/Rerank分别协议测试；超时429重试可控；用量不漏主要路径 |
| D08 | 文本KB、来源revision、人工晋升/撤回、可见性状态机 | D+A；20人日 | D02/D03/D05 | 未审核不可见；并发发布串行；失败关闭；撤回不再召回 |
| D09 | 第二Cell放置、维护窗口迁移、升级/恢复runbook | C+A；12人日 | D04/D05 | 源冻结、目标校验、旧route拒绝、切换失败演练通过 |
| D10 | 云多租户负向矩阵、模型/PG/worker故障、成本压力测试 | E+各模块；15人日 | D03–D09逐步 | 公开入口逐项通过；未过项目不能宣称支持 |
| D11 | 30–50条领域金标与基线对照、第二客户端与兼容矩阵 | E+D；10人日 | D06/D07/D08 | 同预算比较有原始记录；插件test与真实客户端E2E分开 |
| D12 | 控制台收尾、客户文档、灰度/回退、值班交接 | 全员；6人日 | D10/D11 | 非作者按文档接入、定位失败、撤销key并恢复测试资源 |

关键路径：D01→D02→D03→D05→D08→D10→D12。D04/D07、D06、D09并行推进但不能绕过依赖门禁。人日可跨角色调配，周会上按实际消耗更新，表格不是可直接相加的单人串行工期。

| 周 | 里程碑 | 当周必须可演示 |
|---|---|---|
| W1 | 基线和垂直最小链路 | 固定版本→隔离PG→API/Worker→SDK写入召回；列出现存失败 |
| W2 | 身份和云依赖 | workspace/key/Bank授权；目标RDS与获准模型跑通一条链路 |
| W3 | 兼容与可靠受理 | 原生SDK/首个Agent；幂等、超时、worker重启；连接诊断 |
| W4 | 最小团队KB | 个人库私有、团队KB按库授权、文本上传与来源；邀请内测 |
| W5 | 晋升/撤回闭环 | 审批→发布→新成员召回→撤回；故障关闭和重试 |
| W6 | 双Cell与用量 | 放置/迁移、恢复、费用与任务额度、第二客户端 |
| W7 | 试点和容量 | 真实领域样例、目标规格压测、权限/删除/故障补洞 |
| W8 | 发布判定 | 发布门禁、客户说明、灰度及值班；未过则保留邀请试用 |

若必须4周交付：限定单Cell、单模型profile、一个验收客户端、手动开通及审核，提供受控内测。完整团队治理、迁移、精确计费和四客户端自动记忆不能同时保证；不能把这份缩小范围的内测称为完整GA。

## 11 发布门禁与证据交付

每次候选版本必须产出：`release-manifest.json`、测试JUnit、失败/skip分类、公开接口权限矩阵、模型profile结果、真实客户端跨会话记录、恢复与容量记录。日志默认不记录完整Authorization、模型凭据或用户原文。

| 门禁 | 通过条件 | 本轮证据适用范围 |
|---|---|---|
| 上游基础 | 固定版本的必选suite通过或有明确不适用范围 | 本轮实际结果见主开发文档；不能用CI配置存在代替执行 |
| 租户/权限 | 全公开路径含MCP和异步读取，无跨主体泄露 | 27项原型检查只证明已覆盖的局部机制 |
| 可靠受理 | 重复请求、ACK丢失、worker重启、operation清理边界 | 11项本地幂等检查；长期清理与进程故障仍需全链路 |
| KB可见性 | 草稿不可见、发布失败关闭、撤回覆盖派生 | 14项PG状态机检查；完整知识流程待开发 |
| 模型与客户端 | 拟上线模型/插件版本在真实路径通过 | 假模型/插件unit不等同MaaS或客户端E2E |
| RDS/OBS/网关 | 目标区域与规格的权限、故障、恢复、协议验证 | 本机不能替代；没有资源凭据则明确列为待执行 |
| 性能与质量 | 可解释的并发/数据规模、p50/p95、Token及领域成功率 | 小型合成样例不能证明生产SLA或竞品优势 |

启动开发前可以确定上述合同和任务，**是否上线由证据门禁决定，不由“8周已到”决定。**
