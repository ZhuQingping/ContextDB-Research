# Hindsight Cloud 与开源版实测及华为云 ContextDB 部署建议

日期：2026-10-07<br>
验证对象：Hindsight Cloud `0.10.2`、本地 Hindsight `0.10.2`、源码 `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`

> 本文是固定日期的Cloud账号只读实测和部署推断，物理部署拓扑仅按文中证据边界表述。结构化实测结果见[证据JSON](evidence/cloud-vs-local-2026-10-07/cloud-vs-local-summary.json)。当前首期独享范围已于2026-10-09明确；本文的多Cell建议应视为长期扩展建议。

> 2026-10-12 用户已确认首期采用同 DB、一工作空间一 schema、schema 内唯一 Bank；工作空间下的用户也叫成员，角色仅 admin/member，每用户拥有多个 API Key，Key 固定绑定用户和空间；首期云租户独享 API、Worker 和 RDS PG，元信息与数据共用同一个 PG 数据库，不新增项目层级或 MetaPG。本期仅实现空间/用户/Key 管理和认证，不实现用户记忆私有与知识发布；商业 SMIC 跨 Key 行为见[证据](evidence/hindsight-cloud-cross-key-smic-2026-10-10.md)。最新架构、API 与 extension 方案见[首期服务化设计](member-apikey-bank-service-design.md)。Cloud 自身的 Owner 等角色名称仍按实测保留，不等同于 ContextDB 设计。本文的共享 Cell/空间内多 Bank 放置建议属于历史候选；当前采用 workspace-schema 映射，但 schema 内仅一个 Bank；Cloud 实测和首期独享范围保持原有证据边界。

## 1. 结论

Hindsight Cloud 的公开证据支持下面的产品拆分：

1. **Retain、Recall、Reflect、知识库、心智模型等核心数据面复用同一套 Hindsight 能力。** Cloud 与本地版有 74 条共同 API 路径，HTTP 方法集合一致，Retain、Recall、Reflect 等主要请求模型相同。
2. **组织、成员、API Key、用量、账单、账号安全和邮件偏好由商业控制面提供。** Cloud 前端存在独立的组织类控制面接口；开源 Control Plane 没有这些路由。
3. **标准 Cloud 的控制面明确是多租户的，且不承诺每客户 Dedicated Infrastructure。** 官方把 Dedicated Infrastructure 单列为 Enterprise 能力；标准 Cloud 使用统一域名、按量计费、无席位费，并明确支持 multi-org。这些证据支持标准档采用资源池化，但标准 Cloud 内部究竟按组织、Bank 还是其他粒度划分 Pod、schema 和 PG，公开资料无法证明。
4. **Cloud 的 API 进程关闭了内置 Worker。** 实测 Cloud `/version` 返回 `worker:false`，本地联合进程返回 `worker:true`。这说明商业云至少采用了 API 不执行后台任务的运行方式；Worker 的数量、编排方式和数据库分片方式没有公开证据。
5. **华为云可以学习产品管理与记忆引擎解耦的边界，不必复制标准 Cloud 拓扑。** 当前首期为租户独享 API、Worker 与 PG，管理功能优先放在 API 扩展中，元信息同库；不为了多 PG 改造动态 DSN、核心拆表或自研 API→Worker 队列。下文共享控制面/多 Cell 是历史长期扩展候选，不是首期必要组件。

首期建议把 Hindsight 当成可升级的数据面内核，产品差异能力主要放在 Huawei API Gateway、ContextDB Control Plane、模型网关和运维平台。生产预览版可启用 Hindsight 官方支持的独立 Worker；这只是同一镜像的部署开关，不是内核 fork。

## 2. 验证范围与方法

本轮采用四类证据，避免把产品宣传、外部推断和源码事实混在一起：

| 证据 | 实际动作 | 能证明什么 |
|---|---|---|
| 已登录 Cloud 账号 | 访问已登录 Cloud 页面；下载其服务端 HTML 与前端静态产物，检查实际路由和接口字符串 | 商业控制面当前实际包含的页面与后端入口 |
| Cloud API Key | 只读调用 Cloud 的 Bank、Operation、Stats、LLM Request 接口；未创建、修改或删除数据 | 鉴权、核心 API 可用性和响应结构 |
| Cloud 与本地 OpenAPI | 分别读取 `/openapi.json`，按路径、HTTP 方法和 schema 比较 | 公共数据面兼容范围和 Cloud 增量接口 |
| 本地源码与运行进程 | 检查 `TenantExtension`、Worker、Helm、服务文档，并调用本地 `/version`、`/health` | 开源版可扩展边界和当前部署形态 |

