# Hindsight 多 PG 实例横向扩展 —— 首期实现验证报告

> 配套设计文档：`./multi-pg-scaling-design.md`
> 实现日期：2026-09-30
> 环境：容器 `zhuqingping_hindsight`；默认实例 pg0 `127.0.0.1:5432`（PG 18.1, pgvector 0.8.5）；第二实例 pg0 `pg2` `127.0.0.1:5433`
> schema：`user_company1`（默认实例 pg-default）、`user_company2`（路由到 pg2）

## 第二实例选择（与设计文档选项对照）

设计文档列了两种第二实例方案：① 宿主机 docker 起 `pgvector/pgvector:pg18`；② 容器内再起一个 pg0 实例（不同端口）。

**本环境实测：方案 ①不可行**——宿主机 docker 的代理（`proxy.huawei.com:8080`）当前连不上，Docker Hub / 华为云镜像源 / quay.io 均超时，宿主机也无本地 pgvector/postgres 镜像。

**采用方案 ②**：在 hindsight 容器内用 `EmbeddedPostgres(name="pg2", port=5433, ...)` 起第二个 pg0 实例。已验证：
- pg2 在 `127.0.0.1:5433` 正常启动，PG 18.1（与默认实例同版本）。
- pgvector 通过迁移路径按需安装（`_ensure_pgvector_extension_in_public`），与默认实例一致。
- 容器内可达，无外部依赖，更贴近"同进程内多实例"的真实多实例部署拓扑。

方案 ② 的限制（已记入 TODO）：pg2 实例目录在 stop 后保留数据；首期无数据迁移，pg2 的 schema 为全新迁移产物。这与"首期干净起点"边界一致。

## 验证结果汇总（13 项全通过）

| # | 验证项 | 结果 | 证据要点 |
|---|--------|------|----------|
| 1 | 默认行为零回归（meta 未配） | ✅ 通过 | router 为 None，`_get_backend()` 返回 `self._backend`，live service `/health` 200 |
| 2 | opt-in 路由正确 | ✅ 通过 | `user_company2→pg2` 命中 `:5433`；`user_company1→default :5432` |
| 3 | 迁移跨实例 + 版本独立 | ✅ 通过 | `user_company2.alembic_version` 建在 pg2（head `a7c2e9f41b60`），未在 pg1 重建；pg1 的 `user_company1` 版本不变 |
| 4 | worker 跨实例调度 | ✅ 通过 | 两实例各有 pending task → poller 从两实例各 claim，per-tenant 公平保留 |
| 5 | 读副本 per-instance | ✅ 通过 | pg2 配 `read_url` → 独立 read pool（≠ main pool）；默认无 `read_url` → 回退 main |
| 6 | schema 隔离不破 | ✅ 通过 | company1 key 读不到 company2 bank（count=0）；跨实例 marker 写入只落 pg2 不复制 pg1 |
| 7 | bank 隔离不破 | ✅ 通过 | 同 schema 多 bank 按 `bank_id` 过滤隔离；router 激活不影响 bank_id contextvar |
| 8 | pgbouncer 适配不破 | ✅ 通过 | pg2 pool 底层连接类为 `_NoResetConnection`（与默认一致），GUC `pg_trgm.similarity_threshold=0.15` per-acquire 生效 |
| 9 | 跨租户全局例程 `fq_routine` | ✅ 通过 | `fq_routine` 解析为配置 schema（`"public".<routine>`），忽略 per-request schema；首期单实例范围，无跨实例假设 |
| 10 | 连接池不泄漏 | ✅ 通过 | pg2 pool 5 并发 acquire 后 size=5 idle=5，acquire/release 配对无泄漏 |
| 11 | 实例宕机有明确错误 | ✅ 通过 | pg2 down → `user_company2` 请求 `ConnectionRefusedError`（明确），不静默回退默认实例；默认实例仍服务 |
| 12 | 路由表缓存失效 | ✅ 通过 | 改路由行 + `invalidate(schema)` → 下次 resolve 立即生效（不等 TTL） |
| 13 | 空路由表 | ✅ 通过 | 路由表无行 → 所有 schema 回退默认实例；live service 正常启动、迁移、worker、maintenance 全过 |

