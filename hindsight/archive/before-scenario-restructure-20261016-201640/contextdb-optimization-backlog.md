# ContextDB 优化清单与本次落实

更新：2026-10-16。本次实现位于独立分支 contextdb/release-hardening-20261016-182619；原体验实例未切换。本页取代旧候选清单中的当前状态，[完整历史分析与评审](../2026-10-16-before-release-hardening/contextdb-optimization-backlog.md)保留，不将前后冲突方案同时当作要求。

[当前设计](member-apikey-bank-service-design-first-release.md) · [部署与升级](../../implementation/contextdb-optimized-guide.md) · [curl验收](../../implementation/contextdb-management-api-curl-guide.md) · [OpenAPI](../../api/contextdb-optimized.openapi.yaml)

## 1. 本次实施结果

| 编号 | 当前决定与实现 | 验证入口 |
| --- | --- | --- |
| UM-01～08 | 保留已实现的实例级“用户管理”、成员展开/更多菜单、默认读写、逐空间授权、脱敏和一次性明文、吊销隐藏、成员停用/删除与审计 | UI组件、HTTP、真实UI→API、REST/MCP |
| UM-09 | 现有名称搜索足够，不加复杂过滤；使用统一消息、请求取消/归属校验；普通成员无角色选择或个人UI登录 | users-view、UI代理与端到端 |
| UM-10 | NFKC/trim/casefold 名称唯一，active/disabled一起占名；PG唯一索引兜底，并发409；保留管理员名；软删除后新身份，不继承旧Key | release_hardening、bootstrap_deployment、115故事 |
| AUTH-01 | 管理员与业务Key统一PG HMAC认证；角色来自PG；离线导入唯一受保护管理员；不保留运行时SHA回退 | security/repository/bootstrap/tenant、HTTP、系统测试 |
| DEP-01 | 同版源码交付、实际模块路径及扩展接口预检、受支持构建；部署方记录提交/补丁或镜像摘要 | preflight、Node构建、service.sh测试 |
| DEP-02 | 外部PG无强制pg0；embedded-db可选依赖，发行包pg0-embedded | pyproject、部署文档/预检 |
| DEP-03 | HINDSIGHT_API_ENV_FILE显式文件或空值；托管启动关闭cwd/父目录自动发现，PG连接复用 | 原生dotenv的8项测试、启动脚本 |
| DEP-04/07 | 正式.mjs配置、支持Node22.12+/24、平台optional依赖、系统字体 | Node22和24生产构建 |
| DEP-05 | API readiness前不启动UI；启动有界退避，仅暂时故障重试，凭据错误立即拒绝；请求仍实时鉴权 | UI启动回归、实际生产UI→API |
| DEP-06 | 首次秘密原子落盘、0600/0700、重复保留；已初始化缺文件拒绝补生；离线显式管理员轮换 | bootstrap_deployment与脚本重复init |
| DEP-08 | Python/Node/npm/esbuild/PG扩展/UTF8/全文语言预检；中文不能以native英文验收代替 | preflight测试、分层部署说明 |
| API-01～07 | 保留既有敏感载荷门禁、单一authorization、字段/错误/列表合同、并发If-Match、显式恢复及安全代理 | HTTP/OpenAPI、所有ContextDB系统故事 |
| API-08 | 管理代理不再与middleware重复查身份；使用时间最多60秒更新一次；统计只在未带ETag列表，可编辑快照排除统计 | UI请求计数、使用时间/吊销测试、OpenAPI |
| API-09 | /admin/session改/admin/identity，所有UI及测试调用同步，不新增登录或Key接口 | 路由/代理/仪表启动测试 |
| WS-01 | 正常行移除“查询进度”；处理中单目录GET自动刷新1～5秒，最多2分钟；失败可查、未知结果显式恢复 | workspaces-view、recovery测试 |
| WS-02 | 早期全可读bank_id/schema/授权输入候选不采用。遵循最后WS-04确认范围，避免扩大内核改动及名称复用问题 | 设计5.3/5.4及115故事 |
| WS-03 | 安全排空后清理Bank/文件/schema/授权/空间行；操作独立快照默认168小时，审计保留；旧墓碑安排同一执行器清理 | 真实PG清理/外部依赖/旧结构升级/115故事 |
| WS-04 | 仅GET详情按唯一名称，URL编码/精确查询；DELETE、selected授权、原生bank_id继续UUID | HTTP、代理Unicode、真实SDK/MCP |
| DB-01～04 | 保留单行部署、去冗余字段、关联授权、varchar输入约束/COMMENT和必要索引；新增用户规范化唯一与管理员约束 | schema、迁移、目录/注释/并发测试 |
| DB-05 | 采用last_used_at有界更新；不缓存认证、不改持久准入、不去全局管理事务锁 | 使用时间/即时吊销/并发屏障回归 |
| DB-06 | 管理任务、准入、审计分工不合表；完成空间行清理及有界操作历史回收，未知执行者不按TTL清除 | 终态保留、准入/故障/租约/排空故事 |

## 2. 冲突的最终处理

