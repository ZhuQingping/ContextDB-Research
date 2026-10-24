# ContextBase 的 PostgreSQL 权限与数据隔离

更新时间：2026-10-24。适用实现：`contextdb/v1.0.0`，提交 `9fb57bc0470e7784d8766fdfb19d837f603b9638`。

本文面向 ContextBase 与 Supabase 共用 PostgreSQL 实例的部署，说明数据库身份、权限边界、部署步骤和验收要求。客户通过 REST API、MCP 和 UI 使用服务，计算节点通过内部网络以 SSL 连接数据库。

## 1. 推荐方案与适用条件

推荐为每套独享部署的 ContextBase 分配一个专用 PostgreSQL 数据库和一个专用服务角色。API 与 Worker 使用该角色连接数据库，不使用云端数据库管理账号 `root`。每套部署包含一套独立服务和数据库，多个工作空间使用库内不同 schema。

服务角色具有 `LOGIN`，关闭 `SUPERUSER`、`CREATEDB`、`CREATEROLE`、`REPLICATION`、`BYPASSRLS` 五项属性，并且没有可获得高权限的角色成员关系。该角色仍拥有服务库及其业务对象，负责初始化、工作空间建删和业务读写；除业务 DML 外，该角色还需要管理库内业务对象的 DDL 权限。

产品用户与 API Key 由 ContextDB 插件管理，无需为每个用户或 Key 创建 PostgreSQL 角色。数据库权限限制普通角色的访问；同实例高权限管理员仍处于信任范围内，实例资源和故障也由各数据库共享。

## 2. 数据布局与权限边界

### 2.1 实例、数据库和工作空间

PostgreSQL 角色在实例内共享；schema（模式）和业务表属于具体数据库。一条连接只访问一个数据库，数据库内再通过 schema 组织对象。

| 层次 | 用途 | 隔离机制 |
| --- | --- | --- |
| PostgreSQL 实例 | 同时承载 Supabase 与 ContextBase 数据库 | 平台管理权限与实例配置 |
| ContextBase 专用数据库 | 一套服务的全部管理数据和工作空间数据 | 数据库 `CONNECT` 权限、对象权限和角色成员关系 |
| `ctxdb_meta` | 用户、工作空间、API Key 等六张管理表 | 仅向服务角色开放所需访问 |
| `ctxdb_ws_<bank_id>` | 单个工作空间的 Hindsight 业务表 | 插件鉴权后选择工作空间 schema |
| `public` | `vector` 等共享扩展对象 | 保留必要访问权限，不初始化 Hindsight 业务表 |

工作空间对应 Hindsight Bank；产品授权使用不可变的 `workspace_id`，不能仅凭可复用的空间名称继承授权。全部空间由同一服务角色访问，因此空间间隔离依赖应用鉴权和正确的 schema 路由，不能抵御该服务角色直接执行的任意 SQL。

### 2.2 访问者与隔离边界

| 访问者或风险 | 隔离边界 |
| --- | --- |
| 持有业务 API Key 的客户 | 插件检查 Key、用户状态、目标空间及读写权限；不向客户提供数据库凭据 |
| Supabase 及其他业务库的普通角色 | 撤销服务库的 `PUBLIC CONNECT`，且无其他有效授权时，拒绝连接服务库 |
| 获准连接服务库的其他普通角色 | 不授予服务对象所有权、保护 schema 的 `USAGE/CREATE`、对象访问权限或可提权角色成员身份 |
| 泄漏的服务凭据或服务进程 SQL 注入 | 权限受服务角色限制，但服务库内全部工作空间均在潜在影响范围内 |
| 保管管理员凭据的 Agent、数据库及基础设施管理员 | 属于受信任的管理面；专用服务账号的权限限制不约束其管理员连接 |

Supabase 业务角色与 ContextBase 服务角色分别管理。检查权限时，须同时核对直接授权、`PUBLIC`、间接角色成员关系及 `SET ROLE` 能力。新增空间、对象所有者或角色授权变化后，应复核有效权限；默认权限仅影响指定创建者的未来对象。

