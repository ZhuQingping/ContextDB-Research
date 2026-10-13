# ContextDB 首期服务化实现任务

开始：2026-10-13 03:57，交付检查完成：06:15（Asia/Shanghai）。用户要求夜间 8 小时，目标窗口截止 11:57；本次在窗口内完成必要实现、本地验证及五类专家复核。生产联调不在夜间自行发布授权内，作为明确的交付风险保留。Goal 在全部交付检查完成后标记 complete。

> 后续范围澄清：新增管理接口仅通过内部 REST 供管控调用，不向用户面直接开放；原生 REST/MCP 接口保持不变，裁剪另行评估。PG 表与新增 API 说明集中到主设计。本文保留前序原型开发历史，本轮不修改源码或运行配置；文档收敛过程见 D23。

## 范围与授权

- 场景：feature-development，安全/持久化风险为 high。
- Code-edit permission: GRANTED。用户明确授权源码实现、测试及设计更新；Night-run permission: GRANTED。
- 源码仓：`/Users/zhuqingping/Work/Database/Context/hindsight`，基线 `a77c1f3412a7b82f36588dffce1a8d7480e99cc7`。
- 文档仓：`/Users/zhuqingping/Work/Database/Context/ContextDB-Research`，设计版本 `74ab76872c3e9c226df7902a17955252156b46d7`。
- 主代理串行集成；开发完成后启动数据库、agent memory、knowledge、Python、注释五类独立只读检视，修复发现，再收集复核结论。不用“多数同意”掩盖未解决缺陷。
- 允许修改：新增 `hindsight-extensions/contextdb-service/` 包、相关扩展说明、定向 `hindsight-api-slim/tests/` 与 `hindsight-system-tests/`；只有证实原生 hook 不足时才最小修改 extensions/API/engine/Worker 边界并记录理由。允许更新研究仓主设计、OpenAPI、独立 PG 设计、问题与验证记录。
- 测试配置补充：允许修改 `.github/workflows/test.yml` 以接入本扩展及黑盒测试，更新独立测试包依赖/锁；不运行远程 CI。单独锁文件中 SDK/MCP/数据库/验证框架版本约束与根 uv.lock 对齐，避免独立解析悄悄引入新主版本。根环境同步的操作偏差见 D17。
- 禁止：无关重构、个人记忆隔离/知识发布、全局 Codex/Claude 配置、商业服务写入、真实客户凭据、已有服务重启、已有 DB 迁移/删除、提交/推送/merge/rebase。保留源码仓既有 `verification/` 和研究仓竞品未跟踪文件。
- 测试：仅新建隔离临时数据库/目录和专用测试端口，使用合成凭据及 stub 模型；不与现有本机服务或其数据混用。

## 交付顺序

| 阶段 | 内容 | 状态 |
|---|---|---|
| P0 | 扩展点、认证、MCP、Worker、测试环境核对；独立 PG 表方案 | DONE；差异见 D1–D8 |
| P1 | 元信息 repository、成员/用户 Key、实例登记、工作空间及生命周期管理 | DONE；边界见 D1、D10、D14、D18、D20 |
| P2 | Tenant/OperationValidator/Http 扩展，业务 REST/MCP 与 Worker 路由和保护 | DONE；真实主链路及权限负例通过 |
| P3 | 单元、PG 集成、真实 API/Worker 黑盒、原生扩展回归 | DONE；最终冻结批次见验收记录 |
| P4 | 五类专家独立检视、修复、复核；人工可读设计及接口更新 | DONE；五类均 scoped ACCEPT / ACCEPT WITH RISKS，无本期未关闭阻塞项；不代表生产上线验收 |

## 验证命令与交付证据