- 名称用于GET当前对象；不可复用UUID用于写入和授权。没有新增可读bank_id列或可复用schema，没有要求业务客户端改URL规则。
- 正常删除空间后不保留空表或空间墓碑；仍保留操作结果和审计，生命周期不同。旧结构的deleted只在兼容清理中暂存。
- 删除选中空间会删除对应Key关联并递增版本。内部空selected表示无权限，公开创建/替换仍要求1～1000个有效空间；不会变成all或继承同名新空间。
- 管理员同样入users/api_keys，但普通成员列表和CRUD隐藏/保护它。普通UI创建用户无角色选项；all范围不会提权。
- pepper继续保留并独立备份。普通运行无需ADMIN_KEY_SHA256；旧版升级的校验值不是第二条运行认证路径。
- 历史默认168小时，可配置24～8760。浏览器未知意图24小时后不重放；服务端不承诺过期请求“从未执行”。未完成/未知/有残留空间的失败操作不清理。
- 只在API就绪后启动UI；启动暂时故障重试与每次请求的权限复核是两件事，不以授权缓存换启动速度。

## 3. 评估后不增加的机制

以下原本是“先测量再决定”的候选，不是漏实现的既定功能：

| 候选 | 本次决定 |
| --- | --- |
| 名称搜索GIN、全量Key历史索引、更多任务领取索引 | 现有小目录无证据证明瓶颈；保留必要B-tree/唯一/部分索引，不预建近似索引 |
| 全局管理锁替换 | 当前是低频管理写；保持已验证并发语义，不引入更复杂锁序 |
| Bank列表/MCP批量读取及新分页/过滤协议 | 原生逐空间读取保留；没有代表性规模数据，不声称吞吐收益，也不新增接口平台 |
| 取消pepper、SHA-only或多管理员/在线恢复 | 本次统一PG HMAC，保留运维秘密边界；仅显式离线管理员轮换 |
| 通用同步/异步开关、额外Agent服务 | 空间生命周期仍异步；用户/Key同步；复用已有Agent监督器与原生Worker |
| 强行清除异常准入/未知执行者 | 不采纳；阻止破坏性清理是必要安全语义 |

## 4. 验证与交付边界

完整日志位于本次独立artifacts目录；代码未提交/推送/替换现有体验服务。原始dirty基线已保存，新增工作在独立worktree。四类专家复核均无剩余阻断；PG接受的边界是客户不得绕过服务进行并发DDL，以及旧deleted兼容清理三败后需所有者离线恢复。最终测试计数见[本次验收报告](../../implementation/contextdb-release-hardening-acceptance-20261016.md)，过程中失败修复与最终结果分开记录。

本地模拟模型验证权限、路由、任务与资源生命周期；不据此宣称真实MaaS质量、中文全文检索效果、生产容量、HTTPS/突发限流、PGroonga故障恢复或云HA已通过。这些属于部署环境验收，不通过改应用代码伪装完成。

## 5. 阿里ContextDB实测证据（历史保留）

#### 环境和方法