撤销服务库的 `PUBLIC CONNECT` 不会改变其他数据库的授权。服务角色也可能通过其他库的公共授权连接那些库，应分别检查其有效权限。若要求服务数据对客户控制的实例管理员保密，须使用平台控制的独立实例。

`search_path` 是名称查找顺序，不是访问控制。RLS（行级安全）也不能限制超级用户、具有 `BYPASSRLS` 属性的角色或可修改策略的表所有者；本版空间隔离使用应用鉴权和 schema 路由，不使用逐用户 RLS。数据库授权保护数据访问，不隐藏系统目录中的对象名称。

## 3. 数据库连接与所有权要求

`HINDSIGHT_API_DATABASE_URL` 指定 API 和 Worker 的主数据库连接，插件管理数据也使用该连接池。

`HINDSIGHT_API_READ_DATABASE_URL` 用于将 Recall 检索分流到独立连接池，适合连接同一数据集的只读副本、分担主库查询负载。不设置时，Recall 复用主连接池。目标须包含相同的工作空间数据，并使用受限业务角色连接，权限由该角色的 PG 授权决定。

`HINDSIGHT_API_MIGRATION_DATABASE_URL` 可指定原生业务迁移连接，插件元数据迁移仍使用主连接。迁移连接应使用服务角色，保持创建对象的所有者与主连接的 `current_user` 一致，这是空间删除的校验要求。使用不同迁移角色前，须适配对象所有权及空间生命周期；管理员凭据仅用于数据库预配置和维护。

Hindsight 使用部署层已创建的数据库和角色。ContextDB 插件负责产品授权及库内管理表、工作空间 schema 的生命周期。源码机制见[PG 权限调研报告](../testing/evidence/pg-isolation-20261024/research-report.md)。

## 4. Supabase 权限机制与共实例验证依据

### 4.1 Supabase 与 ContextBase 的授权方式

