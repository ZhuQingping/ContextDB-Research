# ContextDB 首期工作空间 用户与 API Key 服务化设计

更新日期：2026-10-13。首期只实现工作空间管理、用户管理和 API Key 管理，以及这些能力必需的认证和工作空间授权。采用租户独享 API/Worker/RDS PG，同一个 PG 数据库中每工作空间独立 schema，schema 内唯一 Bank。管理接口改为管控后端专用，使用部署时配置的管理 API Key；Hindsight 节点不直接接入用户 IAM Token 校验。以下接口和扩展为待实现设计，不代表服务已完成验收。

## 首期交付范围

| 本期实现 | 本期不实现 |
|---|---|
| 动态创建、查询、修改、冻结和删除工作空间；初始化对应 schema 和唯一 Bank | 同 Bank 内个人记忆按用户隔离 |
| 动态创建、查询、改角色、停用和删除工作空间用户 | 私有记忆与共享知识的 tag 授权、记忆晋升和知识发布工作流 |
| 用户多 API Key 的签发、查询、过期、撤销和轮换 | 成员级记忆/文档/派生内容 ACL、成员任务私有状态适配 |
| 管控专用 Key 认证、admin/member 授权、用户 Key 认证与空间/schema/Bank 范围校验 | 节点直接校验用户 IAM Token、父子 Key 委派、跨空间 Key、组织层、用户组与独立计费服务 |

**本期使用默认记忆语义：同工作空间、同 Bank 的用户只要具有相应读取权限，就可能读到其他用户写入的记忆。Key 绑定用户用于凭据归属、管理授权和审计，不等于记忆所有权。**不能宣传“个人记忆私有”，也不能把控制台的用户筛选当成后端隔离。

用户隔离的论据与候选思路见[后续记忆隔离备忘](member-memory-isolation-future-notes.md)。这部分不是本期验收门槛或已经实现的功能。

## 产品关系与存储映射

```text
云租户（独享 API / Worker / 一个 RDS PG 数据库）
  └─ 工作空间 × N（每空间独立 schema 内唯一 Bank）
       ├─ 用户 A：管理员 admin → API Key × N
       ├─ 用户 B：成员 member → API Key × N
       └─ Bank 内记忆/知识：沿用上游共享语义，用户记忆隔离未实现
```

用户也叫成员，两者是同一实体，沿用 `member_id` 作为工作空间用户 ID。只有 admin/member 两种角色，不设 Owner、全局用户目录或单独服务账号类型。同一个云登录身份在多个空间分别建立用户记录，角色和 Key 独立。保留 `iam_subject` 作为与已有管控登录身份的绑定字段，不代表 Hindsight 节点需要调用 IAM。

一个 Key 必须且只归属一个用户，从该用户解析云租户和工作空间；不能自选其他 Bank。每空间唯一 `bank_id = workspace_id`，名称修改不改变 Bank ID 或 schema。应用用一个用户的 Key 服务多个终端用户时，Hindsight 不会自动识别这些终端用户。

![工作空间与用户关系](diagrams/contextdb-workspace-model.svg)

```text
一个租户独享 PG 数据库
  ├─ ctxdb_meta：工作空间、用户、API Key、管理任务与审计
  ├─ ctxdb_ws_a：Bank A、记忆/索引、原生任务表
  └─ ctxdb_ws_b：Bank B、记忆/索引、原生任务表
```

schema_name 由服务端生成并登记，例如 `ctxdb_ws_<workspace_id_hex>`，在本 DB 内唯一且不可修改；不能用显示名/邮箱或客户参数拼接。Hindsight 技术 Tenant 对应空间 schema，不新增产品层级。公共扩展/例程及元信息仍共享。