- 扩展定向测试：`uv run pytest hindsight-extensions/contextdb-service/tests/`（环境以实际可运行配置为准，保留完整命令）。
- 原生回归：extensions、MCP routing/filtering、schema/maintenance/Worker 对应测试；新增用户能力须有 published-client 黑盒 story。
- 必须运行项目 `./scripts/hooks/lint.sh`；先阅读脚本范围，避免自动改动无关文件。定向 Ruff/类型检查、`git diff --check`、包入口检查、OpenAPI 验证。
- 保留命令、退出码、失败首因、测试日志位置；区分 RUN、NOT_RUN、RECOMMENDED。临时 DB 不进入提交资产；最终小体积 JUnit/lint 证据经凭据扫描后保留在文档仓，未提交/推送。
- 早间审阅：接口覆盖矩阵、状态/幂等/最后管理员/撤销测试、REST/MCP/Worker schema 隔离、Key 不泄露、既有测试兼容、变更行数与侵入点、专家剩余风险。

## 设计差异与需后续讨论的问题

### D1：用户提到“实例”，原设计管理资源为“工作空间”

本次已实现独享实例的部署登记/校验与查询，不自动创建云 RDS/API/Worker 或新增产品层级。详细 API 合同明确：一实例属于部署中的固定云租户，workspace 仍是唯一 Bank 的产品门面。真实云资源开通由现有管控承担，不将实例登记误称资源开通。

### D2：原生后台上下文跳过外部 Key 认证

`RequestContext.internal` 用于已受理任务，Worker 从任务所属 schema 执行；设计本来不承诺撤销取消在途任务。需测试任务正确携带空间与 Key ID，防止把用户自报 internal/header 当内部权限。内部目的限定身份与后台执行必须区分，不可仅因 internal=True 就允许任意创建/删除 Bank。

### D3：原生 MCP 可配置共享认证 Token

MCP transport 优先使用旧 `MCP_AUTH_TOKEN`，会绕过动态 TenantExtension。ContextDB 模式应启动时拒绝这类配置，而不是把共享 Token 当成员 Key；REST/MCP 权限由同一扩展策略约束。

### D4：扩展没有公开元信息连接池 accessor

HttpExtension 获得 MemoryEngine，ExtensionContext 没有公开 PG pool。短时鉴权/发现通过单个 `repository_for` 适配器复用 `_get_pool`；handler 不写 SQL、不扩散私有依赖。并发测试和数据库检视证明：持锁请求及等待它的管理请求不能共用数据连接池，否则可能占满连接，导致持锁者无法完成。改为同一 RDS PG 的独立 admission/control 连接池，不是新的 MetaPG 组件。生命周期仍调用原生迁移/Bank 方法；公开 pool accessor 及连接数预算需要后续讨论。

### D5：分页草案与项目规范不一致

原草案使用 cursor/page_size，但源码规范要求 limit/offset 和 total。本期新接口采用后者并限制每页 100 条，详细 OpenAPI 需同步更新；不保留尚未上线的旧分页兼容别名。

### D6：Worker 发现与维护任务共用 list_tenants

冻结/删除空间必须被 Worker 发现以排空既有任务，但原生 MaintenanceLoop 也会对同一空间重新提交整理/知识刷新。已在操作 validator 禁止停用空间的新增周期提交，同时允许已经受理的任务完成，并验证两种 Worker 模式；不能只隐藏 Bank 列表就声称排空已解决。

### D7：元信息 bootstrap 与备份边界

全局 `ctxdb_meta` DDL 在部署单 owner 执行，运行副本只校验版本，避免全局 DDL 启动竞争。它不是原生每 Bank 迁移/备份表集合；生产恢复必须恢复同库元信息，不能只还原 Bank 数据后默认凭据还有效。独立 PG 设计与运行说明需列出该边界。

### D8：启动阶段 list_tenants 在连接池之前执行

真实启动黑盒发现：MemoryEngine.initialize 在打开 PG pool 之前调用 list_tenants 做迁移发现；扩展若调用 `_get_pool` 则 initialize → list_tenants → initialize 递归。修复为启动阶段短期 PG 直连、发现后 finally 关闭；运行阶段发现复用 host pool。已补防重入回归用例，真实服务启动及两种 Worker 模式通过。运行阶段的连接池划分按 D4 修正。

### D9：只等待“没有任务”不足以证明 Worker 完成

