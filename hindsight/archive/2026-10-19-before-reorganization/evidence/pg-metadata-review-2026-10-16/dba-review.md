# ctxdb_meta 表与索引 DBA 审查

日期：2026-10-16。角色：PG DBA 专家。状态：文档审查完成；与 PG 内核专家已交叉讨论，共同建议见第 8 节。Code-edit permission: DENIED。本报告只读源码及父任务提供的 catalog 快照，不修改代码、数据库、服务或配置。

## 1. 基线与结论

- 代码：`/Users/zhuqingping/Work/Database/Context/.local/worktrees/contextdb-v2-simple-20261016`，HEAD `d5e851b60315b79696e995874e7edc1e9a7bae23`，包含未提交首发简化版改动。完整状态见同目录 `code-baseline.json`。
- 数据库快照：`contextdb_simple_20261016_091155`，采集时间 `2026-10-16T11:22:59.012123`，见 `catalog-snapshot.json`。快照仅作结构与统计证据，不包含完整凭据。
- `ctxdb_meta` 当前有 **8 张表、78 个字段、20 个索引**，包括主键及唯一约束产生的索引。8 张表和 78 个字段均无 COMMENT。
- 对照原生工作空间 schema 的 7 张表：`banks`、`documents`、`chunks`、`memory_units`、`async_operations`、`audit_log`、`alembic_version`；这组样本同样没有 COMMENT，不能据此认为无需文档，也不代表所有原生表均无注释。
- 首要目标应是缩小独享版归属模型、明确各表职责和可靠删除边界、补齐结构说明。不是把 text 全改 varchar，也不是一味减少表数。
- 当前数据量极小，不足以证明索引/类型改动的性能收益；下列性能项均是待验证候选。

## 2. 已同意的原则与当前实现区别

| 已同意原则 | 当前实现 | 落地影响 |
| --- | --- | --- |
| 一实例一数据库，不为共享版重复部署字段 | users、api_keys、operations、admissions、workspaces 都带 instance_id；workspaces 还带 cloud_tenant_id | 修改 SQL、模型和外键后删除重复列；不在体验库手工删列 |
| 部署绑定与版本合并 | instances 和 schema_versions 各一条 | 合并为 deployment_info 等强制单行表；保留实例/租户/格式/元数据版本/安装时间 |
| Key 必须归属成员 | api_keys.user_id 参与鉴权 JOIN、列表与统一启停 | 保留，直接 FK 到 users(user_id) |
| 名称、ID 需要清楚约束 | key_id 已有 32 位十六进制 CHECK，名称已有 1～64 字符 CHECK | 可改显式 varchar，不能宣称因此避免 TOAST；同步补齐其他内部 ID 的格式约束 |
| 管理任务、准入登记、审计不同 | 3 张表各有独立职责 | 不为少一张表强合；先说明“为什么需要”与清理规则 |

单行部署表建议用常量布尔主键加 `CHECK(singleton)` 等方式由数据库约束最多一行；初始化负责保证至少一行。版本号不能兼任单行主键，否则版本升级可并存多行。保留一行事务锁协调现有管理写操作，后续若改细粒度锁必须独立验证成员停用、签 Key、编辑授权的并发一致性。

## 3. 各表应保留、删除、进一步评估的字段

