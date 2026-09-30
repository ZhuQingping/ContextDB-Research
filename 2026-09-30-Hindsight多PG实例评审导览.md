# Hindsight schema 级多 PG 横向扩展（首期）—— 评审导览

> 生成日期：2026-09-30
> 配套：设计文档 `2026-09-29-Hindsight多PG实例横向扩展方案.md`、验证报告 `2026-09-30-Hindsight多PG实例验证报告.md`
> 环境：容器 `zhuqingping_hindsight`；默认实例 pg0 `127.0.0.1:5432`（PG 18.1, pgvector 0.8.5）；第二实例 pg0 `pg2` `127.0.0.1:5433`
> 代码改动位置：全部在容器内（容器无 git；宿主副本只读、未改动）

---

## 1. 修改的代码在哪里

容器：`zhuqingping_hindsight`。改动在容器内 `/app/api/` 下（editable 安装，改了立即生效）。

| 文件 | 容器内绝对路径 | 状态 | md5(前12) |
|---|---|---|---|
| config.py | `/app/api/hindsight_api/config.py` | **改** | `81ca36fe15bd` |
| engine/memory_engine.py | `/app/api/hindsight_api/engine/memory_engine.py` | **改** | `c06525fcfd43` |
| engine/schema_router.py | `/app/api/hindsight_api/engine/schema_router.py` | **新增** | `b09e6a0c8cb6` |
| worker/poller.py | `/app/api/hindsight_api/worker/poller.py` | **改** | `14fc1b194328` |
| worker/main.py | `/app/api/hindsight_api/worker/main.py` | **改** | `47133e49a3e0` |
| migrations.py | `/app/api/hindsight_api/migrations.py` | **未改**（md5=`b3e967b0e16a`，与宿主原件一致，已核对） | — |
| extensions/.../extension.py | `/app/extensions/hindsight_ext_static_keys_tenant/extension.py` | **未改** | — |

**未碰核心**：`engine/search/`、`engine/retain/`、`engine/memories/` 零改动。

### 复核方式
- 宿主有一份同源只读副本：`/rri/zhuqingping/Code/ContextDB/hindsight/hindsight-api-slim/hindsight_api/`
  - 可对 `migrations.py` 做 md5 比对，确认未改（`b3e967b0e16af1aca321d535916fb87e`）。
  - 改动文件（config/memory_engine/schema_router/poller/main）无宿主副本可比（容器内 editable 安装），可直接 `docker exec zhuqingping_hindsight cat <path>` 查看，或 `docker cp` 拉出来看。
- 改动文件镜像备份在宿主 `/tmp/hindsight_edit/`（与容器 md5 一致），可作复核参照。

---

## 2. High level / Low level 设计在哪里

都在 **ContextDB-Research 仓库**（宿主 `/rri/zhuqingping/Code/ContextDB/ContextDB-Research/`）：

| 文档 | 路径 | 内容 |
|---|---|---|
| 设计文档（主） | `2026-09-29-Hindsight多PG实例横向扩展方案.md` | high level（§一~三：问题/方案选型/具体方案架构）+ **low level（§low level 设计，第 428 行起，checkbox 已全部勾完 ✓，32 勾 / 0 未勾）** |
| 验证报告 | `2026-09-30-Hindsight多PG实例验证报告.md` | 13 项逐项结果 + 证据 |
| 路由表 DDL | `hindsight_pg_routing_schema.sql` | 三表 + 索引 + 默认实例登记 |
| 初始化脚本 | `hindsight_init_meta_db.sh` | 建 `hindsight_meta` 库 + 跑 DDL + 登记 `pg-default` |
| .env 增量示例 | `hindsight_multi_pg.env.example` | 3 个 env + 注册/路由 SQL 示例 |
| 实现计划（评审用） | `~/.claude/projects/-rri-zhuqingping-Code-ContextDB-ContextDB-Research/plans/hindsight-multi-pg.md` | 计划全文（含关键决策与风险） |
| 本评审导览 | `2026-09-30-Hindsight多PG实例评审导览.md`（本文） | 改动位置 / 设计位置 / 测试 / 关键决策 |

设计文档 low-level 章节已与代码同步：每个组件的类/方法签名、SQL、改动点、边界处理都已写入，checkbox 全勾。

---

## 3. 做了哪些测试，是否可复现

**13 个验证脚本，全部在容器 `/tmp/` 下，可逐个复现**（每个脚本独立、幂等、带断言）：

| 验证项 | 脚本 | 验证清单对应 |
|---|---|---|
| 路由层单元（空表/缓存/invalidate） | `/tmp/test_router_unit.py` | #2 / #12 |
| 零回归（meta 未配） | `/tmp/test_zero_regression.py` | #1 |
| router 激活（空路由表=默认） | `/tmp/test_router_active.py` | #13 |
| 迁移分组 | `/tmp/test_migration_groups.py` | #3 前置 |
| 跨实例迁移（alembic_version） | `/tmp/test_cross_instance_migrate.py` | #3 |
| 引擎完整 init（meta 配置） | `/tmp/test_engine_init_meta.py` | #2 |
| worker 跨实例 claim | `/tmp/test_worker_cross_instance.py` | #4 |
| 实例宕机明确报错 | `/tmp/test_instance_down.py` | #11 |
| 读副本 per-instance + 缓存失效 | `/tmp/test_readreplica_and_invalidate.py` | #5 / #12 |
| schema/bank 隔离 | `/tmp/test_isolation.py` | #6 / #7 |
| pgbouncer 适配（严格） | `/tmp/test_pgbouncer_strict.py` + `/tmp/test_pgbouncer_routine_leak.py` | #8 / #9 / #10 |
| recall 读后端路由 | `/tmp/test_recall_routing.py` | #2 读路径 |