首轮 SDK retain 使用默认同步路径，后台提交被过于严格的 write-operation 白名单拒绝时，wait_until_settled 也可能看到空队列并通过。已修复白名单，允许 memory.write 的原生整理/图维护/索引维护提交；黑盒改为显式 retain_async=True，并断言返回的 operation_id 确实 completed。两个 Worker 模式均通过。之前的主链路结果只证明记忆写读，不能独立作为后台排队验收证据。

### D10：失效任务恢复与重试语义

管理任务崩溃由过期租约重新领取；执行失败自动退避重试最多 3 次，耗尽后空间 failed、拒绝业务请求。原请求按同幂等值再次提交可由仍有效的管理员重启失败任务，不增加额外 retry API；已成功请求只重放状态。租约 token 不出现在管理响应。相关并发/失败用例已通过；这不是 D20 未知业务执行者的自动恢复承诺。

### D11：删除必须等待 HTTP 在途请求，不能只检查后台队列

同步 retain 与 MCP reflect 都可能仍在执行而原生队列为空。API admission 在整个 HTTP 操作期间持工作空间 KEY SHARE 锁，冻结/删除使用 UPDATE 锁等待退出；两类连接池与数据连接池分开。异步队列提交在取得数据连接前持相同锁，避免排空后又写入新任务；PG 连接丢失必须取消下游操作。锁和连接中断测试使用独立临时 PG，不对现有实例注入故障。

### D12：租约不能跨原生迁移 DDL 持有长事务

实测元信息长事务与 CREATE INDEX CONCURRENTLY 的快照等待形成阻塞。已撤销这种实现：原生迁移保留自身序列化；线程取消后等待线程实际返回，随后检查租约；创建 Bank 和元信息完成分别检查 operation/token。模板排队只在短事务检查租约。不能声称原生 DDL 已具备强租约 fencing，跨进程崩溃和部分 DDL 恢复仍需生产演练。

### D13：knowledge.read 不能附带 Bank profile 和原始 mental model 权限

原生 profile 同时授权审计、LLM trace、原始导出等路径，直接赋予会泄露原始记忆。已收紧为只允许 KB tree/page/search/export；知识页对底层 model 的读取由可信引擎 read_origin 标识，不接受客户 header 自报。非空知识页、原始数据负例、知识 CRUD 和 Worker 自动刷新均补公开 SDK/MCP 测试。

### D14：幂等与状态恢复必须绑定生命周期代次

已修复并测试：并发删除相同请求返回同一 operation；旧失败创建不能在后续失败删除后复活；operation/key-request 的组合外键绑定真实实例、工作空间和成员；Key 请求相同幂等值但不同请求体返回冲突。

### D15：MCP 长会话身份必须逐消息恢复

专家追踪本地 SDK 发现，工具协程会继承 initialize 的 ContextVar，不能代表后续 POST 的身份。已修复为从每条消息的真实 HTTP scope 恢复已认证身份/schema/admission，不接受客户声明；同空间降权和跨空间 session 复用回归均通过。不复用初始 Key 权限。

### D16：删除后 MCP 会话失效的 401 不能直接忽略

早期批次 24 个系统测试中 22 通过、2 个 MCP 并发删除用例失败。后续记录 JSON-RPC method/id、HTTP 状态与成功工具响应时序，确认工具已成功，而删除后的 tools/list 返回 401；据此修正测试分类，没有放宽失效 Key 认证。另补 wrong-id、工具自身 401、isError、答案不符四类负例，防止笼统忽略异常。最终冻结批次全部通过；SDK 可将后续 401 抛给调用者，不能直接重试非幂等写入。

### D17：全仓 lint 的操作偏差

约 05:08，曾误从主仓运行 lint（传绝对脚本路径不会改变脚本工作目录），导致根 `uv sync --frozen` 和 9 个无关前端文件格式化。已向用户说明；逐项核对这些文件最初无改动后，仅用逆向补丁撤回新增格式化，确认无关文件不再出现在 diff。根环境依赖同步已发生，不宣称环境完全未动；关键导入已核对。随后在独立临时 worktree 正确执行 lint 并通过。未重启现有服务、未迁移已有 DB。只读观察本机 9999 未连通，不将其归因于上述操作。

### D18：PG 行锁等待期间过期，不能靠同一句 WHERE 判断租约

