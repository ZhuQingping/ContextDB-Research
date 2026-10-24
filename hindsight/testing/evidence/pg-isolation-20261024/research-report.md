# ContextBase 底层 PostgreSQL 权限与数据隔离调研

日期：2026-10-24（Asia/Shanghai）。源码：`9fb57bc0470e7784d8766fdfb19d837f603b9638`；本次分析对象是来源工作区当前代码，不将此前RSIXDB PR #20的验证当作本版本云端部署验收。

证据标签：`[实测·华为]`指本次124.71.227.243:5432操作；`[实测·本地]`指独立临时PG测试；`[源码]`指代码直接可见行为；`[推断/建议]`指方案判断。术语：PG角色是数据库账号/权限集合；ACL是对象授权清单；schema是库内对象命名空间；owner是能修改或删除对象的所有者；RLS是逐行过滤读写的规则；search_path是未写schema时的对象查找顺序；JWT是带签名的身份凭证。

## 1. 执行摘要

1. [建议] 采用方案2：每个ContextBase独享部署使用专用PG库和专用普通账号，API/Worker运行时不用root。
2. [实测·华为] 普通服务账号与独立客户账号互相连接对方库均被42501拒绝；二者可连接supabase_db，但读auth.users被拒。
3. [源码] 工作空间/API Key权限由插件认证和schema路由实现；API Key不是PG角色，没有逐Key SET ROLE或逐Key RLS。
4. [实测·华为] 同一服务账号切换search_path后仍能显式查询自己另一schema；schema分开不等于对该账号隔离。
5. [建议] 客户只走REST/MCP/UI时，保留当前应用隔离；不要为模仿Supabase引入全套PG角色切换。
6. [实测·华为] 客户需要SQL时优先独立业务库；共库边界脚本的26类攻击全部42501，但必须保持schema/object归属及授权安全。
7. [实测·华为] root无临时成员身份时，仍能用全新连接进入服务库、读取服务所有且FORCE RLS/false策略的表。
8. [结论] 方案2能隔离普通账号、缩小凭据泄漏影响；不能把服务数据对本实例root保密。
9. [建议] 如客户持有该RDS root，且必须防客户读改服务数据，应改成平台控制的独立实例；额外schema/REVOKE/RLS不能兑现该要求。
10. [实测·华为] pg_trgm未指定schema时在本流程落public；默认表权限不覆盖旧表/serial序列；USAGE不提供建表能力。
11. [实测] 华为供给/SQL边界、Supabase新测试表RLS已验证；本地边界套件41通过；没有在华为实例部署完整ContextBase API/Worker/UI。
12. [实测·华为] 全部临时库、角色和Supabase测试schema已清理；root原成员关系恢复，终态5库/32角色。

## 2. 实例实测：Supabase权限与隔离

### 2.1 实测范围与授权

最初进程无PGPASSWORD，随后用户提供密码才开始云端操作。密码仅由父进程传给连接环境/驱动，不写入脚本或报告。只读快照在读取既有文档后执行，因此不声称满足提示词“先测后读”的防锚定顺序；所有关键结论另用独立反例重测。

用户随后明确允许：仅对本轮新建*_cx角色临时授予/撤销root成员身份；允许在Supabase相关库新增测试表和插删测试数据。本轮只在supabase_db创建独立`iso_20261024_rls_cx` schema及新表/策略，未修改原有表、策略、库ACL、平台角色属性/授权或root密码。postgres仅作只读快照及CREATE ROLE/CREATE DATABASE等集群供给命令的连接入口，没有修改postgres库内对象/ACL。未启用dblink/postgres_fdw、未终止平台连接。

原始证据：[只读快照](raw/cloud-snapshot-1.log)、[各库元数据](raw/cloud-readonly.json)、[供给与边界](raw/cloud-validation.json)、[全新连接与26攻击](raw/cloud-followup.json)、[文档SQL](raw/cloud-doc-sql.json)。日志SQL密码已替换为`<generated-secret>`，密码hash只输出20字符前缀。

### 2.2 实例及角色全景

[实测·华为] 2026-10-24 10:29:39 +08快照：PostgreSQL18.6/x86_64；5库、32角色；ssl=on；max_connections=96；96个available extensions。root为NOSUPERUSER，但CREATEDB/CREATEROLE/REPLICATION；rolbypassrls=false。rdsAdmin为超级用户。不是仅凭“非超级用户”即可视root为普通账号。

| 类别 | 角色及实际特征 | 隔离含义 |
| --- | --- | --- |
| 云管控 | rdsAdmin、rdsBackup、rdsMetric、rdsRepl | 属平台信任域，不作为客户身份 |
| API权限角色 | anon、authenticated、service_role、supabase_realtime_admin | 前三者不可LOGIN，service_role有BYPASSRLS |
| 组件连接角色 | rds_supabase_authenticator/auth_admin/storage_admin/functions_admin/admin/postgres | LOGIN及ownership按组件划分 |
| 管理角色 | root、postgres | root直接/间接拥有多项平台权限；postgres无密码，不能据LOGIN属性断言可远程认证 |
| 系统预定义角色 | pg_monitor等 | 单独审计成员关系，不能仅检查五NO |

