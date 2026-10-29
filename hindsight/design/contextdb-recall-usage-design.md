# ContextDB 记忆与知识召回统计设计

状态：已实现，当前通过[PR #54](https://github.com/RSIXDB/hindsight/pull/54)送审，尚未合入。更新日期：2026-10-29。当前代码版本：RSIXDB/hindsight `9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5`；完整实现合同见[代码仓DESIGN第7章](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/DESIGN.md#7-记忆与知识召回统计)。第10章保留最初设计的源码依据，第12～14章为历史阶段验收，第15章记录当前结果；完整性能矩阵仍未完成。

功能跟踪：[RSIXDB/hindsight Issue #38](https://github.com/RSIXDB/hindsight/issues/38)。

## 1. 目标与设计选择

为每条记忆和每个知识页记录召回次数 `recall_count`、最后召回时间 `last_recalled_at`，用于观察内容使用情况。统计表示外部直接检索已在服务端生成可用的最终结果，不证明响应已送达、用户已经阅读或模型实际采用。

采用插件采集、进程内有界聚合、异步批量写入的方式。每个工作空间新增一张插件统计表，复用既有扩展建表、Bank 清理及备份恢复接口；原生引擎、内容表、REST/MCP 结果格式和 SDK 保持兼容。统计是最终一致的使用指标，允许故障时漏计，不作为无损计费或审计依据。

首版只覆盖外部直接调用的记忆 Recall 和知识搜索，不增加内容热度排序、阅读次数、用户维度明细或历史补算。统计故障不能改变业务调用的成功结果。

### 1.1 为什么使用插件表

| 选择 | 收益 | 维护成本 |
| --- | --- | --- |
| 给原生 `memory_units`、`knowledge_pages` 增加字段 | 对象查询和物理删除直观；适配列表/详情返回合同后可随内容返回，减少UI额外请求 | 需要维护原生表迁移，并核对记忆归档、恢复、备份及导入等路径 |
| 新增插件统计表 | 统计结构和写入职责由插件维护；不频繁更新内容所在行 | 需要关联查询，并补齐单对象删除清理 |

选择独立表主要是为了隔离扩展职责和降低社区升级成本，不表示读写一定更快。仅加列不会自动让接口返回统计，原生Store、响应模型和字段读取权限仍需适配。独立表也可通过组合查询随内容返回，但需要改变既有读取合同或新增组合接口。增加原表字段并不必然改变 `updated_at`，两种结构也都可以异步批量更新；不能将性能收益全部归因于新增表。

### 1.2 现有时间字段与统计的区别

`S` 表示 `ctxdb_meta.workspaces.schema_name` 指定的工作空间 schema，通常为 `ctxdb_ws_<bank_id>`。

| 对象字段 | 存储位置或计算规则 | 含义 |
| --- | --- | --- |
| 记忆 `updated_at` | `S.memory_units.updated_at` | 内容及相关属性的写入时间水位 |
| 知识页详情 `timestamp` | `S.mental_models.last_refreshed_at`，为空时回退到 `S.knowledge_pages.created_at` | 接口计算字段；知识目录表没有 `timestamp` 列 |
| Mental Model `last_refreshed_at` | `S.mental_models.last_refreshed_at` | 最近成功刷新完成时间；无内容变化的成功刷新及直接编辑内容也会推进它 |
| 知识目录 `updated_at` | `S.knowledge_pages.updated_at` | 名称、父目录、排序等目录元数据的更新时间 |

知识页通过 `mental_model_id` 和 `bank_id` 关联 Mental Model，正文由后者保存。知识树中的页面时间取 `last_refreshed_at`，没有详情接口的创建时间回退；知识搜索结果的 `updated_at` 也来自模型刷新时间。

召回统计不得修改上述字段，避免将访问行为误判为内容变化或刷新完成。

## 2. 统计口径

记忆 Recall 与知识搜索是不同调用。调用记忆 Recall 不会因此自动累计知识页统计，知识页读取也不能等同于记忆 Recall。

| 行为 | 统计规则 |
| --- | --- |
| 成功的外部记忆 Recall | 完成钩子取得最终 `results` 后，每个不同记忆 ID 加 1 |
| 成功的外部知识搜索 | 成功结果可解析后，每个不同知识页 ID 加 1 |
| 同一请求中被多路检索找到、重复出现 | 同一对象只计一次 |
| 检索候选、重排后未返回的对象 | 不计入 |
| Recall 附带的 chunks、实体、`source_facts` | 不单独计入，也不因此给来源记忆加次数 |
| 知识搜索后读取页面全文，或直接查看详情、浏览目录、导出 | 不计入；搜索与后续读取不重复累计 |
| Worker consolidation合并/去重、Reflect内部检索、知识页及Mental Model后台生成/刷新 | 次数和最后召回时间均不更新；客户手动触发的后台刷新也不计入 |
| 采集点之前认证、授权或检索失败，以及知识搜索工具错误 | 不计入；采集之后失败按第 3.1 节不撤销 |
| 成功但最终结果为空 | 不新增统计记录 |

只有客户通过REST/MCP直接发起的Recall或知识搜索更新统计。是否为直接调用由入口及内部上下文判断，不取决于人工/定时发起或Key身份；客户定时任务通过REST/MCP直接Recall仍计数。只读、读写和管理员调用采用相同口径，权限范围沿用原有认证与对象可见性规则。用户重新执行一次请求属于一次新调用；首版不实现跨请求重试去重。

当前 MCP 的“多 Bank 模式”表示每次调用可以显式选择一个 Bank，不表示一次工具调用搜索多个工作空间。支持 `/mcp/{bank_id}` 和根 MCP 指定 `bank_id` 两种模式；每次调用只绑定一个已认证工作空间。记忆统计统一使用完成钩子，MCP 包装层不再重复累计 Recall。

例如：一次 Recall 最终返回 A、B，A/B 各加 1；另一次知识搜索返回 X、Y，X/Y 各加 1。随后读取 X 全文，不再增加 X 的召回次数。

## 3. 采集入口与写入时机

### 3.1 从请求完成到数据库更新

1. 请求通过现有认证、授权，插件记录根操作种类及工作空间 UUID、bank_id、已验证的 schema，不保存查询文本、正文或 Key。
2. 直接 Recall 在 `on_recall_complete(success=True)` 中取得最终记忆 ID；REST 知识搜索收齐可解析的成功 JSON 后取得页面 ID；MCP 知识搜索取得可解析的成功工具结果后取得页面 ID。
3. 在上述采集点生成 UTC 事件时间、按本次调用去重，直接合并到内存聚合器。采集失败只记录诊断，不影响原有业务结果。
4. 后台批量更新 PG。`last_recalled_at` 保存事件时间，不使用后台执行 SQL 的时间。

不等待 ASGI `send` 或客户端确认，不维护“暂存命中、等待交付、再次发布”的状态机。采集点之前失败或取消不计数；已经采集后，序列化失败、发送失败或断连都不撤销计数。不同入口以各自能够取得最终对象集合的采集点为准，不能声称能覆盖所有“引擎已成功但尚未暴露结果”的边界。

### 3.2 插件接入点

| 入口 | 实现方式 |
| --- | --- |
| 记忆 Recall | `on_recall_complete` 检查直接 Recall 根操作及 `success`，将最终记忆 ID 合并到聚合器；REST/MCP 共用 |
| REST 知识搜索 | 无原生完成钩子；插件 ASGI 层只观察该接口的成功 JSON，不等待发送确认 |
| MCP 知识搜索 | 复用插件工具包装，在工具成功结果中提取最终页面 ID；不再观察其 HTTP/SSE 响应 |

原生引擎会等待 `on_recall_complete`，因此该钩子只能做 ID 整理和内存操作。不得在其中执行 SQL、网络请求，或为每条命中创建后台任务。认证钩子只有请求意图，没有最终结果，不能用于计数。

请求上下文明确区分直接 Recall、直接知识搜索及其他根操作；记忆完成钩子同时要求request_context.internal=false。根调用退出时将UsageCall失活，继承上下文的迟到后台任务不能计数。不能仅凭 `request_context.internal` 判断，否则可能把 Reflect 内部调用也算入。上下文在 `finally` 中清理，并发工具调用及内部子调用之间不得串用。后台事件只含冻结的归属和 ID，不持有请求对象。框架如果以子任务执行引擎调用，应验证它能继承根操作标记；无需从子任务向父任务回传可变暂存集合。

当前插件位于原生 GZip 中间件外层，不能假定观察到未压缩 JSON。仅对 REST 知识搜索移除传给内层应用的 `Accept-Encoding`，沿用现有小接口的 identity 请求策略；该接口的原生 JSON 内容不变，其他接口仍正常压缩。代理仍可在插件外层压缩最终响应。

观察器边转发边限量复制该接口的 JSON 块，收齐后解析，初始上限 512 KiB。超限、无法解析、意外压缩或其他不支持编码时只放弃该次统计并记录原因，不修改业务响应，不新增 gzip 解压器，不复用配置响应的投影/失败替换逻辑。该端点取消应用压缩带来的网络开销须纳入第 7 章压测。

MCP 适配处理两种注册模式产生的对象结果或 JSON 文本。当前插件拿到的 FastMCP `ToolResult` 只有 `content`、`structured_content`、`meta`，不能访问不存在的 `is_error`。先排除 `ToolError` 等调用异常，再解包并检查原生 `{"error": ...}` 业务错误；仅在实际拿到协议层 `CallToolResult` 时才使用其 `isError` 字段。不能仅以 HTTP 200 判定工具成功。

## 4. 表结构与写入规则

### 4.1 工作空间统计表

统计表位于各工作空间 schema 内，不放在 `public`，也不增加管理元数据表。以下以 `ctxdb_ws_example` 为命名示例，DDL 由插件部署升级路径生成并执行，不是手工生产部署命令。

```sql
CREATE TABLE ctxdb_ws_example.ctxdb_usage_stats (
    bank_id varchar(54) NOT NULL,
    object_type text NOT NULL
        CHECK (object_type IN ('memory', 'knowledge_page')),
    object_id varchar(64) NOT NULL CHECK (length(object_id) > 0),
    recall_count bigint NOT NULL CHECK (recall_count > 0),
    last_recalled_at timestamptz NOT NULL,
    PRIMARY KEY (bank_id, object_type, object_id)
);
```

| 字段 | 约束与用途 |
| --- | --- |
| `bank_id` | 业务寻址及原生BankScopedTable生命周期清理所需的 Bank 标识 |
| `object_type` | 区分记忆与知识页，不统计目录或独立 Mental Model |
| `object_id` | 记忆保存规范化 UUID 字符串；知识页保存 `knowledge_pages.id`，不是 `mental_models.id` |
| `recall_count` | 从本次启用且未重置的统计历史开始累计，缺记录不表示启用前从未被使用 |
| `last_recalled_at` | 已记录事件的最大时间，使用带时区时间类型 |

空间身份不再逐行保存，但同一次刷盘的内存事件必须绑定发生时的工作空间身份、bank_id 和 schema。身份来自ctxdb_meta.workspaces，经请求认证取得，当前为secrets.token_hex(16)生成的32位随机十六进制标识，不是标准UUID v4。批量写入前的目录事务校验保留，避免旧事件落入同名新空间；不为每个对象新增JOIN或目录查询。表、字段与约束补齐简洁英文 COMMENT。首版只建主键，不为次数、时间建立排序索引。

不设置到 `memory_units` 的级联外键：记忆失效会从有效表移入归档，级联删除会错误地丢失可恢复记忆的统计。通用对象字段也不能用一个普通外键同时引用记忆和知识页。统计表不建立跨 schema 外键；工作空间归属由插件验证，整个 Bank 的清理由扩展登记负责。

### 4.2 批量累计

每批按主键聚合 `delta_count` 和 `max_event_time`，使用一条批量 `INSERT ... ON CONFLICT DO UPDATE`：

```text
recall_count     = 已有 recall_count + delta_count
last_recalled_at = GREATEST(已有 last_recalled_at, max_event_time)
```

使用数据库原子增量，不先查次数再覆盖，保证多进程并发累计不会丢更新。参数采用绑定值，schema 只能来自已验证的工作空间记录，不能拼接用户输入。

每批在同一短事务内按 UUID 读取并对工作空间行加 `FOR SHARE` 锁，确认其仍为 active 且 bank_id/schema 一致，再写统计表。固定顺序为管理目录行、统计行；不同对象按主键排序。删除状态更新不能越过该事务，旧 UUID 的迟到批次在同名重建后也无法写入新空间。这是普通短事务校验，不增加新的删除调度或业务执行屏障。

每批只校验空间归属，不重新加载全部命中正文。对象在响应完成后被删除时，迟到事件可能形成短暂统计残留，由第 6 章清理；统计查询始终先确认对象存在和可见。

### 4.3 失败与准确性

首版保持一张统计表，不增加持久事件队列或批次回执表。每批增量只尝试提交一次，采用以下规则：

- 明确失败并回滚时，放弃该批并记录丢弃事件量，不保留重试批次或重新合并在途增量。
- 连接中断、超时等导致提交结果不确定时，也不重放增量，单独记录“不确定批次”；原事务可能已提交，也可能造成漏计。
- 失败后采用一个有上限的进程级冷却时间暂缓后续刷盘，避免数据库不可用时持续打满连接池；新事件仍可进入有界缓冲，容量满后按既定规则丢弃。冷却不代表重试原批次。
- 缓冲溢出、进程异常退出、写入失败或响应解析失败都可能漏计，分别记录数量和原因。不能将失败统计伪装为零丢失。
- 正常运行、无上述故障且所有批次刷盘后，未删除、未清空、未恢复重置对象的计数，必须与当前统计历史内已采集的最终命中次数严格一致。

只有在需求升级为可靠重试或无损计数时，才重新评估事务内批次回执或持久事件记录；数据库 UPSERT 本身不能消除客户端重试带来的重复增量。

## 5. 聚合器与查询

### 5.1 有界异步聚合

每个 API 进程维护一个聚合器，由 HTTP 扩展的 `on_startup/on_shutdown` 唯一创建、关闭，Validator、ASGI、MCP 共用。纯 Worker 不启动这项直接召回统计任务，四个扩展也不能各建一份。初始参数如下，作为压测起点，调度参数采用插件内部常量，仅另增5.3节的插件总开关：

| 项目 | 初始设计 |
| --- | --- |
| 刷盘触发 | 每 1 秒，或累计 500 个不同对象 |
| 单批上限 | 500 个不同对象 |
| 缓冲上限 | 10,000 个不同对象，含待写和正在写的数据 |
| 数据库并发 | 每进程一个后台任务，最多占用一个现有连接池连接 |
| 连接与事务预算 | 连接获取最多 100 ms；刷盘和清理单批总预算各 1 秒，锁与语句超时不超过剩余预算 |
| 退出刷新 | 最多等待 5 秒，未完成量纳入丢弃记录 |

同一对象的事件合并为一个计数增量和最大时间。后台 I/O 期间不阻塞请求聚合；每轮冻结当前有限键集合，按空间拆成最多500行的批次连续处理，批间让出事件循环，不为每个空间或批次再等一秒。批次脱离活动缓冲后，新事件进入下一轮；失败冷却仍优先于后续批次。清理调度加入0～3秒抖动；刷盘按1秒或500对象触发，不承诺多进程刷盘去重。缓冲满时丢弃无法容纳的新对象事件，已聚合对象仍可更新；记录丢弃事件数，不能无限创建队列或阻塞召回等待空间。

连接池获取及 SQL 使用短超时。连续失败时增加冷却时间、最多 30 秒，成功后恢复正常节奏；同类错误限频记录。指标包括待写对象数、最老事件等待时间、成功刷盘量、丢弃事件量、提交不确定量及清理进度；复用现有日志/指标设施，不记录正文或凭据。

### 5.2 统计读取与权限

插件提供只读REST接口 `GET /ext/contextdb/v1/workspaces/{bank_id}/usage?object_type=memory|knowledge_page&ids=<id>`，沿用目标空间及内容读取权限：memory对应memory.read，knowledge_page对应knowledge.read；管理员、获授权的只读及读写业务Key均可调用，不新增权限项或业务登录。`ids`是重复参数，1～100个同种对象；响应包含bank_id、object_type和items[{object_id,recall_count,last_recalled_at}]，不要求或返回workspace_id。每个请求只认证一次，复用得到的空间UUID/schema，不按对象重复鉴权或另查管理员目录。

当前权限模型为工作空间加操作scope；查询标签不是独立标签ACL。原生内容和统计使用同一授权模型，不额外新增标签权限。匿名/无效/吊销Key或禁用用户为401；无空间读取权限、空间不存在/非active或缺少读取scope为403；参数错误400。已授权空间内不存在或已删除的对象不在items中，现存对象无记录才返回0/null；缺表或PG查询失败返回503，不能伪造0。关闭时已授权读取返回404 usage_disabled。

刷新只是重新GET，继续验证当前授权，不增加次数或推进时间、不强制刷盘。刷盘处理已采集事件，不重新鉴权客户Key，仍校验空间身份。其他13项管理操作及现有UI登录保持管理员边界，管理员身份能力接口不向业务Key开放。

不向原生Recall响应同步查询统计，不改变原生SDK或新增usage MCP工具。统计查询在短事务中核对对象存在及归属；归档核对复用Store，一次100条归档对象最多100次读取，远程PG可能触及1秒预算返回503。UI批量异步展示并说明统计延迟，不能声称完整历史次数。

### 5.3 插件总开关与UI能力识别

| 配置 | 默认值 | 作用与要求 |
| --- | --- | --- |
| `CONTEXTDB_RECALL_USAGE_ENABLED` | `false` | API插件唯一统计开关，仅接受小写 `true` / `false`；修改后重启API/UI，并刷新已打开页面 |
| 部署intent的 `recall_usage_enabled` | `false` | 严格JSON布尔值；Agent render据此生成api.env，启用时设为 `true`，不是字符串 `"true"` |
| `capabilities.recall_usage` | 由API返回 | UI读取的能力字段，不是可配置变量；未加载插件、缺字段、关闭或读取失败时隐藏统计 |

不增加独立UI统计开关。关闭时停止采集、刷盘、统计GC和知识响应观察，UI不显示字段或刷新按钮，也不请求usage；既有统计保留，重新开启继续累计，不补算关闭期间。统计GET沿用空间及内容读取权限：管理员、获授权的只读/读写业务Key均可读；刷新只重新GET，不要求写权限，不计数或强制刷盘。匿名/无效Key为401，无目标空间读取权限为403；关闭时已授权请求为404 `usage_disabled`。UI仍仅支持管理员登录。

能力通过插件管理员身份接口读取，UI只依据明确的recall_usage=true展示，不额外检查role；管理员Key仍只保存在UI服务端。原生模式不探测插件，产品身份切换或卸载时取消旧请求并屏蔽迟到结果。能力是初始化快照，不轮询或热更新。缺插件时扩展REST接口不存在，原生功能沿用社区行为。

### 5.4 旧版统计表的受控升级

1. 备份数据库、当前API/UI产物、部署配置及秘密文件；停止新业务访问，等待已接受请求、Worker任务和统计刷盘结束，再停止API/Worker/UI。`--offline`不会替操作方完成停服或排空。
2. 使用匹配版本的API和插件。原生schema若需要版本升级，先按该版本部署流程完成；下面的命令只创建/升级插件统计表，不迁移原生内容表或public业务表。
3. 在新版代码仓根目录，用原部署的api.env加载数据库连接与实例身份，再执行：

```bash
# 示例部署目录；替换为原实例的私有目录，保留原配置及秘密文件。
(
  set -eu
  export CONTEXTDB_DEPLOY_DIR='/srv/contextdb'
  set -a
  . "$CONTEXTDB_DEPLOY_DIR/api.env"
  set +a
  export PYTHON_DOTENV_DISABLED=1
  export PYTHONPATH="$PWD/hindsight-extensions/contextdb-service:$PWD/hindsight-api-slim"
  "${CONTEXTDB_PYTHON:-./.venv/bin/python}" -m hindsight_ext_contextdb upgrade-usage --offline \
    --directory "$CONTEXTDB_DEPLOY_DIR" \
    --admin-key-file "$CONTEXTDB_DEPLOY_DIR/admin-key.json"
)
```

`--directory`读取原api-secrets.json中的pepper，不会代替加载api.env；`--admin-key-file`使用既有管理员凭据。不要重新生成实例身份、pepper、UI密码或API Key。

| 升级前状态 | 处理结果 |
| --- | --- |
| 已有工作空间，没有统计表 | 在登记空间schema补建ctxdb_usage_stats；原记忆/知识及管理数据保留 |
| 早期统计表包含workspace_id | 校验主键和全部行的空间身份/Bank后去掉冗余列，保留次数和时间 |
| 已是当前结构 | 可以重复执行，既有统计保持 |
| 身份不匹配、异常主键或空间状态不允许 | 中止并报告；不合并异代数据、不清空统计 |

4. 在原部署配置中启用 `CONTEXTDB_RECALL_USAGE_ENABLED=true`；采用Agent render时同步设置intent的 `recall_usage_enabled: true`，按原部署流程生成配置，复用秘密文件。启动匹配的API/Worker/UI并刷新页面，验证原数据、原凭据、REST/MCP召回及统计展示。

新空间创建时自动provision插件表；既有空间必须显式升级，重复执行init/migrate不等于upgrade-usage。升级不会补算历史召回：现存对象无统计记录时为0/null，启用后开始累计。普通升级不执行reset-usage，后者用于规定的内容恢复场景，会清空统计。

升级按空间分别提交，不保证整实例原子性。中途失败时保持停服，检查原因后重跑；已经完成的空间可重复处理。需要止损时可关闭统计并保留数据；若回退到依赖旧统计表结构的代码，需使用与旧版本匹配的数据库备份，不提供自动降级DDL。

### 5.5 最小使用示例

前提：统计已启用，目标工作空间已经创建，并有可召回的记忆或知识页。使用有该空间读取权限的Key即可；下例不要求写权限。命令需要Bash、curl和jq，查询内容应替换为实际数据中的主题。

```bash
export API_URL='http://127.0.0.1:8891'  # 替换为自己的服务地址
export BANK_ID='example'                # 已存在的bank_id
export API_KEY='<已有的管理员或业务Key>'

# 直接Recall：最终返回的记忆，每次调用每对象计一次。
RECALL_RESPONSE="$(curl --fail-with-body -sS \
  "$API_URL/v1/default/banks/$BANK_ID/memories/recall" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  --data '{"query":"What database does our project use?","types":["world","observation"],"budget":"low","max_tokens":1024}')"
printf '%s\n' "$RECALL_RESPONSE" | jq '.results[] | {id,text}'
MEMORY_ID="$(printf '%s' "$RECALL_RESPONSE" | jq -er '.results[0].id')"

# 仅在上一条成功取得ID后执行。只读GET，不增加次数、不强制刷盘。
curl --fail-with-body -sS -G \
  "$API_URL/ext/contextdb/v1/workspaces/$BANK_ID/usage" \
  -H "Authorization: Bearer $API_KEY" \
  --data-urlencode 'object_type=memory' --data-urlencode "ids=$MEMORY_ID" | jq .
```

返回包含 `bank_id`、`object_type` 和 `items[{object_id,recall_count,last_recalled_at}]`。统计异步落库，第一次GET可能仍为0/null或旧值，稍后重新GET即可，不要为了等统计而重复Recall。最终结果为空时不会产生统计，应先调整查询并确认内容存在。最多100个ID一批，使用重复的 `ids` 参数。

知识页使用同一方式：

```bash
SEARCH_RESPONSE="$(curl --fail-with-body -sS -G \
  "$API_URL/v1/default/banks/$BANK_ID/knowledge-base/search" \
  -H "Authorization: Bearer $API_KEY" --data-urlencode 'q=database' --data-urlencode 'limit=5')"
printf '%s\n' "$SEARCH_RESPONSE" | jq '.results[] | {id,name}'
PAGE_ID="$(printf '%s' "$SEARCH_RESPONSE" | jq -er '.results[0].id')"

# 仅在成功取得页面ID后执行；使用page_id，不使用mental_model_id。
curl --fail-with-body -sS -G \
  "$API_URL/ext/contextdb/v1/workspaces/$BANK_ID/usage" \
  -H "Authorization: Bearer $API_KEY" \
  --data-urlencode 'object_type=knowledge_page' --data-urlencode "ids=$PAGE_ID" | jq .
```

MCP的 `recall` / `search_knowledge_base` 使用同一统计口径，没有新增usage MCP工具；统计查询使用上述REST接口。consolidation、Reflect内部检索和知识页后台生成/刷新均不计入，次数和最后召回时间都保持原值。UI在记忆表格、记忆详情及知识页详情显示统计；知识目录不逐页请求，当前页最多100个记忆一次批量GET。异常退出可丢失尚未提交的内存增量，指标不用于无损计费或审计。

## 6. 删除、失效与恢复

| 场景 | 统计处理 |
| --- | --- |
| 记忆内容编辑 | 保留同一 ID 的统计；不因编辑重新计数 |
| 记忆失效，移入 `invalidated_memory_units` | 保留统计，失效期间不再产生正常 Recall 命中 |
| 失效记忆恢复为相同 ID | 继续累计原次数；恢复动作本身不计数 |
| 记忆永久删除、文档删除或重导入导致旧记忆消失 | 后台清理旧 ID；新生成的 ID 从零开始 |
| 删除知识页、删除其模型或删除含页面的目录子树 | 后台清理所有已消失页面的统计；不能只清理父目录 ID |
| 知识页重命名、移动或正文刷新，页面 ID 保持不变 | 保留统计；同名新页面使用新 ID，不能继承 |
| 按事实类型清空部分记忆 | 后台核对并清理已删除对象；不误删其他类型或可恢复归档的统计 |
| 清空整个 Bank | `extra_bank_tables()` 登记 `delete_with_bank=True`，清除已落盘统计；迟到事件按单对象残留清理。要求清空后立即无统计残留时，先停业务并排空统计任务 |
| 删除工作空间 | 统计表随所属 schema 一起删除 |
| 删除后同名重建工作空间 | 使用新 UUID、空统计表；旧缓冲事件丢弃 |

### 6.1 单对象后台清理

业务删除立即生效，统计物理残留允许最终清理。首版只使用已有后台任务做小批次轮转，不增加清理调度器或另一个长任务：

- 每进程每 10 秒至多处理一个清理批次，加 0～3 秒抖动；每批只访问一个工作空间、最多 20 个统计对象，总预算 1 秒。
- 工作空间目录按现有分页接口每页最多 32 条轮转，只保留有界页缓存和当前位置；不全量枚举空间，也不为每个空间常驻一个任务或无界游标集合。
- 对象游标只属于当前 workspace_id。跨批保留该空间的续查位置，进入时固定本轮统计主键上界，扫完后才推进目录；切换空间重置对象游标，不能把 A 的游标套用到 B。新插入不能无限延长当前空间的一轮巡查，已越过的主键在下一轮重查。
- 每次先处理一轮有限的到期刷盘，再允许一个到期清理批次；清理批次结束释放连接。过载或刷盘持续积压时暂停清理并暴露积压，容量恢复后续查，不能无条件承诺清理完成时间。
- 仅在事务提交成功后推进最后已核实的主键；接近预算时停止新增核对并提交已确认进度。SQL 超时、取消或序列化冲突则回滚整批并退避，游标不前进。缺表、schema消失或权限损坏等结构性故障记录后跳过当前空间本轮巡查，避免饿死后续健康空间；下一轮仍会重查。跨页、跨空间及巡查结束后循环重查，避免迟到事件或新插入的小主键永久漏扫。

记忆核对复用 Store 的 `live_memory_ids` 批量查询；未命中的 ID 使用 `get_archived_memory` 确认可恢复性。单批 20 个对象将归档查询限制在最多 20 次，不另建“500 条批次中的归档续查”状态。该接口会读取正文等字段，仍是实际后台成本，不是轻量批量存在性查询。

有效与归档检查使用同一个短 `REPEATABLE READ` 事务及同一连接，避免失效/恢复移动期间两次查询观察不同快照。每批验证目录身份后，用已有 `bank_target(bank_id, schema_name=registered_schema)` 包围 Store 调用，并在 `finally` 恢复上下文。当前 Store 会读取原生 schema ContextVar，单传 `fq_table`、连接或 `search_path` 不够，后台任务不得继承上一个请求或空间的定位。

只有有效集合与归档均不存在的记忆才能清理，未核实或读取失败时保留统计。不在插件散布原生记忆表 SQL，也不为统计扩展 Store 接口。知识页按 ID、bank_id、`kind='page'` 批量核对，依赖封装在插件存储适配模块。

清理与增量写入采用相同的空间 UUID 校验及锁顺序。P 个 API 进程可能重复巡查；抖动只能错峰，不能去重，总负载随进程数增加，须纳入压测。首版接受有界重复，不增加 leader、租约或分布式游标。清理收敛以迟到事件停止、PG 可用和调度容量恢复为前提；仅在对象再次被读取时惰性清理无法覆盖永不再访问的残留，因此仍需周期清理。

### 6.2 备份与恢复

表通过 `extra_bank_tables()` 登记 `include_in_backup=True`、`delete_with_bank=True`，建表通过 `provision_bank_tables()` 执行。新空间沿现有 `context.run_migration(schema)` 路径在原生迁移后创建统计表。

已有空间先按服务版本升级步骤准备原生schema，再停业务并排空API/Worker，执行插件 `upgrade-usage --offline`，按登记目录每页32条仅补本插件表。该命令不迁移原生内容表，也不替代原生版本升级。`service.sh init` / `python -m hindsight_ext_contextdb migrate` 只迁移管理元数据，不等于统计升级。默认原生 `run-db-migration` 可能迁移base schema（通常public），不能原样代用。统计provision只接受登记且归属匹配的creating/active工作空间，拒绝public、ctxdb_meta及未登记名称。

按第5.4节加载原部署环境，设置CONTEXTDB_DEPLOY_DIR；reset另需设置BANK_ID，在同版插件环境执行：

```bash
python -m hindsight_ext_contextdb upgrade-usage --offline \
  --directory "$CONTEXTDB_DEPLOY_DIR" \
  --admin-key-file "$CONTEXTDB_DEPLOY_DIR/admin-key.json"
```

命令复用CONTEXTBASE/HINDSIGHT数据库配置别名及现有管理员鉴权；`--directory`加载持久化pepper。`--offline`是操作者声明已完成停服排空，不会自行停止服务或证明执行者停止。请求不执行DDL，不改变管理六表及元数据版本。

恢复前停止业务入口，等待 API/Worker 工作结束，排空并停止统计任务；恢复后重启时缓冲为空。恢复规则按工具实际能力区分：

| 恢复方式 | 统计规则与必须执行的步骤 |
| --- | --- |
| 含 `ctxdb_meta` 的整库一致性备份恢复 | UUID、schema 和业务数据共同恢复，可以保留同一快照统计；开放前核对身份及表结构 |
| 原生单 schema 恢复、业务内容导入 | 先准备目标 schema/统计表；恢复后、开放业务前清空目标统计表，从零开始，即使 bank_id 或 UUID 看起来相同也不例外 |
| 没有统计表文件的旧备份 | 目标统计表已创建且登记时，原生恢复先清空后跳过缺失文件，结果从零开始 |

原生单 schema 备份清单没有 ContextDB UUID，恢复命令只做结构校验及数据复制，不提供身份核对或上述恢复后清零。恢复后执行以下插件命令清空目标统计表，包括导入的其他Bank行；必须在开放入口前成功完成，失败则保留停服状态，不修改原生恢复内核。

```bash
python -m hindsight_ext_contextdb reset-usage --offline \
  --directory "$CONTEXTDB_DEPLOY_DIR" \
  --admin-key-file "$CONTEXTDB_DEPLOY_DIR/admin-key.json" \
  --bank-id "$BANK_ID"
```

只有完整、身份一致的快照才能保留统计。要求精确备份切点时先排空内存统计；不增加绑定清单、自动身份改写或在线恢复协议。回退到旧快照后次数也会回退，不代表整个服务历史的单调累计。既有“删除前停止新访问、等待已接受工作结束”的规格约束不变。

## 7. 性能影响与验收目标

请求路径只增加最终 ID 的整理、去重和内存聚合，开销约为最终返回对象数 O(K)，不等待 PG。知识搜索还有有界 JSON 解析开销，以及该小接口取消应用 gzip 后的网络增量，不能宣称完全没有延迟影响。后台写入仍与召回竞争数据库 CPU、I/O、连接池和 WAL 资源，独立表不能消除这些成本。

例如每秒 1,000 次请求、每次返回 20 个对象，会产生每秒 20,000 次命中观察。热点对象在缓冲中合并，行更新量可明显下降；若全部是不同对象，仍接近每秒 20,000 行增量写入。500 行满批约需每秒 40 批，多进程的部分批次会额外增加事务数。该计算是负载示例，不是已测容量。

初期不对次数和时间建索引，减少更新时的索引维护；未修改索引列且页内空间充足时，PG 才可能采用 HOT 更新。统计表仍需正常 autovacuum，并观察死元组和表膨胀。

压测使用相同数据、模型替身、并发、数据库及进程数，对比关闭统计与启用统计：

| 项目 | 必测范围 |
| --- | --- |
| 最终结果量 | 0、10、50；记忆 Recall 再覆盖 100，知识搜索遵守原生上限 |
| 结果分布 | 高度热点、均匀分散、大量永久删除及大量可恢复归档；清理不得误删或饿死 |
| 访问方式 | REST、MCP，单进程和多进程 |
| 数据库压力 | 正常、连接池紧张、网络往返变慢、写入变慢、短暂不可用；归档逐条读取和多进程重复巡查成本 |
| 传输成本 | 知识搜索取消应用 gzip 前后，响应大小、耗时和代理压缩行为；其他接口仍正常压缩 |
| 指标 | 请求 P50/P95/P99、吞吐、插件 CPU/内存、池等待、WAL、锁等待、死元组、统计延迟/丢弃及清理积压 |

初始验收目标：正常目标负载下，P95/P99 增幅各不超过 5%，吞吐下降不超过 3%；无缓冲丢弃或不确定批次，99% 的事件在 5 秒内可查询。先按这些目标实测再调整批量参数，不将它们写为当前性能承诺。故障压测允许漏计，但召回不能因统计故障失败，资源占用必须有界。

## 8. 实施范围

实现集中在 `hindsight-extensions/contextdb-service/`，使用现有工具链，不新增依赖或另一套任务框架。

| 模块 | 实现职责 |
| --- | --- |
| `validator.py` | 在成功完成钩子直接聚合 Recall 最终记忆 ID |
| `transport.py`、`mcp.py` | 根调用标记、知识搜索结果观察及错误识别；不维护交付确认状态 |
| 小型 `usage.py` | 类型化事件、有界聚合、后台刷盘及清理调度 |
| 小型 `usage_repository.py` | 插件表 DDL、增量 SQL、统计查询及生命周期核对 |
| `tenant.py` | 登记表，受控 provision；不启动另一份后台任务 |
| HTTP 扩展生命周期 | 唯一创建、关闭聚合器和后台任务，其余入口只复用 |
| `usage_admin.py`与现有CLI | 既有空间按目录创建或离线升级插件表，单schema恢复后停服清零及验收 |
| 插件 HTTP及自研UI | 按空间及内容读取权限批量读取；UI沿用管理员登录和服务端Key，不修改原生召回返回合同 |

不替换原生引擎方法，不新增全局响应缓存，不重复认证与权限 SQL。后台清理有界复用已有 Store 接口，知识目录 SQL 的依赖集中封装并用回归约束。REST/MCP 适配必须保留团队品牌、身份、代理、安全 Host/Origin、配置别名及 SEC-01 已有保护。

## 9. 验证用例

下列为验收清单，实际覆盖与边界见第12章，不将每行所有场景笼统记为通过。测试复用插件Python和真实API/临时PG系统故事，模型显式替身，不操作用户数据库或运行中的服务；后台阶段未包含UI，新增UI验证见第13章。

| 编号 | 场景 | 必须断言 |
| --- | --- | --- |
| T01 | REST Recall 返回 A/B，多路候选还含 C | A/B 各加 1，C 无记录，附带 source_facts 不额外计数 |
| T02 | REST/MCP 同等结果，重复 ID、空结果 | 口径一致；一次调用每对象最多 1；空结果无记录 |
| T03 | 只读、读写、管理员；跨空间、无效和吊销 Key | 成功调用正常计数，拒绝调用不计数；统计不扩大对象可见性 |
| T04 | 知识搜索 X/Y，随后读取 X、浏览目录或导出 | X/Y 各加 1，后续读取和目录访问不加 |
| T05 | 单 Bank URL、根 MCP 指定 Bank；工具异常及 JSON 错误 | 每次唯一归属且不重复计数；按真实 ToolResult 类型判错，不把 MM ID 当页面 ID |
| T06 | consolidation、Reflect内部检索、知识页手动/自动后台刷新及嵌套Recall | 先建立非零统计，再确认内部检索实际命中并等待后台完成；跨刷盘窗口检查次数和时间均不变，根调用上下文不串用 |
| T07 | 采集前失败/取消；采集后序列化、发送失败或断连 | 采集前不计数；已经采集不撤销，不以交付确认作为门槛 |
| T08 | 知识搜索分块 JSON、identity 策略、工具包装、超限或意外编码 | 只对知识搜索移除内层 Accept-Encoding，其他接口 gzip 保留；解析失败业务不受影响且有诊断 |
| T09 | 乱序事件、多进程并发、写入期间新事件到达 | 次数为成功事件之和；时间取最大值；无先读后写覆盖或重复发布 |
| T10 | 明确回滚、提交确认丢失、持续 PG 故障 | 每批只提交一次，不重放增量；失败量及不确定量准确；冷却有效且业务正常 |
| T11 | 缓冲满、进程退出或强制终止 | 容量包含在途批次；正常限时刷新；异常丢失符合已声明边界 |
| T12 | 记忆编辑、失效、恢复；无请求上下文的后台任务连续清理两个空间 | 同 ID 统计保留；RR 快照避免移动误判；bank_target 正确设置/恢复，不访问 public 或上一空间；内容时间字段不变 |
| T13 | 单条/文档删除、重导入、部分类型清空 | 残留最终清理；新 ID 从零开始；没有未核实就删除统计 |
| T14 | 删除知识页、模型及目录子树；重命名和移动 | 所有消失页面最终清理；存续页面保留统计 |
| T15 | 全量 Bank 清空、空间删除、同名重建及迟到批次 | 空间删除无整表残留；Bank 清空的迟到对象最终清理；新 UUID 不继承；空间校验与写入之间不存在重绑定窗口 |
| T16 | 非超级用户新库、重复升级、creating/active 空间补表 | DDL 幂等，按登记目录迁移；重复 init 不冒充升级；public/ctxdb_meta 不建统计表或 public 业务表 |
| T17 | 整库一致恢复、原生单 schema 恢复、旧备份及新 UUID 导入 | 只有完整身份一致恢复保留统计；其他路径开放前清零；先预建表，无恢复前缓冲污染 |
| T18 | 统计批量查询、无记录、缺表、PG 失败、不可见和已删除对象 | 无记录才返回 0；不可用返回 503；批量上限及资源可见性有效，无逐条统计查询 |
| T19 | 性能矩阵、持续写入、大空间增长、慢 PG、多进程及高归档比例 | 达到第 7 章目标；GC 预算有效，大空间续查且不饿死后续空间；B 的小 ID 不被 A 的游标跳过；过载积压可见且恢复后续查 |
| T20 | 多扩展共用、启动失败、正常退出及纯 Worker 启动 | 每 API 进程只有一个聚合器/后台任务，生命周期关闭正确；纯 Worker 不创建统计任务 |

## 10. 核对依据

设计依托当前已有扩展能力；实现时按同版源码复核，不将钩子的存在当作统计已落地：

- [Recall 完成钩子及结果结构](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-api-slim/hindsight_api/extensions/operation_validator.py)：`RecallResult`、`on_recall_complete`。
- [原生引擎调用与知识实现](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-api-slim/hindsight_api/engine/memory_engine.py)：Recall 等待完成钩子；知识搜索没有相应后置钩子；全量 Bank 清理读取扩展表登记。
- [原生接口时间字段](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-api-slim/hindsight_api/api/http.py)：`_knowledge_page_response`、`_knowledge_node_model`、Mental Model 时间定义。
- [插件表初始化及登记](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-api-slim/hindsight_api/extensions/tenant.py)：`provision_bank_tables`、`extra_bank_tables`。
- [记忆存储接口](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-api-slim/hindsight_api/engine/memories/base.py)：有效集合、归档及恢复语义。
- [工作空间生命周期](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py)及 [schema 删除](https://github.com/RSIXDB/hindsight/blob/cdd067170c050780634335f62cfed59f6c73eec1/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py)：先清 Bank，再删除所属 schema 与管理目录。
- [PostgreSQL UPSERT](https://www.postgresql.org/docs/18/sql-insert.html)、[HOT 更新条件](https://www.postgresql.org/docs/18/storage-hot.html)：原子累计及更新成本依据。
- [PostgreSQL 行锁](https://www.postgresql.org/docs/18/explicit-locking.html)、[事务隔离](https://www.postgresql.org/docs/18/transaction-iso.html)：空间行短锁和有效/归档一致快照依据。

## 11. 专家检视决定

Hindsight、PG/DBA、代码设计三个独立只读检视均基于第 10 章源码及官方 PG 文档，未运行 SQL、服务、故障注入或性能测试。按以下决定收敛后进入实现，运行验收仍按第 9 章执行：

| 检视项 | 最终决定 | 对应章节 |
| --- | --- | --- |
| 写入时机过于依赖交付确认 | 以服务端生成最终结果为准，完成钩子直接聚合，取消两阶段发布 | 2、3 |
| MCP 模式与错误类型假设不准确 | 单次单空间；按真实 ToolResult 与原生错误内容识别，不假设存在 is_error | 2、3.2 |
| 知识搜索压缩适配过重 | 只对该小接口请求 identity JSON，限制观察大小，不建设解压或响应投影框架 | 3.2、7 |
| 统计任务与清理状态过多 | 每 API 进程一个任务，单批提交一次；清理每批最多 20 对象、分页轮转及时间预算 | 4.3、5.1、6.1 |
| Store 后台空间上下文可能错误 | 核验目录后显式使用 bank_target；同连接 RR 快照检查有效和归档，未核实不清理 | 6.1 |
| 升级和恢复被误当作原生已有能力 | 登记空间逐一升级；缺表不可用；整库一致恢复保留，单 schema 恢复开放前清零 | 5.2、6.2 |
| 统计表主键、短锁与一致快照是否过度 | 保留Bank/对象主键、事件身份及目录短锁、一致快照；后续收敛删除持久workspace_id（见5.4），不增加持久队列、leader或删除屏障 | 4、5.4、6 |


## 12. 后台实现与验证（2026-10-28阶段记录）

实现目录：`hindsight/integration/rsixdb-contextdb/hindsight-extensions/contextdb-service/`。后台阶段代码和测试限于自研插件；保留团队安全策略，没有新增原生内核差异、依赖、生产配置变量或元数据版本。既有Embedding节流工作区修改保持原样。本阶段验证时尚未提交；当前提交/送审状态见本文开头及第15章，Issue #38进展使用评论记录。

| 验收项 | 实际覆盖与边界 |
| --- | --- |
| T01～T06 | 真实SDK异步retain/后台完成、REST、两种MCP、三类调用者、跨空间拒绝、知识搜索与详情/刷新、Reflect不计数；Python补重复ID及根上下文隔离 |
| T07～T11 | Python覆盖过期上下文、发送失败、编码/解析失败、并发累计、失败不重放、冷却、容量包含在途及正常退出；未做真实断网提交确认丢失、进程强杀注入 |
| T12～T15 | 真实API验证失效/恢复及空间同名重建；PG/Store替身验证归档RR快照、永久删除/子树残留、20对象清理、跨空间游标及结构故障轮转；未逐个原生删除/重导入入口做端到端统计断言 |
| T16 | 真实临时PG重复补表、creating/active和非法schema保护、成功CLI加载目录秘密；插件全量保留非超级用户新库/public无业务表部署验证 |
| T17 | 原生备份/恢复COPY+manifest仅插件表往返、旧备份缺文件及恢复后清零；整库一致性快照、完整内容及跨实例恢复未验 |
| T18 | 管理员批量查询、0/null、缺表503、参数400、业务Key拒绝、对象存在性与上限；远程PG高归档读取预算未验 |
| T19 | 自动静默2000对象、10空间小批次及真实PG调度；本机双Worker性能样例见下文。完整性能矩阵未完成 |
| T20 | 单实例聚合器生命周期和两个Worker模式；独立Worker未承载HTTP直接采集任务 |

插件Python全量517通过，双Worker非UI系统85通过，原生相关回归91通过，Key合同1通过；插件Ruff/format/ty及OpenAPI检查通过。独立Hindsight/Python、PG/DBA及代码设计/测试检视发现的有限轮调度、异常编码诊断、坏空间巡查公平性和恢复证据问题已修复复核，无剩余Must fix。

仓库lint未通过：开始HEAD原生HTTP已有F841；knip@5未通过：开始HEAD已有未使用开发依赖contextbase-client。两者单独保留证据，没有扩大修复或绕过钩子；不能声称所有仓库门禁通过。

本机性能采用一个API进程、临时PG和模型替身，3轮×200请求、每轮20预热、并发4。嵌入Worker的Recall P95/P99为15.99/17.85→13.63/15.41ms，知识搜索8.37/8.75→7.98/8.59ms；独立Worker的Recall18.35/25.48→14.33/19.44ms，知识9.66/9.99→7.91/8.12ms。样例未观察到退化，不能将更快归因为统计提速。两组统计次数660与实际预热及测量调用严格对应。6页知识响应由gzip556 B变为identity1622 B，增加1066 B，不能隐去传输成本。

详细命令、结果与未验项统一保存在代码仓 `docs/contextdb-management/VALIDATION.md` 第19章，设计落地见DESIGN第7章，检视闭环见CODE-REVIEW第21章。临时证据 `/tmp/contextdb-issue38-kzbjg8na/` 包含日志、补丁和源码指纹；性能最终插件树指纹为 `12f4e4e8692fad75b4486dadcd1ac3252bc518f6739b9453a38608c79610dda7`。未操作现有服务和用户数据库；未验生产UI/浏览器、远程PG/真实MaaS、生产长期容量及完整灾备恢复。


## 13. UI接入（2026-10-28阶段记录）

在记忆表格文本下、记忆详情及知识页详情展示召回次数和最后召回时间。知识树不逐页查询，关系图/时间线通过记忆详情查看。当前沿用已落地插件表；本轮不切换到原表，不新增原生内核修改。

共享组件在Control Plane自研contextdb目录，三个原页面只提供Bank/ID与挂载点。记忆当前页最多100 ID一次批量GET；详情各查询一个ID。正文原有请求完成后先显示，统计在effect中异步加载；不轮询、不全量扫描、不逐行查询，不将统计读取拼入原生正文查询。统计增加额外网络、认证与PG负载，不能承诺总耗时不变，但完整的统计等待不会串到正文显示前。

UI通过固定代理及服务端管理员Key读取usage，Key不进入浏览器。该阶段原有“业务Key不可读”限制已由第5.2节的内容读取权限合同替代；当前已授权只读/读写业务Key可通过REST查询，UI不新增业务用户登录。响应做身份/类型/对象集合、非负安全整数及时间有效性检查。空间/对象/产品切换取消旧请求并同步屏蔽旧值，迟到响应无效。加载、有效0/null、遗漏对象及失败区分；失败不影响正文，可仅GET重试。时间跟随UI locale和原浏览器时区，按钮手动刷新统计快照；查看统计/正文不增加次数。

原表方案的收益与成本见1.1节，不将“减少原生侵入”等同于“性能更高”。本轮没有做原表与独立表的同负载A/B性能比较；UI验证使用独立临时API/PG/生产构建和Chrome，不覆盖现有运行中的UI产物。最新实际结果统一见代码仓VALIDATION第20章。

本轮UI全量783项、双Worker生产UI故事2项及JUnit完整性门禁通过，TypeScript/ESLint/格式及Key合同通过。Chrome在临时环境验证真实字段、加载/超时/重试、中英文日期及主题，单对象正常统计请求样例约11～20ms；不作为生产性能承诺。仓库原有原生HTTP F841、knip未使用开发依赖仍阻断对应全仓检查，未纳入本次修复。开发验收时未替换现有部署；2026-10-28 15:38（Asia/Shanghai）另经用户授权部署到本机9991，沿用数据库、UI密码及API Key。原密码、新旧会话和业务Key验证通过，Chrome确认字段可见，统计代理与API响应一致；详细证据见目标仓VALIDATION第21章。


## 14. 开关与身份字段收敛落地（2026-10-28阶段记录）

按第5.3～5.4节完成插件开关、后端能力驱动UI和统计表收敛。`CONTEXTDB_RECALL_USAGE_ENABLED`默认false，仅接受小写true/false；部署intent使用JSON布尔。关闭不创建统计采集/刷盘/GC任务，不处理知识响应，不发UI统计请求；原有业务和数据保留。旧服务缺少能力字段时UI隐藏统计，原生模式不探测。

表及usage响应删除workspace_id，表继续保留Bank/对象主键；内部事件身份及同事务目录核验保持。现有含身份列的表通过显式离线upgrade-usage转换，次数和时间保留；异代数据、异常结构拒绝，不自动合并。迁移逐空间提交，后续失败需保持离线、处理后重跑；不得直接打开新版本开关代替升级。单schema恢复仍须reset-usage。能力为初始化快照，修改开关后重启API/UI并刷新旧页面，不提供在线推送。

本轮实际结果：插件Python540、UI799、ContextDB系统89（包含双Worker生产UI2项）、原生相关91、Key合同1通过；独立生产构建、manifest及源码匹配，生产UI专用JUnit门禁通过。Chrome分别在临时开启/关闭实例验证记忆与知识页，关闭时内容保留、无统计字段和刷新动作，网络记录usage请求为0。两组独立后端/PG和UI/测试完整性检视均无Must fix或Should fix。本轮新增原生UI接入仅layout挂载自研Provider，无新增原生Python修改。

全仓lint仍被基线原生HTTP F841阻断，knip仍被基线contextbase-client未使用开发依赖阻断；未修改依赖或绕过检查。未验远程PG、真实MaaS、生产P95/P99/容量、Node24/Linux、Docker、完整灾备和设备矩阵。该阶段验收未替换用户服务或迁移用户数据库；该阶段记录不声明当前运行版本。

同版设计、检视和完整验收分别见代码仓DESIGN第7.6节、CODE-REVIEW第23章、VALIDATION第22章。证据由`/tmp/contextdb-usage-switch-path`定位，包含任务开始快照、增量补丁、原始日志、产物指纹、Chrome截图及独立检视；当时验收基于edea57c上的工作区快照，当前送审代码身份见第15章。


## 15. 当前实现、验收与截图（2026-10-29）

实现通过[PR #54](https://github.com/RSIXDB/hindsight/pull/54)送审，源码与交付文档固定到 `9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5`。读取/刷新沿用空间和内容权限；管理接口/UI登录仍仅管理员。无新增原生Python、SDK或MCP统计工具。第12～14章的提交、部署及测试数字仅描述对应阶段，不能作为当前状态。

- [部署参数、升级及最小示例](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/hindsight-extensions/contextdb-service/README.md#召回使用统计issue-38)。
- [完整设计](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/DESIGN.md#7-记忆与知识召回统计)、[完整检视](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/CODE-REVIEW.md)、[验收记录](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/VALIDATION.md)。

当前统计口径补证：插件Python全量573通过，双Worker召回统计故事12通过，确认直接REST/单Bank/root MCP计数，consolidation、Reflect内部检索及知识页手动/自动后台刷新命中后次数和时间不变。真实临时PG/API、显式模型替身，未操作现有服务或用户库；Ruff/格式通过，完整lint仍有既有原生F841。

此前完整特性验收为UI801、全部系统89（含双Worker生产UI2项）、原生相关91及Key合同1通过；它们是此前版本的完整回归，本轮文档与排除口径补证未重新构建UI或验收Chrome，不将12项子集与89项相加。具体命令、版本和未验环境见代码仓VALIDATION第26～27章。异常退出未提交统计可能丢失；远程PG容量、完整灾备和真实故障注入未验。

截图保留各自验收版本，来自代码仓VALIDATION §20.2、§22.2；展示的是召回次数和最后召回时间，不能当作内容更新时间。本文引用同一份图片，不另行复制。

| 场景 | 图片 |
| --- | --- |
| 记忆表格 | [记忆召回统计](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/screenshots/recall-usage-memory.jpg) |
| 知识页 | [知识页召回统计](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/screenshots/recall-usage-knowledge.jpg) |
| 开启 | [启用统计](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/screenshots/recall-usage-enabled.jpg) |
| 关闭 | [关闭统计](https://github.com/RSIXDB/hindsight/blob/9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5/docs/contextdb-management/screenshots/recall-usage-disabled.jpg) |