数据库专家用真实 PG 复现：SQL 等待行锁前 lease 有效，等待中到期，醒来仍可能执行 UPDATE 并续租。已修复为先锁 owner 绑定、再用第二条语句检查实时 `clock_timestamp()`；renew/complete/fail/defer 与模板短锁均覆盖。补 5 个“先确认 Lock 等待、再等到期”的回归，不用单纯 sleep 推定已进入等待。

### D19：MCP 工具协程与 HTTP 响应协程分离

取消 HTTP 不必然结束长会话内的工具 handler。已跟踪当前消息实际 handler，准入结束先失效、取消并等待它退出；第二次取消也不能提前释放健康 PG 锁。真实两种 Worker × PG 断锁/HTTP transport 中断测试记录 started → cancelled → exited，均发生于放开 LLM hold 前。迁移线程亦补双取消等待回归，不让 shutdown 返回后仍继续迁移。

### D20：分连接断锁窗口需要持久清理屏障

数据库专家确认，metadata session 锁释放早于旧数据事务结束时，其他副本可能误判无任务，再清掉刚晚提交的队列；同步记忆表也不能一概依赖 banks FK 回滚。取消测试不足以证明这个跨进程窗口原子关闭。

选择保守方案：在同库增加第 9 张 `request_admissions` 表，执行前短事务登记并提交，正常退出移除；执行后的异常/未知旧执行者保留。HTTP 和非 HTTP 队列都覆盖，生命周期同时检查无持久记录及无原生任务，才清理 Bank。不新增核心删除 hook、服务或数据库。

偏差与后续问题：中断/崩溃后 DELETE 可能一直等待，记录不按超时清零。需可信维护窗口确认旧 API/Worker 和 PG 工作会话停止，再恢复；本期无客户覆盖接口和自动恢复流程。状态接口提供 waiting_for_admissions/waiting_for_tasks 安全等待码。接受这个可恢复性限制，不把“保守阻止清理”宣传成已实现自动故障恢复。

### D21：明确保留的轻量实现边界

- 工作空间改名只更新管控显示名，底层 Bank 初始标签暂不同步。
- 软删除身份绑定不回收，同一登录身份重新加入需后续显式流程，不能自动继承旧 Key。
- 管理元信息 DDL 是尚未发布的初始版本，不是旧原型原地升级工具。
- Worker HTTP 仅健康/指标/基础状态，不新增用户管理或数据写 RPC；仍须私有监控入口。
- 默认无 MCP event store，工具结果发送到对应 POST 私有流；启用结果重放/正文通知前另验 Key/空间会话绑定。同一有效空间内其他 Key+session ID 可能扰动会话，是后续 session-owner 硬化项，不宣称已支持所有自定义 MCP 能力。

### D22：协议返回“成功”不能代表后端没有异常

原生 MCP 工具可能捕获后端异常，返回 HTTP 200、isError=false、正文 status=error；只依赖 ASGI 抛异常会误删准入屏障。已增加默认 no-op 的零参数故障回调，未知后端异常标记当前请求；REST 500 也保留记录。不向回调传异常、Key 或记忆正文。

knowledge 专家进一步指出，认证撤销竞态产生的 AuthenticationError 属于安全拒绝，不应误标未知执行；已与 OperationValidationError 一起单独分类，保留原响应、不误留屏障。新增纯 mock 分类回归及真实 REST/MCP 入队故障 × 两种 Worker 测试。删除保持 waiting_for_admissions，不能以“队列为空”宣称可安全清理。

### D23：按功能模块重组设计，澄清新增管理 API 与原生接口边界

PG 表设计、16 个新增管理操作的请求/响应/权限集中到主文档；目录按实例/空间、成员、用户 API Key、认证授权组织，再分别说明存储、接口、原生业务/Worker 集成、扩展和验收。用户身份绑定属于成员管理，首把 Key 属于初始化流程；记忆/知识是现有能力，不作为新开发模块。

一度将“新增接口只用 REST”扩大解释为整个产品关闭 MCP。经用户澄清已撤回：只有新增管理接口采用内部 REST、供可信管控后端调用，不向用户面直连开放；原生 REST/MCP 路径与协议保持，是否关闭部分原生接口独立评估、与本特性无关。

