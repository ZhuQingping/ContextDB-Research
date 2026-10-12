# ContextDB 成员与 API Key 管理：阿里云实测、Hindsight 组织模型与华为云建议

更新日期：2026-10-10。本文聚焦成员身份、API Key 的归属/授权/生命周期，以及 Hindsight Cloud 为什么采用 Organization（组织）。阿里云部分基于当日登录控制台的只读观察；Hindsight Cloud 组织能力基于 2026-10-07 的登录态页面/API 与官方资料核验。控制台与商业产品会演进，不能把单账号当前配置外推为所有客户的默认配置。

> 2026-10-12 首期产品模型已由用户确认：云租户独享 API、Worker 与 RDS PG，元信息和数据共用一个 PG 数据库；云租户下多个工作空间，每空间独立 schema 内一个 Bank，用户（也叫成员）在空间下，仅 admin/member 两种角色；每个管理员或成员均可拥有多个 API Key，Key 隶属用户。首期不引入项目、独立 MetaPG 或独立生命周期服务。当前架构、OpenAPI 与插件细节见[首期服务化设计](member-apikey-bank-service-design.md)。本期只实现工作空间/用户/Key 管理和必需认证，不实现用户私有记忆或知识发布；候选 tag 方案见[后续备忘](member-memory-isolation-future-notes.md)。本文保留竞品历史观察，API/插件尚待实现。

