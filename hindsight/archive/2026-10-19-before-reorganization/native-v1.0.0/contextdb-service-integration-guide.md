# 原生 Hindsight v1.0.0：管控联调操作指南

本指南与[部署合同](contextdb-deployment-contract.md)配套。目标是先打通“管控 → 节点 Agent → 原生 API/Worker/UI → RDS PG/MaaS”。没有 ContextDB 管理接口和用户管理。所有示例面向一个新建专用库，不接管客户已有业务库。

## 1. 准备官方原生镜像

节点需要Docker及Compose v2、Python3、psql、curl、jq。推荐直接使用官方slim镜像，外部MaaS模式不需要下载本地ML模型。固定版本后记录镜像摘要：

```bash
export HELPERS=/opt/contextdb-source/hindsight-extensions/contextdb-service/deployment/native-v1.0.0
export RUN=/srv/hindsight/runtime
docker pull ghcr.io/vectorize-io/hindsight:1.0.0-slim
export NATIVE_IMAGE=$(docker image inspect ghcr.io/vectorize-io/hindsight:1.0.0-slim --format '{{index .RepoDigests 0}}')
docker image inspect "$NATIVE_IMAGE" --format '{{json .Config.Labels}}'
```

核对镜像标签版本1.0.0-slim与revision `39c65ffe2f140d0c84cee58566cad8900c5b9908`。Agent持久保存批准的摘要，后续不要改用latest。HELPERS连同上一级prepare-pg.sql一起交付即可，不安装自研Python扩展。配置渲染与Compose是节点部署材料，运行镜像仍是上游原生镜像。

若需要源码联调，构建机另装Git、Python3.11、uv、Node24/npm：

```bash
export NATIVE=/opt/hindsight/v1.0.0
git clone --branch v1.0.0 --depth 1 https://github.com/vectorize-io/hindsight.git "$NATIVE"
test "$(git -C "$NATIVE" rev-parse HEAD)" = 39c65ffe2f140d0c84cee58566cad8900c5b9908
cd "$NATIVE"
uv sync --frozen --package hindsight-api-slim
npm ci --no-audit --no-fund
npm run build -w @vectorize-io/hindsight-control-plane
```

## 2. PG 管理员建库并启用扩展

数据库端先安装与 PG 主版本匹配的插件二进制。托管 RDS 从支持列表安装；自行编译 PostgreSQL 时，contrib 和外部插件必须使用目标安装目录的 pg_config。客户端安装插件不影响远端 RDS。

```bash
export PGADMIN_URL='postgresql://provisioner@pg.example.internal:5432/postgres'
read -r -s -p '新服务账号密码: ' CONTEXTDB_NEW_DB_PASSWORD
printf '\n'
export CONTEXTDB_NEW_DB_PASSWORD
psql -X "$PGADMIN_URL" -v ON_ERROR_STOP=1 \
  -v service_role=hindsight_service -v service_db=hindsight \
  -f "$HELPERS/../prepare-pg.sql"
unset CONTEXTDB_NEW_DB_PASSWORD
```

此脚本创建新库/角色、启用 vector/pg_trgm/btree_gin，遇到已存在对象停止。PGADMIN_URL 里的 provisioner 必须有建库、建角色、安装扩展权限。数据库密码可通过受控 PGPASSFILE 提供。默认 PGADMIN_URL 和后续 database-url 不指定 sslmode，可连接未启用 SSL 的 PG；数据库 SSL 及 CA 证书不作为强制前置条件。需要 SSL 时按[部署合同](contextdb-deployment-contract.md)自行配置，渲染器原样保留输入 URL。

首版 RDS 配置只启用上述三个基础扩展，全文后端固定 `native`，使用 PG 内置 `english` 配置；**不安装 PGroonga/Groonga，也不要求 pg_search 或 zhparser**。这是明确的首版能力取舍，不是部署失败后的静默降级。