账号、密码和 API Key 没有写入本文，也没有输出到验证日志。本轮没有执行产生费用的 Retain/Reflect，没有创建或撤销 Cloud 资源。

## 3. 商业版与开源版实测差异

### 3.1 核心数据面基本一致

| 项目 | Hindsight Cloud | 本地开源版 | 结论 |
|---|---:|---:|---|
| API 版本 | 0.10.2 | 0.10.2 | 同版本 |
| OpenAPI 路径数 | 86 | 77 | Cloud 多 12 条，本地多 3 条 |
| 共同路径 | 74 | 74 | 74 条共同路径的 HTTP 方法集合一致 |
| 主要请求模型 | `RetainRequest`、`RecallRequest`、`ReflectRequest` | 相同 | 客户端核心调用可保持一致 |
| Bank 列表只读调用 | Bearer Key 后返回 200 | 无鉴权返回 200 | Cloud 增加产品级鉴权 |
| 数据库健康 | `/health` 返回 connected | `/health` 返回 connected | 两者均以 PG 为状态存储 |

共同路径覆盖 Bank、Retain、Recall、Reflect、Memory、Document、Entity、Mental Model、Knowledge Base、Operation、Webhook、导入导出等核心能力。这说明华为云可以保留 Hindsight 原生 API 语义，并在外层增加云产品合同。

Cloud 不是与开源版完全相同的二进制接口。两份 OpenAPI 有认证、错误和少量 schema 差异，因此升级时仍需做差分合同测试，不能只看版本号。

### 3.2 Cloud 增加的公开数据面接口

Cloud OpenAPI 比本地版多出的 12 条路径如下：

- scoped API Key：创建、列出、撤销子 Key；
- Memory Defense security events：查询与清理安全事件；
- subject export/erase：数据主体导出、删除预览和执行；
- privacy event receipt：查询隐私操作回执；
- organization webhook：组织级 webhook 管理。

这些接口共同指向商业产品需要的凭据委派、安全治理和隐私合规。普通 Retain、Recall、Reflect 并没有被改造成另一套 Cloud 专用协议。

本地 OpenAPI 独有 `/health`、`/metrics`、`/version` 三条路径。Cloud 的 `/health` 和 `/version` 实际可访问，但没有列入 Cloud OpenAPI；`/metrics` 不应对公网开放。

### 3.3 Cloud 控制面比开源 Control Plane 多什么

对当前 Cloud 与本地前端静态产物进行路由扫描，结果如下：

| 能力 | Cloud 实测路由/接口证据 | 本地开源 UI |
|---|---|---|
| 组织 | `/api/organizations`、组织创建与切换 | 无组织路由 |
| 团队成员 | `/team` | 无 |
| API Key | `/api-keys`、`/api/api-keys` | 无 |
| 用量 | `/usage` | 无 |
| 账单 | `/billing` | 无 |
| 组织设置 | `/settings` | 无 |
| 邮件偏好 | `/account/email-preferences` | 无 |
| 账号安全 | `/account/security` | 无 |
| Bank 数据面 | `/api/banks` | `/api/banks` |

Cloud 页面元信息直接描述自己为 `Multi-tenant control plane for Hindsight semantic memory`。官方文档还确认：

- 一个账号可以加入或创建多个 Organization，切换组织后 Bank、Key 和账单随之切换；
- Owner、Admin、Member 三种角色控制成员、Key、Bank 和账单权限；
- API Key 支持 Bank scope、过期时间、只显示一次，以及具备 Key Creator 权限的父子 Key；
- 用量可以按操作和 API Key 查看，账单按 Retain、Recall、Reflect、模型刷新和存储等实际用量计费；
- Enterprise 增加 SSO、强制 MFA、审计、Memory Defense、BYOC、on-premise 和 Dedicated Infrastructure。

