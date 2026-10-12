# ContextDB 首期工作空间 用户与 API Key 服务化设计

更新日期：2026-10-12。首期只实现工作空间管理、用户管理和 API Key 管理，以及这些能力必需的认证和工作空间授权。采用租户独享 API/Worker/RDS PG，同一个 PG 数据库中每工作空间独立 schema，schema 内唯一 Bank。以下接口和扩展为待实现设计，不代表服务已完成验收。

## 首期交付范围

| 本期实现 | 本期不实现 |
|---|---|
| 动态创建、查询、修改、冻结和删除工作空间；初始化对应 schema 和唯一 Bank | 同 Bank 内个人记忆按用户隔离 |
| 动态创建、查询、改角色、停用和删除工作空间用户 | 私有记忆与共享知识的 tag 授权、记忆晋升和知识发布工作流 |
| 用户多 API Key 的签发、查询、过期、撤销和轮换 | 成员级记忆/文档/派生内容 ACL、成员任务私有状态适配 |
| 管理 IAM 认证、admin/member 授权、Key 认证与空间/schema/Bank 范围校验 | 父子 Key 委派、跨空间 Key、组织层、用户组与独立计费服务 |

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

用户也叫成员，两者是同一实体，沿用 `member_id` 作为工作空间用户 ID。只有 admin/member 两种角色，不设 Owner、全局用户目录或单独服务账号类型。同一个 IAM 身份在多个空间分别建立用户记录，角色和 Key 独立。

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
| 组织及用户管理 | 登录控制台创建/切换组织、团队管理；历史前端证据有 `/api/organizations` 和 `/team` | 复用云租户和 IAM，用户在空间下，仅 admin/member；不复制 Organization、邀请邮件或密码系统 |
| 常规 API Key 管理 | 登录控制台 `/api-keys`、`/api/api-keys`；名称、到期、Bank scope、完整 secret 展示一次 | 用户多 Key、固定一个空间、摘要存储、展示一次和撤销 |
| 程序化子 Key | `/v1/api-keys/scoped` 的创建/列表、按 ID 撤销；有特定能力的父 Key 可管理自己的子 Key | 仅作为后续自动化参考；本期普通业务 Key 不可签发其他 Key |