| 表 | 保留核心 | 精简与补充 |
| --- | --- | --- |
| schema_versions / instances | 实例 ID、云租户 ID、metadata_version、format_id、installed_at | 合并单行；name 当前由实例 ID 截断生成，created_by='deployment'，无额外业务意义，可去掉。不能顺便去掉启动归属核对、版本核对、事务锁 |
| workspaces | ID、name、name_key、description、schema_name、state、version、时间 | 删除实例/租户重复列。schema_name 虽可由 ID 推导，仍可保留明确映射和唯一约束，便于运维；不为少一列引入解析依赖 |
| users | user_id、name、status、version、时间 | 删除 instance_id；保留逻辑删除，用户 ID 不复用。成员是否同名属于产品规则，不擅自新增唯一约束 |
| api_keys | key_id、user_id、digest、授权、revoked_at、version、时间 | 删除 instance_id；created_by 总为 instance-admin，审计有操作凭据，可评估去掉。新增脱敏尾缀只服务展示，不保存明文、不参与鉴权 |
| management_operations | operation_id、workspace_id、生命周期代数、幂等信息、state、租约、attempts、错误与时间 | 删除 instance_id；actor_subject 恒为 instance-admin 可精简，但不要连同 idempotency_key/target_id/workspace_version 一起盲删 |
| request_admissions | admission_id、workspace_id、owner_id、origin、state、created_at | 删除 instance_id；owner_id 不是 user_id，而是旧执行者身份。state 和时间用于异常排查，不能把它当可过期心跳 |
| audit_events | 事件 ID、request_id、action、涉及的 user/key/workspace、运维凭据标识、created_at | instance/tenant 可在导出时补充；actor_subject 固定值、result 当前恒为 success，可精简或明确语义。control_key_id 可改成 admin_key_id，但须同步调用链与文档 |

几个不能误删的“看似重复”字段：

- operations.target_id：创建时为空，删除时是 workspace_id，建立“创建在部署级幂等、删除按空间幂等”的不同作用域。若删除此列，必须重新表达唯一键与查询的同等语义，不能直接替换成所有操作都按 workspace_id 幂等。
- operations.workspace_version：防止过时的失败创建任务在后续删除后重新激活空间；不是重复的 UI 版本。
- audit 的对象 ID 不必加指向业务对象的删除级联 FK：审计需要在对象被清理后继续保留归属。不能照搬原生 chunks/documents 的 ON DELETE CASCADE。
- 空 `metadata jsonb` 可按已知扩展需要保留，当前不加 GIN、不用它存授权；预留 JSON 不代表以后无需结构迁移，也不需要每张表预留无用途字段。

### 类型与约束建议

- 内部 ID 保持文本 API 合同，可采用 varchar(32) + 小写十六进制 CHECK；varchar(32) 只限制最大长度，不保证恰为 32 位。没有必要为减少占用同时改 UUID、接口和生成器。
- 部署外部实例/租户 ID 可采用 varchar(128)，不把当前 32/36 字符格式写死为长期协议。实际 85 字符业务 Key 与 32 字符 key_id 完全不同；数据库仍只保存 32 字节 bytea 摘要。
- name varchar(64) 表达上限即可，保留业务非空检查；空格名称目前可通过长度约束，建议服务端统一 trim、拒绝纯空白。
- workspaces.name 在 NFKC 归一化后可能变长，需要重新检查归一后长度；name_key 来自 NFKC + casefold，字符数可扩张，**不能机械改成同样的 varchar(64)**。可继续 text 并统一生成规则，再据规范决定上限。
- version 在 users/api_keys 补 `CHECK(version>0)`；attempts 补非负检查；哈希、租约 token 等内部字段按实际格式补约束。不要增加与合法失败/退避状态矛盾的“终态 lease_token 一定 NULL”约束，当前完成后 token 可以保留。
- 数据库约束与 API 校验职责不同：`workspace_ids` 数组当前 API 检查 ID 格式、去重和最多 1000 个，DB 只检查空/非空。若暂时继续数组，可补容量和无 NULL 约束；逐空间授权落地时不要先做一套随后废弃的数组复杂 CHECK。

## 4. 两张运行表为什么不合并

`management_operations` 是由 API 进程中的 Lifecycle.run 调度的空间创建/删除任务，约每 0.5 秒空闲轮询、60 秒租约、10 秒续租，通过 `FOR UPDATE SKIP LOCKED` 领取。不是 Hindsight 原生 Retain/Reflect 队列。

`request_admissions` 在 REST/MCP 或后台任务提交作用域进入前提交登记，正常结束后删除；异常保留 active/interrupted。没有调度器。删除时结合原生 async_operations 的 pending/processing 状态与这些登记共同排空。它不是审计，也不是任务队列。

