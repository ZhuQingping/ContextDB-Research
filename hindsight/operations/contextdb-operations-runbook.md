# ContextDB 运维与故障定位手册

适用：华为云独享实例，节点 Agent 管理 ECS 上的 Hindsight 容器，外部 PG 保存管理元数据与工作空间数据。命令以本分支代码为准；首版一个容器，API 8888、UI 9999，Worker 内置于 API 进程，不启用独立 8889 端口，实际地址由部署合同传入。值班时先定位层次，再处理；不要用重建实例或清空任务表作为通用修复。

## 1. 运维时先准备什么

每个实例保存一份部署记录：实例/租户 ID、镜像摘要与代码版本、PG 主机/端口/数据库/服务角色、全文后端及扩展版本、模型与地址、端口、Worker 拓扑和稳定 ID、配置版本、最近备份与变更时间。秘密另存受控存储，不写入部署记录或普通工单。

| 责任方 | 负责处理 |
| --- | --- |
| 华为云管控 / 节点 Agent | 创建实例、持久配置、容器启停/升级、资源与网络、密码变更下发、监控采集 |
| Hindsight 节点开发 | API/UI/Worker/扩展的代码与诊断、原生任务及空间生命周期问题 |
| RDS 运维 | 账号、插件、容量、锁、慢 SQL、备份/PITR/主备 |
| MaaS 运维 | 密钥有效性、模型权限、配额/限流、模型服务故障 |

进入容器使用部署记录中的确切容器名。下列 Shell 示例使用 Bash；先替换实际路径，配置文件是受信任的运维文件，不能 source 客户任意上传内容。

```bash
export API_URL='http://127.0.0.1:8888'
export UI_URL='http://127.0.0.1:9999'
# 先用 docker compose ps 核对实际容器名；以下是示例。
export CONTAINER='contextdb-hindsight-1'
# 宿主机上的持久运行目录，不是容器内的 /var/lib/contextdb。
export CONTEXTDB_DEPLOY_DIR='/srv/contextdb/runtime'
export CASE_DIR="/var/tmp/contextdb-diagnose-$(date +%Y%m%d-%H%M%S)"
umask 077
mkdir -m 700 "$CASE_DIR"
```

本地源码运行时先按照部署手册设置 CODE、PY 和 PYTHONPATH。容器内应使用同镜像的工具，不临时安装另一版本 Hindsight。部署目录中的数据库 URL、pepper、UI 密码和 Admin Key 都是秘密；不要执行 `env`、`docker inspect` 全量导出或 `set -x` 后提交日志。

## 2. 五分钟判断故障在哪一层

```bash
curl -sS --connect-timeout 2 --max-time 5 "$API_URL/health/live"
curl -sS --connect-timeout 2 --max-time 10 "$API_URL/health/ready"
curl -sS --connect-timeout 2 --max-time 5 -o /dev/null -w '%{http_code}\n' "$UI_URL"
docker ps --filter "name=$CONTAINER" --format '{{.Names}} {{.Status}} {{.Ports}}'
docker stats --no-stream "$CONTAINER"
```

curl 成功建立 HTTP 连接不等于业务成功，核对状态码和返回体。UI 返回登录页也不代表后台 Admin Key 正确；需进一步验证实际工作空间列表。