本轮只修改文档、OpenAPI 描述和架构图，未修改源码、实际部署配置或历史测试结果；没有执行关闭 MCP。独立 PG 文件保留兼容跳转，不维护第二套表设计。

文档验证：16 个管理操作与 YAML 的 method/path 一致；9 张表、7 个显式索引与源码 DDL 一致；本地文档链接/目录锚点、两张更新图渲染与 diff 检查通过；管理 OpenAPI CLI 校验有效，与实际路由/响应字段的合同测试 1 passed（既有第三方弃用告警）。本轮未复跑全部原型测试，不将文档验证当成新的运行时验收。

### D24：五类专家局部文档复核，不变更首期架构

用户要求已实现版本以最小侵入、尽快上线、简单和人易读为目标，只接受小幅局部修订，架构调整须另行一致。资料、文档、agent memory、PG、Hindsight 开发者五类代理完成只读初审和修订后复核，均接受限定范围修订。

主文档相对此轮送审稿仅 28 行插入、6 行删除，原目录/9 表/16 操作不变；校准配置加载、DELETE 首响应等待、共享写入及 scope 范围、人工恢复/连接预算、原生补丁部署和代理自测/用户未验收边界。源码、DDL、运行配置、权限模型和原始测试未改。报告与证据见[五专家局部复核](contextdb-design-five-expert-review-2026-10-13.md)。

### D25：按实际调用链路删除图中虚构入口

用户指出当前只有 Console → 管理面 → Hindsight 计算节点，以及 Agent → Hindsight 计算节点。部署图移除“内部管理入口”“现有业务入口”两个额外组件，认证图同步命名；管理面直接调用实际挂载路径 `/ext/contextdb/v1`，文档与 OpenAPI 示例不再声称已有额外转发映射。

此轮仅校正文档和图，不新增网关/监听，不修改源码、凭据规则或运行配置。节点仍分别校验管理 Key 与用户 Key，管理请求的来源限制及 HTTPS 仍需部署联调验收。D24 五专家复核的哈希保留为此前版本证据，不用于声称此次图文修订已完成五专家复核。

本轮验证：三张更新图重新生成，部署图预览无额外入口节点；OpenAPI CLI 校验通过，与实际管理路由/响应字段的合同测试 1 passed（既有第三方弃用告警）；研究仓 diff 检查通过。未运行真实服务或生产网络验证。

### D26：明确 audit_events 仅记录管理面管理操作

按用户要求，将主设计和部署图中的泛称“审计”明确为“管理操作审计”：管理面调用新增管理 REST，计算节点写入 ctxdb_meta.audit_events。补充空间、成员、用户 Key 的动作范围、成功受理与后台完成的区别，以及不覆盖实例登记、查询、认证失败或 retain/recall 等业务调用的边界。不新增审计功能、接口或服务，不修改源码和表结构。

## 最终已执行验证

- 扩展单元/PG 集成：175 passed；新鲜冻结扩展环境再次 175 passed，不累加重复用例。
- 新鲜 Python 3.12 冻结系统环境：47 passed，覆盖真实 REST/MCP 与内置/独立 Worker。
- 原生定向回归：41 passed；隔离 worktree 全仓 lint PASS。
- 新增源码与测试 Ruff、format、扩展 ty、两仓 diff 检查、OpenAPI 与 CI YAML 校验通过。
- 命令、接口覆盖、最终原始证据与专家分工统一见[实现验收记录](contextdb-service-verification-2026-10-13.md)，不在这里维护第二套滚动结论。
- 早期 37/8/60/90 等批次只是里程碑；失败日志保留用于追踪 D16、D18–D22，不替代最终冻结结果。
- 隔离 PG 与真实 API/Worker 进程在 fixture finally 中停止；数据目录保留于 pytest 临时目录，不触碰默认本机实例。未提交/推送源码。

## 停止条件

需要真实凭据/商业写入、修改运行中服务或现有数据、改变已确认产品隔离语义时停止相关分支；其他安全的实现/测试继续。验证困难不等于通过；授权不扩大到自动发布。