英文全文可按原生路径验证；中文内容仍可写入并通过 MaaS bge-m3 向量召回，但中文分词/关键词全文不作已完成能力承诺。不能把中文 recall 返回非空当作中文全文验收通过。后续中文全文适配见[设计 TODO](../design/contextdb-release-design.md#本轮实现收敛与-todo)，基础插件及选型边界见[PG 插件说明](../design/postgresql-extensions.md)。

## 3. 写入私密输入并渲染

由管控下发私密文件，禁止把秘密写入 Git、工单或命令行参数。以下 read 命令用于首次手工联调，节点 Agent 应使用已有秘密管理通道。

```bash
umask 077
mkdir -p /srv/hindsight/input
read -r -s -p '数据库完整URL: ' DB_INPUT
printf '\n'
printf '%s\n' "$DB_INPUT" > /srv/hindsight/input/database-url
unset DB_INPUT
read -r -s -p 'MaaS API Key: ' MAAS_INPUT
printf '\n'
printf '%s\n' "$MAAS_INPUT" > /srv/hindsight/input/maas-key
unset MAAS_INPUT
read -r -s -p 'UI登录密码: ' UI_INPUT
printf '\n'
printf '%s\n' "$UI_INPUT" > /srv/hindsight/input/ui-password
unset UI_INPUT
chmod 600 /srv/hindsight/input/*
cp "$HELPERS/intent.example.json" /srv/hindsight/intent.json
```

编辑 intent 的绝对路径、PG/MaaS/UI 输入引用、端口和全文后端。首版固定 `topology=merged`，示例使用 native 英文全文；API、内置 Worker、UI 在同一个容器。`ui_api_url=http://127.0.0.1:8888` 指容器内部 API；修改 API 端口时同步修改此地址。

```bash
python3 "$HELPERS/render.py" /srv/hindsight/intent.json "$RUN"
```

成功只输出确认，不输出秘密。已有输出时拒绝重建；重启直接复用 RUN。此时 API 尚未启动，Key 已离线生成并存储，不需要先调用 API。

## 4. 节点Agent启动容器

**首版只启动一个长期运行的容器 `hindsight`，不是两个或三个容器。**

```text
节点 Agent（宿主机，负责启停）
  └─ hindsight 容器
       ├─ Python：Hindsight API :8888 + 进程内 Worker
       └─ Node.js：Hindsight UI :9999 → 127.0.0.1:8888
                 │
         外部 RDS PG / 华为云 MaaS
```

容器内有两个应用主进程，另有 init/启动监督脚本和临时健康检查进程。Worker 是 Python 进程内的后台任务执行器，不额外启动 `hindsight-worker`。PG、模型服务和节点 Agent 均不放入本容器。原生镜像已有 `/app/start-all.sh`，直接复用它启动、等待 API 就绪、转发停止信号并清理进程，不修改 Hindsight 原生源码。

这样选择是为了减少首版部署对象、配置和故障排查分支；代价是 API、Worker、UI 共享资源上限和容器生命周期，不能独立限额或重启。只有明确出现后台任务挤占查询资源、需要独立扩容等场景后，才扩展分容器交付；分离并不自动改善模型耗时或实现高可用。CPU、内存和磁盘预算见[资源说明](../design/contextdb-resource-sizing.md)。

```bash
export NATIVE_RUNTIME="$RUN"
# 私密配置必须由容器使用的非root账号读取；本机联调使用当前账号UID。
if test "$(id -u)" -eq 0; then
  chown -R 1000:1000 "$RUN"
  export HINDSIGHT_UID=1000 HINDSIGHT_GID=1000
else
  export HINDSIGHT_UID=$(id -u) HINDSIGHT_GID=$(id -g)
fi
docker compose --env-file "$RUN/ports.env" -f "$HELPERS/compose.yaml"   -p hindsight-native up -d --wait
docker compose --env-file "$RUN/ports.env" -f "$HELPERS/compose.yaml"   -p hindsight-native ps
```

api.env/ui.env 是 Shell 引用格式，在同一个容器中只读挂载，由入口 Shell 加载；**不能作为 Docker env_file 直接传入**。ports.env 供 Compose 解析端口；首版不启用 split profile。原生启动脚本先启动 API（含内置 Worker），ready 后再启动 UI。API/UI 监听 0.0.0.0，默认发布 8888/9999；生产入口使用 HTTPS 及安全组。同容器、同 UID 属于同一秘密信任边界；原生启动脚本的两个子进程会继承已加载的环境，不能宣称组件之间仍有容器级秘密隔离。

容器访问RDS必须使用可达的PG DNS；本机开发PG可使用Docker提供的host.docker.internal，PG需监听相应地址并配置密码认证。容器内127.0.0.1不能连接宿主PG。不要修改客户正在使用的PG参数来迁就测试，联调使用独立数据库服务。

检查与停止，只操作本实例的Compose项目：

```bash
curl -fsS http://127.0.0.1:8888/health/ready | jq .
docker compose --env-file "$RUN/ports.env" -f "$HELPERS/compose.yaml"   -p hindsight-native logs --tail 100 hindsight
docker compose --env-file "$RUN/ports.env" -f "$HELPERS/compose.yaml"   -p hindsight-native down
```

重启复用 RUN 和同一 PG，不重新 render 或生成 Key。配置变更后使用同一 Compose 命令追加 `up -d --force-recreate --wait` 重建容器。`docker compose restart hindsight` 只重启已有配置。Compose 的两个健康探测均需成功；业务验收另需异步 retain 完成，不能只检查 API ready。

源码开发仍可用 `run.sh api|ui` 分别启动前台进程；这是开发入口，不是另一个首版容器部署方案。历史分容器配置保留在 Git 历史及调研记录，当前 compose.yaml 不启用 split；本期不额外交付第二套部署模板。

## 5. API 创建两个 Bank 并验证

在私密 shell 中执行。API_KEY 不回显；不要开启 `set -x`。原生模式全部 Bank 在同一 schema，以下两个 Bank 只验证数据按 bank_id 隔离，共享 Key 不提供用户访问权限隔离。

```bash
export BASE=http://127.0.0.1:8888
API_KEY=$(cat "$RUN/api-key")
export API_KEY
curl -fsS "$BASE/health/live" | jq .
curl -fsS "$BASE/health/ready" | jq .
# 无 Key 必须失败（401/403）；健康接口不需要 Key。
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/v1/default/banks"

curl -fsS -X PUT "$BASE/v1/default/banks/mysql" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"name":"MySQL"}' | jq .
curl -fsS -X PUT "$BASE/v1/default/banks/pg" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"name":"PG"}' | jq .
curl -fsS "$BASE/v1/default/banks?limit=100&offset=0" \
  -H "Authorization: Bearer $API_KEY" | jq .
```

PUT 创建/更新原生 Bank，不需要 ContextDB 的 Idempotency-Key 或 UUID。预期列表包含 mysql、pg。

retain 默认同步处理时，成功表示抽取/入库完成；耗时由模型决定，不要以几秒的探测超时衡量此请求。

```bash
curl -fsS --max-time 300 -X POST "$BASE/v1/default/banks/mysql/memories" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"items":[{"content":"验证项目采用 MySQL 8.0，事务隔离级别是 READ COMMITTED。The validation project uses MySQL 8.0."}],"async":false}' | jq .
curl -fsS --max-time 120 -X POST "$BASE/v1/default/banks/mysql/memories/recall" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"项目使用哪个数据库，事务隔离级别是什么？","budget":"low"}' | jq .
curl -fsS --max-time 180 -X POST "$BASE/v1/default/banks/mysql/reflect" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"根据已有记忆，说明项目数据库和事务隔离级别。","budget":"low"}' | jq .
# PG Bank 不应返回刚才写入 MySQL 的事实。
curl -fsS --max-time 120 -X POST "$BASE/v1/default/banks/pg/memories/recall" \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"验证项目的 MySQL 8.0","budget":"low"}' | jq .
```

retain 返回入库结果；recall 返回 results 等原生字段，非空且证据符合写入内容；reflect 返回合成答案。上面的中文查询用于验证完整混合召回中的中文语义能力，不能作为中文分词全文测试；英文全文需另用英文材料和关键词验证。模型答案不要求逐字相同。还需发一次 `"async":true` retain，取得 operation_id 后轮询 `/v1/default/banks/mysql/operations/{operation_id}` 至 completed，确认内置 Worker 真正领取执行；仅 API ready 不代表任务执行正常。

## 6. MCP 与 UI

原生支持 Streamable HTTP MCP，客户端设置 URL `http://ECS_IP:8888/mcp`、Header `Authorization: Bearer <同一 API Key>`。初始化探测：

```bash
curl -fsS --max-time 15 -X POST "$BASE/mcp" \
  -H "Authorization: Bearer $API_KEY" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"node-agent-validation","version":"1"}}}'
```

此命令只验证初始化；有状态会话后续请求须保留响应的 MCP-Session-Id、发送 initialized，再 tools/list、tools/call，不能把一次 initialize 当成完整功能验收。业务 bank_id 使用 mysql/pg，与 REST 相同。

UI 用指定密码登录，能看到两个 Bank；在 mysql 中查看记忆、执行 recall/reflect，切换 pg 后没有 MySQL 事实；浏览器不应暴露 PG/MaaS 密码。原生 UI 文案仍叫 Bank/记忆库，也没有 ContextDB 用户管理页，这是本阶段预期。

## 7. PG 验证、重启和清理

使用 PG 管理员或受控只读诊断账号，确认目标 database、public 中原生表、扩展版本、向量维度，且没有 ctxdb_meta。

```sql
SELECT current_database(), current_user;
SELECT extname,extversion FROM pg_extension ORDER BY extname;
SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;
SELECT bank_id,name FROM public.banks ORDER BY bank_id;
SELECT vector_dims(embedding) FROM public.memory_units WHERE bank_id='mysql' AND embedding IS NOT NULL LIMIT 1;
SELECT to_regnamespace('ctxdb_meta'); -- NULL
```

节点 Agent 停止 API/UI/Worker 后，用同一 RUN 重启；Key、UI 密码和原生数据应保持。升级先备份数据库与配置、停止写入、单进程迁移再放量。优雅停止用 SIGTERM，等待在途任务退出；不要删除 PG 任务表“修复”问题。

只在确认属于本次验证时删除两个 Bank：

```bash
curl -fsS -X DELETE "$BASE/v1/default/banks/mysql" -H "Authorization: Bearer $API_KEY" | jq .
curl -fsS -X DELETE "$BASE/v1/default/banks/pg" -H "Authorization: Bearer $API_KEY" | jq .
unset API_KEY
```

不要由通用清理脚本 DROP 客户数据库。原生删除 Bank 不等于删除整个实例。实例释放由管控/Agent 处理容器、配置、备份和 RDS 生命周期。

故障定位先看 Agent 的启动退出码、API/Worker JSON 日志、UI 日志、PG 连接和 MaaS HTTP 状态。重点区分：ready 失败（DB/迁移/模型初始化）、401（共享 Key 不匹配）、异步一直 pending（Worker 未启动/未发现同库）、模型 400（模型名/端点/字段错误）、连接耗尽（主读池按进程累加）。不要把秘密配置或完整错误响应发到工单。详细方法见[运维手册](../design/contextdb-operations-runbook.md)，其中 ContextDB 专属元数据与恢复命令不适用于本原生模式。

## 8. 本机验证与环境差异

2026-10-19验证的官方slim镜像摘要为`sha256:f284d0d63e92e993686e18c15f6e4a221cd80fdfd47625a7c5f6cd8568078440`，revision与上述v1.0.0相符。源码与容器分别测试，不以自研镜像冒充原生结果；该历史验证使用独立PG18、非超级用户、PGroonga、真实MaaS与1024维向量，不代表当前 native 全文配置已通过同一轮测试。

本机Colima ARM上，官方API容器无日志退出132（SIGILL）；设置`OPENSSL_armcap=0`后正常。仅遇到该CPU/OpenSSL兼容问题时使用以下本机覆盖文件；不写入正式Compose，不作为目标ECS的默认配置：

```bash
cat > "$RUN/local-colima.yaml" <<'YAML'
services:
  hindsight:
    environment:
      OPENSSL_armcap: "0"
YAML
docker compose --env-file "$RUN/ports.env" \
  -f "$HELPERS/compose.yaml" -f "$RUN/local-colima.yaml" \
  -p hindsight-native up -d --wait
```

此前两容器 merged 与三容器 split 的历史实测均通过：创建两个Bank、真实MaaS retain/中文recall/reflect、UI登录与列表；停止独立Worker时新异步任务保持pending，重启Worker后完成，确认API内置Worker已关闭。MCP会话与中文recall另行验证。

采用该覆盖后，后续stop/up/down也带同一个覆盖文件；保持镜像、PG、Key和UI密码不变。此项证明本机调用和部署链路可用，不能代替目标ECS CPU兼容、安全扫描、生产吞吐与RDS恢复验收。

首版交付已调整为本章的单容器形态。上述历史分容器结果不能代替单容器的启动、UI、异步任务及停止信号验证；单容器本次验证记录见资源说明。

2026-10-19 补充验证：新建独立 UTF8 数据库仅启用 plpgsql、vector、pg_trgm、btree_gin，未启用 PGroonga；官方原生1.0.0-slim单容器使用 native + english，真实 MaaS retain、中文 recall、reflect、内置 Worker 异步任务和 UI 登录/列表均通过。另检查原生 GIN 索引和英文词干匹配 SQL。该结果证明没有 PGroonga 依赖的本机功能链路可运行，不证明中文关键词全文效果，也不是目标华为云 RDS 实测。