合并不会减少登记、续租、锁定、异常恢复机制，只会形成两类空值很多、生命周期相反的行。因此保持职责分开。真正进一步精简必须先改变在线删除需求，例如停服务维护删除；不能先删持久登记再假定 native queue 覆盖同步请求和提交窗口。

当前 operations 3 条终态记录留存符合实现：成功只更新状态，没有清理器。应定义幂等重放窗口、终态保留与审计保留规则；未完成、失败可恢复且仍在支持重试期的任务不能一刀切删除。admissions 永远不能按 TTL 自动删除“旧”记录；需确认旧执行者及其工作会话已停止后运维处理。

**锁语义警告：** 删除入口显式 `FOR UPDATE` 用于关闭准入，不能改为只 `UPDATE state`。普通非键列更新通常取得 FOR NO KEY UPDATE，不会与 FOR KEY SHARE 冲突，可能破坏原保护边界。删除部署列不能顺便取消必要事务、行锁和租约。

## 5. 索引删留清单

以下是设计目标，不是已执行 DDL；现有外键依赖必须先重建。

| 当前索引/约束 | 建议 | 依据及条件 |
| --- | --- | --- |
| instances_pkey、instances(instance_id,cloud_tenant_id) UNIQUE、schema_versions_pkey | 合并为部署表单行主键 | 原独享部署复合唯一是为现有外键服务；切换外键/校验后再去掉 |
| workspaces_pkey | 保留 | 空间路由、管理读取、操作行锁点查 |
| workspaces_schema_name_key | 保留 | Worker/schema→workspace 映射查询及唯一性 |
| workspaces(instance_id,workspace_id) UNIQUE | 重建引用外键后删除 | workspace_id 已全局 PK，复合唯一只是范围 FK 所需 |
| workspaces_name_unique | 替换为 name_key UNIQUE WHERE state<>'deleted' | 保持删除后名称可复用的规则，不改成包含已删的全局唯一 |
| workspaces_instance_page | 替换为 (created_at,workspace_id)，是否部分索引随读取需要决定 | list_workspaces 按此顺序分页并排除 deleted；Worker 另查 active/frozen/deleting，不加每种状态一个索引 |
| users_pkey | 保留 | 鉴权和成员点查 |
| users(instance_id,user_id) UNIQUE | 外键转为 user_id 后删除 | 全局 user_id 主键已足够 |
| users_instance_page | 替换为 (created_at,user_id) WHERE status<>'deleted' | 正常列表已带该条件；同一谓词可服务 count，不为正常页同时保留完整分页索引 |
| api_keys_pkey | 保留 | credential 解析出 key_id，鉴权直接点查；不需要 digest 索引 |
| keys_user_page | 去实例前缀；普通列表改只显示未吊销后，候选 (user_id,created_at,key_id) WHERE revoked_at IS NULL | 当前列表尚未过滤吊销，必须先修改查询合同；FK检查/历史物理清理也可能要完整user_id前缀索引，但首版用户是软删除，没有必要默认两套都加，按物理清理方案再评估 |
| management_operations_pkey | 保留 | UI 查询结果、续租与完成点查 |
| management_operations 幂等 UNIQUE | 去实例前缀，可去固定 actor，但保留 action/target/idempotency 语义 | 创建/删除不同作用域；换一个唯一键必须有并发与重放测试 |
| operations_pending | 保留调度索引职责，候选改为 (created_at,operation_id) WHERE state IN('pending','running') | 当前 (instance,state,lease_until,created_at) 配合 OR 过滤不天然满足全局 created_at 顺序；历史终态不应挤占热索引。新版可堆过滤 lease_until，续租有 HOT 机会，但需代表性任务规模验证，不直接宣布更快 |
| 无对应索引：按 workspace_id 查未完成 operation | 若操作历史很大再评估 (workspace_id) WHERE state IN('pending','running') | delete_workspace 有此查询，但首版每空间任务少；不先加第二个热索引，更不为省一个 SELECT 增加无需求的唯一约束 |
| request_admissions_pkey | 保留 | 完成/异常时 admission_id 精确定位 |
| admissions_workspace | 替换为 workspace_id | 删除排空 EXISTS；不需要按 origin/state 分别索引 |
| audit_events_pkey | 保留 | 稳定事件标识/运维定位 |
| audit_workspace_time | 去实例前缀后是否保留，需明确审计查询 | 代码目前只写无读；workspace为NULL的用户/Key事件，(workspace_id,created_at)不能很好服务全局时间清理/筛选。不直接增加 user/key/action/time 多套索引，有查询再确定 |