分 schema 复用社区路由、迁移与 Worker 机制，目标是不为工作空间分表修改内核；动态映射和用户/Key 管理仍需开发 ContextDB 扩展。各空间表和索引独立增长，但 CPU、内存、I/O、连接容量、WAL 及故障/恢复边界共享，性能收益与混合负载影响须压测。[PG Schema](https://www.postgresql.org/docs/current/ddl-schemas.html)、[PG 资源](https://www.postgresql.org/docs/current/runtime-config-resource.html)

## Hindsight Cloud 的可借鉴做法

不能把 Cloud 的 Organization 直接等同于我们的工作空间，也不能从 UI 推断其 PG schema 拓扑。

| 能力 | Cloud 已有证据 | ContextDB 首期采用 |
|---|---|---|
| Bank 管理 | 原生 REST `/v1/default/banks/...` 以及部分 Bank MCP 工具；没有证明存在同名 Workspace 管理 API | 资源包装为工作空间，由管理 REST 开通 schema 和唯一 Bank；业务 Key 禁止原生建/删 Bank |
| 组织及用户管理 | 登录控制台创建/切换组织、团队管理；历史前端证据有 `/api/organizations` 和 `/team` | 复用云租户及已有管控登录认证，用户在空间下，仅 admin/member；不复制 Organization、邀请邮件或密码系统 |
| 常规 API Key 管理 | 登录控制台 `/api-keys`、`/api/api-keys`；名称、到期、Bank scope、完整 secret 展示一次 | 用户多 Key、固定一个空间、摘要存储、展示一次和撤销 |
| 程序化子 Key | `/v1/api-keys/scoped` 的创建/列表、按 ID 撤销；有特定能力的父 Key 可管理自己的子 Key | 仅作为后续自动化参考；本期普通业务 Key 不可签发其他 Key |

组织角色与管理动作由登录后的成员权限决定，API Key 调用并不自动获得完整账户管理权限。[Cloud Team Management](https://docs.hindsight.vectorize.io/team-management/)

Cloud 的一个重要例外是：具有 `create_scoped_keys` 能力的父 Key 可以用 Bearer 调用子 Key 管理 API，子 Key 的 Bank 范围和到期时间受父 Key 限制，子 Key 不能继续签发。这是**明确的委派能力**，不是“所有 API Key 都能管理用户/Key”。本期不引入这种能力。[Cloud API Keys](https://docs.hindsight.vectorize.io/api-keys/)

历史[协议对比](Hindsight-API协议对比-Rest-MCP-商用与开源.md)主要证明数据面 REST/MCP 与 scoped Key 路径，不是全部控制台管理 API 的合同；[Cloud 对比 §3.3](hindsight-cloud-open-source-comparison.md#33-cloud-控制面比开源-control-plane-多什么)补充前端路由证据。没有捕获并核验全部控制台管理请求的 Cookie/JWT/Token 交换，不能断言其完整认证协议。当前官网还存在部分角色细节描述差异，因此不照搬其权限矩阵。

“治理走 REST、不默认给模型管理权限”是可借鉴边界，但不能说 Cloud 所有管理功能都没有 MCP：原生工具中确有 create_bank/delete_bank。ContextDB 首期管理接口不注册成 MCP 工具，并拦截业务 Key 的原生 Bank 管理调用。

## 管理接口与业务接口如何认证

**首期采用“管控后端 → 内部管理 REST”的调用方式，不再允许用户直接携带 IAM Token 调用节点管理接口。** 用户认证与权限检查复用现有管控；同一个 Hindsight API 进程承载管理和业务路由，但使用不同凭据、路由依赖和访问入口。

| 入口 | 凭据 | 谁验证 | 后续授权 |
|---|---|---|---|
| 控制台/管控对用户的入口 | 现有云登录会话或云认证凭据 | 现有管控认证与权限逻辑 | 云租户、云管理动作及目标空间/成员权限；不向用户下发管理 Key |
| 内部管理 REST `/contextdb/v1/...` | `X-ContextDB-Control-Key: <CONTROL_API_KEY>` | 自定义 `ControlPlaneKeyAuth`，独立于业务 Key 验证器 | Key 绑定本部署租户；根据可信操作人与当前元信息复核空间角色、本人关系和目标归属 |
| 业务 REST `/v1/default/banks/...` | `Authorization: Bearer <ContextDB_API_Key>` | ContextDBTenantExtension，查询 Key 摘要与状态 | Key scopes、用户/空间状态、绑定 schema 与 Bank |
| 业务 MCP | 成员的 ContextDB API Key | 同一 TenantExtension 认证逻辑 | 同一空间/Bank 与操作权限，不能绕过 REST 授权 |
| API 内部 Bank 开通/清理 | 服务生成的短期、限定目的内部凭据 | 自定义扩展验证，不向客户端返回 | 固定空间/schema/Bank/操作，不变成客户万能 Key |

### 管理认证链路

![管控管理 Key 与用户业务 Key 两条链路](diagrams/contextdb-member-request.svg)

```text
用户/控制台 → 现有管控后端：用户登录认证 + 权限检查
                ↓ 内网 HTTPS + 管理 Key + 可信操作人
           Hindsight API 管理路由：服务认证 + 目标/角色复核

Agent/应用 → 用户 API Key → Hindsight 业务 REST/MCP
```

1. 用户登录现有管控。管控完成登录认证、云租户和云管理动作权限检查，并检查用户对目标空间/成员的权限；本期不新增 Hindsight 云登录系统。
2. 管控丢弃客户端提交的内部身份/角色头，从已认证登录上下文重新生成 `X-ContextDB-Actor-Subject`。该值是实际操作人的稳定身份 ID，与 `workspace_members.iam_subject` 对应；URL 中的 member_id 仍只是目标用户。
3. 管控从受保护配置读取管理 Key，通过内部 HTTPS 调用管理 REST。浏览器、Agent、用户 SDK 均不接触管理 Key。用户 IAM Token 不向 Hindsight 节点转发用于认证。
4. `ControlPlaneKeyAuth` 校验管理 Key，得到 `ControlPrincipal(control_key_id, cloud_tenant_id, actor_subject)`。云租户来自受信任的部署/Key 配置，不接受客户自报 tenant 头；先通过服务认证，再信任管控传递的操作人字段。
5. 对已有空间，API 按空间和 actor_subject 查询当前成员角色，复核目标归属、状态及 admin/member/本人权限。管控侧权限检查不能替代节点对当前元信息的复核，也不新增独立权限服务或第二套成员目录。
6. 全部通过后执行管理模块；有 Bank 开通/清理时，再生成限定目的内部身份调用原生引擎。审计记录管理 Key ID 和实际操作人，不记录 Key 明文或用户登录凭据。

管理 Key 只证明调用者持有管控凭据，不能独立识别具体用户，也不证明传来的操作人确实登录过；此保证来自可信管控后端。创建首个空间的云创建权限尤其由管控检查，节点不能仅凭 actor 头验证云策略。因此管控必须是完成认证/授权的后端，不能做匿名请求的透传代理。节点仍校验租户、输入与资源约束，并为创建者绑定初始管理员。

### 管理 Key 的配置与安全边界

| 项目 | 首期约定 |
|---|---|
| 生成与绑定 | 实例开通阶段生成，secret 至少 32 字节密码学随机数；每个租户的独享部署使用独立 Key，不是所有客户共用的固定值 |
| 保存 | 管控后端持有 secret；API 端保存可校验的摘要及 key_id/租户/有效状态。通过受保护配置注入，不硬编码到源码、镜像、文档或浏览器配置 |
| 凭据种类 | 管理 Key 可采用 `ctx_ctrl_<key_id>_<secret>`；用户 Key 为 `ctx_live_<key_id>_<secret>`。前缀只是识别提示，认证必须核验实际凭据及其用途 |
| 权限范围 | 管理 Key 只用于内部管理路由；不进入用户 `api_keys` 表、用户列表或签发接口，不默认获得 retain/recall/MCP 权限；用户 Key 无论角色是否 admin，都不能访问管理路由 |
| 网络入口 | 内部管理监听/入口仅允许管控网络来源，通过安全组/访问控制限制；公共入口不映射 `/contextdb/v1` 和 `/ext/contextdb/v1` 管理路径。共享进程时必须覆盖所有可绕过的直连入口 |
| 轮换与撤销 | 通过部署配置通道更新，不增加用户可调用的管理 Key 签发接口；可限定新旧 Key 短期并存。全部 API 副本加载后撤销旧 Key，不承诺取消已通过认证的在途请求 |
| 泄露处理 | Key 不入日志、错误或响应；持有泄露 Key 的攻击者可能冒充管控及操作人，应立即限制入口、撤销/轮换并审计，不能承诺“内置即绝不泄露” |

首期不强制额外引入 mTLS、服务签名或新的 IAM 适配器；采用已有用户认证/授权、内部网络限制、HTTPS 和专用 Key 的组合。仅“用户不知道 Key”、隐藏 URL、Referer 或 User-Agent 都不能作为安全边界。

### 第一个工作空间和第一把 Key

```text
实例开通 → 配置管控与节点之间的管理 Key（独立于用户 Key）
  → 用户登录管控，管控检查创建权限
  → 管控用管理 Key 创建工作空间 → 创建者成为初始管理员
  → 管理员/成员通过管控申请 → 管控用管理 Key 签发用户 API Key
  → Agent 使用 API Key 调用 retain/recall
```

因此不存在“没有用户 Key 就不能创建第一把用户 Key”的循环依赖：**管理 Key 在实例开通阶段由管控配置，不通过尚未可用的用户 Key 管理接口生成。**用户通过管控申请业务 Key，不需要先持有业务 Key，也不获得管理 Key。

### 创建 API Key 如何防止冒充

下列请求仅由管控后端发送，用户不能直连节点执行。用户可通过控制台或管控对外接口提出申请，后者的登录协议复用已有管控，不由本 OpenAPI 定义。

```http
POST /contextdb/v1/workspaces/ws1/members/u1/api-keys
X-ContextDB-Control-Key: <CONTROL_API_KEY>
X-ContextDB-Actor-Subject: <VERIFIED_ACTOR_SUBJECT>
Content-Type: application/json
```

这里必须区分四个值：

| 值 | 含义 | 可信来源 |
|---|---|---|
| 管理 Key | 管控到节点的服务凭据 | 实例开通配置；节点核验摘要、状态和部署租户，不由业务用户生成 |
| actor_subject | 哪个用户发起管理申请 | 管控完成用户认证后重建的身份头，仅在管理 Key 验证成功后接受；不是任意用户传入的字符串 |
| ws1 | 要在哪个工作空间创建 Key | URL 只表示请求目标；服务端查元信息核对云租户、状态和调用者在该空间的权限 |
| u1 | 要为哪个用户创建 Key | URL 只表示目标用户；不是调用者身份，必须查表核对其属于 ws1 |

攻击者不能只传 actor_subject、role=admin、租户头或修改 URL 就获得管理权限。公网不提供节点管理入口；管控先验证登录和权限、覆盖伪造内部身份头；节点仍要求管理 Key，并从元信息解析角色，不接受角色头。这个模型信任管控和管理 Key 的保密性，不防已经攻破管控或窃取管理 Key 的攻击者冒充管控。

创建接口按以下顺序处理，全部通过后才生成随机 Key：

1. **管控认证与授权。** 管控确认登录用户、云租户及目标空间/成员权限，重建可信 actor_subject；失败不转发节点请求。
2. **节点服务认证。** `ControlPlaneKeyAuth` 核验管理 Key 及本部署租户绑定；缺少或无效凭据不能以 actor 头、业务 Key、用户 IAM Token 等降级替代。缺少可信操作人也拒绝。
3. **核对目标与授权。** 查询 ws1、actor 对应的空间成员和目标 u1；管理员可为本空间用户创建 Key，普通成员只能为绑定到自己登录身份的成员创建。无登录身份绑定的成员只能由管理员代签。
4. **授权后签发。** 检查用户/空间有效状态、Key scopes 和到期策略，在一致的元信息状态下写入 Key 摘要及审计，完整 Key 仅成功返回一次。任何认证/授权检查失败或依赖不可用，都不能签发。

| 请求情况 | 本期预期处理 |
|---|---|
| 用户直连节点管理路径 | 公网入口不路由；内部入口按网络规则拒绝，不能仅靠前端不展示 |
| 无管理 Key、伪造 Key、失效/已撤销/过期 Key，或只传 actor 头 | 可达内部路由时返回 401，不签发 Key |
| 有效管理 Key，但缺少或非法 actor_subject | 400，无法构造管理上下文，不签发 Key |
| 管理 Key/目标工作空间不属于本部署租户 | 拒绝，不能管理其他租户；不可见目标可用 404 隐藏资源 |
| 可信操作人是普通成员，但为另一用户创建 Key | 管控拒绝；节点复核时也返回 403 |
| 普通成员为登录身份绑定的自己创建 Key | 其他权限/状态条件通过后允许 |
| 本空间管理员为本空间有效用户创建 Key | 其他权限/状态条件通过后允许 |
| 用用户业务 Key 或用户 IAM Token 代替管理 Key，即使用户是管理员 | 401，凭据类型不能混用 |
| 管控权限检查不可用 | 管控拒绝请求，不转发；节点不负责调用 IAM |
| 节点凭据配置/元信息依赖不可用，无法确认认证或权限 | 503，不降级放行、不签发 Key |

上述是待实现的接口合同，不是现有 Hindsight 已完成的安全校验。原生 HttpExtension 只挂载 Router；**如果只新增创建 Key 接口、不实现 ControlPlaneKeyAuth、可信管控链路和目标授权，该接口是不安全的，不能上线。**

### 为什么仍保留用户身份绑定

云登录用户、ContextDB 空间成员、管控服务凭据和 PG 账号是不同层次。`iam_subject` 只绑定已有管控认证得到的用户身份：用于本人管理、管理员角色解析及审计，不是需要用户提交到节点的 IAM Token。管控创建/绑定成员前核验该身份属于本云租户；普通业务 Key 不能设置或修改此绑定。首期不提供 IAM Token 验证适配器，也不新增产品项目层级。

API/Worker 通过服务端 PG 账号访问数据库，客户端不持有 PG 密码；管理 Key 或内部操作凭据不会自动切换或提升 PG 权限。迁移、建 Bank/索引、清理操作所需数据库权限须单独验收。

## 最小元信息模型与 Key 安全

所有元信息与数据共用同一个 RDS PG 数据库，不新增 MetaPG。

| 表 | 字段与约束 |
|---|---|
| workspaces | workspace_id, cloud_tenant_id, schema_name, name, state, authz_version；schema_name 唯一且不可修改；Bank ID 等于 workspace ID |
| workspace_members | member_id, workspace_id, name, iam_subject, role, status, authz_version；role 仅 admin/member；iam_subject 绑定管控登录身份，同空间非空值唯一 |
| api_keys | key_id, workspace_id, member_id, digest, pepper_version, scopes, expires_at, revoked_at, created_by, last_used_at；复合关联保证 Key 用户与空间一致 |
| management_operations | operation_id, workspace_id, action, state, idempotency_key, request_hash, attempts；仅工作空间开通/删除管理任务 |
| audit_events | request_id, cloud_tenant_id, workspace_id, control_key_id, actor_subject/成员/用户 Key ID, action, result, time；不保存凭据或记忆正文 |

本节 `api_keys` 表和动态管理接口仅管理用户业务 Key，不包含部署配置中的管理 Key。用户 Key 为 `ctx_live_<key_id>_<secret>`，secret 至少 32 字节密码学随机数；保存摘要或带服务端 pepper 的 HMAC 摘要，不保存可恢复明文。完整用户 Key 只在成功创建时返回一次；管控转交给通过授权的申请用户，响应 Cache-Control: no-store，管控/代理日志也不得记录 secret；列表无 secret/摘要。

轮换为创建新 Key、客户端切换、撤销旧 Key。Key 不改变归属用户/空间；身份归属不是数据隔离。停用用户影响其所有 Key 的后续鉴权；首期不缓存授权结果，新请求查 PG 主库，撤销提交前已通过的在途请求及已受理任务不承诺取消。

创建空间时按管控传递的可信 actor_subject 绑定初始管理员，至少保留一个 active、绑定管控登录身份的管理员；角色提升也需已有可信身份绑定。管理员通过管控管理本空间其他用户及 Key；普通成员通过管控管理本人 Key。Key scopes 仅表示业务操作能力，不包含 keys.create、users.manage 等管理能力。

## REST 管理合同

管控到节点的内部前缀 `/contextdb/v1`，内部入口固定映射到 HttpExtension 的 `/ext/contextdb/v1`；两种路径均禁止通过公共业务入口访问。管理 REST 全部要求 `X-ContextDB-Control-Key` 和 `X-ContextDB-Actor-Subject`，不接受用户直连或 IAM Token 认证；[OpenAPI 草案](api/contextdb-control-plane.openapi.yaml)版本 `0.3.0-draft`，仍为 14 个操作。以下权限是用户通过管控申请时的权限，节点按可信 actor 及元信息复核，不表示用户拥有管理 Key。

| 路径 | 方法与作用 |
|---|---|
| /workspaces | POST 开通 schema/唯一 Bank/初始管理员，202；GET 管理可见空间，200 |
| /workspaces/{workspace_id} | GET 查询；PATCH 改名/冻结，200；DELETE 排空后清理空间 Bank，202 |
| /operations/{operation_id} | GET 管理任务状态，200；不泄露不可见空间任务 |
| /workspaces/{workspace_id}/members | POST 创建用户，201；GET 管理员列出本空间用户，200 |
| /workspaces/{workspace_id}/members/{member_id} | GET 管理员/本人查询，200；PATCH 管理员改角色/状态，200；DELETE 管理员软删除，204 |
| /workspaces/{workspace_id}/members/{member_id}/api-keys | POST 管理员/本人签发 Key，201；GET 管理员/本人列 Key，200 |
| /workspaces/{workspace_id}/members/{member_id}/api-keys/{key_id}/revoke | POST 管理员/本人幂等撤销，204 |

普通成员不能创建其他用户、修改角色或为其他用户签发 Key。最后一个有效管理员不可降级/停用/删除；未绑定管控登录身份的用户不能以自报 member_id 取得本人管理权限。工作空间管理员也不能管理其他空间；管理 Key 不是把每个用户都视作管理员。

创建/删除空间要求 Idempotency-Key，同值不同正文 409；同步修改用 If-Match，版本冲突 412。Key 签发幂等重放返回原 key_id 的 409，不保存明文用于重发，首响应丢失时撤销后重建。幂等记录按部署租户、可信 actor_subject、动作和目标隔离，不以可轮换的管理 Key ID 作为用户身份。

错误包括 400 缺少/非法操作人或输入、401 管理凭据无效、403 权限不足、404 不可见/不存在、409 冲突、412 版本不符、429 限流、503 配置/数据库依赖不可用。所有管理响应含 request_id。普通业务 Key 无论用户 role 是否 admin，都不能替代管理 Key；用户 IAM Token 在节点管理路由同样不被接受。

管控后端内部调用示意，无真实凭据；不是给浏览器或用户客户端执行的命令：

```bash
curl -X POST 'https://contextdb-internal.example.com/contextdb/v1/workspaces' \
  -H 'X-ContextDB-Control-Key: <CONTROL_API_KEY>' \
  -H 'X-ContextDB-Actor-Subject: <VERIFIED_ACTOR_SUBJECT>' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: workspace-demo-1' -d '{"name":"研发空间"}'
```

## 扩展包与原生记忆接口

![部署架构](diagrams/contextdb-service-architecture.svg)

API 与 Worker 并列，共用租户独享 PG。管理功能是 API 内部模块，不新增生命周期/审计服务；图中的管控后端是已有云管控，不是要求额外新建一套管理平台。

```text
contextdb_hindsight_ext/
  http.py         HttpExtension：工作空间/用户/Key 管理 REST
  management_auth.py  ControlPlaneKeyAuth、ControlPrincipal、可信 actor 与空间角色复核
  tenant.py       Key 验证与工作空间 schema 路由
  validator.py    Bank/操作权限、禁止业务 Key 建删 Bank
  repository.py   ctxdb_meta 查询及状态版本
  lifecycle.py    原生 schema 迁移/Bank 调用及幂等恢复
  auth.py         不可变业务 AuthContext 和内部目的限定凭据
  audit.py        管理动作与 Key 归属记录
```

HttpExtension 只提供挂载 FastAPI Router 的机制，**不会自动为新增管理 API 完成管理 Key 认证**。应在整个管理 Router 加 `ControlPlaneKeyAuth` 依赖，再在具体 handler 按可信 actor 检查目标空间、角色与本人关系；不只保护写接口，也要保护列表、详情和 operation 状态。不能复用一把全局业务 Key 或认为原生 ApiKeyTenantExtension 会保护这些新路由。OpenAPI security 只是合同声明，不能代替实际代码。凭据配置不可用、认证失败或权限无法确定时拒绝，不 fail-open。

管理依赖先校验 Key，再解析 actor；Key 核验应使用恒定时间摘要比较。输入校验需统一适配本合同的 400，不直接沿用 FastAPI 默认的 422；无效管理凭据优先返回 401。actor 格式/长度检查及角色复核不是再次向 IAM 认证这个用户。

```python
# 设计伪代码，ControlPlaneKeyAuth / 管理策略是待实现内容
router = APIRouter(
    prefix="/contextdb/v1",
    dependencies=[Depends(require_control_principal)],
)
# require_control_principal：核验专用 Key，再接受可信管控传递的 actor。
# handler：根据 actor_subject 和当前元信息校验空间/角色/目标；不信任 role 头。
# 新 Router 不依赖业务 TenantExtension，不调用 IAM 校验用户 Token。
```

| 原生接口 | 本期扩展职责 |
|---|---|
| TenantExtension.authenticate / authenticate_mcp | 验证随机 Key 摘要、Key/用户/空间状态；选择登记 schema，设置 api_key_id 和技术 tenant_id=workspace_id |
| TenantExtension.list_tenants | 返回本部署初始化完成且仍需后台任务处理的空间 schema；Tenant(schema=schema_name, tenant_id=workspace_id) |
| OperationValidator.validate_bank_read/write / validate_create_bank | 检查目标 Bank、操作权限；仅限定内部管理身份可创建/配置/删除 Bank，拒绝未知 Bank 懒创建 |
| bank_list_scope / filter_bank_list / filter_mcp_tools | Key 只看本空间唯一 Bank；管理工具不对业务 Key开放；隐藏工具不能替代引擎权限校验 |
| ExtensionContext.run_migration(schema) | 初始化/升级空间 schema，复用上游迁移 |
| resolve_tag_scope / resolve_write_tag_scope | 本期不实现用户 tag 私有/共享策略，不据此宣称个人记忆隔离 |

业务协议保留上游 REST/MCP。memory.read 表示本 Bank 的记忆读取，不是“本用户记忆读取”；memory.write 表示本 Bank 的记忆写操作，要求 memory.read；knowledge.read 只开放原生知识页面的读取工具/接口，不把 recall 变成“只读确认知识”；reflect 要求 memory.read 并使用同 Bank 可见记忆。具体暴露的原生接口仍需准入和兼容测试，不承诺全套 API。MCP 必须走动态 Key/空间认证，不以全局共享 MCP Token 替代，也不能把已认证标志当成 Bank 授权通过。

用户归属/Key ID 可用于审计，但本期不注入 owner/shared ACL 标签，不做成员级文档、任务或派生页面权限。旧“成员任务状态适配”“knowledge/publications”接口不进入本期合同。

## 工作空间状态与验收

创建：登记空间/schema 和管理任务 → run_migration → 限定内部身份创建唯一 Bank → 校验 → active。失败保持 creating/failed，由 API 进程内持久管理任务重试；同库不代表跨原生迁移和 Bank 操作天然原子。

删除：拒绝新请求 → 排空已接收任务 → 在目标 schema 执行 Bank 清理 → 标记 deleted。禁止触及 ctxdb_meta、公共对象或其他空间；首期不要求立即 DROP schema。用户/Key 历史记录保留以供任务归属和审计。

| 本期验收 | 内容 |
|---|---|
| 动态管理 | 不重启即可创建空间/用户/多 Key，唯一 schema/Bank、状态与幂等恢复 |
| 两套认证与入口 | 公网无法访问管理两种路径、无/伪造/失效管理 Key 401、仅 actor 头拒绝、业务 Key/IAM Token 调管理拒绝、管理 Key 调业务拒绝 |
| 可信管控与凭据运维 | 管控覆盖客户端伪造 actor/role 头；未登录/越权申请不转发；合法管控请求仍复核角色、目标与租户；缺少 actor 400；跨实例 Key 拒绝；全副本轮换/撤销及日志脱敏 |
| 用户/Key 管理 | 用户目录管理员限定、本人 Key 管理、最后管理员保护、摘要存储/展示一次、撤销/停用生效 |
| 工作空间隔离 | 修改 Bank/alias/空间/schema 参数不能跨空间；REST/MCP 与 Worker 指向正确 schema，Bank 创建绕过被拒绝 |
| 运维与负载 | 多 schema 升级/失败恢复、删除排空、不影响其他空间；大空间导入与小空间查询混合压测 |
| 非本期验收 | 用户记忆私有+共享知识的 tag ACL、成员私有任务状态、记忆晋升/知识发布 |

真实管控登录/转发、管理 Key 认证、SDK/MCP 和数据库端到端实现测试为 NOT_RUN；本次只更新文档、OpenAPI 和图。已有 public/共享 schema 的数据不会自动迁移，需要另行停写、拆分校验和切换映射。

## 源码与证据

固定源码基线：`a77c1f3412a7b82f36588dffce1a8d7480e99cc7`。ContextDB 扩展、认证依赖和管理 API 是待实现内容。

- [HttpExtension](https://github.com/vectorize-io/hindsight/blob/a77c1f3412a7b82f36588dffce1a8d7480e99cc7/hindsight-api-slim/hindsight_api/extensions/http.py)
- [TenantExtension](https://github.com/vectorize-io/hindsight/blob/a77c1f3412a7b82f36588dffce1a8d7480e99cc7/hindsight-api-slim/hindsight_api/extensions/tenant.py)
- [OperationValidatorExtension](https://github.com/vectorize-io/hindsight/blob/a77c1f3412a7b82f36588dffce1a8d7480e99cc7/hindsight-api-slim/hindsight_api/extensions/operation_validator.py)
- [原生迁移入口](https://github.com/vectorize-io/hindsight/blob/a77c1f3412a7b82f36588dffce1a8d7480e99cc7/hindsight-api-slim/hindsight_api/extensions/context.py)
- [Worker schema 发现](https://github.com/vectorize-io/hindsight/blob/a77c1f3412a7b82f36588dffce1a8d7480e99cc7/hindsight-api-slim/hindsight_api/worker/poller.py)
- [SMIC 跨 Key 实测](evidence/hindsight-cloud-cross-key-smic-2026-10-10.md)
- [成员/Key 竞品调研](member-and-apikey-management-design.md)
- [文档验证记录](evidence/member-service-design-doc-validation-2026-10-12.md)
- [管理 Key 认证修订验证记录](evidence/member-service-design-control-key-validation-2026-10-13.md)