### 复现方法
每个脚本顶部已设好所需 env（`HINDSIGHT_API_META_DATABASE_URL` 等）。运行：
```
docker exec zhuqingping_hindsight /app/api/.venv/bin/python3 /tmp/test_<name>.py
```

**注意事项**：
- `test_worker_cross_instance.py` / `test_isolation.py` 需 pg2（5433）在线——脚本本身不启动 pg2。
- `test_instance_down.py` 会停 pg2，跑完需手动重启 pg2（`EmbeddedPostgres(name="pg2",port=5433).ensure_running()`）。
- 其余脚本幂等可重跑。

### live service 验证
重启容器后（meta 未配）`GET /health` → `200 {"status":"healthy","database":"connected"}`，确认零回归路径在真实运行服务中生效（代码已加载、服务正常启动、迁移/worker/maintenance 正常）。

### 13 项验证结果汇总（全通过）

| # | 验证项 | 结果 |
|---|--------|------|
| 1 | 默认行为零回归（meta 未配） | ✅ |
| 2 | opt-in 路由正确 | ✅ |
| 3 | 迁移跨实例 + 版本独立 | ✅ |
| 4 | worker 跨实例调度 | ✅ |
| 5 | 读副本 per-instance | ✅ |
| 6 | schema 隔离不破（跨租户、跨实例） | ✅ |
| 7 | bank 隔离不破 | ✅ |
| 8 | pgbouncer 适配不破 | ✅ |
| 9 | 跨租户全局例程 `fq_routine` | ✅ |
| 10 | 连接池不泄漏 | ✅ |
| 11 | 实例宕机有明确错误 | ✅ |
| 12 | 路由表缓存失效 | ✅ |
| 13 | 空路由表 | ✅ |

逐项证据见验证报告 `2026-09-30-Hindsight多PG实例验证报告.md`。

---

## 4. 关键决策与"按我建议落地"的项

**两处记录，内容一致，互相印证：**

**(a) 实现计划文件** `~/.claude/projects/-rri-zhuqingping-Code-ContextDB-ContextDB-Research/plans/hindsight-multi-pg.md`
- §"Decisions locked (with user)" — 4 个请你确认的决策
- §"⚠️ Critical: pool_getter lambdas..." — 发现并建议的关键机制问题（**重点复核项**）
- §"Risks / notes" — 风险与边界

**(b) 记忆文件** `~/.claude/projects/-rri-zhuqingping-Code-ContextDB-ContextDB-Research/memory/hindsight-multi-pg-project.md`
- "Implementation facts" 段：每处改动的行号/方法
- "CRITICAL design finding" 段：pool_getter 问题与解法

### 需重点复核的决策清单

| # | 决策 | 我的建议 | 落地位置 | 为何建议如此 |
|---|---|---|---|---|
| D1 | Router 激活方式 | **env 门控 opt-in**（meta 未配→router=None，单 backend 路径完全不动） | `memory_engine._get_backend` | 最强零回归保证；现有部署不走新代码路径 |
| D2 | poller 跨实例模型 | **claim_batch 内 per-instance fan-out**（按实例分组，每实例在自己的 pool 上 claim） | `poller._claim_batch_multi_instance` | 复用现有 `_claim_batch_on_conn` 公平轮转；执行路径自动经 `_get_backend` 路由 |
| D3 | 迁移测试范围 | **pg2 上配新 schema**（不复制数据） | `test_cross_instance_migrate.py` | 首期不涉数据迁移；证明版本表 per-schema 跟 schema 走 |
| D4 | meta 库位置 | **默认 pg0 实例内的独立 `hindsight_meta` 库** | `hindsight_init_meta_db.sh` | 自包含、无额外服务；HA 留 TODO |
| D5 | 第二实例方式 | **方案② 容器内 pg0 第二实例**（非方案①宿主 docker） | `EmbeddedPostgres(name="pg2",port=5433)` | 宿主 docker 代理挂、无 pgvector 镜像；方案②无外部依赖 |
| **D6** | **pool_getter 是否需 schema-aware** | **必须**（原 prompt 未枚举） | 4 处 `pool_getter=self._pool_for_current_schema` + 2 处 warm hook | **机制必需**：3 个 `pool_getter=lambda:self._backend` 子系统（BrokerTaskBackend/AuditLogger/LLMTraceRecorder）+ file storage 绕过 `_get_backend()`，写 schema 限定表；不处理则路由到 pg2 的 schema 写入会打到默认 pg1（schema 不存在→fail）。**这是与原 prompt"所有 `_get_backend()` 调用点不变"字面表述的偏离，我建议落地，请重点复核** |
| D7 | Tenant dataclass 是否加 pg_instance_id | **不加**（router 是 instance 单一来源） | `extension.py` 未改 | 避免动共享 `Tenant` dataclass（其他 extension 实现） |
| D8 | 实例宕机行为 | **抛明确错误，不静默回退默认** | `get_backend_for_schema` 不 catch acquire 失败 | 静默回退会把写入打到错误实例（schema 不存在）→数据不一致风险 |
| D9 | 缓存 miss 回退 | **回退默认 backend**（wrong-instance 查询 fail-fast，不静默写坏） | `backend_for_schema` | sync 路径不能 await meta 查询；warm 在请求入口预热降低 miss |
| D10 | 迁移 fan-out 位置 | **在 caller `memory_engine` 侧，不改 `migrations.py`** | `memory_engine.initialize` PG 分支 | 保持 per-schema-per-process + per-schema alembic_version 不变；`migrations.py` 稳定 |