不在元数据中增全文、trigram、向量、JSON/数组 GIN 索引。名称包含搜索当前是 strpos(lower(name),lower(q))，常规 name B-tree 不会因此支持任意子串；小目录扫描合理，不能“为了搜索”盲加普通 name 索引。

## 6. 与 Hindsight 原生设计的对比

| 原生样本 | 可以借鉴 | 不应照搬 |
| --- | --- | --- |
| documents/chunks 的复合键与外键 | 同语义字段类型一致、真实对象归属用 FK | 原生一个 schema 可多 Bank；我们的一个 schema 一个 workspace/Bank，不能为对齐加入冗余 bank_id/instance_id |
| memory_units 的 UUID、text、GIN、HNSW、PGroonga | 不定长内容使用 text，索引服务明确查询 | 23 个样本索引用于向量/图/时间检索；meta小目录无相同负载，不能对标数量 |
| async_operations 的领取、状态与部分索引 | 历史与在途分开索引，终态按明确策略清理 | 原生 Worker 任务不替代扩展 schema/Bank 生命周期，也不覆盖同步请求 |
| audit_log 的 started_at 及保留清理 | 日志时间查询和有界保留策略 | 原生 audit_log 是每 Bank 功能审计，配置决定是否记录；管理事件不应丢到某个空间表，删空间后还要可追溯 |
| alembic_version 的独立版本信息 | 有顺序、可核验的迁移历史与启动门禁 | 原生迁移自动管理业务 schema，不会自动迁移 ctxdb_meta；独享元数据无需为了模仿再保留单独版本表 |

原生 `c3e5a7b9d1f4_widen_history_bank_id_to_text.py` 曾修复 history.bank_id 的 varchar(64) 与原生 text 不一致导致迁移问题。它说明“同语义字段约束一致”比“全部改短 varchar”更重要。本轮只规范自研元数据，不能改原生 BankID 类型或原生索引。

原生 `engine/maintenance.py` 已有按保留期分批清理终态 async_operations 和历史表的机制；只处理指定原生表，**不会清 ctxdb_meta**。不能把原生保留配置写成我们的管理幂等有效期已实现。

## 7. 其他优化：注释、写放大、逐空间权限、迁移

### 注释：本轮应明确要求，后续通过迁移实施

为 ctxdb_meta schema、每张表、每个字段及特殊索引/约束补持久 COMMENT，不只在 schema.sql 写 `--`。应说明单位、归属、枚举、NULL含义、保留/清理、版本并发用途、凭据敏感性。特别说明：key_id不是明文、digest不可逆、revoked_at=NULL不等于一定有效（还要看用户/空间）、metadata不是授权入口、准入不能超时自动过期、管理审计提交成功不等于空间任务完成。

示例（RECOMMENDED，未执行）：

```sql
COMMENT ON TABLE ctxdb_meta.request_admissions IS
 '工作空间在途请求/后台提交登记；正常结束删除，异常登记保留；不是任务队列，不得按TTL清理。';
COMMENT ON COLUMN ctxdb_meta.api_keys.digest IS
 '业务API Key的32字节HMAC摘要；不保存明文；验证依赖部署pepper。';
COMMENT ON COLUMN ctxdb_meta.api_keys.revoked_at IS
 '吊销时间，NULL表示未吊销；有效性还取决于所属成员状态、空间状态和授权。';
COMMENT ON INDEX ctxdb_meta.workspaces_name_unique IS
 '未删除工作空间名称规范键唯一；删除后允许复用名称，空间ID不复用。';
```