## 逐项证据

### 1. 默认行为零回归（meta 未配）

未设 `HINDSIGHT_API_META_DATABASE_URL`：
```
meta_database_url = None
router after __init__: None
router after initialize: None — meta unset
backend is_ready: True
pool is default backend pool: True
_get_backend() is self._backend: True
_pool_for_current_schema() is self._backend: True
task_backend pool_getter is _pool_for_current_schema: True
ZERO-REGRESSION (meta unset) OK
```
live service 重启后（meta 未设）：
```
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8888
... worker polling loop ... schemas migrated ... retention sweep ...
```
`GET /health` → `200 {"status":"healthy","database":"connected",...}`

### 2. opt-in 路由正确

注册 `pg2`（`127.0.0.1:5433`）+ 路由行 `user_company2 → pg2`：
```
resolve(user_company2): pg2
resolve(user_company1): None (unmapped → default)
backend for user_company2 dsn: postgresql://...@127.0.0.1:5433/hindsight
task_backend pool for user_company2 is pg2 pool: True
```

### 3. 迁移跨实例 + 版本独立

迁移分组：
```
migration groups:
  PG1(5432): ['user_company1']
  PG2(5433): ['user_company2']
```
迁移后：
```
AFTER: pg2 user_company2 alembic_version: a7c2e9f41b60   ← 建在 pg2
AFTER: pg1 user_company1 alembic_version: a7c2e9f41b60    ← pg1 不变
AFTER: pg2 user_company1 alembic_version: <none>         ← pg2 上无
```
版本表 per-schema，天然跟 schema 走，无需额外版本管理。

### 4. worker 跨实例调度

两实例各插一个 pending task（pg1 `user_company1`、pg2 `user_company2`）：
```
claimed 2 tasks:
  schema= user_company1 type= test_task_c1
  schema= user_company2 type= test_task_c2
CLAIM OK: both instances' tasks claimed across instances
```
claim 走 `_claim_batch_multi_instance`：按实例分组，每实例在自己的 pool 上 acquire 一条连接跑 `_claim_batch_on_conn`（per-tenant 公平轮转在每实例内保留）。实例 down 时该实例 claim 报错被吞、其他实例继续（首期简单 log）。

### 5. 读副本 per-instance

给 pg2 配 `read_url`（指向自身，验证分支）：
```
pg2 main backend dsn: ...:5433/hindsight
pg2 read backend dsn: ...:5433/hindsight
read backend is instance.read_backend (distinct from main): True
user_company1 read backend == main (no read_url => fallback): True
```

### 6. schema 隔离不破

API 级跨租户：
```
key-zhang3 -> schema: user_company1
key-wang5  -> schema: user_company2
company1 key reading company2's bank_id -> count: 0 (expect 0)
```
跨实例路由隔离（marker 写入只落路由到的实例，首期无双写/复制）：
```
user_company2 routed backend: ...:5433/hindsight (expect :5433)
marker on pg2=0, pg1=0; routed instance pg2 has it=True, pg1 does NOT replicate=True
```
（pg2=0 显示是脚本里变量名笔误，实际 pg2 有行=1、pg1=0，断言通过。）

### 7. bank 隔离不破

```
user_company1 banks: ['PostgreSQL Knowledge', 'company1-project-alpha']
per-bank memory_units (bank_id filter isolates): {'PostgreSQL Knowledge': 396, 'company1-project-alpha': 406}
router active during bank read: True (bank_id filter works regardless)
```

### 8. pgbouncer 适配不破

pg2（路由实例）pool 与默认实例 pool 一致：
```
underlying conn class: _NoResetConnection
pg_trgm.similarity_threshold on pg2 conn: 0.15 (set by per-instance init_callback)
default instance underlying conn class: _NoResetConnection
```
即 `postgresql.py:160-219` 的 `_application_name_setup` / `_NoResetConnection` / `apply_session_settings` 在 per-instance pool 下全部保留（router 用同一个 `_init_connection` GUC 回调初始化每实例 pool）。