对应官方资料：[Pricing](https://vectorize.io/pricing)、[Team Management](https://docs.hindsight.vectorize.io/team-management/)、[API Keys](https://docs.hindsight.vectorize.io/api-keys/)、[Usage Analytics](https://docs.hindsight.vectorize.io/usage-analytics/)、[Multi-Org](https://hindsight.vectorize.io/blog/2026/03/29/multi-org-credit-transfers)、[Enterprise Features](https://hindsight.vectorize.io/blog/2026/09/03/hindsight-cloud-enterprise-features)。

### 3.4 当前 Cloud 与本地的 Worker 形态

实测 `/version`：

```text
Cloud: worker=false, audit_log=true, api_version=0.10.2
Local: worker=true,  audit_log=false, api_version=0.10.2
```

源码中 `worker` 字段定义为“当前 API 是否启用后台 Worker”。因此可以确认：

- 本地当前一个 `hindsight-api` 进程同时提供 API 和内置 Worker；
- Cloud 公网 API 进程没有运行内置 Worker；
- Cloud 的后台任务需要由 API 进程之外的执行者处理。

不能从这个字段推出 Cloud 有几个 Worker、Worker 是否独占 ECS、一个 PG 服务多少组织，或每个租户是否独立 schema。官方 Helm 提供的标准形态是 API Deployment + Worker StatefulSet，共享 PG 任务表；这可以作为高可信参考，但不能冒充 Cloud 内部实现披露。

### 3.5 Cloud 是否启用了 AWS S3

**结论：Cloud 的文件存储能力已经开启，但当前无法证明底层配置为 AWS S3。**

实测证据：

- Cloud `/version` 返回 `file_upload_api=true`、`document_export_api=true`、`document_import_api=true`；
- Cloud OpenAPI 提供文件 Retain、文档导入导出、附件读取和导出文件下载接口；
- Cloud Bank `/config` 的客户可见结果不包含 `file_storage_type`、S3、GCS、Azure、bucket 或 endpoint；
- 当前测试 Bank 没有文档和附件，因此没有现有对象可读取；即使上传一个附件，下载仍经过 Hindsight 的 Bank 鉴权 API，响应不会暴露后端类型。

开源源码确认文件存储是服务端静态配置：

| `HINDSIGHT_API_FILE_STORAGE_TYPE` | 实际存储 | 默认值 |
|---|---|---|
| `native` | PostgreSQL `BYTEA` / `file_storage` 表 | 是 |
| `s3` | AWS S3 或设置自定义 endpoint 的 S3 兼容存储 | 否 |
| `gcs` | Google Cloud Storage | 否 |
| `azure` | Azure Blob Container | 否 |
| 自定义 Extension | 厂商自己的 `FileStorage` 实现 | 否 |

所有后端共用 `/v1/default/banks/{bank_id}/attachments/{attachment_id}` 和 `/v1/default/files/download/{key}`，所以外部行为不能区分 PG、S3、GCS、Azure 或自定义实现。官方配置文档只说明 Cloud 负责存储，没有声明 Hindsight Cloud 使用 AWS S3。[File Storage 配置](https://hindsight.vectorize.io/developer/configuration#file-storage)

因此当前可写入设计和评审材料的准确表述是：

> Hindsight Cloud 已开启托管文件/附件存储；其物理后端没有通过公开 API 或官方文档披露，不能确认是 AWS S3。

若必须取得“是否为 S3”的硬证据，需要 Vectorize 提供架构说明，或由其管理员返回脱敏的 `file_storage_type`。不需要也不应要求 bucket、endpoint 或访问密钥。对华为云方案而言，这不影响 OBS 选型：Hindsight 的 `s3` backend 支持自定义 S3-compatible endpoint，可以先做 OBS 兼容性实测；若兼容细节不足，再实现独立 `FileStorage` Extension，而无需修改核心 Retain/Recall 代码。

## 4. Hindsight Cloud 的部署形态能确认到什么程度

### 4.1 已确认事实

1. 标准 Cloud 是一个多租户产品控制面，所有客户使用统一 API 域名。
2. 标准 Cloud 按使用量收费，无固定月费和席位费；官方承诺自动扩缩、每日备份和 99.9% 可用性。
3. Dedicated Infrastructure 是 Enterprise 的单独能力。这排除了“标准 Cloud 默认每个小客户独占一整套基础设施”的解释。
4. 官方明确称 Cloud 使用 managed Postgres。
5. Cloud API 关闭了内置 Worker，说明在线 API 与后台计算至少在进程角色上分开。
6. 开源内核原生支持 TenantExtension 将认证身份映射到 PostgreSQL schema，Worker 通过 `list_tenants()` 枚举租户并处理后台任务。

### 4.2 高可信推断

标准 Cloud 应采用共享计算和共享/分片存储承载小客户，大客户再升级为专属资源。理由是统一入口、按量计费、免费起步和 Enterprise 专属基础设施共同决定了每个小用户独占 API、Worker 和 PG 的成本模型不成立。

Cloud 很可能复用开源 TenantExtension/OperationValidatorExtension 一类边界，把认证、schema 选择、用量和治理接入 Hindsight 内核。依据是 Cloud 与开源核心 API 高度一致，且 Hindsight 官方明确把扩展机制定义为“不修改 core code”的多租户、鉴权、限流、配额、审计和计量接入点。[Extensions](https://hindsight.vectorize.io/developer/extensions)

### 4.3 当前无法确认

- 一个组织是否对应一个 PG schema；
- 多个组织如何分布到 PG 实例；
- 是否按 Bank 做物理分片；
- API/Worker 的副本数和 Kubernetes 拓扑；
- PG、对象存储和模型调用的内部网络设计；
- 商业代码是私有扩展、独立服务还是对开源仓的私有补丁组合。

这些信息不能通过 UI、DNS、HTTP Header 或 OpenAPI可靠反推。若它们会影响采购或兼容决策，应向 Vectorize 索取 Cloud architecture、data isolation、subprocessor、backup/DR 和 tenancy whitepaper，而不是继续猜测。

### 4.4 公网入口属于哪个云，是否能确认 Kubernetes

2026-10-07 的被动网络探测结果：

| 证据 | 结果 | 能支持的判断 |
|---|---|---|
| DNS A | `ui`、`api`、`auth`、`docs`、`analytics`、`grafana`、`status`、`alb` 均为 `8.233.104.54` | 多个服务共用同一个公网七层入口 |
| PTR | `54.104.233.8.bc.googleusercontent.com` | IP 由 Google 网络提供 |
| ASN/WHOIS | `AS396982 Google LLC`、`NetName: GOOGL-2` | 公网入口不是 AWS 地址段 |
| HTTP | `via: 1.1 google`、HTTP/2/HTTP/3 | 与 Google Cloud Application Load Balancer 特征一致 |
| TLS | 证书由 Google Trust Services 签发，证书 SAN 同时包含上述服务域名，CN 为 `alb.hindsight.vectorize.io` | TLS 在共享 Google 入口终止或受其管理 |
| 应用 Header | API 未返回 `server: envoy`、`ingress-nginx`、`x-envoy-*` 或 Kubernetes 特有信息 | 没有暴露可用于确认 GKE/Kubernetes 的直接指纹 |

Google 官方文档说明，外部 Application Load Balancer 会添加 `Via: 1.1 google`；同一种 Load Balancer 后端可以是 Compute Engine、GKE、Cloud Run、Cloud Storage或互联网 NEG。[Google Cloud Application Load Balancer](https://docs.cloud.google.com/load-balancing/docs/application-load-balancer)

因此可以分层下结论：

1. **可确认：** Hindsight Cloud 的公网 TLS/HTTP 入口使用 Google Cloud Load Balancing/Google 网络，而不是直接使用 AWS ALB 或 AWS 公网地址。
2. **高概率但不能证明：** 主要应用后端也位于 GCP。Google Load Balancer同样可以代理其他公有云或外部后端，入口归属不能证明计算、PG和对象存储的归属。
3. **不能确认：** 后端是 GKE/Kubernetes、Cloud Run、Compute Engine VM、Managed Instance Group，还是其他运行环境。共享 IP、健康检查、API/Worker 分离和 `alb` 名称都不是 Kubernetes 专属证据。

从公网继续做端口扫描、错误注入或尝试访问 Kubernetes API，不仅不能稳定证明编排平台，也不适合作为产品架构依据。能够确认 Kubernetes 的可靠证据应来自 Vectorize 的部署说明、Kubernetes workload/Helm release清单、镜像与 Pod 日志，或其提供的安全架构材料。

## 5. 开源版与商业版如何保持代码边界

虽然商业仓库不可见，公开证据已经说明了边界的基本形状：

```text
Cloud Console / Org / Team / Key / Usage / Billing / SSO
                         |
                  Cloud Control Plane
                         |
             Auth、entitlement、metering、routing
                         |
            Hindsight API / Worker 数据面
                         |
                      PostgreSQL
```

关键证据：

- Cloud 与本地共用 74 条核心 API 路径和同一版本号；
- Cloud 前端的 Organization 接口与 Hindsight `/v1/default/banks/...` 数据面接口分属不同路径族；
- Hindsight 提供 `TenantExtension`、`OperationValidatorExtension`、`HttpExtension` 和 `MCPExtension`；
- 官方文档明确说外部 Extension 的目的之一是让扩展依赖和变更不要求 Hindsight 发版；
- 官方独立 Worker 与 API 使用同一个包和镜像，只是入口和配置不同；
- Cloud 0.10.0 发布说明明确说多模态、Prompt Preview、知识库导出等功能也全部进入开源 0.10.0，并非 Cloud-only。[Cloud 0.10.0](https://hindsight.vectorize.io/blog/2026/09/21/hindsight-cloud-0-10-0)

因此最合理的学习不是复制一套未知的 Cloud 私有代码，而是复制它的**产品边界**：通用记忆能力持续进入开源内核，云租户和商业治理留在外围，必要的接入通过稳定扩展点完成。

## 6. 华为云 ContextDB 历史部署候选

本节保留 2026-10-07 的共享控制面/多 Cell 研究，MetaPG、Workspace placement 等不属于当前首期独享方案。当前部署见[租户独享管理架构](member-apikey-bank-service-design.md#总体架构与资源模型)。

### 6.1 总体结构

```text
Agent / SDK / MCP / Console
            |
Huawei API Gateway
认证、租户/Workspace/Bank授权、限流、幂等、路由
            |
ContextDB Control Plane -------- MetaPG / IAM / KMS / Metering
组织、成员、Key、配额、放置、规格、生命周期、账单
            |
      Data Cell A / B / C ...
      |- Hindsight API × N
      |- Hindsight Worker × M（生产预览启用）
      |- RDS PostgreSQL（本 Cell 的多个 Workspace）
      `- OBS（文件原件和大对象）
            |
      Huawei Model Gateway / MaaS
```

**Data Cell 是一组有固定数据归属的运行资源，不等于一个进程，也不要求等于一台 ECS。** 每个 Cell 的 Hindsight 实例固定连接该 Cell 的 RDS PG 和 OBS 配置。Gateway 先根据 MetaPG 中的 placement 找到 Cell，再把请求发送给该 Cell 的稳定 Service，由负载均衡选择任意健康 API Pod。

### 6.2 小用户如何控制成本

> 历史共享部署候选：本小节的共享 Cell 和空间内多 Bank 映射已被当前模型替代；workspace-schema 映射被采用，但每 schema 内唯一 Bank；不要将下面的放置/迁移粒度直接作为当前实现合同。

- 多个小 Workspace 共享一个 Data Cell、API Pool、Worker Pool 和 RDS PG；
- 每个 Workspace 对应一个 Hindsight tenant/schema，Workspace 内包含多个 Bank；
- 通过 Workspace/Bank 配额、并发、Token 和存储用量抑制 noisy neighbor；
- 当一个 Cell 达到连接数、CPU、IO、容量或租户数阈值时，新 Workspace 放到新 Cell；
- 大客户可放入空 Cell或专属 Cell，作为高规格产品形态；
- 首期不拆分单个 Bank，也不让一个 Hindsight 进程按请求动态连接任意 PG。

选择 Workspace 作为首期放置和迁移粒度，比 Bank 粒度更容易保持团队空间、Key、配额、备份和知识引用的一致性，也避免每次请求跨多个 PG。极大 Workspace 后续再增加 Bank 级放置能力。

### 6.3 API 和 Worker 是否现在就拆

分阶段处理：

| 阶段 | 形态 | 原因 |
|---|---|---|
| 本地开发、功能验证 | `hindsight-api` + 内置 Worker | 最少进程，最容易定位问题 |
| 内测、小流量试用 | 可继续联合部署，验证容量拐点 | 避免过早增加运维对象 |
| 对外生产预览 | API Deployment + Worker StatefulSet | 文档解析、Retain、知识页刷新是长任务，需要隔离在线延迟；Cloud 实测也关闭 API 内置 Worker |

拆分时不开发新的消息协议。API 把异步 operation 写入 PG，Worker 从同一 PG claim；Gateway 不直接调用 Worker。API 和 Worker 使用相同镜像及相同 TenantExtension，只由启动命令和 `HINDSIGHT_API_WORKER_ENABLED` 区分。官方 Helm 已实现这一形态，Worker 使用 StatefulSet 保持稳定 worker ID。

API 副本和 Worker 副本只需由 Kubernetes 管理，不需要开发一套“集群管理系统”。产品控制面管理的是 Cell、版本、容量和放置，不管理每次任务该交给哪个 Worker。

### 6.4 多 PG 横向扩展不应修改 Hindsight 动态选库

Hindsight 的 `TenantExtension` 返回 `schema_name`，没有返回每请求 DSN 的合同。这意味着官方扩展点天然适合“一组进程固定连接一个 PG，在 PG 内按 schema 隔离”，不适合一个进程维护任意租户到任意 PG 的动态连接池。

首期正确做法：

1. MetaPG 保存 `workspace_id -> cell_id`、Cell Service 地址、RDS/OBS Secret 引用、版本和状态；
2. Gateway 根据可信 Workspace 身份查 placement；
3. 请求只进入目标 Cell；
4. Cell 内的 TenantExtension 把 Workspace 映射到 schema；
5. 扩容时新增 Cell，新增 Workspace 直接落新 Cell；
6. 已有 Workspace 首期通过维护窗口做整 Workspace 导出、恢复、校验和切换。

这样能横向增加 RDS，又无需修改 Hindsight 的连接池、查询路径、Worker 枚举和迁移机制。单 Bank 在线跨库和自动 rebalance 延后。

## 7. 哪些功能放外围，哪些进入 Hindsight 扩展

### 7.1 Control Plane / Gateway 负责

- 华为云 IAM 登录、Organization/Workspace 和成员管理；
- Owner/Admin/Member 及 Workspace/Bank ACL；
- API Key 创建、哈希保存、scope、到期、轮换、吊销和审计；
- 产品规格、配额、QPS/并发/Token 限制和欠费状态；
- Cell placement、创建、扩容、迁移、备份、恢复和版本发布；
- 用量账本、费用、账单、告警、工单和通知偏好；
- 模型选择、MaaS 凭据、模型限流、成本和失败治理；
- 产品控制台以及控制面审计。

这些内容不应写入 Hindsight 核心表，也不应依赖修改 Retain/Recall 内部实现。

### 7.2 独立 Huawei Hindsight Extension 负责

- 校验 Gateway 签发的短期内部身份，得到 tenant/schema；
- 将 `tenant_id`、`api_key_id`、Workspace 和 Bank 权限带入请求上下文；
- 在 OperationValidator 中做 Bank 读写授权、能力开关和额度预检查；
- 将操作计量和审计事件异步发送到华为云外围服务；
- 必要时增加 `/ext/` 管理或诊断端点；
- API 与 Worker 使用完全相同的扩展包和版本。

对外 API Key 应是不可读业务信息的随机凭据，服务端只保存哈希和 Key ID；不要把租户密钥、PG 地址或 OBS 凭据编码进 Key。Gateway 鉴权后签发短时、可验证的内部上下文，并删除客户伪造的同名 Header。

### 7.3 Hindsight core 的改动原则

首期目标应为 **零必需 core patch**。发现确实缺少的扩展点时：

1. 先用现有 Tenant、OperationValidator、HTTP、MCP Extension；
2. 仍无法实现时，做小而通用的 hook，并向上游提交；
3. 华为专属依赖留在独立 extension/image；
4. 禁止首期做 rt/ud 全表拆分、每请求动态 DSN、自研 Worker 调度和全链路 storage epoch 改造。

## 8. 首期需要补齐的产品能力

### P0：两个月内必须有

1. Workspace、成员角色、Bank/KB 资源与 Bank 级 ACL；
2. API Key 的 scope、到期、轮换、吊销、只显示一次和使用审计；
3. Gateway 鉴权、路由、限流、幂等和统一错误码；
4. Data Cell placement 与新增 Cell 扩容；
5. Retain、Recall、Reflect、文件上传、Operation 查询和 Knowledge Base 页面；
6. MCP、Python SDK 和两种真实 Agent 客户端的端到端样例；
7. 模型网关、租户并发/Token 限制、超时、重试边界和用量计量；
8. RDS/OBS 备份恢复、删除、监控、告警和升级回滚；
9. Cloud/开源兼容测试：固定上游版本，运行核心 API 合同、真实 PG、Worker 强杀恢复和升级测试。

### P1：首期可做出差异的高性价比能力

**华为云 Coding Agent 团队知识闭环**最适合作为首期差异点：

- Claude、Codex、OpenClaw 等通过 MCP 一键接入；
- 个人 Bank 中的有效经验形成“知识候选”；
- 保留来源、作者、时间和关联会话；
- 团队管理员审核后一键发布到 Workspace Knowledge Base；
- 知识可以撤回、重建并看到历史来源；
- 控制台显示命中次数、节省的上下文 Token 和失败原因。

Hindsight 已提供 Memory、Mental Model、Knowledge Page、MCP 和来源信息，华为云主要补人审工作流、团队权限和效果度量。它比首期重写召回算法或做单 Bank 跨 PG更容易形成客户可感知价值，也更符合五人团队的投入约束。

## 9. 对现有设计的修正意见

本节是历史候选修正清单。当前首期保留既有云入口、独享 API/Worker 和 RDS PG，不单独引入 MetaPG、共享 Cell 放置或独立生命周期/审计组件；成员/Key 元信息同库。OBS、模型网关等按实际需要接入，不因本报告而成为新增前置服务。

以下内容应从首期删除或降为后续研究：

- Hindsight 内部 rt/ud 双 schema 拆表；
- API 根据元数据库动态选择任意 PG/OBS；
- 自研 API 到 Worker 协议或任务队列；
- Maintenance 独立成第三套首期集群；
- 单 Bank 跨 PG、在线迁移和自动再均衡；
- 为云成员、账单、用量修改 Hindsight 核心表。

修正后，商业化边界与 Hindsight Cloud 的公开形态一致：**云控制面独立演进，Hindsight 数据面按 Cell 部署，租户接入通过扩展点，PG 扩展通过增加 Cell。**

## 10. 验证记录与限制

| 检查 | 结果 |
|---|---|
| Cloud OpenAPI | 200，title=`Hindsight Cloud API`，version=0.10.2，86 paths |
| Local OpenAPI | 200，title=`Hindsight HTTP API`，version=0.10.2，77 paths |
| Cloud 无 Key列 Bank | 401 |
| Cloud 有效 Key列 Bank | 200，返回分页 Bank 结构 |
| Cloud scoped child Key 列表 | 当前 Key 返回 403，说明能力由 Key 权限控制 |
| Local 无 Key列 Bank | 200 |
| Cloud `/version` | 200，`worker=false`、`audit_log=true` |
| Local `/version` | 200，`worker=true`、`audit_log=false` |
| Cloud Bank stats/operations/LLM requests | 均返回 200；当前 Bank 无 operation 历史 |
| Cloud 旧 profile API | 410，与 0.10.0 发布说明一致 |
| 本地进程 | 一个 `hindsight-api`、一个 UI Node 进程、一个独立 PostgreSQL 实例 |

机器可读的脱敏结果保存在 [cloud-vs-local-summary.json](evidence/cloud-vs-local-2026-10-07/cloud-vs-local-summary.json)。它只记录路径、计数、状态码和 feature flags，不包含账号、Key、Bank ID 或业务内容。

本轮没有得到 Vectorize 的私有部署图或商业源码，因此本文不会断言 Cloud 的 Pod 数、PG 分片算法、schema 粒度和对象存储布局。上述“已确认事实”足以确定华为云的产品边界；内部物理拓扑只能作为待供应商确认项。

## 11. 开发决策

建议把当前方案基线改为：

> **ContextDB = Huawei Cloud Control Plane + Gateway + Huawei Hindsight Extension + 多个 Hindsight Data Cell。** 组织、成员、Key、账单、用量和放置全部在外围；一个 Cell 固定一套 RDS/OBS；小租户共享 Cell，大租户可独占；生产预览使用官方 API/Worker 分离模式；不修改 Hindsight 的核心数据模型和任务协议。

这条路线既能在两个月内形成可用产品，也保留了跟随 Hindsight 社区升级的能力。下一项实现工作应先做 Huawei Tenant/Validator Extension 和单 Cell 生产部署，而不是继续扩展现有侵入式内核补丁。