COMMENT 是 DDL、有锁，应由迁移应用，不在请求路径或随手直接修改运行库。注释不能含密码、Key、真实客户请求内容。

### last_used_at 与准入登记开销

`repository.authenticate(record_use=True)` 当前每次业务 REST/MCP 鉴权均执行 UPDATE last_used_at；同一热 Key 会竞争同一行，生成 WAL/MVCC 版本。现有该列没有索引，具备 HOT 前提之一，HOT并不等于无锁或无WAL。

建议可接受“最近使用时间近似到分钟”后，优先用条件更新，仅当 NULL 或早于窗口才更新（例如60秒，具体窗口待定），减少实际写次数；它不能改变每次新请求的实时吊销/成员状态/权限检查。是否容忍遥测更新失败需明确，不能吞掉鉴权数据库失败并放行。先做简单数据库条件，不默认引入Redis、缓存服务或异步写入队列。

request_admissions 每请求至少 INSERT+DELETE，tiny表也可能高周转。观察 n_dead_tup、autovacuum、WAL、锁等待，必要时针对表调整vacuum；不采用UNLOGGED（崩溃丢屏障）或每请求VACUUM，不未经测量写统一fillfactor/scale_factor常量。

### 逐空间权限：新增关系仅在功能实施时引入

当前数组 + 一个 permission 不能表达 MySQL只读、PG读写。建议候选是 key_workspace_permissions(key_id,workspace_id,permission)，PK(key_id,workspace_id)，FK到两侧；认证已通过key_id定位Key，随后按目标空间点查。all模式仍保存统一权限，不为每个未来空间预创建行；selected模式用显式关系。UI新增默认读写，编辑保留已有权限。

这是候选结构，需与接口/模型整体确认，不是本次数据库既定改造。它多一张有明确业务关系的表，却比授权JSON、数组并行下标、字符串拼接更容易约束和排错。若Key物理清理，可CASCADE删授权关系；删空间优先保留空间tombstone，避免重建同名空间继承旧授权。不为将来的workspace→key反查默认加反向索引，按实际清理/查询需要评估。

### 迁移与保留

当前 bootstrap 只支持首发v1格式且 CREATE TABLE IF NOT EXISTS 不是升级。结构变更需独立、有序、可回滚/恢复的迁移：先查存量长度和约束、建新部署表并复制校验、改代码读取/锁定、转换外键及索引、最后删列/旧表；应用版本与元数据版本一起门禁，不能启动旧程序读新结构。原生 migrations 与 ctxdb_meta migration 分别负责，不能仅靠修改 schema.sql。

全局单行管理锁目前是简单正确的选择；目录写QPS低时不预优化为复杂锁服务。未来如有等待证据再细化成用户/Key行锁和一致锁序。

## 8. 交叉审查共同意见

与 `/root/pg_kernel_meta_review` 交换了代码、索引和约束发现；两方均同意：

1. 先精简独享版模型与重复复合约束；保留真实归属和部署门禁。
2. 版本和部署合并强制单行；实例事务锁的行为必须保留或有等价替换。
3. 管理任务与在途登记不合；准入不使用TTL/UNLOGGED；在线删除锁语义不得弱化。
4. 补全持久注释；对varchar仅作业务约束解释，不承诺性能增益。
5. 索引按真实查询减重；部分索引、续租索引移除、热字段节流均明确条件及验证需求。
6. 采用“已同意原则 / 新建议 / 待验证”区别，不将本轮审查当实施结果。

这不代表用户已经批准全部候选 DDL；逐空间存储形态、保留期、索引具体选择应在实现时确定。

## 9. 验收 SQL 与分阶段落地