| 现象 | 优先检查 | 处理方向 |
| --- | --- | --- |
| live 超时，容器退出/OOM | 退出状态、CPU/内存、事件循环阻塞日志 | 先留存证据，再由 Agent 定向重启；不要重启整台 PG |
| live 200、ready 503 | PG 网络、账号、连接池等待、数据库负载 | 修复依赖；readiness 摘流，不因 PG 短暂不可用触发全实例重启 |
| ready 200、retain/reflect 慢 | MaaS 单次延迟、重试、并发和任务积压 | 区分模型慢与队列慢；不要只增大超时 |
| API 正常、UI 502/无法加载空间 | UI 服务端 API URL、后台 Admin Key、API 可达性 | 首版同容器内使用 loopback；后台密钥在 UI 服务端配置 |
| 401/403 | Key、用户状态、授权空间、只读/读写、pepper | 区分认证失败与授权拒绝；不把 Admin Key 交给业务规避检查 |
| 404 | bank_id 是否存在且 active，是否错误使用内部 UUID/旧名称 | 从空间目录核对可读 bank_id 与对象身份 |
| 管理写入 409/412/428 | 名称冲突、版本或 If-Match、操作状态 | 读取最新对象；不能无条件重放删除来“消除报错” |
| 创建/删除空间等待或失败 | 空间 state、请求 ID、API 日志、PG 锁/DDL、原生任务 | 同步响应未知不等于回滚；核对原对象及实际执行进程 |
| 外部机器访问失败 | 监听地址、端口映射、安全组、入口 TLS/反向代理 | 默认监听0.0.0.0不等于安全组已开放；按实际部署地址验证 |