- 日期：2026-10-16。
- 页面：阿里云 ContextDB，杭州区域，`research` 工作空间的 [用户管理页面](https://rdsnext.console.aliyun.com/cn-hangzhou/contextDbDetail/ws-8cc8o2zty2u47cz/userManagement)。该链接需要账号登录，仅用于定位本次观察环境。
- 使用用户已登录的 Chrome 实际操作页面；浏览器扩展连接超时后，改用桌面方式完成查看。
- 先查看已有成员的表单和确认弹窗，全部取消，没有修改已有成员或 Key。
- 后续创建专用临时成员 `ui-review-disposable-20261016`，角色为成员；初始 Key 名称为 `ui-revoke-test`。测试对象仅用于本次调研。
- 创建提交由用户在 Chrome 完成；吊销由助手在用户确认后完成。下一次连接时成员删除已完成，助手未再次点击删除，而是刷新及重新加载页面核验结果。
- 截图仅包含表单、脱敏凭据和列表结果，不保存完整 API Key。

#### 按钮与表单观察

| 操作 | 实际观察 | 验证程度 |
| --- | --- | --- |
| 新建成员 | 成员名称、管理员/成员；默认选成员 | 已打开表单并切换选项 |
| 同时生成初始 ApiKey | 默认选“是”，可填写初始 Key 名称；选“否”后隐藏名称框 | 已切换观察；临时成员按“是”创建 |
| 成员行展开箭头 | 在该成员行下展示 ApiKey 列表 | 已实际展开、收起 |
| 管理 ApiKey | 同样展开该成员的 Key 列表，不跳转独立页面 | 已实际操作 |
| Key 列表 | 名称、脱敏 Key、创建时间、最近使用时间、操作 | 已查看已有与测试 Key |
| 新建 ApiKey | 显示所属成员，只填写 Key 名称 | 已打开表单；没有通过该独立入口签发第二把 Key |
| 编辑 Key | 显示脱敏 Key、成员、状态；可修改名称，提示吊销需使用吊销按钮 | 已查看后取消，没有提交修改 |
| 角色设置 | 打开“编辑成员”，包含角色与状态；成员名称只读展示 | 已打开查看，没有提交变更或确认实际授权效果 |
| 角色说明 | 页面说明涉及工作空间成员、用户组及组管理员管理 | 已查看说明，不代表本次验证了这些权限 |
| 删除成员 | 确认框说明永久删除、其所有 Key 失效、不可恢复 | 已查看；后续核实临时成员删除结果 |
| 刷新 | 成员列表和展开的 Key 列表分别提供刷新按钮 | 已实际刷新 |
| 阿里云 UID 绑定 | 成员列表包含绑定信息；普通成员行的绑定按钮在本次页面中为禁用 | 仅观察，不纳入我们的首版设计 |

#### 测试时间线与结果

| 步骤 | 操作及结果 |
| --- | --- |
| A1 创建临时对象 | 用户提交新建成员。列表出现临时成员，角色为成员、状态可用，页面显示创建时间为 2026-10-16 10:26:20。 |
| A2 核对脱敏展示 | 展开临时成员，看到 `ui-revoke-test`，凭据显示为 `ctxdb-***b423a8`，最近使用时间为空。 |
| A3 实际吊销 | 打开吊销确认框；用户确认后，助手点击“确定”。Key 行从列表消失。 |
| A4 刷新 Key 列表 | 刷新后仍显示“没有数据”，没有留下“已吊销”的历史行。临时成员仍保留，状态可用。 |
| A5 成员删除确认 | 打开临时成员的删除确认框，提示永久删除及全部 Key 失效。 |
| A6 核实成员删除 | 用户确认后，助手重新连接时弹窗和临时成员已不存在。刷新成员列表并重新加载页面，临时成员仍不存在，原有三名成员保留；分页按钮均禁用。 |

**界面结论：** 吊销相当于从用户日常管理视图中删除一把凭据；删除成员则移除成员及其管理入口。界面不要求用户理解数据库中的吊销、软删除或审计状态。

#### 没有验证的事项

- 未使用测试 Key 发业务请求，未验证吊销前后 HTTP/MCP 鉴权结果。
- 成员删除前，其唯一测试 Key 已吊销，未验证“删除成员使未吊销 Key 失效”的链路。
- 创建由用户提交，助手没有直接观察创建成功时的完整 Key 弹窗；不能把“明文仅展示一次”写成本次 UI 已实测结论。
- 未测试实际角色变更、成员停用/恢复、管理员的权限边界、Owner 保护规则。
- 未查看阿里服务端数据库或实现，不能从 UI 行消失判断物理删除或历史保留方式。

#### 截图证据

截图保存在资料仓库中，避免依赖 `/tmp` 临时文件。它们包含登录后的成员元信息，分享范围应与该资料仓库一致；不是完整密钥备份。

| 证据 | 内容 |
| --- | --- |
| [E1 新建成员待提交](../../evidence/alibaba-user-management-2026-10-16/contextdb-ui-test-create-confirmation.jpg) | 临时成员名称、成员角色、初始 Key 名称 |
| [E2 吊销确认](../../evidence/alibaba-user-management-2026-10-16/contextdb-ui-test-revoke-confirmation.jpg) | 明确吊销对象及不可恢复提示 |
| [E3 吊销后列表](../../evidence/alibaba-user-management-2026-10-16/contextdb-ui-test-revoked-result.jpg) | 成员保留，Key 列表为空 |
| [E4 删除成员确认](../../evidence/alibaba-user-management-2026-10-16/contextdb-ui-test-delete-confirmation.jpg) | 成员名称及永久删除提示 |
| [E5 删除后列表](../../evidence/alibaba-user-management-2026-10-16/contextdb-ui-test-deleted-result.jpg) | 临时成员消失，原有成员保留 |

#### 官方资料补充

以下资料用于确认公开接口语义，与上述实际 UI 观察分开记录：

- [创建成员](https://help.aliyun.com/zh/rds/developer-reference/api-rdsai-2025-05-07-createcontextdatabasemember)：公开角色包含 owner/admin/member，支持可选签发初始 Key；文档说明明文仅在该次创建响应返回。
- [创建 API Key](https://help.aliyun.com/zh/rds/developer-reference/api-rdsai-2025-05-07-createcontextdatabaseapikey)：请求包含工作空间、成员和 Key 名称。
- [吊销 API Key](https://help.aliyun.com/zh/rds/developer-reference/api-rdsai-2025-05-07-revokecontextdatabaseapikey)：响应包含 `Status=revoked` 和 `RevokedAt`。这些字段不证明其底层采用哪种删除方式。
- [列出 API Key](https://help.aliyun.com/zh/rds/developer-reference/api-rdsai-2025-05-07-listcontextdatabaseapikeys)：列表不返回明文。吊销后从 UI 消失的结论来自 A3/A4，不单凭该接口示例推断。
- [权限管理](https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/permission-management)：阿里还有工作空间角色、用户组和资源授权等机制。本轮不复刻这些能力。