阶段一：补注释与结构字典，合并部署信息，去重复字段及其复合外键/索引，字段规范和API校验同步；不混入原生业务表改造。
阶段二：成员/Key UI和逐空间权限完整合同，补尾缀、实时鉴权回归、条件last_used_at更新。
阶段三：按保留规则和代表性数据评估热索引、历史清理、vacuum；没有证据不先上分区、GIN或新服务。

只读验收示例（RECOMMENDED，未执行；在后续实际结构变更后由主任务调整表名）：

```sql
-- 注释覆盖率：应无缺失表或列。
SELECT c.relname AS table_name, a.attname AS column_name,
       obj_description(c.oid,'pg_class') AS table_comment,
       col_description(c.oid,a.attnum) AS column_comment
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped
WHERE n.nspname='ctxdb_meta' AND c.relkind IN('r','p')
  AND (obj_description(c.oid,'pg_class') IS NULL OR col_description(c.oid,a.attnum) IS NULL)
ORDER BY c.relname,a.attnum;

-- 核对实际索引，不以索引数量判定性能。
SELECT tablename,indexname,indexdef FROM pg_indexes
WHERE schemaname='ctxdb_meta' ORDER BY tablename,indexname;

-- 监测周转与HOT，统计不是精确实时行数。
SELECT relname,n_live_tup,n_dead_tup,n_tup_upd,n_tup_hot_upd,
       last_autovacuum,last_autoanalyze
FROM pg_stat_user_tables WHERE schemaname='ctxdb_meta' ORDER BY relname;

-- 当前状态核对：终态历史不代表任务仍在运行。
SELECT action,state,count(*) FROM ctxdb_meta.management_operations GROUP BY action,state;
SELECT workspace_id,origin,state,count(*) FROM ctxdb_meta.request_admissions
GROUP BY workspace_id,origin,state;
```

实现验收必须在独立测试库验证：归属不匹配/多绑定拒绝启动；首次安装/已有库迁移/重入；分页总数与软删除过滤；吊销和删除成员的真实REST/MCP请求；创建/删除重放及并发；API/Worker崩溃后准入保护；旧创建不复活已删除空间；UTF8/空白/归一扩长名称；若改索引，准备代表性历史/活动任务分布验证EXPLAIN和开销，而非拿3条任务证明收益。

## 10. 执行与未验证边界

RUN：读取AGENTS.md、CLAUDE.md及通用审查流程；cat/sed/rg读取schema.sql、repository.py、lifecycle.py、admission.py、tenant.py、models.py、security.py、bootstrap与原生迁移/maintenance代码；读取既有优化文档；Python只读解析catalog快照统计表/列/索引及约束；浏览PG18官方文档核实类型、部分索引、HOT与COMMENT语义；与PG内核专家交叉讨论。以上读取命令退出码0。

NOT RUN：本agent不连接运行数据库，不执行DDL、DML、ANALYZE、VACUUM、EXPLAIN ANALYZE、测试/压力、服务启停、故障注入、迁移、提交或推送。父任务采集的只读catalog不作为本agent独立执行SQL的结果。上列SQL/DDL均为未来建议，未应用。

风险与限制：现有数据约3空间/1成员/1Key，无法评估并发热Key、队列历史增长和vacuum曲线；未发现无效索引，但无实际规模性能结论。单库超级用户可绕过元数据权限，不靠字段/COMMENT/普通GRANT约束其行为；对客户可见PG的高权限账号边界另行处理。

官方参考：
- [PG18字符类型](https://www.postgresql.org/docs/18/datatype-character.html)：text与varchar物理模型相近，varchar上限是约束；不用char补空格。
- [PG18部分索引](https://www.postgresql.org/docs/18/indexes-partial.html)：查询须蕴含索引谓词；不在谓词写随时间变化的now()条件。
- [PG18 HOT](https://www.postgresql.org/docs/18/storage-hot.html)：不修改普通索引引用列且页有空间才可能HOT；降低填充率不是默认答案。
- [PG18 COMMENT](https://www.postgresql.org/docs/18/sql-comment.html)：持久注释支持对象、列、约束与索引；有对象锁，不在请求中执行。