健康检查的原生说明见 [Monitoring](https://hindsight.vectorize.io/developer/monitoring)。liveness 使用 `/health/live`，readiness 使用 `/health/ready`；后者会检查数据库。健康通过不证明 MaaS、中文效果或业务授权均正常。

## 3. 日志、请求和任务怎样关联

推荐 API 与 Worker 使用以下运维配置：

```dotenv
HINDSIGHT_API_LOG_LEVEL=info
HINDSIGHT_API_LOG_FORMAT=json
HINDSIGHT_API_OTEL_TRACES_ENABLED=false
```

需要接入现有 OpenTelemetry 平台时再开启 traces，并设置 `HINDSIGHT_API_OTEL_EXPORTER_OTLP_ENDPOINT`、`HINDSIGHT_API_OTEL_SERVICE_NAME`、`HINDSIGHT_API_OTEL_DEPLOYMENT_ENVIRONMENT`；认证头另按秘密传入。是否可记录原文/提示词需按客户数据策略配置，不能为排障全量打印业务内容。不要长期使用 debug。

```bash
docker logs --since 15m --timestamps "$CONTAINER" > "$CASE_DIR/hindsight.log" 2>&1
docker inspect --format '{{json .State}}' "$CONTAINER" > "$CASE_DIR/container-state.json"
docker inspect --format '{{.Image}}' "$CONTAINER" > "$CASE_DIR/container-image.txt"
curl -fsS --max-time 10 "$API_URL/metrics" > "$CASE_DIR/api-metrics.txt"
```

首版 API、内置 Worker 与 UI 的 stdout/stderr 由同一容器日志收集，按时间、进程/日志来源和请求信息区分。

这些文件仍可能包含客户数据或第三方错误正文，仅限实例授权运维查看，脱敏后才进入工单。不要直接打包部署目录、完整 inspect、凭据、请求体或原生 llm_requests 内容。

定位链路分两条：

- 管理请求：记录响应 `X-Request-ID` / 错误体 `request_id`、HTTP 状态、可读 bank_id、内部 workspace_id 和状态。创建、删除同步执行，不返回管理 operation_id。
- 原生业务：记录 bank_id、请求时间、原生返回的 operation_id（异步时），以及可用的 trace ID。不要假定所有原生接口都返回 ContextDB 管理层的 X-Request-ID。

本期没有承诺一条现成的全链路日志系统；Agent 负责统一采集 stdout/stderr、保留和检索。日志轮转应设置大小/文件数或接入平台采集，不能让容器日志无限占满 ECS 磁盘。

## 4. PG：连接、锁、容量与目录检查

用服务端持久配置加载连接，禁止在共享终端输出 URL。下例将私密 URL 转为 libpq service/password 文件，密码不进入 psql/pg_dump 的命令参数。环境和生成文件仍只允许授权运维访问。

```bash
# 在受控节点加载已校验、运维拥有的配置：
set -a
source "$CONTEXTDB_DEPLOY_DIR/api.env"
set +a
# 只读取已加载的秘密环境，不将 URL 或密码打印到终端。
python3 - <<'PYCONF'
import os
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs
url = urlsplit(os.environ['HINDSIGHT_API_DATABASE_URL'])
out = Path(os.environ['CASE_DIR'])
fields = {'host': url.hostname or '', 'port': str(url.port or 5432),
          'dbname': unquote(url.path.removeprefix('/')), 'user': unquote(url.username or '')}
for key in ('sslmode', 'sslrootcert', 'sslcert', 'sslkey', 'connect_timeout'):
    value = parse_qs(url.query).get(key)
    if value:
        fields[key] = value[0]
password = unquote(url.password or '')
if any('\n' in v or '\r' in v for v in [*fields.values(), password]):
    raise SystemExit('Invalid connection file value')
def save(name, value):
    target = out / name
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value)
save('pg_service.conf', '[contextdb]\n' + ''.join(f'{k}={v}\n' for k,v in fields.items()))
def escape(value):
    return value.replace('\\', '\\\\').replace(':', '\\:')
save('pgpass', ':'.join(escape(fields[k]) for k in ('host','port','dbname','user')) + ':' + escape(password) + '\n')
PYCONF
export PGSERVICEFILE="$CASE_DIR/pg_service.conf"
export PGPASSFILE="$CASE_DIR/pgpass"
export PGSERVICE=contextdb
psql -X -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_database(), current_user, version();
SELECT extname, extversion FROM pg_extension ORDER BY extname;
SELECT instance_id, cloud_tenant_id, metadata_version FROM ctxdb_meta.deployment_info;
SELECT workspace_id, bank_id, schema_name, state, version
FROM ctxdb_meta.workspaces ORDER BY created_at;
SELECT state, count(*) FROM ctxdb_meta.workspaces GROUP BY state;
SELECT workspace_id,bank_id,schema_name,state,version,updated_at,
       metadata->>'error_code' AS error_code
FROM ctxdb_meta.workspaces WHERE state<>'active' ORDER BY updated_at;
SELECT state, wait_event_type, wait_event, count(*)
FROM pg_stat_activity WHERE datname=current_database()
GROUP BY state,wait_event_type,wait_event ORDER BY count(*) DESC;
SELECT pid, usename, state, wait_event_type, wait_event,
       now()-xact_start AS transaction_age, pg_blocking_pids(pid) AS blockers
FROM pg_stat_activity
WHERE datname=current_database() AND pid<>pg_backend_pid()
ORDER BY xact_start NULLS LAST;
SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
SQL
```

普通服务角色看到的其他会话信息可能受限；只在授权诊断账号中查看更多，不为运行服务赋予 SUPERUSER。管理元数据只读排查，不手工修改 state、version 或 workspace_id。

连接池按**总进程数**估算：每个 API 进程和独立 Worker 都有池，ContextDB 元数据复用主池；迁移、监控和其他客户端另留余量。增加进程或 Worker 时，不能简单沿用单进程 pool_max 后相乘超出 RDS max_connections。先看 acquire 等待、活跃查询、锁和模型耗时，再决定加池还是降并发。

`pg_stat_statements` 不是业务必需。平台允许时由 RDS 配置预加载并重启，目标数据库再 CREATE EXTENSION；只安装扩展不能保证统计已启用。不要在故障现场未经安排修改 shared_preload_libraries 或重启 PG。

## 5. 原生 Worker 积压和恢复

先从元数据查询 schema，避免根据客户输入直接拼 SQL 标识符：

```bash
export BANK_ID='mysql'
SCHEMA=$(psql -X -v ON_ERROR_STOP=1 -At -v bank="$BANK_ID" <<'SQL'
SELECT schema_name FROM ctxdb_meta.workspaces WHERE bank_id=:'bank' AND state='active';
SQL
)
test -n "$SCHEMA"
hindsight-admin worker-status --schema "$SCHEMA"
```

`hindsight-admin` 直接连接 PG，不走 REST 和业务 Key 鉴权；必须在受控节点使用同版配置执行。原生命令默认 schema 可能是 public，不显式指定会查错位置。

查看原生任务状态时只取必要字段：

```bash
psql -X -v ON_ERROR_STOP=1 -v schema="$SCHEMA" <<'SQL'
SELECT status, operation_type, count(*), min(created_at) AS oldest
FROM :"schema".async_operations GROUP BY status,operation_type;
SELECT operation_id, bank_id, status, worker_id, claimed_at, updated_at
FROM :"schema".async_operations
WHERE status IN ('pending','processing') ORDER BY created_at LIMIT 50;
SQL
```

Worker ID 必须稳定且每个执行者唯一。确认旧 Worker 已停止/失去执行能力，并隔离其重启后，才能释放其任务供新执行者领取；不能在旧进程仍执行时强制转交：

```bash
# 这是修改任务状态的恢复命令；先按上述步骤确认旧执行者已停止。
hindsight-admin decommission-worker 'ctxdb-demo-worker-0' --schema "$SCHEMA"
```

优雅 SIGTERM、等待在途任务结束应先于强制退出。不要批量释放所有健康 Worker，也不要直接把所有 processing 更新为 pending。空间响应未知时须另行核对原调用与残留，任务恢复不等于空间管理恢复。[原生 Admin CLI](https://hindsight.vectorize.io/developer/admin-cli)。

## 6. MaaS、检索和权限问题

| 症状 | 检查方法与处理 |
| --- | --- |
| MaaS 401/403 | 验证密钥有效性、模型授权和目标地址；只在私密环境探测，不把响应里可能回显的请求配置上传 |
| MaaS 400 | 核对具体接口字段和模型支持；bge-m3 不发送 dimensions；本次实测 rerank 要 query，不是旧样例的 input |
| MaaS 429 | 看实例/账号总并发及配额，降低写入和模型并发并有界退避；多个Worker共享同一模型配额，扩容不会自动增加配额 |
| MaaS 超时或 5xx | 对比 DNS/TLS/连接耗时与模型生成耗时，记录超时/重试预算和 token；不要关闭 TLS 校验 |
| retain 成功但 recall 找不到 | 核对是否提取到事实、原生任务是否完成、bank_id/授权、时间/tag/预算/阈值；原文已保存不等于生成了可检索事实 |
| 英文正常、中文关键词差 | 核对全文后端、实际分词、索引状态；向量召回成功不能替代中文关键词验收 |
| 吊销/停用似乎没生效 | 使用原 Key 发新请求，核对是否误用Admin Key；浏览器旧列表或已返回的数据不等于新请求被放行 |

第一版模型固定由运维配置，不增加客户模型选择页面。更改 embedding 维数或模型不是普通换密钥，涉及已有向量和索引，需要受控迁移/重建；LLM 更换也要验证结构化提取、consolidation 和 reflect，不能只测一条 chat。

## 7. 备份、恢复和升级

必须共同备份：**整库 PG 数据、私密部署目录、镜像摘要与配置版本、原生文件/对象存储（如启用）**。只备份某个 Bank 或只备份 ctxdb_meta 都不足以恢复完整实例。pepper 遗失会使原 Key 无法校验；仅从 PG 摘要不能找回它。

```bash
# 在受控环境，使用既有PG认证，不将含密码连接串放进工单：
pg_dump --format=custom --file="$CASE_DIR/contextdb.dump"
pg_restore --list "$CASE_DIR/contextdb.dump" > "$CASE_DIR/restore-list.txt"
```

上面仅检查归档目录，不证明恢复成功。恢复演练须在新建、空的隔离数据库执行，预装相同插件，再 pg_restore --exit-on-error；启动同版实例，验证管理员认证、用户Key、两空间内容、任务和中文检索。秘密备份加密，访问权限与保留策略由平台负责。恢复正在执行的任务时先确认原实例写入者已停，避免两个实例同时执行同一工作。

首版 RDS 使用 native + english，不包含 PGroonga/Groonga。以下仅适用于历史自建PG的PGroonga试验库：PGroonga 的 crash-safe、WAL、物理备份和主备有专门要求；不能由“PG支持PITR”推导“任意PGroonga配置都安全”。PG节点需依据实际版本部署对应组件，并单独演练逻辑恢复、物理恢复及切换；本机逻辑恢复通过不能代替云RDS主备验收。[PGroonga 流复制要求](https://pgroonga.github.io/reference/streaming-replication.html)。

升级顺序：旧版先排空pending/processing原生任务 → 摘流并停止该实例全部API/Worker写入 → 备份数据库并保留秘密部署目录 → 执行新版本预检及受支持迁移 → 启动新API/Worker → readiness → UI → 管理与业务冒烟 → 恢复流量。旧镜像不一定能读新元数据结构；涉及不可逆迁移时回退要恢复升级前的数据库与匹配配置，不能只回滚镜像。

不得使用原生 rename-bank、原生删除Bank或手工schema改名绕过ContextDB管理目录；这些操作会破坏工作空间映射或授权。客户面空间生命周期统一走扩展管理API/UI。

## 8. 告警、故障记录和学习顺序

优先告警：API错误率与p95、ready状态、Worker最旧pending/processing任务年龄、空间管理失败及未知状态、PG连接/锁/磁盘、MaaS失败/429/延迟、容器OOM/重启、日志磁盘与最近成功备份时间。阈值根据实例规格和基线压测设置，不提供未经实测的通用吞吐承诺。

每次故障使用以下模板，保留时间线，不记录秘密：

```text
实例/版本/镜像摘要：
发生时间、影响范围、最近变更：
接口与HTTP状态、request_id/operation_id/bank_id：
API/UI/Worker健康与资源：
PG连接/锁/容量：
MaaS状态与耗时：
已执行命令、修改内容及结果：
恢复时间、数据完整性检查：
根因、预防措施、负责人：
日志/指标/备份证据位置（已脱敏）：
```

学习按请求路径进行：先读 [Hindsight Services](https://hindsight.vectorize.io/developer/services) 和 [配置说明](https://hindsight.vectorize.io/developer/configuration)，理解API与Worker；再读 [Monitoring](https://hindsight.vectorize.io/developer/monitoring) 和 [Admin CLI](https://hindsight.vectorize.io/developer/admin-cli)，练习健康/积压/单Worker恢复；最后练习 [PG监控](https://www.postgresql.org/docs/current/monitoring.html)、[备份恢复](https://www.postgresql.org/docs/current/backup.html)；本期 RDS 不安装 PGroonga/Groonga。

复现时使用同版最小配置、脱敏数据和可重复步骤，先搜索 [Hindsight Issues](https://github.com/vectorize-io/hindsight/issues)；准备版本、预期/实际结果、最小复现和安全日志再提问。官网可能描述比本交付更新的版本，操作参数以本镜像的 --help 与代码为准。

## 首版功能边界与空间失败处理

`HINDSIGHT_API_LLM_TRACE_ENABLED=false`、`HINDSIGHT_API_AUDIT_LOG_ENABLED=false`固定关闭，原生持久调用正文、业务审计和 Webhook 尚未完成独立 schema 路由与存储归属验收，不为排障临时开启。`ctxdb_meta.audit_events` 管理事务审计、运行日志、原生任务、PG 统计与按需 OTEL 保留。

原生任务 cancelled 不证明执行者已退出。本版复用原生执行、取消和缓存机制，不提供完整执行屏障、可靠繁忙探测、跨进程瞬时缓存失效或删除后旧请求隔离保证。删除前管理员必须停业务、等待已受理任务及后台工作结束；同名重建也遵守该前提。内置 Worker 没有独立8889探针，结合原生任务积压和异步 retain 最终完成判断。

| 查询结果 | 处理方法 |
| --- | --- |
| active | 正常访问；删除前停业务并等待，保存对象 UUID 和 ETag |
| failed | 确认原调用已结束，核对同一 UUID、schema 归属及外部依赖，再用当前 ETag 发 DELETE；不以 POST 接管同名残留 |
| creating/deleting 或响应未知 | 先查 API 日志、PG 锁/DDL 和相关进程；不按等待时长判定结束，不自动重发写入。当前 API 返回409，无自动恢复/强制解锁入口。必要时停止所有可能执行的相关进程，再由服务所有者核对残留 |
| 空间行不存在但同名 schema 尚在 | CREATE 返回 schema_conflict409；核对归属和备份后人工处理，不自动接管 |
| DELETE204 | schema、对应授权和空间行完成最终事务清理，保留管理审计；原生外部文件清理遵守 best-effort，不承诺零残留 |

旧对象 ETag 不可更新为同名新对象的 ETag 后重试删除。原生 v1.0.0 数据库连接串日志可能含凭据的问题未随本特性修复，由[独立 Issue #3](https://github.com/ZhuQingping/ContextDB-Research/issues/3)跟踪；采集和分享日志前须受控脱敏。

## 容器启动报 Illegal instruction / SIGILL

先区分进程崩溃与数据库、鉴权失败。保留镜像摘要、退出码、CPU架构/虚拟化版本和 faulthandler 栈；不要改PG或重新生成秘密。本轮 Colima ARM 环境在 cryptography 的 Rust/OpenSSL 扩展导入时触发 SIGILL，独立的 PG 连接和其他依赖导入正常。

以下命令不挂载配置或连接数据库，只复现已定位的模块导入：

```bash
: "${CONTEXTDB_IMAGE:?设置本次镜像标签或摘要}"
docker run --rm --read-only --entrypoint /app/.venv/bin/python   "$CONTEXTDB_IMAGE" -X faulthandler   -c 'import cryptography.hazmat.bindings._rust; print("crypto import ok")'
# 仅用于对照诊断；在本轮Colima中此覆盖使相同导入成功：
docker run --rm --read-only -e OPENSSL_armcap=0   --entrypoint /app/.venv/bin/python "$CONTEXTDB_IMAGE" -X faulthandler   -c 'import cryptography.hazmat.bindings._rust; print("crypto import ok")'
```

[OpenSSL说明](https://docs.openssl.org/master/man3/OPENSSL_armcap/)中，OPENSSL_armcap控制CPU指令扩展选择，0关闭这些扩展；它不是关闭TLS证书验证的开关。这里只用于判断虚拟CPU能力探测与运行指令是否相容。不要把本机兼容覆盖当作所有ECS的默认配置；目标ECS必须验证实际架构、锁定依赖及原样镜像启动，再决定修复虚拟化环境或采用经验证的兼容措施。本轮容器对照若使用该覆盖，会在结果中单列，不能据此宣布目标ECS默认配置已经验收。


## UI日志出现 .next/cache mkdir 异常

Next图片处理入口在校验请求前初始化缓存，即便外部图片URL最终被400拒绝，只读根文件系统仍可能产生cache目录错误。交付Compose只为UI增加64MiB的 `/app/hindsight-control-plane/standalone/.next/cache` tmpfs，同时保留只读根FS与只读秘密。自定义容器启动命令需保留此挂载：

```bash
# 加到既有UI docker run命令；缓存不是PG数据或秘密目录：
# --tmpfs /app/hindsight-control-plane/standalone/.next/cache:mode=1777,size=64m
```

该缓存可丢弃，不要改成整个 `/app` 可写，也不要为消除日志而放开图片远程域名。当前UI没有配置images.remotePatterns；依赖审计命中版本不等于该部署满足漏洞触发条件，实际适用性及完整发行扫描仍须分别核查。