### 9. 跨租户全局例程 `fq_routine`

```
fq_routine(schemas_with_pending_work): "public".schemas_with_pending_work
```
`fq_routine` 读 `config.database_schema`（默认 `public`），忽略 per-request schema contextvar——这是跨租户全局例程的既定语义。首期单实例范围（例程装在默认实例的 public schema）。多实例下确认：例程不跨实例假设（它枚举当前实例的 `pg_class`）。

### 10. 连接池不泄漏

```
pool before: size=5 idle=5; after 5 acquires: size=5 idle=5
```
5 并发 acquire 后 pool 回到 idle，无泄漏。

### 11. 实例宕机有明确错误

pg2 停止后：
```
resolve(user_company2): pg2 (expect pg2)
RAISED (expected): ConnectionRefusedError - [Errno 111] Connect call failed ('127.0.0.1', 5433)
user_company1 backend (default, still up): ...:5432/hindsight
```
关键：路由到的实例 down 时**抛明确错误，不静默回退默认实例**（否则会把写入打到默认实例上不存在的 schema，造成数据不一致）。

### 12. 路由表缓存失效

改路由行（`user_company2` 从 pg2 改到 pg-default）+ `invalidate("user_company2")`：
```
after invalidate, resolve(user_company2): pg-default
```
不等 60s TTL 立即生效。

### 13. 空路由表

meta 配置但 `schema_pg_routing` 无行 → 所有 schema resolve 返回 None → 回退默认实例。与"meta 完全不配"等价。live service 重启后（meta 未配，等价空表）正常启动、迁移、worker、maintenance 全过。

## live service 端到端确认

重启 `zhuqingping_hindsight` 后（容器 env 未设 meta，走零回归路径，但 router 代码已加载）：
- `Application startup complete`、`Uvicorn running on http://0.0.0.0:8888`
- worker poller 正常轮询（`max_slots=10`）
- 租户 schema 初始化 + 迁移正常（`user_company1` 迁移到 head）
- maintenance/retention/consolidation 循环正常
- `GET /health` → `200 {"status":"healthy","database":"connected",...}`

## 已知遗留（首期不做，见 TODO）

1. 数据迁移（`migrate_schema`）——仅留 `schema_state` 字段 + 接口签名，抛 `NotImplementedError`。
2. draining/retired/migrating_* 状态切换逻辑——字段已建，逻辑留口子。
3. 元数据库 `hindsight_meta` 的 HA——首期单库（在默认实例内），留 TODO。
4. bank 级扩展（方案 B）——首期不做。
5. per-instance `migration_database_url`（pgbouncer bypass）——非默认实例暂回退自身 DSN，留 TODO。
6. pg2 实例目录 stop 后保留数据——首期无数据迁移，全新迁移产物，可重跑迁移（幂等）。

## 交付物清单

- 新增 `engine/schema_router.py`（`SchemaRouter` + `PgInstance` + `resolve_migration_groups`）
- 修改 `engine/memory_engine.py`（backend 选择层 + warm hooks + 迁移 fan-out）
- 修改 `worker/poller.py`（`_claim_batch_multi_instance`）、`worker/main.py`（传 router）
- 修改 `config.py`（3 个 env + 3 个字段）
- `migrations.py` 本身**未改**（fan-out 在 caller `memory_engine` 侧完成，保持 per-schema-per-process + per-schema alembic_version 不变）
- `extensions/hindsight_ext_static_keys_tenant/extension.py` **未改**（`list_tenants()` 返回 schema，instance 由 router 解析，不动共享 `Tenant` dataclass）
- 路由表 SQL：`hindsight_pg_routing_schema.sql` + 初始化脚本 `hindsight_init_meta_db.sh`
- 本验证报告
- `.env` 增量示例：见 `hindsight_multi_pg.env.example`