Supabase 的 PostgREST 校验 JWT 后，在请求事务内切换到 JWT 对应的数据库角色，结合对象授权和 RLS 限制访问。`anon`、`authenticated` 是共享权限角色，用户之间可由基于 JWT 身份的行策略区分，无需每个用户一个 PG 登录账号。该机制依赖可信的 JWT 校验和身份传递，不能将任意 SQL 客户端自行设置的会话变量作为可信身份。参见 [PostgREST 认证](https://docs.postgrest.org/en/stable/references/auth.html)、[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)。

| 项目 | Supabase / PostgREST | 当前 ContextBase |
| --- | --- | --- |
| 产品身份 | JWT 用户身份及角色声明 | 插件管理的用户与 API Key |
| PG 执行身份 | 连接角色登录，请求事务内切换权限角色 | API/Worker 使用统一服务角色 |
| 数据授权 | PG 对象权限与 RLS 行策略 | 插件鉴权、操作权限和工作空间 schema 路由 |

因此，共用 PG 实例不会使 ContextBase 自动获得 Supabase 的 JWT/RLS 隔离；两套服务分别管理身份和授权，PG 库间权限由部署层配置。

### 4.2 华为 RDS 实例的验证事实

以下是 2026-10-24 对华为 RDS PostgreSQL 18.6 的验证结果，实例配置和组件连接身份仅代表被测环境。

| 事实 | 部署含义 |
| --- | --- |
| `root` 的 `rolsuper=false`、`rolbypassrls=false`，仍具有厂商管理权限 | 无服务角色成员身份的全新连接仍可读取启用强制 RLS 和拒绝策略的测试表；仅检查角色属性不足以判断管理员能力 |
| PostgREST 使用 `rds_supabase_authenticator` 连接 `supabase_db`；`anon`、`authenticated`、`service_role` 均为 `NOLOGIN`，其中 `service_role` 有 `BYPASSRLS` | 区分数据库连接身份与请求权限角色，不能将 `service_role` 视为受普通 RLS 限制的用户 |
| Realtime、Supavisor 存在 `root` 连接 | ContextBase 应使用专用角色；修改共享管理账号密码可能影响 Supabase 组件 |
| `supabase_db`、`_supabase`、`postgres` 允许 `PUBLIC CONNECT/TEMP` | 普通角色可连接这些库，但在 `supabase_db` 查询 `auth.users` 被拒绝；连接权限与表访问权限须分别检查 |

在新建测试表中，`authenticated` 配合身份行策略只能读取对应用户的合成行，越权插入被拒绝；`service_role` 和云 `root` 可读取全部合成行。该验证覆盖数据库角色和 RLS 行为，未覆盖实际 PostgREST HTTP/JWT 全链路。组件连接、表权限及测试 SQL 的完整依据见[调研报告第2章](../testing/evidence/pg-isolation-20261024/research-report.md#2-实例实测supabase权限与隔离)。

## 5. 部署步骤

部署分为数据库预配置和服务初始化两个阶段。Agent 或 DBA 使用管理员身份完成预配置，随后以服务角色连接初始化和运行业务。下表的执行身份均指 PG 会话角色，`contextbase`、`contextbase_service` 为示例名称。

| 阶段 | 执行身份 | 连接数据库 | 操作 |
| --- | --- | --- | --- |
| 5.1 创建角色和数据库 | 有建角色、建库及指定 owner 权限的部署管理员 | 维护库，例如 `postgres` | 创建专用角色、创建服务库、收紧数据库权限 |
| 5.2 安装扩展 | 有目标库访问、schema 管理及扩展安装权限的部署管理员 | **重新连接到 `contextbase`** | 检查当前库、收紧 `public`、安装扩展 |
| 5.3 初始化和运行 | `contextbase_service` | `contextbase` | 创建管理表；API/Worker 处理业务并管理工作空间 |

部署 Agent（自动化部署程序或其执行节点）通过 psql 或驱动远程执行预配置和维护，无需登录 PG 节点。Agent 持续保管可用的 `root` 或具备所需权限的管理员凭据，用于创建角色、数据库、安装或升级扩展、授权和故障处理；凭据保存于 Agent 私有文件或可持续访问的平台凭据存储，并随管理员密码轮换更新。

Agent 向 API/Worker 下发专用服务角色的连接信息。管理员凭据独立保管，不写入服务的 `api.env/ui.env`，也不通过继承的环境变量传入 API/Worker/UI 进程。

### 5.1 在维护库创建服务角色和数据库

先确认目标角色和数据库不存在。正式脚本 [deployment/prepare-pg.sql](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/deployment/prepare-pg.sql) 遇到同名对象会停止，不接管已有数据库。

由部署环境提供 `PGHOST`、`PGPORT`、`PGUSER`、`PGPASSWORD`，其中 `PGUSER` 是部署管理员；将新服务密码私有注入 `CONTEXTDB_NEW_DB_PASSWORD`。通过以下命令进入维护库，随后按顺序执行第5.1、5.2节：

```sh
PGSSLMODE=require psql -X -v ON_ERROR_STOP=1 --dbname=postgres
```

下列 psql/SQL 与正式脚本使用相同的密码输入约定，不将密码直接写入 SQL 文件。自动化部署也可直接调用正式脚本完成第5.1、5.2节；两种方式选择一种，避免重复创建同名对象。

```sql
-- 当前连接：部署管理员 @ postgres。
SELECT current_database(), session_user, current_user;
\getenv service_password CONTEXTDB_NEW_DB_PASSWORD
CREATE ROLE contextbase_service LOGIN PASSWORD :'service_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\unset service_password
CREATE DATABASE contextbase OWNER contextbase_service
  TEMPLATE template0 ENCODING 'UTF8';
REVOKE ALL ON DATABASE contextbase FROM PUBLIC;
GRANT CONNECT, CREATE, TEMPORARY ON DATABASE contextbase TO contextbase_service;
```

`\getenv`、`\unset` 是 psql 客户端命令；缺少密码输入或任一步失败时，应停止并检查已创建的对象，不继续启动服务。`CREATE DATABASE` 必须在事务块外单独执行。不要将上述 SQL 放入 `BEGIN/COMMIT` 事务块，也不要启用 psql 的单事务执行模式。参见 [PG18 CREATE DATABASE](https://www.postgresql.org/docs/18/sql-createdatabase.html)。

社区 PostgreSQL 要求创建者有建库权限，并能 `SET ROLE` 到指定的新 owner。被测华为 RDS 实例的 `root` 可直接为新服务角色建库；其他环境需核对实际权限。若确需让部署管理员临时成为新服务角色的成员，保留该授权至第5.2节完成，再撤销临时授权并核对原有成员关系。授权方向为“服务角色授予管理员”，不得反向授予管理员角色给服务角色；保留现有 Supabase 组件授权。

### 5.2 重新连接服务数据库并安装扩展

扩展安装是将服务器已提供的扩展注册到 `contextbase` 数据库，创建所需类型、函数、运算符等 SQL 对象。应先由 DBA 确认 RDS 支持 `vector`、`pg_trgm`、`btree_gin`，且执行角色有安装权限；另一个数据库已安装它们，不代表新库已安装。参见 [PG18 CREATE EXTENSION](https://www.postgresql.org/docs/18/sql-createextension.html)。

创建数据库后，原连接仍在 `postgres`，需要重新连接到 `contextbase`。在第5.1节使用的 psql 会话中执行以下命令，保持连接同一实例并使用部署管理员身份：

```sql
-- psql 客户端命令：重新连接到服务数据库。
\connect contextbase

-- 确认数据库为 contextbase，身份为部署管理员，再执行后续 SQL。
SELECT current_database(), current_user;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO contextbase_service;
CREATE EXTENSION vector WITH SCHEMA public;
CREATE EXTENSION pg_trgm WITH SCHEMA public;
CREATE EXTENSION btree_gin WITH SCHEMA public;

-- 核对扩展版本及其成员对象所在 schema。
SELECT e.extname, e.extversion, n.nspname AS object_schema
FROM pg_extension e
JOIN pg_namespace n ON n.oid = e.extnamespace
WHERE e.extname IN ('vector', 'pg_trgm', 'btree_gin')
ORDER BY e.extname;
```

`\connect` 是 psql 客户端命令，不是 SQL。使用其他数据库客户端或自动化驱动时，应新建指向 `contextbase` 的连接，再执行上述 SQL。PostgreSQL 不支持 `USE contextbase`；`SET search_path` 也不会切换数据库。

`WITH SCHEMA public` 指定扩展成员对象的安装位置。当前引擎依赖这些共享对象，须保留服务角色所需的 schema、类型和函数访问权限；保留 `public`，其中不初始化业务表。

### 5.3 初始化并启动服务

第5.2节完成并撤销所需的临时授权后，退出管理员 psql 会话。Agent 继续保管管理员凭据，服务子进程仅接收业务运行配置。将服务角色连接串保存到部署意图引用的 `database_url_file`，渲染后的 `api.env` 应包含以下设置：

```sh
HINDSIGHT_API_DATABASE_URL='postgresql://contextbase_service:<url-encoded-password>@<RDS-host>:5432/contextbase?sslmode=require'
HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP=false
```

密码含 URI 保留字符时须进行百分号编码，不能直接拼接原始密码。API 和 Worker 使用同一目标库及服务角色；UI 使用独立进程和配置，不需要 PG 或模型凭据。

连接串统一使用 `?sslmode=require`。华为 RDS 环境已验证该写法可完成连接、初始化和 Worker 执行。URL 中的 `?ssl=require` 会被当前 asyncpg 作为数据库会话参数发送，触发 `CantChangeRuntimeParamError`，应避免使用。

按同版 [intent.example.json](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/deployment/intent.example.json) 准备部署意图，填写实例、租户、未占用端口及数据库 URI、模型 Key、UI 密码文件路径，使用 `topology="merged"`。依赖环境、输入文件权限和生产产物的准备见[部署联调指南](contextdb-service-integration-guide.md)。完成这些前置准备后，在同版源码根目录执行：

```sh
set -e
# 清理当前部署会话的临时输入；Agent 独立保存的管理凭据保持不变。
unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE CONTEXTDB_NEW_DB_PASSWORD
export CONTEXTDB_DEPLOY_DIR=/srv/contextdb/runtime
export PYTHONPATH="$PWD/hindsight-extensions/contextdb-service:$PWD/hindsight-api-slim"
.venv/bin/python -m hindsight_ext_contextdb.deployment render \
  --config /srv/contextdb/input/intent.json \
  --directory "$CONTEXTDB_DEPLOY_DIR"
bash hindsight-extensions/contextdb-service/scripts/service.sh init
bash hindsight-extensions/contextdb-service/scripts/service.sh all
```

`CONTEXTDB_DEPLOY_DIR` 是持久化私有目录；配置文件为0600，目录为0700，运行用户须有相应访问权限。`init` 创建秘密文件、六张管理表和管理员，重复执行保留已有秘密；它不创建 PG 数据库，也不执行 `prepare-pg.sql`。`all` 在前台运行 API、内置 Worker 和 UI，应交由节点 Agent 或进程管理器监督。工作空间业务表在创建空间时初始化到对应 schema。

其他 CLI 参数见同版[服务插件 README](https://github.com/ZhuQingping/hindsight/blob/9fb57bc0470e7784d8766fdfb19d837f603b9638/hindsight-extensions/contextdb-service/README.md)。

## 6. 验收与日常运行

验收同时覆盖数据库权限、产品授权和完整业务链路。

| 范围 | 必须检查的结果 |
| --- | --- |
| 初始化与布局 | 使用专用服务角色完成初始化；重复初始化秘密不变；完整业务和 Worker 执行后，`public` 仍无业务表 |
| 产品授权 | REST、SDK、MCP、UI 可用；只读权限、跨空间拒绝、用户禁用、Key 吊销有效 |
| 后台与生命周期 | 等待异步 Worker 完成；删除/重建后的 UUID、ETag 与旧授权符合设计 |
| 运行身份与连接权限 | 确认 API/Worker 主连接使用专用服务角色，读/迁移连接不使用管理员账号，子进程无管理员凭据；用实际 Supabase 及其他普通业务角色的新连接验证服务库访问被拒；核对服务角色在其他数据库的有效授权 |
| 服务对象权限 | 对获准连接服务库的其他普通 SQL 角色，验证真实管理表和工作空间表的读取、写入、TRUNCATE、DROP 及切换到服务所有者均被拒绝；新增空间或授权变化后复验 |
| 平台边界 | 验证普通账号受限、高权限管理员仍可访问的边界；清理临时验证对象 |

2026-10-24 验证覆盖内置与独立 Worker、真实云数据库及模型调用。结果与命令见[验收记录](../testing/contextbase-cloud-pg-e2e-20261024.md)。远程应用部署、性能及备份恢复尚未验收。

改密只影响后续连接认证，不会自动使已有会话退出。服务密码轮换须更新服务连接配置并重建 API/Worker 连接池；管理员密码轮换须同步 Agent 凭据存储及使用该账号的 Supabase 组件配置。维护操作仅处理相关会话，不终止无关 Supabase 连接。

删除空间前，管理员必须停止该空间的新业务并等待已接受请求和后台工作结束。本版没有并发删除排空屏障，不支持删除与业务访问并发。

## 7. 验证依据与参考资料

- [云端验收记录](../testing/contextbase-cloud-pg-e2e-20261024.md)：本版部署、业务链路、权限结果及未解决项。
- [PG 权限调研报告](../testing/evidence/pg-isolation-20261024/research-report.md)：Supabase 快照、SQL 清单、角色/RLS 反例和源码定位。
- [PG18 schema 与 search_path](https://www.postgresql.org/docs/18/ddl-schemas.html)、[角色属性](https://www.postgresql.org/docs/18/role-attributes.html)、[行级安全](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)、[华为 RDS root 权限](https://support.huaweicloud.com/productdesc-rds-pg/rds_02_0012.html)。