### 建议复核顺序
1. **D6**（与 prompt 偏离、机制核心）—— 重点
2. **D1 / D8 / D9**（安全边界：零回归、实例宕机、缓存 miss）
3. **D2**（worker 调度模型）
4. **D5**（环境适配：第二实例方式）
5. 其余

---

## 附：改动点速查（容器内行号，供复核定位）

**engine/schema_router.py（新增）**
- `class PgInstance`（dataclass）：pg_instance_id/host/port/.../status + 懒建 `backend`/`read_backend` + `backend_owned_externally` 标记
- `class SchemaRouter`：
  - `__init__`（meta_url, default_pg_instance_id, backend_type, ttl_s, pool 规格, init_callback_builder, default_dsn, default_backend）
  - `initialize()` / `_load_instances()` / `shutdown()`
  - async `resolve(schema)` / `warm(schema)` / `get_pool(pg_instance_id)` / `get_backend_for_schema(schema)` / `get_read_backend_for_schema(schema)` / `group_schemas_by_instance(schemas)` / `reload_instances()` / `migrate_schema(...)`(stub)
  - sync `backend_for_schema(schema)` / `read_backend_for_schema(schema)`（只读 TTL 缓存，miss→默认）
  - `invalidate(schema)` / `invalidate_all()`
- 模块函数 `resolve_migration_groups(meta_url, schemas, default_dsn, default_instance_id)`

**engine/memory_engine.py（改）**
- `__init__`：新增 `self._router: SchemaRouter | None = None`；import `SchemaRouter`
- 新增 sync `_pool_for_current_schema()` / `_read_pool_for_current_schema()` / async `_warm_router_cache(schema)`
- 4 处 `pool_getter=lambda: self._backend` → `pool_getter=self._pool_for_current_schema`（task backend ~2673、audit ~2682、llm trace ~2696、file storage ~5334）
- warm hook：`_authenticate_tenant`（`_current_schema.set` 后）/ `_execute_task`（`_current_schema.set` 后）
- `_get_pool` / `_get_backend` / `_get_read_backend`：router 激活时按 schema 路由
- `initialize()`：`self._backend.initialize` 后构建 router（default_backend=mem._backend，不重复建 pool）；PG 迁移分支按实例分组 fan-out（`resolve_migration_groups` → per-instance `run_migrations_for_schemas` via `asyncio.gather`）
- `close()`：router.shutdown()

**config.py（改）**
- ENV：`HINDSIGHT_API_META_DATABASE_URL` / `HINDSIGHT_API_DEFAULT_PG_INSTANCE` / `HINDSIGHT_API_SCHEMA_ROUTER_TTL`
- 字段：`meta_database_url` / `default_pg_instance` / `schema_router_ttl_s`（loader 接线）

**worker/poller.py（改）**
- `WorkerPoller.__init__` 加 `router=` 参数；`TYPE_CHECKING` import `SchemaRouter`
- `claim_batch`：router 激活时走 `_claim_batch_multi_instance`（group by instance → per-instance pool acquire → `_claim_batch_on_conn`）
- 模块函数 `_has_capacity(availability)`

**worker/main.py（改）**
- poller 构造传 `router=getattr(memory, "_router", None)`

**migrations.py / extension.py：未改**

---

## 附：已知遗留 TODO（首期不做，接口/字段已留）

1. 数据迁移（`migrate_schema`）—— 签名留，抛 `NotImplementedError`（第二阶段做）
2. `pg_instances.status` draining/retired 切换逻辑 —— 字段已建，逻辑留口子
3. `schema_pg_routing.schema_state` migrating_out/migrating_in/frozen 切换逻辑 —— 字段已建，逻辑留口子
4. `hindsight_meta` 元库 HA —— 首期单库（在默认实例内），TODO
5. bank 级扩展（方案 B）—— 首期不做
6. per-instance `migration_database_url`（pgbouncer bypass）—— 非默认实例暂回退自身 DSN，TODO
7. pg2 实例目录 stop 后保留数据 —— 首期无数据迁移，全新迁移产物，可重跑迁移（幂等）