> 2026-10-13 管理认证修订：新增管理 REST 仅由已有管控后端调用，使用部署时配置的专用管理 Key，不向用户下发。用户登录和权限检查保留管控侧；节点验证管理 Key，并按管控传递的可信操作人及当前元信息复核角色和目标。本文的 IAM 身份绑定表示与管控登录身份对应，不要求节点校验 IAM Token；管理 Key 与下文用户业务 Key 的归属、签发、scope 分开，详见[当前设计](member-apikey-bank-service-design.md#管理接口与业务接口如何认证)。

## 结论先行

**Organization 不是 Hindsight 记忆引擎的必需概念，也不能据此推断一个 Organization 就对应一个 PostgreSQL schema、数据库实例或部署单元。**它首先是商业控制面中的协作、资源归属和商业治理边界：成员、API Key、Bank、用量/账单等由组织承载；一个账号可加入多个组织并切换。

华为云 ContextDB 不应为了“对齐 Hindsight”而照搬一个独立的组织层。先确定自己的客户/账号边界：

- 华为云租户已经是客户归属边界，可以直接采用 **云租户→工作空间→用户（管理员/成员）→API Key**，不再增加语义重复的 Organization。
- 只有在一个客户租户需要管理多个可独立授权、独立计量或独立生命周期的工作空间集合时，才引入显式“组织/团队”实体；它应是控制面分组，而不是硬编码的存储拓扑。
- API Key 是主体的凭据，不是成员本身。每个 Key 应绑定 workspace 和工作空间用户 member_id、创建者、scope/资源约束、有效期与撤销状态；其权限不得超过所属主体当前权限。

## 1. 阿里云 RDS ContextDB 控制台：现场核对结果

核对入口：[阿里云 RDS ContextDB（杭州）](https://rdsnext.console.aliyun.com/contextDb/cn-hangzhou)，核对时间：2026-10-10。只进行了页面浏览，没有创建、删除或修改成员/Key/资源。

### 1.1 页面实际呈现的资源层级

登录账号下可见两个运行中的工作空间：`research` 与 `MySQL`。这里的 `MySQL` 是工作空间显示名称；控制台没有据此证明其后端数据库引擎为 MySQL。

进入 `research` 后，导航包括记忆、知识库、技能、记忆整理、记忆晋升、知识评审、策略与模板、用户管理和审计。总览当时显示 487 条记忆、3 个知识库、5 个待审核记忆晋升。技能页介绍了对话经验自动提炼、共享复用和持续改进；知识库页将其定位为可共享的正式知识/文件资产。

因此，用户最初的模型大体抓到了“工作空间承载上下文资产和管理功能”，但不能把这些页面导航项都当成和记忆/知识库同级的独立持久化对象；技能、审计、用户管理等属于工作空间的能力或管理域。

### 1.2 成员与 API Key 的关系（UI 证据）

`用户管理`页面标注“管理工作空间成员与用户组”，成员表包含成员名称、成员 ID、绑定的阿里云 UID、角色、状态、创建时间和操作。当前 `research` 列表中可见 Owner `qingping` 和 Member `jiamu`。每行均提供“管理 ApiKey”“角色设置”“删除”操作；页面说明 RAM 子账号绑定后可按成员身份访问工作空间，Owner 由服务端自动绑定。

这说明在该实测空间中，**API Key 管理入口挂在成员行上**，而不是一个与成员完全无关的全局密钥列表。UI 暗示 Key 按成员上下文管理；但本次没有打开 Key 管理页，因此尚不能确认一个成员可有几个 Key、Key 的完整归属字段，以及是否支持到期、scope、展示一次、轮换等细节，也不能确定 RAM 身份绑定的全部流程。

审计页面标题说明其记录“工作空间内的 API 调用和操作记录”。页面当时列出 5 条记录，其中可见 `CreateContextDatabaseMember`、`CreateContextDatabaseApiKey`、知识库创建和文档上传等操作。记录中包含 Action、操作类别、RequestId、耗时和结果。页面证明了该账户下发生过这些成功操作，并非我们在本次核对中触发的操作。

### 1.3 记忆隔离的证据边界

记忆页提供成员筛选，并显示当前选择的成员；这只能证明 UI 提供成员维度的浏览入口，不能独立证明后端所有读写 API 都实施成员隔离。此次页面的记忆列表为 0，而空间总览显示 487 条，可能涉及默认筛选、数据加载或控制台状态差异，不能用列表数字证明数据缺失或隔离正确。

所以，阿里云“不同成员记忆相互隔离”应视为需由官方权限/API 文档和跨成员黑盒测试共同确认的安全语义，而不是由这次 UI 观察单独推出。上线验收应使用两个独立成员/Key，覆盖记忆写入、列表、搜索、Recall、详情、导出、MCP、异步操作及撤权。

## 2. Hindsight 开源版与 Hindsight Cloud 的层次

### 2.1 开源数据面不需要 Organization

Hindsight 开源版的主要数据面概念是 Tenant（通过 TenantExtension 把可信身份映射到租户上下文/schema）和 Bank（租户内记忆库）。开源默认 API Key/Tenant 扩展不是完整云账号系统：默认扩展不负责云成员、组织成员资格、客户账单、成员级 Bank ACL 或 API Key 管理生命周期。相关固定源码和边界见[服务化核验证据](cloud-service-evidence.md#s3-隔离与授权)与[多 Bank 隔离设计](bank-isolation-gateway.md)。

重要区分：**Tenant 是数据面隔离/路由上下文；Organization 是 Cloud 控制面的产品归属/协作实体。**两者可以一对一映射，但公开 UI/API 证据没有证明其必然一对一，也没有证明 Organization 对应 schema 或物理数据库。

### 2.2 Cloud 为什么引入 Organization

Hindsight Cloud 的登录态产品页面和官方 Team Management、API Keys、Usage Analytics 文档呈现的组织模型包括：账号可以创建或加入多个组织；切换组织后组织内 Bank、Key 和账单随当前组织切换；Owner/Admin/Member 等角色决定管理动作；Key 可以附带 Bank scope 等约束；用量与账单围绕组织及 Key 归集。商业版和开源版的实测差异汇总见[Hindsight Cloud 与开源版实测](hindsight-cloud-open-source-comparison.md#33-cloud-控制面比开源-control-plane-多什么)。

从产品职责看，Organization 解决的主要是：

1. **个人账号与客户空间解耦。** 登录账号是人的身份；组织是该身份参与协作的资源上下文。成员离开组织，不需要删除其个人登录账号。
2. **一个用户参与多个团队/客户。** 组织切换提供上下文边界，避免把个人账号误当成唯一租户；适用于顾问、开发者或同时参与多家公司的用户。
3. **资源归属和协作授权。** Bank、成员、API Key、角色等有明确的归属主体；团队成员和自动化程序可以被分别授权。
4. **用量、账单和套餐归集。** 组织可作为客户级付费/额度边界，Key 进一步用于识别应用或调用方，支持查用量、撤销凭据和限额。
5. **组织级商业治理。** 后续 SSO、MFA、审计、BYOC 或专属基础设施等企业能力需要一个可配置的客户边界。

这些是**组织作为控制面实体的产品理由**，不等于 Hindsight 记忆算法需要组织概念。公开材料不能确认 Hindsight Cloud 的真实数据库分片粒度或内部组织到 Tenant/schema 的映射。

## 3. 成员、API Key 应如何建模

首期按工作空间用户建模，“用户”和“成员”是同一实体；管理员和成员是用户的两种角色，不是两张用户表或两个资源层级。不引入 Owner、全局用户目录、用户组或单独服务主体。

```text
云租户
  └─ 工作空间 × N（每空间唯一 Bank）
       ├─ 用户 A（管理员 admin）→ API Key × N
       └─ 用户 B（成员 member）→ API Key × N
```

| 对象 | 代表什么 | 关键约束 |
|---|---|---|
| 云租户 | 客户资源归属与独享部署边界 | 由可信身份解析，不增加组织或项目层 |
| 工作空间 | 用户、个人记忆与共享知识的范围 | 对应唯一 Bank |
| 用户（成员） | 工作空间内的调用者 | `member_id` 为稳定用户 ID，role 仅 admin/member；可绑定管控登录身份，管理员必需 |
| API Key | 归属于某个用户的凭据 | 每个用户可有多个 Key；权限不高于用户，固定用户与空间，不能跨空间 |
| 审计事件 | 用户通过某 Key 执行的动作 | 记录 workspace、member_id、key_id、动作与结果；不保存 secret |

同一个云登录身份在多个空间需要独立的用户记录。Agent 或应用使用某个用户的 Key，不单独增加服务账号类型；多人共用一个用户的 Key 会共用该用户的凭据身份和审计归属，不能区分为多个独立成员。首期同 Bank 记忆沿用共享语义，并没有已实现的“个人记忆”边界。

### 3.1 Key 不应等同于成员，也不应独立授予越权

管理员和成员都可以有多个 Key，例如按本地开发、CI、生产 Agent 分开创建，以便独立轮换、撤销、限额和追踪调用。Key 的创建权限与 Key 本身的运行权限是两种权限：管理员可以授予成员创建 Key 的资格，但新 Key 的有效权限仍需受该成员授权上限约束。

推荐授权计算：

```text
有效权限 = 用户当前工作空间角色授权
           ∩ API Key scopes / 资源约束
           ∩ 资源当前 ACL
           ∩ 工作空间状态与策略
```

因此 Key 不应把角色权限扩大；成员被禁用/移出空间时，其所有 Key 应立即失效或在下一次鉴权时被拒绝。首期每个新请求直接查 PG 主库，不缓存鉴权结果，因此无需缓存失效组件。后台异步任务应保存 `member_id/key_id` 作为审计与重验线索，而不是把过期 bearer token 当长期授权。

### 3.2 生命周期与安全要求

- 创建：高熵随机 secret；服务端只存不可逆摘要（含 pepper/key version）；完整 secret 只在创建时展示一次。数据库、日志、审计和错误消息不得回显明文。
- 使用：通过 Authorization Header 传递；服务端解析到 key_id 后查询状态、主体、空间、scope 与资源 ACL。客户端提供的 tenant/workspace/schema/Bank ID 只能作为待校验目标，不是授权证明。
- 轮换：允许并行新旧 Key 的短暂迁移窗口；验证新 Key 生效后撤销旧 Key，并审计两步操作。
- 撤销/过期：按 key_id 可即时禁用；成员停用、离职、空间冻结或用户角色变化时执行级联失效/重新授权。
- 归属与委派：记录创建者、归属主体、最后使用、用途标签、环境和过期时间；管理员通过管控管理本空间用户的 Key，绑定管控登录身份的用户可通过管控管理自己的 Key；不增加第三种角色，不给用户管理 Key。
- 审计/用量：按云租户/工作空间、用户、Key、API 动作分别聚合；一个 Key 代表一个调用方，但不能取代客户级计费归属。

## 4. 华为云首期建议：何时需要 Organization

### 4.1 建议的首期实体

2026-10-12 用户确认采用以下首期模型，一个云租户可创建多个工作空间：

```text
华为云租户（外部客户身份与账单归属，独享 API/Worker/PG）
  └─ ContextDB 工作空间 × N（每个空间对应唯一 Bank）
       ├─ 用户（管理员/成员），每个用户拥有多个 API Key
       └─ Bank 记忆/知识：沿用共享语义，用户隔离未实现
```

#### 当前首期目标模型（2026-10-12，产品模型已确认）

本模型替代此前“空间内多个 Bank、Key 多 Bank 授权”的候选设计；实现细节仍需原型验证：

- 一个云租户包含多个工作空间；每个工作空间映射独立 Hindsight schema，schema 内唯一 Bank，默认 Bank ID 等于 workspace ID。
- 工作空间下统一建立用户记录，role 只允许 admin/member；API Key 隶属于用户，两种角色均支持多 Key。一个 Key 固定绑定空间和用户，服务端解析租户/schema 和唯一 Bank；首期没有独立成员 Bank ACL 或 Key Bank 集合。
- 本期同空间 Bank 内记忆/知识沿用上游语义，有相应权限的用户可共享记忆；不承诺用户私有记忆。
- **未决问题：Hindsight 同一个 Bank 默认没有成员级记忆隔离。**本地 REST 验证中，同一 tenant、同一 Bank 下以 `metadata.user_id=zhang3/li4` 写入后，交叉 Recall 能读到对方内容。因此目前不能假设“Key 绑定成员”或“记忆带 user_id metadata”就会自动实现隔离。
- 用户隔离是后续候选：可以通过稳定 member ID、服务端强制 tag scope、写入校验和派生任务范围尝试实现，但本期不开发/验收；metadata.user_id 不是授权规则。SMIC 商业跨 Key 实测也证明不同 Key 本身不隔离记忆，见[证据](evidence/hindsight-cloud-cross-key-smic-2026-10-10.md)。
- 一个独享部署共用一个 PG 数据库，每空间独立数据 schema，表、索引及原生任务分开；元信息位于同库 ctxdb_meta，不增加独立元数据库。空间/schema 映射和授权由扩展实现，复用上游迁移及 Worker 枚举，不承诺零新增代码或性能互不影响；删除不得触及其他空间或元信息。

同一 RDS PG 中的元信息表至少需要 `workspaces`、`workspace_members`、`api_keys`，并保留状态、角色、scope、有效期/撤销、创建者和审计字段。具体表草案见[首期服务化设计](member-apikey-bank-service-design.md)，不是独立组件或已实现表结构。

### 4.2 再决定要不要“组织”

在首期范围，若“客户账户/华为云租户”已能承载成员、资源归属和账单，建议**不增加独立 Organization 表和用户界面概念**。把 `tenant_id` 映射到可信 IAM 身份及工作空间；一个租户可以有多个 workspace。若未来出现跨租户协作、一个账号管理多家公司、组织级 SSO/策略、工作空间集合转移、统一额度/账单或专属部署套餐，再新增 Organization，并定义组织与 workspace 的基数和迁移规则。

可用下列判断门槛：

| 需求 | 是否需要独立 Organization |
|---|---|
| 一个华为云客户租户下建多个工作空间 | 不需要；云租户作为父级 |
| 同一个个人账号加入多个互相独立的客户组织 | 需要一个可切换的组织上下文，或直接复用云 IAM 的跨租户能力 |
| 统一跨 workspace 的成员目录、策略、额度与账单 | 倾向需要；明确组织层级和权限继承 |
| 每个 workspace 单独授权、单独 Key、单独账单 | 不需要额外组织层也能实现 |
| 只想把多个 PG schema 合并成一个组 | 不是组织的充分理由；那是数据路由/部署映射问题 |

## 5. 需要实现与验证的场景

在成员/Key 管理进入可上线设计前，至少做如下合同测试：

1. **成员边界：** 同一 workspace 两个成员 A/B；验证 A 的私有记忆对 B 的列表、搜索、Recall、详情、导出、MCP、后台任务均不可见；显式共享 KB 按授权可见。
2. **Key 边界：** 管理员和成员都可拥有多个 Key；不同 Key 可分别限 scope、过期、撤销；同用户各 Key 对应同一认证身份，但本期不实现个人记忆隔离，其他有权用户仍可能读取同 Bank 内容。
3. **继承与撤权：** Key 权限不得高于成员；降权、离职、成员禁用、workspace 冻结提交后，新请求直接查 PG 主库并拒绝无效身份；首期不引入鉴权缓存。
4. **资源归属：** 修改请求中的 workspace_id、Bank ID、用户 ID 或 tenant 头不能越权；服务端从认证主体和控制库解析真实归属。
5. **审计：** 成员邀请/绑定/角色变化/禁用，Key 创建/轮换/撤销，记忆与 KB 的关键读写都可按 RequestId 追溯；审计不泄露 secret 或未授权正文。
6. **后台与重试：** 异步 retain、晋升、导出在创建者权限被撤销后有明确策略；重试不能复用已失效的客户 bearer token 或绕过资源 ACL。

## 6. 证据与未决问题

| 结论 | 证据类型 | 置信度/边界 |
|---|---|---|
| 阿里云有 workspace 内的用户管理、成员角色和成员行上的 API Key 管理入口 | 2026-10-10 登录控制台只读实测 | 高；只代表实测账号/空间当前 UI |
| 阿里云审计页包含 API 调用/操作记录，现场见到成员、Key、KB 操作事件 | 同上 | 高；没有检查每种事件的完整字段或保留期限 |
| 阿里云记忆 UI 提供成员筛选 | 同上 | 高；不足以证明后端隔离正确 |
| Hindsight Cloud 将组织、成员、API Key、用量/账单放在开源数据面之外的控制面 | Cloud UI/接口与官方文档实测汇总，见[对比报告](hindsight-cloud-open-source-comparison.md) | 高；不能反推出其内部物理部署映射 |
| Organization 的主要作用是产品归属、协作、权限和商业治理 | 根据公开 UI/文档的架构解释 | 中高；是功能分析，不是厂商内部实现披露 |
| Organization 与 Hindsight Tenant/schema 一一对应 | 没有公开证据证明 | 未知；不可作为设计前提 |
| 华为云首期不需要单独 Organization | 结合目标云 IAM/租户模型的架构建议 | 建议；由实际产品账户、计费和跨客户协作需求最终决定 |

公开来源：

- [阿里云 RDS ContextDB 控制台（杭州）](https://rdsnext.console.aliyun.com/contextDb/cn-hangzhou)（需登录；现场只读核验）
- [阿里云 ContextDB 快速入门](https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start)
- [阿里云权限管理](https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/permission-management)
- [Hindsight Cloud 与开源版实测及部署建议](hindsight-cloud-open-source-comparison.md)
- [Hindsight Cloud Team Management](https://docs.hindsight.vectorize.io/team-management/)
- [Hindsight Cloud API Keys](https://docs.hindsight.vectorize.io/api-keys/)
- [Hindsight Cloud Usage Analytics](https://docs.hindsight.vectorize.io/usage-analytics/)
- [Hindsight 开源版租户扩展与授权核验](cloud-service-evidence.md#s3-隔离与授权)