组织角色与管理动作由登录后的成员权限决定，API Key 调用并不自动获得完整账户管理权限。[Cloud Team Management](https://docs.hindsight.vectorize.io/team-management/)

Cloud 的一个重要例外是：具有 `create_scoped_keys` 能力的父 Key 可以用 Bearer 调用子 Key 管理 API，子 Key 的 Bank 范围和到期时间受父 Key 限制，子 Key 不能继续签发。这是**明确的委派能力**，不是“所有 API Key 都能管理用户/Key”。本期不引入这种能力。[Cloud API Keys](https://docs.hindsight.vectorize.io/api-keys/)

历史[协议对比](Hindsight-API协议对比-Rest-MCP-商用与开源.md)主要证明数据面 REST/MCP 与 scoped Key 路径，不是全部控制台管理 API 的合同；[Cloud 对比 §3.3](hindsight-cloud-open-source-comparison.md#33-cloud-控制面比开源-control-plane-多什么)补充前端路由证据。没有捕获并核验全部控制台管理请求的 Cookie/JWT/Token 交换，不能断言其完整认证协议。当前官网还存在部分角色细节描述差异，因此不照搬其权限矩阵。

“治理走 REST、不默认给模型管理权限”是可借鉴边界，但不能说 Cloud 所有管理功能都没有 MCP：原生工具中确有 create_bank/delete_bank。ContextDB 首期管理接口不注册成 MCP 工具，并拦截业务 Key 的原生 Bank 管理调用。

## 管理接口与业务接口如何认证

**管控是逻辑职责，不由部署在哪个进程决定。** 同一个 Hindsight API 节点可以同时承载两类路由，但必须各自使用正确的认证依赖，不能统一套一个业务 Key 验证器。

| 入口 | 外部凭据 | 谁验证 | 后续授权 |
|---|---|---|---|
| 管理 REST `/contextdb/v1/...` | 云 IAM 临时 Token：`X-Auth-Token` | ManagementAuth 的 CloudIdentityVerifier 或等价可信云认证适配 | 云租户一致性、云 API 权限、本空间 admin/member 及是否本人 |
| 业务 REST `/v1/default/banks/...` | `Authorization: Bearer <ContextDB_API_Key>` | ContextDBTenantExtension，查询 Key 摘要与状态 | Key scopes、用户/空间状态、绑定 schema 与 Bank |
| 业务 MCP | 成员的 ContextDB API Key | 同一 TenantExtension 认证逻辑 | 同一空间/Bank 与操作权限，不能绕过 REST 授权 |
| API 内部 Bank 开通/清理 | 服务生成的短期、限定目的内部凭据 | 自定义扩展验证，不向客户端返回 | 固定空间/schema/Bank/操作，不变成客户万能 Key |

### 管理认证链路

![管理 IAM 与业务 Key 两条链路](diagrams/contextdb-member-request.svg)

1. 用户在华为云 IAM 登录/获取 Token。ContextDB 不收集云密码，也不先要求拥有 ContextDB Key。
2. 管理请求携带 `X-Auth-Token`。API 的 ManagementAuth 调用可信适配验证有效性，形成不可变 `CloudPrincipal(cloud_tenant_id, iam_subject, expires_at)`。不能仅解码 Token、读取自报 tenant 头或认为登录成功就获得管理员权限。
3. 校验 principal 的云租户与独享部署一致，并检查该云身份的 ContextDB 管理动作权限。动作如 `contextdb:workspaces:create` 是拟注册的示意名称，云 IAM 授权接入仍待实现；校验 Token 不是自动完成云策略授权。
4. 对已有空间，从 `ctxdb_meta.workspace_members` 按空间和 iam_subject 解析角色。管理员可管理本空间用户/Key；成员只能查看自己和管理自己的 Key。用户无 IAM 绑定时，由管理员管理其 Key。
5. 通过检查后执行管理模块；有 Bank 开通/清理时，生成限定内部身份调用原生引擎。外部 IAM Token 不当作 Hindsight 业务 Key，不原样发给 LLM 或写入 PG 审计。

IAM 提供 Token 校验接口；Token 调用使用 X-Auth-Token，AK/SK 则是另一种云签名认证，不是 ContextDB API Key。本期管理合同先采用 Token，自动化 AK/SK 接入后续适配。正式 IAM Token scope/区域策略按云平台要求确定，不引入产品“项目”实体。[IAM Token 校验](https://support.huaweicloud.com/api-iam/iam_30_0004.html)

如果使用 IAM 的自校验接口，需要按官方协议提供 X-Auth-Token 和待校验的 X-Subject-Token；不要给 ContextDB 配置能够校验任意其他账号的假定超级 Token。生产可替换为云平台可信鉴权组件，但不得改变上述角色/资源校验。

### 第一个工作空间和第一把 Key

```text
IAM 登录 → 获得有创建权限的云身份
  → 创建工作空间 → 创建者成为初始管理员用户
  → 管理员创建用户 → 管理员/用户本人签发该用户的 API Key
  → Agent 使用 API Key 调用 retain/recall
```

因此不存在“没有 Key 就不能创建第一把 Key”的循环依赖。**没有 ContextDB API Key 不代表没有认证凭据：调用者先有 IAM Token，再申请业务 Key。**第一把 Key 不是匿名签发，也不以尚未创建的 Key 来认证。

### 创建 API Key 如何防止冒充

按当前设计，用户可以通过控制台、SDK 或 curl 调用以下管理接口，但每次都必须携带有效 IAM 凭据并通过权限检查：

```http
POST /contextdb/v1/workspaces/ws1/members/u1/api-keys
X-Auth-Token: <IAM_TOKEN>
Content-Type: application/json
```

这里必须区分三个值：

| 值 | 含义 | 可信来源 |
|---|---|---|
| 调用者 IAM 用户 ID | 谁发起创建请求 | 服务端验证 IAM Token 后得到，不由 URL/请求体指定 |
| ws1 | 要在哪个工作空间创建 Key | URL 只表示请求目标；服务端查元信息核对云租户、状态和调用者在该空间的权限 |
| u1 | 要为哪个用户创建 Key | URL 只表示目标用户；不是调用者身份，必须查表核对其属于 ws1 |

例如，攻击者把 URL 中的 u1 改成管理员 ID，不能因此变成管理员；传入 role=admin、用户 ID 或租户头，也不能覆盖服务端从可信 IAM 身份与元信息解析的权限。

创建接口按以下顺序处理，全部通过后才生成随机 Key：

1. **认证凭据。** ManagementAuth 通过配置的可信 IAM 服务/鉴权组件校验 Token 有效性和有效期。请求头存在、有某种 Token 格式或可以解码，都不等于认证成功。
2. **确认调用者。** 从验证结果获得真实云租户与 IAM 用户 ID，校验与本独享实例一致；同时检查云身份是否被允许执行该管理动作。Token 有效不等于具有签发权限。
3. **核对目标与授权。** 查询 ws1、调用者的空间用户记录和目标 u1 的记录；管理员可为本空间用户创建 Key，普通成员只能为绑定到自己 IAM 身份的用户创建。未绑定 IAM 的用户只能由管理员代签。
4. **授权后签发。** 检查用户/空间有效状态、Key scopes 和到期策略，在一致的元信息状态下写入 Key 摘要及审计，完整 Key 仅成功返回一次。任何认证/授权检查失败或依赖不可用，都不能签发。

| 请求情况 | 本期预期处理 |
|---|---|
| 没有、伪造、失效或过期 IAM Token | 401，认证拒绝，不签发 Key |
| IAM Token 有效，但云租户或空间范围不匹配 | 拒绝，不能管理其他租户/空间；不可见目标可用 404 隐藏资源 |
| 普通成员为本空间另一用户创建 Key | 403，身份有效但没有目标用户的管理权限 |
| 普通成员为 IAM 绑定的自己创建 Key | 其他权限/状态条件通过后允许 |
| 本空间管理员为本空间有效用户创建 Key | 其他权限/状态条件通过后允许 |
| 用 ContextDB 业务 Key 代替 IAM Token，即使该 Key 属于管理员 | 认证拒绝，凭据类型不能混用 |
| IAM 校验或权限依赖不可用，不能确定权限 | 503，不降级放行、不签发 Key |

上述是待实现的接口合同，不是现有 Hindsight 已完成的安全校验。原生 HttpExtension 只挂载 Router；**如果只新增创建 Key 接口、不实现 ManagementAuth 和目标授权，该接口是不安全的，不能上线。**

### 管理 API 与管理后台专用接口的区别

“提供给管理面”的当前含义是**需要管理身份与权限的 API**，不是“只能从管理页面点击”。合法用户从 SDK/curl 调用也应允许；是否来自控制台页面、Referer、User-Agent、URL 是否隐蔽等，不能代替身份和资源权限验证。

如果要求“只有管理后台服务可以调用”，则是另一种接口暴露方式：管理接口限制为内部网络访问，认证后台服务身份（例如 mTLS 或服务签名），并验证其传递的可信用户身份，之后仍做空间/目标用户授权。本期采用用户携带 IAM Token 调用管理 REST 的方式，不默认新增这一后台专用接口或管控服务。

IAM Token 被盗时，攻击者可能以合法身份调用，认证无法直接区分实际持有人。需要 HTTPS、Token 不入日志/响应、过期与失效处理、管理登录安全策略等保护；不能承诺“任何攻击者都无法冒用”。

管理 Token 误传到业务入口，或业务 Key 误传到管理入口，都应拒绝，不能 fallback 放行。若云入口先验证身份，必须删除客户伪造的内部身份头，并通过服务认证/签名或不可绕过的可信链路传入 principal；API 必须验证来源。首期直接在管理路由依赖中验证 IAM，可避免只信任一个任意可伪造头。

云 IAM 用户、ContextDB 空间用户和 PG 数据库账号是不同层次：IAM 身份登录管理，ContextDB 用户归属 Key，API/Worker 通过服务端 PG 账号访问数据库。客户端不持有 PG 密码；内部操作凭据仅控制服务授权，不会自动切换或提升 PG 权限。迁移、建 Bank/索引、清理操作所需数据库权限须单独验收。

## 最小元信息模型与 Key 安全

所有元信息与数据共用同一个 RDS PG 数据库，不新增 MetaPG。

| 表 | 字段与约束 |
|---|---|
| workspaces | workspace_id, cloud_tenant_id, schema_name, name, state, authz_version；schema_name 唯一且不可修改；Bank ID 等于 workspace ID |
| workspace_members | member_id, workspace_id, name, iam_subject, role, status, authz_version；role 仅 admin/member；同空间非空 IAM subject 唯一 |
| api_keys | key_id, workspace_id, member_id, digest, pepper_version, scopes, expires_at, revoked_at, created_by, last_used_at；复合关联保证 Key 用户与空间一致 |
| management_operations | operation_id, workspace_id, action, state, idempotency_key, request_hash, attempts；仅工作空间开通/删除管理任务 |
| audit_events | request_id, cloud_tenant_id, workspace_id, 管理 IAM subject/成员/Key ID, action, result, time；不保存凭据或记忆正文 |

Key 为 `ctx_live_<key_id>_<secret>`，secret 至少 32 字节密码学随机数；保存摘要或带服务端 pepper 的 HMAC 摘要，不保存可恢复明文。完整 Key 只在成功创建时返回一次；列表无 secret/摘要，响应 Cache-Control: no-store，日志不得记录 Token/Key。

轮换为创建新 Key、客户端切换、撤销旧 Key。Key 不改变归属用户/空间；身份归属不是数据隔离。停用用户影响其所有 Key 的后续鉴权；首期不缓存授权结果，新请求查 PG 主库，撤销提交前已通过的在途请求及已受理任务不承诺取消。

创建空间时绑定初始管理员，管理员需绑定可信 IAM 身份，至少保留一个 active、可登录管理的管理员；角色提升也需已有 IAM 绑定。管理员可管理本空间其他用户及 Key；普通成员的管理操作限定本人。Key scopes 仅表示业务操作能力，不包含 keys.create、users.manage 等管理能力。

## REST 管理合同

外部前缀 `/contextdb/v1`，现有入口固定映射到 HttpExtension 的 `/ext/contextdb/v1`。管理 REST 均使用 IAM Token，并各自检查权限；[OpenAPI 草案](api/contextdb-control-plane.openapi.yaml)版本 `0.2.0-draft`，共 14 个操作。

| 路径 | 方法与作用 |
|---|---|
| /workspaces | POST 开通 schema/唯一 Bank/初始管理员，202；GET 管理可见空间，200 |
| /workspaces/{workspace_id} | GET 查询；PATCH 改名/冻结，200；DELETE 排空后清理空间 Bank，202 |
| /operations/{operation_id} | GET 管理任务状态，200；不泄露不可见空间任务 |
| /workspaces/{workspace_id}/members | POST 创建用户，201；GET 管理员列出本空间用户，200 |
| /workspaces/{workspace_id}/members/{member_id} | GET 管理员/本人查询，200；PATCH 管理员改角色/状态，200；DELETE 管理员软删除，204 |
| /workspaces/{workspace_id}/members/{member_id}/api-keys | POST 管理员/本人签发 Key，201；GET 管理员/本人列 Key，200 |
| /workspaces/{workspace_id}/members/{member_id}/api-keys/{key_id}/revoke | POST 管理员/本人幂等撤销，204 |

普通成员不能创建其他用户、修改角色或为其他用户签发 Key。最后一个有效管理员不可降级/停用/删除；未绑定可信 IAM 身份的用户不能以自报 member_id 取得本人管理权限。工作空间管理员也不能管理其他空间。

创建/删除空间要求 Idempotency-Key，同值不同正文 409；同步修改用 If-Match，版本冲突 412。Key 签发幂等重放返回原 key_id 的 409，不保存明文用于重发，首响应丢失时撤销后重建。幂等记录按可信身份、动作、目标隔离。

错误包括 401 凭据无效、403 认证有效但权限不足、404 不可见/不存在、409 冲突、412 版本不符、429 限流、503 认证/数据库依赖不可用。所有管理响应含 request_id。普通业务 Key 无论用户 role 是否 admin，都不能替代管理 IAM Token。

示意请求，无真实凭据：

```bash
curl -X POST 'https://contextdb.example.com/contextdb/v1/workspaces' \
  -H 'X-Auth-Token: <IAM_TOKEN>' -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: workspace-demo-1' -d '{"name":"研发空间"}'
```

## 扩展包与原生记忆接口

![部署架构](diagrams/contextdb-service-architecture.svg)

API 与 Worker 并列，共用租户独享 PG。管理功能是 API 内部模块，不新增生命周期/审计服务。

```text
contextdb_hindsight_ext/
  http.py         HttpExtension：工作空间/用户/Key 管理 REST
  management_auth.py  IAM 验证、CloudPrincipal、云权限与角色检查
  tenant.py       Key 验证与工作空间 schema 路由
  validator.py    Bank/操作权限、禁止业务 Key 建删 Bank
  repository.py   ctxdb_meta 查询及状态版本
  lifecycle.py    原生 schema 迁移/Bank 调用及幂等恢复
  auth.py         不可变业务 AuthContext 和内部目的限定凭据
  audit.py        管理动作与 Key 归属记录
```

HttpExtension 只提供挂载 FastAPI Router 的机制，**不会自动为新增管理 API 完成 IAM 认证**。应在整个管理 Router 加 ManagementAuth 依赖，再在具体 handler 检查目标空间、角色与本人关系；不只保护写接口，也要保护列表、详情和 operation 状态。OpenAPI security 只是合同声明，不能代替实际认证代码。Token/IAM 验证失败或权限无法确定时拒绝，不 fail-open。

```python
# 设计伪代码，CloudIdentityVerifier / 管理策略是待实现内容
router = APIRouter(
    prefix="/contextdb/v1",
    dependencies=[Depends(require_cloud_principal)],
)
# handler 再按可信 principal 校验空间归属、admin/member 与目标用户。
# 新 Router 不依赖业务 TenantExtension 自动完成 IAM 认证。
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
| 两套认证 | 无 IAM 管理请求 401、业务 Key 调管理拒绝、过期/伪造 Token 拒绝、有效普通成员越权 403、伪造内部身份头拒绝 |
| 用户/Key 管理 | 用户目录管理员限定、本人 Key 管理、最后管理员保护、摘要存储/展示一次、撤销/停用生效 |
| 工作空间隔离 | 修改 Bank/alias/空间/schema 参数不能跨空间；REST/MCP 与 Worker 指向正确 schema，Bank 创建绕过被拒绝 |
| 运维与负载 | 多 schema 升级/失败恢复、删除排空、不影响其他空间；大空间导入与小空间查询混合压测 |
| 非本期验收 | 用户记忆私有+共享知识的 tag ACL、成员私有任务状态、记忆晋升/知识发布 |

真实 IAM/SDK/MCP 和数据库端到端实现测试为 NOT_RUN；本次只更新文档、OpenAPI 和图。已有 public/共享 schema 的数据不会自动迁移，需要另行停写、拆分校验和切换映射。

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