[实测·华为] root拥有anon/authenticated/service_role及多个rds_supabase角色的INHERIT/SET成员身份；还拥有pg_monitor、pg_maintain、pg_checkpoint、pg_signal_backend、pg_create_subscription等。完整35条成员关系含ADMIN/INHERIT/SET三项选项在快照中。所有rolvaliduntil为空；有密码的角色本次前缀为SCRAM-SHA-256$4096；root读取pg_authid和pg_shadow成功，pg_hba_file_rules返回42501。

[官方规则+实测解释] BYPASSRLS等角色属性不能笼统解释为沿INHERIT自动传递；PG角色权限、SET ROLE能力和云厂商额外权限须分别判断。本次root新连接绕过false策略已实测，具体内核提权路径未追踪。华为文档明确列出root在多场景被额外提权，但未据该清单推导每一项绕过机制。[PG角色属性](https://www.postgresql.org/docs/18/role-attributes.html)、[华为root权限说明](https://support.huaweicloud.com/productdesc-rds-pg/rds_02_0012.html)。

### 2.3 数据库、schema和RLS

[实测·华为] supabase_db、_supabase、postgres的数据库owner均rdsAdmin。三库ACL中的PUBLIC均有CONNECT/TEMP；不能写成“只有显式授予的组件才能连接”。不拥有CREATE和不能读表，是另外两道检查。

| 库 | 用户表数（r/p） | schema/owner示例 | RLS |
| --- | ---: | --- | --- |
| supabase_db | 50 | auth→auth_admin；storage→storage_admin；realtime/_realtime→supabase_admin；public→pg_database_owner；extensions/vault等→rdsAdmin | 27张启用RLS；pg_policies为0条 |
| _supabase | 43 | _analytics/_supavisor→rdsAdmin，public→root | 0张启用RLS，0策略 |
| postgres | 0 | public→pg_database_owner | 无业务表 |

RLS启用却无policy时，普通角色在无其他绕过前提下默认看不到行；不能据“启用27张”断言所有组件/租户均受保护，也不能据0策略断言RLS无作用。[PG RLS](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)。本次没有读取既有用户行内容；表权限探针及新建表反例与真实既有业务行读取应区分。

[实测·华为] root对supabase_db的11个非系统schema均显示CREATE；在postgres.public上CREATE=false。三库均未安装dblink/postgres_fdw；这只能证明当前检查的两类通道未安装，不证明root不能自行建立其他外联通道。

### 2.4 组件连接快照

| 组件 | 本次可见连接角色/库 | 证据与限制 |
| --- | --- | --- |
| PostgREST14.8 | rds_supabase_authenticator→supabase_db，2连接 | pg_stat_activity实际application_name |
| Storage | rds_supabase_storage_admin→supabase_db，1连接 | 角色映射；本次无明确application_name |
| Realtime | root→supabase_db，5个supabase_mt_realtime+2个cluster_node_realtime | 明确平台进程仍用root |
| Supavisor | root→_supabase，20个supavisor_meta+2个cluster_node_supavisor | 另有15个无application_name的root连接，不强行全部归因 |
| Auth/GoTrue | 本次未见对应连接 | schema归属/角色存在不能替代活跃进程证据 |
| 监控/后台 | rdsMetric/rdsAdmin | pg_stat_activity快照 |

[推断/建议] root轮换仍需考虑平台组件；为ContextBase换成专用账号可消除它对root密码的运行时依赖，但不代表整个Supabase平台已与root解耦。

### 2.5 两个必须区分的实测结果

**普通账号能隔离。** 专用服务账号和biz账号均是五NO，拥有不同库。`CONNECT bizdb AS service`和`CONNECT ctxdb AS biz`均42501。二者连接supabase_db成功，但`SELECT 1 FROM auth.users LIMIT 1`均42501；这里隔离数据的直接依据是schema/表授权，而不是连接被拒。

**本实例root不能靠该方案隔离。** followup证据：

```sql
-- 临时角色均撤销后，pg_auth_members中root对两个临时角色返回0行。
-- 重新以root建立全新连接（不是复用撤权前旧连接）：
SELECT session_user, current_user, current_database();
SELECT * FROM meta_cx.users;
-- 服务owner已执行：ENABLE ROW LEVEL SECURITY、FORCE ROW LEVEL SECURITY；
-- nobody_cx策略USING(false) WITH CHECK(false)。
```

[实测·华为] root新连接成功；返回`protected`。普通service owner同一表查询为空集。不能把数据库ownership和撤销成员身份写成“root物理上进不来”。

### 2.6 Supabase新测试表RLS对照

本轮新schema内两条合成行：alice/alpha、bob/beta；给anon/authenticated/service_role表级访问，开启FORCE RLS，给authenticated策略：`tenant_id=current_setting('request.jwt.claim.sub',true)`。每次使用事务内SET LOCAL ROLE/claim，最后ROLLBACK，未改角色成员关系。

| 当前角色/上下文 | 实测SELECT | 越权写入 |
| --- | --- | --- |
| anon，claim=alice | 0行 | 未测 |
| authenticated，claim=alice | 仅alice | 插入bob行42501 |
| authenticated，claim=bob | 仅bob | 未测 |
| service_role | alice+bob | 本角色有BYPASSRLS；未做写入扩展测试 |
| root | alice+bob | 对自建表DISABLE RLS成功 |

此为数据库机制验证，不是实际PostgREST HTTP/JWT验签端到端。普通客户端不能自行指定可信claim；如果把能够执行任意SQL的连接交给客户，不能把可自行设置的自定义GUC当作不可伪造的身份。

## 3. Hindsight / ContextBase源码分析

### 3.1 谁以哪个PG账号执行

| 路径 | 代码依据 | 当前含义 |
| --- | --- | --- |
| 写池/API/Worker主连接 | [hindsight-api-slim/hindsight_api/config.py:153](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/config.py#L153)；[hindsight-api-slim/hindsight_api/engine/memory_engine.py:5973](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L5973) | DATABASE_URL的用户名就是PG会话身份；没有固定要求名叫root |
| recall读分流 | [hindsight-api-slim/hindsight_api/engine/memory_engine.py:5988](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L5988) | READ_DATABASE_URL未配则复用主backend；配了不自动变成PG只读角色，需真实授权/只读端点 |
| 原生业务迁移 | [hindsight-api-slim/hindsight_api/migrations.py:474](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/migrations.py#L474)；[hindsight-api-slim/hindsight_api/extensions/context.py:134](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/extensions/context.py#L134) | MIGRATION_DATABASE_URL优先，否则主连接；支持绕过pooler的独立直连，但不自动协调对象owner |
| 插件管理元数据迁移 | [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py:27](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py#L27) | 直接读取主DATABASE_URL、asyncpg连接；不是原生迁移URL自动覆盖所有DDL |
| 管理鉴权/目录 | [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py:61](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py#L61) | repository复用engine主池；API Key不是PG账号 |

[源码] API与Worker用哪个数据库角色由部署配置决定；“只换MIGRATION_DATABASE_URL就完成全链路迁移/运行账号分离”不成立。离线元数据迁移、运行时创建工作空间的业务迁移、删除schema及后台维护要一起核对。

### 3.2 schema路由不是逐租户PG权限

[源码] Tenant验证当前Key和目标Bank，返回`TenantContext(schema_name)`：[hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py:56](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py#L56)。Repository查询元数据中的Key、用户及workspace授权：[hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py:245](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py#L245)。validator检查目标、schema与权限，内部任务也需合法workspace：[hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py:86](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py#L86)。

[源码] 引擎将认证schema放入每异步任务独立的ContextVar（上下文变量），然后用带schema的完整表名：[hindsight-api-slim/hindsight_api/engine/memory_engine.py:3530](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L3530)、[hindsight-api-slim/hindsight_api/engine/schema.py:56](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/engine/schema.py#L56)。内存表实现位于`engine/memories/postgres.py`及`engine/memories/pg/`；提示词省略engine层的路径在当前版本不成立。

[源码] 不能照提示词假设“每次借连接会切到租户search_path”。运行时关键路径依赖完整表名；迁移才显式`CREATE SCHEMA`和`SET search_path TO tenant,public`：[hindsight-api-slim/hindsight_api/alembic/env.py:119](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/alembic/env.py#L119)。同一schema内可多Bank，原生SQL仍需bank_id约束，schema上下文不替代表内Bank约束。

[实测·华为] 服务账号`SET search_path=meta_cx,public`后，`SELECT * FROM bank_cx.memories_cx`仍成功。数据库不会因为当前API Key只有空间A权限而阻止同一owner账号访问空间B。

### 3.3 连接池复位及PostgREST方案的适配限制

[源码] PostgreSQLBackend使用`_NoResetConnection`跳过asyncpg释放时的SQL reset；仍回滚未结束事务/清理驱动监听器，但不再依赖RESET ALL清除普通SET会话状态：[hindsight-api-slim/hindsight_api/engine/db/postgresql.py:196](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/engine/db/postgresql.py#L196)、[hindsight-api-slim/hindsight_api/engine/db/postgresql.py:307](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-api-slim/hindsight_api/engine/db/postgresql.py#L307)。连接setup会重设特定配置，不是任意session状态全量清洗。

[推断/建议] 不能在现有池上直接塞入普通`SET ROLE workspace_x`然后期待释放时恢复；必须有明确事务、SET LOCAL、结束/异常回滚、下一请求反例及元数据/Worker处理。这里是未来改造风险，不是本轮已经证实的跨租户漏洞。

### 3.4 创建/删除的ownership约束

[源码] 工作空间create经lifecycle调用context.run_migration；schema未写AUTHORIZATION，通常由迁移PG当前用户持有：[hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py:35](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py#L35)、alembic/env.py:128。

删除前Repository核对schema及表/函数/类型的owner必须匹配当前主池current_user，且不允许空间schema持有扩展/外部依赖：[hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py:642](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py#L642)。`DROP SCHEMA ... CASCADE`也由主池执行（同文件:663）。因此将业务迁移改用独立owner而运行时用另一普通账号，现有删除检查可能拒绝；只授DML还不够支持当前空间生命周期。

### 3.5 两个PG脚本各管哪层

| 资产 | 能保证什么 | 不能保证什么 |
| --- | --- | --- |
| prepare-pg.sql | 新建五NO专用角色+UTF8专用库；回收数据库PUBLIC权限；安装共享扩展 | 不清理现有库；不实施每Key角色/RLS；不隔离root；不提供跨环境完全相同的云root能力 |
| pg-role-boundary.sql | 普通SQL客户不能访问ctxdb_meta和指定workspace schema；核验危险属性/成员身份、owner/public CREATE，再撤权限和设置未来对象默认权限 | 不保护超级用户/云root；不自动处理所有新workspace；不隐藏catalog对象名；不授予客户读取记忆数据的JOIN能力 |

边界脚本先校验，再在一个DO块内收紧；继承角色仍能获得schema权限时拒绝，不悄悄修改无关角色。schema USAGE拒绝是主要闸门；按schema的默认REVOKE不能抵消全局默认授权。需要核对实际创建者和未来对象，而不能只写一条ALTER DEFAULT PRIVILEGES。源码：[hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql:20](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql#L20)；默认权限官方规则见[PostgreSQL18](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)。

[实测] 本地`test_customer_pg_boundary.py` 41 passed，2条依赖弃用warning；独立pg0在随机非5432端口启动并清理。华为同脚本配代表性对象，26条原测试攻击全部42501；客户自有schema写入成功、共享vector可用、catalog仍可见保护schema名称。没有据此冒称完整Hindsight原生迁移和API/MCP云端端到端已通过。

### 3.6 Supabase插件与PostgREST的本质差别

| 项目 | PostgREST官方模式 | hindsight supabase-tenant | 当前ContextBase插件 |
| --- | --- | --- | --- |
| 外部身份 | JWT中的受信role/claims | Supabase Auth JWT用户UUID | PG元数据中的动态API Key |
| PG实际角色 | authenticator登录，事务SET LOCAL ROLE | 仍是配置连接角色 | 仍是配置连接角色 |
| 对象定位 | 按授权表/RLS | user_UUID schema | ctxdb_ws_bank_id schema |
| 最终授权 | PG对象权限/RLS | 应用认证+schema路由 | 应用认证、操作validator+schema/Bank约束 |

[源码] supabase-tenant验证JWT、校验UUID、首次迁移schema后返回TenantContext，未按JWT执行PG SET ROLE：[hindsight-extensions/supabase-tenant/hindsight_ext_supabase_tenant/extension.py:288](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/supabase-tenant/hindsight_ext_supabase_tenant/extension.py#L288)。它对接Supabase身份，不代表自动采用Supabase所有数据库安全机制。[PostgREST官方认证链路](https://docs.postgrest.org/en/stable/references/auth.html)。

## 4. 隔离方案建议

### 4.1 先确定要防谁

| 对手/故障 | 推荐边界 | 能否由当前方案保证 |
| --- | --- | --- |
| 业务API Key访问未授权空间 | 应用认证+validator+明确schema/Bank+回归 | 现有设计覆盖；仍需逐入口/Worker保持合同 |
| 客户普通PG账号读取服务数据 | 独立库ACL；必要时共库schema ACL | 本次云端普通角色反例验证通过 |
| 服务账号凭据泄漏/任意SQL执行 | 限定专用库及可信角色，无额外成员授权 | 保护其他普通隔离库；本服务库内所有空间仍暴露 |
| 客户拥有同实例RDS root | 平台控制独立实例，隔离管理凭据及网络 | 同实例库/schema/RLS无法保证，本次已有反例 |
| 一个租户拖垮CPU/连接/IO | 资源限流/配额，强需求独立实例 | 不由库ACL/schema保证 |
| 云平台/OS管理员读取数据 | 单独定义信任边界；必要时端侧密钥/加密设计 | 当前系统不保证；端侧加密会影响向量/全文检索，需独立方案 |

### 4.2 明确推荐与优先级

1. **P0：专用账号+专用库。** 不是5个账号，而是一个服务账号带五个NO属性。API和内置/独立Worker只拿服务凭据；root只由平台供给/维护持有。创建独立客户业务库时也用独立账号，关闭两库PUBLIC CONNECT，并校验互访拒绝。普通账号不得得到root、service_role、pg_read_all_data等高危成员身份。
2. **P0：客户仅通过API/MCP/UI时不发PG凭据。** 不让业务Key变成PG owner；管理端Admin Key也不等于root。保留现有动态Key/工作空间权限，不新增原生角色切换/RLS架构。
3. **P0：如客户掌握RDS root且要求对其保密，选平台控制独立实例。** 专用库只能防普通角色，不能把本次观察到的root排除；单纯把服务换一个库仍不满足该威胁模型。
4. **P1：供给与健康检查补权限巡检。** 检查实际session_user/current_user、五NO、成员闭包/SET能力、CONNECT矩阵、public CREATE、schema owner及可读敏感目录。优先落在部署材料/自研preflight与测试，不改原生查询引擎。
5. **P1：只在确需SQL共库时用边界脚本。** 为客户单独schema且不给服务owner凭据；新空间激活前核验ACL，不靠运维事后补跑留下窗口。可选择在自研lifecycle增加明确的局部检查/加固，但需设计故障回滚/failed状态及客户角色配置来源；本报告不直接加变量、元数据表或调度框架。
6. **P2：迁移owner/运行DML角色分离是更深改造。** 先解决元数据迁移、动态建空间、删除owner检查、后台维护/Trace/Webhook例程权限，再考虑独立owner。现阶段建议主池和业务迁移使用同一专用owner（可用同账号直连迁移端点），不凭一个配置就宣称分权完成。
7. **P2：若要求数据库自身强制每空间互斥权限，单独评审每部署独立DB/实例，或每空间角色/事务授权/RLS。** 后者将触及主池、metadata与业务池、Worker、维护DDL、owner检查；不属于无需侵入的部署调整。

### 4.3 最小落地清单

| 内容 | 只改配置/运维即可 | 需要代码/设计修改 |
| --- | --- | --- |
| 当前API/Worker改用专用库账号 | 配DATABASE_URL；新库初始化；普通账号负向矩阵 | 主引擎无需为此修改 |
| 原生迁移绕pooler | MIGRATION_DATABASE_URL同owner直连 | 若不同owner，必须改lifecycle/ownership合同 |
| READ_DATABASE_URL | 指向同数据只读端点；PG授权需单独配置 | 插件鉴权继续主池；只读URL不自动成为RLS边界 |
| public共享扩展 | 供给方安装vector/pg_trgm/btree_gin于public，撤客户CREATE，保留必要USAGE/函数类型访问 | 避免未经适配搬到新schema导致原生解析失败 |
| 客户独立业务库 | 供给库/角色/ACL，负向连接测试 | 不改ContextBase API |
| 客户共库SQL | owner与客户分离，当前/未来对象权限检查 | 如产品支持动态SQL客户，插件需可闭环地处理新空间ACL |
| 启动阻止特权服务凭据 | 运维准入/巡检可先执行 | 自研preflight可加真实属性/成员检查；不只比对用户名root |

[建议] 当前客户只通过REST/MCP/UI访问的需求下，第一版选择P0+P1部署检查即可；不要把共库SQL或逐租户PG身份当成默认要求。

## 5. SQL验证矩阵与文档勘误

### 5.1 关键验证矩阵

结果中的00000表示成功；42501表示权限不足；28P01表示密码认证失败；22023为不接受的参数。代表性对象替换为本次*_cx名称，不将模板原文叫作逐字云端执行。

| SQL/场景 | 预期/争议 | 本次结果 | 证据 |
| --- | --- | --- | --- |
| CREATE ROLE …五NO | 普通服务身份 | 成功；五项均false | cloud-validation:service-flags |
| root未显式GRANT即CREATE DATABASE … OWNER service | 旧文称必须先GRANT | 本实例直接00000，后续补测root自动成员查询0行 | non-super-create-db-without-set；followup:root-auto-membership-before-explicit-grant |
| vector/pg_trgm/btree_gin WITH SCHEMA public | 独立库扩展可用 | 三者成功，普通service调用vector成功 | extension-*、vector-works |
| REVOKE ALL DATABASE FROM PUBLIC | 客户不能连服务库 | 双向均42501 | biz-cannot-connect-service等 |
| service/biz→supabase_db→auth.users | 连接与读表分开 | 连接成功，读表42501 | *supabase-connect/read |
| 边界脚本DO块 | 社区PG脚本在华为可运行 | meta_cx、bank_cx均成功 | boundary-* |
| 26条攻击 | 全部应拒绝 | 26/26均42501 | cloud-followup:full-attack-01～26 |
| 客户自有schema写入/查询 | 不影响正常客户业务 | 成功 | customer-own-write/read |
| 客户访问共享vector | 不误伤扩展 | 成功 | shared-vector-available |
| SELECT pg_namespace | 名称不是数据内容保密 | 仍看见bank_cx | catalog-name-visible |
| SET search_path后显式另schema查询 | search_path非ACL | 服务owner仍成功 | owner-cross-schema |
| CREATE EXTENSION pg_trgm不指定schema | 是否落biz_ext | 默认路径落public；改变路径后落doc_ext_cx | cloud-doc-sql:default-pg-trgm-schema；unqualified-extension-schema |
| 默认权限之前/之后的表 | 是否能补旧表 | 旧表SELECT=false，新表INSERT=true | existing-vs-future-acl |
| serial序列与USAGE schema | 是否包含在表DML授权 | sequence USAGE=false，schema CREATE=false | existing-vs-future-acl |
| ALTER ROLE VALID UNTIL | 语法与PG行为 | 成功，日期按时区解释 | valid-until* |
| 服务自助改密 | 不依赖root | 改密成功；新密码成功，旧密码28P01 | own-password-rotation等 |
| root新连接+无成员身份+FORCE RLS false | 是否真被隔离 | root仍读到protected，service owner为空集 | cloud-followup:root-fresh-* |
| authenticated claim=alice/Bob | RLS按行过滤 | 各1行，跨用户插入42501 | rls-authenticated-* |
| service_role和root查询RLS表 | 是否受同策略过滤 | 均2行 | rls-service_role-alice、rls-root-owner-force |
| 超长生成密码 | 环境passwordcheck是否有约束 | 首次34字符被22023拒绝（too long）；26字符重试成功 | attempt1-cloud-validation.json |

最后一项只证明该长度的失败/成功，不据此虚构精确密码长度上限或推荐把所有环境限制为26位。

### 5.2 《PG权限与Supabase数据隔离分析.md》勘误

| 位置 | 原说法/流程 | 修正建议 |
| --- | --- | --- |
| §5“库间隔离充分/跨库必须dblink或FDW” | 混淆连接、内容权限及高权账号 | 改为“普通角色受目标库CONNECT及对象权限约束；当前未安装这两扩展。账号可另建连接，云root及其他外联能力需单审” |
| §5数据库ACL | 暗示只有显式Supabase角色可连 | 当前PUBLIC已有CONNECT/TEMP；普通服务账号确实能连supabase_db，读auth被schema拒绝 |
| §6读取hash/扩展/权限 | 将云root行为推广成社区PG规则 | 标明本实例定制能力；普通专用账号pg_authid被42501拒绝 |
| §7“独立schema不污染public” | 只vector指定biz_ext，pg_trgm未指定 | CREATE SCHEMA不改变search_path；本流程pg_trgm落public，要求同schema则显式WITH SCHEMA（ContextBase仍按原兼容public部署） |
| §7默认权限 | 未说明旧表/序列/创建者 | 旧表另GRANT；serial序列另授权；FOR ROLE指向真正对象创建者，不能假设成员角色默认权限继承 |
| §7业务账号建表 | 只给USAGE，没有CREATE | DML账号可不建表；需要DDL时为其建自有schema并赋owner，或明确GRANT CREATE，避免开放共享public |
| §8完整rolpassword查询 | 直接导出可暴露完整hash | 改成算法/20字符前缀或统计，报告不包含完整hash |
| §2/§4表数、活跃连接 | 54表、组件连接是旧快照 | 本次50表；Auth未见活跃连接。保留历史日期，不把变化直接判为旧文造假 |

### 5.3 《ContextDB数据隔离方案2落地文档.md》勘误

| 位置 | 原说法/流程 | 本次证据与修正建议 |
| --- | --- | --- |
| §1“三条连接互不相见” | 未限定身份和权限 | 专用两库普通账号互连被拒，但service/biz仍可连Supabase库。改成“普通账号不能访问未授权数据；目录名/数据库名可能可见” |
| §2“ownership…root撤走后物理上进不来”及步骤2“root通道关闭” | 关键安全承诺错误 | root无成员身份、新连接仍读服务表且绕过FORCE RLS；删掉该承诺，明确root在信任域内 |
| §2“root对所有schema有CREATE” | 概括过度 | 本次supabase_db 11schema均有CREATE，postgres.public没有；必须限定库与快照 |
| 步骤1/附录“华为必须先GRANT才能代建库” | 与本次实例不一致 | 未显式GRANT即成功，且自动成员查询为空；作为跨环境待判条件，不强制增加不必要成员授权 |
| 步骤4A顺序 | 先REVOKE成员再标注在窗口内连库加固 | 文案与执行顺序冲突；把加固/扩展放窗口内再撤销，并新建连接验证。本云root可能仍能成功，不证明顺序普遍正确 |
| 步骤4B使用场景“同连接JOIN记忆数据” | 边界脚本却禁止访问记忆schema | 当前脚本实现“不允许读服务记忆数据”，不能直接JOIN。确需JOIN须另定受限视图/导出/API，不能直接授记忆基表 |
| 步骤4B供给身份 | 没写谁以何种owner建客户schema | 明确供给方拥有创建与指定owner能力；不把客户角色授予服务进程。新增空间必须持续核对ACL |
| 步骤5“旧密码立即失效” | 容易理解为踢掉旧会话 | 本次只验证旧密码新连接28P01；既有连接不会因普通改密自动被注销 |
| 运维“root零耦合” | 混淆运行依赖和控制权限 | 仅指ContextBase不使用root密码运行；root对数据的管控能力仍存在，Supabase组件仍依赖root |
| 红线“dblink/FDW唯一跨库方式” | 过于绝对 | 改成“默认禁止这两扩展及未经批准的跨库/外联能力，并以真实权限和网络准入验收” |
| 清理模板 | 先撤成员再DROP库，暗含云root能力 | 普通供给者可能须临时成员/owner权限才能DROP；明确只终止本轮临时库的连接，不终止平台backend |
| 验证范围总述“全部可行” | 4A/4B和进程端到端的证据程度不同 | 更新为“本轮4A独立库和4B代表性对象边界已云测；完整ContextBase进程端到端待验” |

两份原始文档未直接改写，本节给出可定位的勘误，避免覆盖其历史实测记录。

## 6. 附录：SQL、代码证据与清理

### 6.1 证据入口与可重复命令

永久证据目录：[/Users/zhuqingping/Work/Database/PG/contextbase-isolation-evidence-20261024](raw)。本次新增报告与证据，未修改源码、既有部署、用户verification/、PR/Issue；源码工作区仍只有原先的`?? verification/`。

```sh
# 本地测试仅启动自身临时pg0，不接管5432或云库
PYTHON_DOTENV_DISABLED=1 PYTHONPATH="$PWD/hindsight-extensions/contextdb-service:$PWD/hindsight-api-slim" \
  .venv/bin/python -m pytest -c hindsight-extensions/contextdb-service/pyproject.toml \
  hindsight-extensions/contextdb-service/tests/python/test_customer_pg_boundary.py -q
# 云端脚本先审读，再通过进程环境提供PGPASSWORD；禁止写进脚本/历史。
# cloud-validation.py/ cloud-followup.py/ cloud-doc-sql.py只面向其声明的*_cx对象。
```

源SQL/结果在JSON每个条目的sql/result/sqlstate中；followup保存26攻击逐条结果。首次密码过长失败和终态检查保留。脚本是本次研究工件，不是生产自动加固工具；不应不经审查投入已有客户库。

### 6.2 终态

[实测·华为] 2026-10-24 10:34:35 +08独立终态查询：5个原数据库、32个原角色；本轮iso/follow/doc临时库和角色各0。Supabase测试schema0；supabase_db用户表恢复50、policy恢复0。每轮pg_auth_members全部行与该轮基线逐项比较一致，不只是“查不到临时名字”。见[终态](raw/cloud-final.log)、[Supabase终态](raw/cloud-final-supabase.log)及三份cleanup.json。

没有修改root密码、现有角色成员关系或连接数限制；临时授予仅本轮新增角色，并已恢复。没有在Supabase原库安装/卸载扩展；扩展安装/卸载仅在自建临时库。没有执行pg_terminate_backend；DROP DATABASE WITH(FORCE)仅本轮临时库。supabase_db只改本轮授权的新schema/table/policy，已删除，未读写既有业务行。

### 6.3 官方依据

- [PG18角色与云root例外需分开判断](https://www.postgresql.org/docs/18/role-attributes.html)
- [schema/search_path及安全命名空间](https://www.postgresql.org/docs/18/ddl-schemas.html)
- [RLS、owner、BYPASSRLS与FORCE](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)
- [默认权限只针对未来对象和实际创建角色](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)
- [CREATE EXTENSION目标schema](https://www.postgresql.org/docs/18/sql-createextension.html)
- [PostgREST JWT与SET LOCAL ROLE](https://docs.postgrest.org/en/stable/references/auth.html)
- [华为RDS root提权说明](https://support.huaweicloud.com/productdesc-rds-pg/rds_02_0012.html)

### 6.4 两份原文SQL逐项清单

下表/后附清单覆盖SQL代码块及正文代码片段中的完整SQL；变量、密码占位符与psql命令不是可原样执行的SQL。动态验证替换为*_cx对象；对Supabase现有数据仅做元数据/权限只读查询。不可将“同类已测”解释为对现有生产对象执行了对应DDL。

共48条SQL/psql语句或正文模板，保留重复出现项以便逐处修订；原文行号指SQL块起始行或内联所在行。


**A01 · PG权限与Supabase数据隔离分析.md:85** — psql命令；本轮用独立驱动连接等价替代

```sql
\c my_biz
```

**A02 · PG权限与Supabase数据隔离分析.md:85** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE DATABASE my_biz OWNER root;
```

**A03 · PG权限与Supabase数据隔离分析.md:85** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE ROLE biz_app LOGIN PASSWORD '<强密码>';
```

**A04 · PG权限与Supabase数据隔离分析.md:85** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT CONNECT ON DATABASE my_biz TO biz_app;
```

**A05 · PG权限与Supabase数据隔离分析.md:85** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE SCHEMA biz_ext AUTHORIZATION root;
```

**A06 · PG权限与Supabase数据隔离分析.md:85** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE EXTENSION vector WITH SCHEMA biz_ext;
```

**A07 · PG权限与Supabase数据隔离分析.md:85** — 同语句云测：默认public；路径可改变结果

```sql
CREATE EXTENSION pg_trgm;
```

**A08 · PG权限与Supabase数据隔离分析.md:85** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT name FROM pg_available_extensions ORDER BY name;
```

**A09 · PG权限与Supabase数据隔离分析.md:85** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT USAGE ON SCHEMA public, biz_ext TO biz_app;
```

**A10 · PG权限与Supabase数据隔离分析.md:85** — 同类云测：不补旧表/序列；核对创建角色

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO biz_app;
```

**A11 · PG权限与Supabase数据隔离分析.md:85** — 同语句类云测成功（替换为临时角色）

```sql
ALTER ROLE biz_app VALID UNTIL '2027-12-31';
```

**A12 · PG权限与Supabase数据隔离分析.md:120** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT rolname, rolcanlogin, rolvaliduntil FROM pg_roles ORDER BY 1;
```

**A13 · PG权限与Supabase数据隔离分析.md:120** — 只读等价实测；实际输出截断hash，不原样导出全hash

```sql
SELECT rolname, rolpassword, rolvaliduntil FROM pg_authid WHERE rolcanlogin;
```

**A14 · PG权限与Supabase数据隔离分析.md:120** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT datname, usename, application_name, count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() GROUP BY 1,2,3 ORDER BY 4 DESC;
```

**A15 · PG权限与Supabase数据隔离分析.md:120** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT has_database_privilege('root','supabase_db','CREATE');
```

**A16 · PG权限与Supabase数据隔离分析.md:120** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT has_schema_privilege('root','public','CREATE');
```

**B01 · ContextDB数据隔离方案2落地文档.md:47** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE ROLE ctxdb_service LOGIN PASSWORD '<强密码>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

**B02 · ContextDB数据隔离方案2落地文档.md:47** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT ctxdb_service TO root;
```

**B03 · ContextDB数据隔离方案2落地文档.md:47** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE DATABASE ctxdb OWNER ctxdb_service TEMPLATE template0 ENCODING 'UTF8';
```

**B04 · ContextDB数据隔离方案2落地文档.md:47** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
REVOKE ALL ON DATABASE ctxdb FROM PUBLIC;
```

**B05 · ContextDB数据隔离方案2落地文档.md:47** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT CONNECT, CREATE, TEMPORARY ON DATABASE ctxdb TO ctxdb_service;
```

**B06 · ContextDB数据隔离方案2落地文档.md:65** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

**B07 · ContextDB数据隔离方案2落地文档.md:65** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE EXTENSION vector WITH SCHEMA public;
```

**B08 · ContextDB数据隔离方案2落地文档.md:65** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE EXTENSION pg_trgm WITH SCHEMA public;
```

**B09 · ContextDB数据隔离方案2落地文档.md:65** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE EXTENSION btree_gin WITH SCHEMA public;
```

**B10 · ContextDB数据隔离方案2落地文档.md:65** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
REVOKE ctxdb_service FROM root;
```

**B11 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE ROLE biz_app LOGIN PASSWORD '<强密码>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

**B12 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT biz_app TO root;
```

**B13 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE DATABASE biz OWNER biz_app TEMPLATE template0 ENCODING 'UTF8';
```

**B14 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
REVOKE ALL ON DATABASE biz FROM PUBLIC;
```

**B15 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT CONNECT, CREATE, TEMPORARY ON DATABASE biz TO biz_app;
```

**B16 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
REVOKE biz_app FROM root;
```

**B17 · ContextDB数据隔离方案2落地文档.md:90** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

**B18 · ContextDB数据隔离方案2落地文档.md:105** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE ROLE customer_sql LOGIN PASSWORD '<强密码>' NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS;
```

**B19 · ContextDB数据隔离方案2落地文档.md:105** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
GRANT CONNECT, TEMPORARY ON DATABASE ctxdb TO customer_sql;
```

**B20 · ContextDB数据隔离方案2落地文档.md:105** — 临时对象同类云测；具体结果/顺序限制见第5章

```sql
CREATE SCHEMA own_customer1 AUTHORIZATION customer_sql;
```

**B21 · ContextDB数据隔离方案2落地文档.md:134** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT datname, usename, application_name, count(*) FROM pg_stat_activity WHERE pid <> pg_backend_pid() GROUP BY 1,2,3 ORDER BY 4 DESC;
```

**B22 · ContextDB数据隔离方案2落地文档.md:134** — 只读同类实测；见快照/元数据/终态证据

```sql
SELECT * FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles g ON g.oid=m.member WHERE r.rolname='ctxdb_service' AND g.rolname='root';
```

**B23 · ContextDB数据隔离方案2落地文档.md:156** — 占位模板，需替换；临时对象DROP/REVOKE同类实测

```sql
REVOKE <role> FROM root;
```

**B24 · ContextDB数据隔离方案2落地文档.md:156** — 占位模板，需替换；临时对象DROP/REVOKE同类实测

```sql
DROP DATABASE <db> WITH (FORCE);
```

**B25 · ContextDB数据隔离方案2落地文档.md:156** — 占位模板，需替换；临时对象DROP/REVOKE同类实测

```sql
DROP ROLE <role>;
```

**B26 · ContextDB数据隔离方案2落地文档.md:123** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
SELECT rolname FROM pg_authid LIMIT 1;
```

**B27 · ContextDB数据隔离方案2落地文档.md:124** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
ALTER ROLE ctxdb_service SUPERUSER;
```

**B28 · ContextDB数据隔离方案2落地文档.md:125** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
CREATE DATABASE x;
```

**B29 · ContextDB数据隔离方案2落地文档.md:125** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
CREATE ROLE x LOGIN;
```

**B30 · ContextDB数据隔离方案2落地文档.md:129** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
ALTER ROLE ... PASSWORD
```

**B31 · ContextDB数据隔离方案2落地文档.md:148** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
ALTER ROLE ctxdb_service PASSWORD '<新密码>';
```

**B32 · ContextDB数据隔离方案2落地文档.md:149** — 正文模板/检查语句；临时角色同类验证，不能原样改现有账号

```sql
ALTER ROLE ctxdb_service PASSWORD '<新密码>';
```

### 6.5 未完成的验证

- 华为完整ContextBase API/Worker/UI及真实模型全流程；本轮是数据库供给/权限/脚本验证。
- 实际PostgREST HTTP JWT到RLS的端到端，Supabase备份恢复/故障切换及性能隔离。
- 根因级确认云root绕过权限/RLS的具体内核实现；本次仅确认实际行为，未修改云参数或追踪平台内核。
- 迁移URL换成不同owner、独立只读角色及pooler事务模式下的生命周期组合；这是代码改造前的必要验收，不视为现有方案已支持。
