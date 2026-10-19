# ContextDB 独享版：管控与节点部署指南

本指南用于管控、ECS 节点 Agent 与 Hindsight 开发人员联调。字段规范及自动化入口见 [部署合同](contextdb-deployment-contract.md)。必须使用同一次构建的 ContextDB API、扩展和 UI；上游通用镜像不包含本仓新增功能。

## 1 谁负责什么

| 责任方 | 负责的输入与操作 |
| --- | --- |
| 华为云管控 | 创建 ECS/RDS、网络及证书；预建 PG 数据库和服务账号；安装数据库端插件；申请 MaaS Key；接收客户指定的 UI 密码；下发部署意图及秘密文件 |
| 节点 Agent | 校验并渲染配置；拉取指定镜像；执行一次初始化；监管 API/UI/Worker，处理重启和日志采集。使用现有本机命令，不增加实例管理 HTTP 服务 |
| Hindsight 服务 | 初始化管理表；创建工作空间 schema/业务表；提供业务 REST/MCP、UI 和工作空间/用户/Key 管理 |
| 浏览器/业务应用 | 浏览器使用 UI 密码；业务使用授权 Key。二者都不需要 PG 密码、MaaS Key 或后台 Admin Key |

数据库不存在时，外部 PG 部署会失败；Hindsight 不会替管控创建数据库或 RDS。实例启动与工作空间初始化是不同步骤：启动完成后，由管理员在 UI 创建空间，也可调用管理 REST 接口验证。

## 2 PG 需要提供什么

| 输入 | 要求 |
| --- | --- |
| 地址、端口 | API 和 Worker 容器均可访问的 PG 地址，通常 5432；容器里的 `127.0.0.1` 指容器自身 |
| database | 预建 UTF8 专用数据库；一独享实例一数据库；不要复用已有应用库 |
| user/password | 专用 LOGIN 角色，拥有该数据库和服务 schema，允许建 schema、表、索引及执行迁移；不授予 SUPERUSER、CREATEDB、CREATEROLE、BYPASSRLS |
| 数据库 SSL（可选） | 默认示例不指定 sslmode；不要求 PG 预先启用 SSL 或提供证书。需要 SSL 时由部署方按数据库策略配置；URI 密码须百分号编码 |
| 基础插件 | 目标数据库中启用 `vector`、`pg_trgm`、`btree_gin`；安装文件存在不等于已在目标库启用 |
| 全文后端 | 首版 RDS 固定 native + english，不另装全文插件；中文向量召回可用，中文分词关键词全文待适配 |
| 可观测性 | `pg_stat_statements` 可选。需要共享预加载时由 PG 运维安排，节点初始化不擅自修改实例参数或重启数据库 |

### 新库准备命令

由 PG 管理员执行。命令只创建新对象，遇到已有同名库/角色就停止，不接管、不删除旧库。

```bash
export REPO=/opt/contextdb/source
export PGADMIN_URL='postgresql://provisioner@pg.example.internal:5432/postgres'
read -r -s -p '新服务账号密码: ' CONTEXTDB_NEW_DB_PASSWORD
printf '\n'
export CONTEXTDB_NEW_DB_PASSWORD
psql -X "$PGADMIN_URL" -v ON_ERROR_STOP=1 \
  -v service_role=contextdb_service -v service_db=contextdb \
  -f "$REPO/hindsight-extensions/contextdb-service/deployment/prepare-pg.sql"
unset CONTEXTDB_NEW_DB_PASSWORD
```

`provisioner` 的 PG 认证通过受保护的 `.pgpass`/平台秘密注入处理，不在命令行写密码。默认 PGADMIN_URL 和运行时 database-url 均不附加 sslmode；客户端按默认连接策略工作，可连接未启用 SSL 的 PG。如需明确使用非 SSL 连接可附加 `sslmode=disable`；如需验证服务器证书可自行配置 `sslmode=verify-full` 和 `sslrootcert`，不由部署器强制添加。RDS 从平台支持列表启用 vector、pg_trgm、btree_gin；首次部署不安装 PGroonga/Groonga，也不自动改用 pg_search 或 zhparser。

意图模板已经配置 `text_search=native`、`language=english`。这里的 language 是**全文预检/验收语言**，不是禁止输入中文，也不修改 MaaS 模型语言能力。中文可写入和进行向量语义召回；中文关键词全文尚未适配，不能声称达到中文分词验收。`native + chinese/multilingual` 仍会被校验拒绝，不能通过放宽预检伪装已支持。

华为云 RDS 暂不支持 PGroonga，因此不将其列为首版依赖；未来中文全文候选及适配差距保留在[设计](../design/contextdb-release-design.md#fulltext-selection)中。已使用 PGroonga 的试验库不能仅修改环境变量切换；保留原库，当前首版在新建专用库验证 native，后续存量数据切换需专项迁移/重建方案。

### 客户自带 PG 的隔离边界

客户普通 SQL 账号不要拥有服务数据库、服务角色或 `ctxdb_meta`、`ctxdb_ws_*` schema，不授予这些表的 SELECT/DML/DDL，不允许 SET ROLE 为服务角色。服务账户不交付给业务使用；不要把工作空间权限映射成数据库超级权限。

客户若拥有同一 PG 的超级用户、数据库所有者或底层主机控制权，就能修改/删除服务数据，**不能保证元数据不被破坏**。这属于部署信任边界；备份、变更约束和检测只能帮助恢复，不能替代权限隔离。禁止为“保护元数据”错误地承诺能阻止 root。

## 3 下发配置与第一次启动

节点需要容器运行时及 Compose v2。先构建本分支镜像（构建机需要访问 Python/npm/基础镜像仓库）；发布时记录镜像摘要，Agent 只拉取批准的摘要。

```bash
cd /opt/contextdb/source
REV=$(git rev-parse HEAD)
docker build --build-arg SOURCE_REVISION="$REV" \
  -f hindsight-extensions/contextdb-service/deployment/Dockerfile \
  -t "contextdb:$REV" .
docker image inspect "contextdb:$REV" --format '{{.Id}}'
export CONTEXTDB_IMAGE="contextdb:$REV"
```

若直接拉取已发布镜像而不在节点构建，先将 `CONTEXTDB_IMAGE` 设为批准的镜像摘要；后续两条渲染路径和 Compose 使用同一个值。

Dockerfile 支持 `NODE_IMAGE` 构建参数；正式发布应固定批准的 Node24 基础镜像摘要。源码脏树构建仅用于开发，不能用 HEAD 标签冒充已提交发布版本；记录实际源码补丁及构建输出。源码构建失败应交付错误证据，不继续使用旧上游镜像。

管控下发以下文件，权限由 Agent 设置。`database-url` 包含完整 PG URI，`maas-key` 包含 MaaS Key，`ui-password` 包含用户指定密码，均为单行；不要把值放入 Git、工单或命令行参数。

```text
/srv/contextdb/input/intent.json       非秘密部署意图
/srv/contextdb/input/database-url      0600，PG URI
/srv/contextdb/input/maas-key          0600，MaaS Key
/srv/contextdb/input/ui-password       0600，独立 UI 密码，至少12字符
/srv/contextdb/runtime/                0700，必须持久化备份
```

Linux节点以镜像默认UID10001运行时，Agent可用管理员权限执行以下目录准备，再将收到的三个秘密文件设为0600、属主10001。不要用chmod777或在容器中临时生成后丢失：

```bash
sudo install -d -m 0700 -o 10001 -g 10001 /srv/contextdb/input /srv/contextdb/runtime
sudo chown 10001:10001 /srv/contextdb/input/database-url /srv/contextdb/input/maas-key /srv/contextdb/input/ui-password
sudo chmod 0600 /srv/contextdb/input/database-url /srv/contextdb/input/maas-key /srv/contextdb/input/ui-password
```

从 [意图模板](https://github.com/ZhuQingping/hindsight/blob/75ae4b7ed806c6c6e54d6306b9420e5fd9535014/hindsight-extensions/contextdb-service/deployment/intent.example.json) 复制 `intent.json`，修改实例、租户、秘密文件路径、端口和明确的拓扑选择。首版固定 topology=merged；示例 `ui_api_url=http://127.0.0.1:8888` 是同容器内 UI 服务端访问 API 的地址，不是浏览器地址。

```bash
cd /opt/contextdb/source
export CONTEXTDB_PYTHON="$PWD/.venv/bin/python"
AGENT="$PWD/hindsight-extensions/contextdb-service/scripts/node-agent.sh"
sudo bash "$AGENT" validate --config /srv/contextdb/input/intent.json
sudo bash "$AGENT" render --config /srv/contextdb/input/intent.json \
  --directory /srv/contextdb/runtime
sudo chown 10001:10001 /srv/contextdb/runtime/api.env /srv/contextdb/runtime/ui.env
```

以上主机渲染分支由具备管理权限的节点Agent执行，render后必须将0600配置文件属主设为容器UID10001；仅chown目录不够。每次 --replace 原子替换后也要核对属主。实际采用其他非root UID时，两处统一替换。

节点没有 Python 依赖时，可用同版镜像运行渲染器。输入挂载只读，输出持久化目录可写；镜像默认 UID10001，需要提前给目录和输入文件设置对应所有者，或者使用批准的 UID/GID 覆盖。`--user` 不改变文件权限检查要求。

```bash
docker run --rm --entrypoint /app/.venv/bin/python \
  -v /srv/contextdb/input:/srv/contextdb/input:ro \
  -v /srv/contextdb/runtime:/var/lib/contextdb:rw \
  "$CONTEXTDB_IMAGE" -m hindsight_ext_contextdb.deployment render \
  --config /srv/contextdb/input/intent.json --directory /var/lib/contextdb
```

渲染只生成私有 `api.env`、`ui.env`，尚未修改 PG。随后初始化会写 PG，生成并持久保存后台 Admin Key、pepper 和 UI 秘密；重复初始化核对既有凭据，不重新生成。

```bash
export CONTEXTDB_DEPLOY_DIR=/srv/contextdb/runtime
export CONTEXTDB_API_PORT=8888 CONTEXTDB_UI_PORT=9999
COMPOSE=/opt/contextdb/source/hindsight-extensions/contextdb-service/deployment/compose.yaml
docker compose -p contextdb -f "$COMPOSE" --profile initialize run --rm initialize
# 初始化完成后只启动一个长期运行容器，API内置Worker和UI共用该容器。
docker compose -p contextdb -f "$COMPOSE" up -d --wait hindsight
docker compose -p contextdb -f "$COMPOSE" ps
curl -fsS http://127.0.0.1:8888/health/ready
```

首版固定一个运行容器、两个应用主进程：Python 运行 API/内置 Worker，Node.js 运行 UI。初始化命令结束后一次性容器退出，不额外常驻。`service.sh all` 监督两个主进程，UI 等待 API ready 后启动；故障时整体退出，容器运行时重启。不要另启独立 Worker。资源建议、磁盘预算和验证方法见[资源说明](contextdb-resource-sizing.md)。
默认监听 `0.0.0.0`，API8888、UI9999，允许其他机器通过 ECS 地址访问。安全组、负载均衡、HTTPS 和鉴权由部署层配置；不要把“外部可达”实现为关闭验证。端口改动必须同时修改 intent 的 `api_port/ui_port`、`ui_api_url` 和 Compose 发布端口变量；容器内部监听与外部映射需一致。

## 4 模型、凭据与重启

| 项目 | 首版配置 |
| --- | --- |
| LLM | OpenAI 兼容适配，`https://api.modelarts-maas.com/v2`，`deepseek-v4.1-flash`；运维字段 `llm_model` 可在评测批准后调整，客户 UI 不暴露 |
| Embedding | OpenAI 兼容适配，`https://api.modelarts-maas.com/v1`，`bge-m3`；运行初始化探测实际1024维，**不发送 dimensions** |
| Rerank | 复用 siliconflow 适配，`https://api.modelarts-maas.com/v1`，`bge-reranker-v2-m3` |
| UI 密码 | 客户指定；`prepare` 首次复制到 `ui-secrets.json`，后续保持不变；不是 PG 密码或业务 Key |
| Admin Key | 离线生成，写 `admin-key.json`，数据库只存 HMAC；UI 后台从 `ui-secrets.json` 获取。用户浏览器不接触此 Key |
| Pepper | `api-secrets.json`；只给 API/Worker，不能丢失或随重启重生成 |

当前使用用户已有验证路径 `/v2`、`/v1`，不要未经验证就自动替换成另一个 MaaS 网关路径。Key 和模型要在目标区域及账号确实可调用；API ready 不能证明模型调用、维数和效果正确。

本轮真实协议探测中，MaaS `/v1/rerank` 要求查询字段为 `query`，历史示例的 `input` 返回400。复用的 siliconflow 适配发送 `query` 和 `documents`；不要照搬旧手写请求。

重启使用原 `runtime` 目录；不要重新生成秘密、删目录或重新创建数据库。普通渲染不能修改已持久化的 UI 密码。Admin Key/pepper 轮换需要专门维护步骤，不能通过覆盖环境文件实现。升级前备份服务数据库和秘密，停止写入后按同版迁移/恢复流程执行。

配置固定`HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP=false`。新空间由管理生命周期显式初始化业务schema；已有空间升级要停止API/Worker后，针对元数据记录的各个schema执行原生迁移，不让API启动自行遍历或创建schema。此项是同名删除重建的安全要求，不能改回默认true。

同一个运行容器只读挂载 api.env、api-secrets.json、ui.env、ui-secrets.json；API/UI 启动器仍按进程加载必要环境，但同 UID 可以读取这些挂载，不提供组件间强隔离。仅初始化命令获得整个 runtime 可写目录。UI另有64MiB临时Next缓存，重启可丢弃，不作为持久数据备份。备份应同时包含数据库和这组秘密，并加密保管。只备份其中一项无法保证恢复可用。

## 5 Agent 的验收与失败处理

```bash
sudo bash "$AGENT" status --config /srv/contextdb/input/intent.json \
  --directory /srv/contextdb/runtime --api-url http://127.0.0.1:8888
docker compose -p contextdb -f "$COMPOSE" logs --tail=200 hindsight
docker compose -p contextdb -f "$COMPOSE" stop
```

status校验私密文件格式与权限、API健康正文，并用后台Admin Key检查实例/租户身份与输入配置匹配；不证明Worker、MaaS或工作空间业务正常。完整验收还需登录 UI、创建两个空间、创建受限 Key、retain/recall/reflect、REST/MCP 越权验证及重启复验。日志含业务输入和故障细节，必须脱敏后对外分享；不收集 `docker compose config`、`docker inspect` 全量环境或 env/秘密文件原文。

证书代理环境使用受信 CA：容器内挂载相同绝对路径的 CA 文件，intent 设置 `ca_bundle_file`，API 使用 `SSL_CERT_FILE`，UI 使用 `NODE_EXTRA_CA_CERTS`。API的CA文件应是包含公共根证书和企业CA的完整信任包，避免替换后无法验证MaaS证书。Compose 示例没有自动挂载 CA 或配置代理；按企业网络显式补充只读证书卷及 `HTTPS_PROXY/NO_PROXY`，构建期也需要相应受信配置。禁止 `verify=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0` 或 monkey patch 关闭 TLS 校验。

## 私有CA、文件挂载与升级补充

配置ca_bundle_file时，Agent本机状态检查也使用该CA；API/Worker和UI必须在同一绝对路径看到只读CA文件。为 hindsight 服务添加 volumes 条目，例如 `/srv/contextdb/ca.pem:/srv/contextdb/ca.pem:ro`，不要把整个秘密目录挂到全部组件。运行服务文件只读挂到一个容器，更新文件后使用 `docker compose ... up -d --force-recreate hindsight` 重新建立挂载，保留原runtime目录。CA不得通过关闭证书校验替代。

首发管理元数据结构版本固定为1。migrate仅初始化新库，或核对已经采用当前结构的数据库；开发期试验结构不作为已发布版本，不自动升级或直接改号。已有试验库先保留数据和配置备份，再使用新的专用数据库验证；不能仅修改metadata_version冒充结构匹配。未来正式发布结构变更时，再从版本1增加有序迁移。

首版固定一个容器合并部署，先减少交付复杂度；以后明确有独立扩容、资源隔离需求时再扩展分容器。历史对照见[补充调研](../archive/2026-10-19-before-reorganization/design/contextdb-service-research-validation.md)，当前决策见[设计](../design/contextdb-release-design.md#api-worker-deployment)。

渲染器固定关闭原生持久 LLM Trace/Audit，并禁止原生 Webhook；不能通过临时export打开这些未受代次保护的写入。ContextDB管理审计继续保留，详情见[首版限制](../archive/2026-10-19-before-reorganization/design/contextdb-service-research-validation.md#4-删除重建保护与首版限制)。

源码镜像构建使用BuildKit。依赖安装通过锁文件固定；Docker构建关闭npm安装时的隐式audit/fund网络请求以保证构建职责明确，发行流水线须单独执行批准的依赖/镜像安全扫描，不能把安装成功当成安全扫描通过。


数据库连接只配置 HINDSIGHT_API_DATABASE_URL；初始化、管理员离线轮换及API/Worker使用相同目标库和专用服务账号。管控预建数据库和安装插件，服务账号运行时须能创建空间schema、表和索引。不支持单独的bootstrap连接地址，遗留设置不能覆盖或替代此变量。

<a id="offline-upgrade"></a>

## 6 已发布结构的离线升级与管理员恢复

首发没有开发期旧库自动升级。下面仅供后续发行要求升级原生业务表时，对已经采用当前首发结构的实例使用。先备份PG和秘密，排空任务，停止全部API/Worker及迁移执行者；失败不得继续启动。各schema用同一版本、同一服务账号迁移。

设置同版源码、Python和部署目录，加载显式配置。不要把数据库密码放入命令行参数：

```bash
export CODE=/opt/contextdb/source
export PY="$CODE/.venv/bin/python"
export CONTEXTDB_DEPLOY_DIR=/srv/contextdb/runtime
export PYTHONPATH="$CODE/hindsight-extensions/contextdb-service:$CODE/hindsight-api-slim"
set -a
source "$CONTEXTDB_DEPLOY_DIR/api.env"
set +a
export PYTHON_DOTENV_DISABLED=1
"$PY" - "$CONTEXTDB_DEPLOY_DIR" <<'PY'
import asyncio, os, subprocess, sys
from pathlib import Path
import asyncpg
from hindsight_ext_contextdb.bootstrap import load_deployment_secrets
from hindsight_ext_contextdb.config import Settings
from hindsight_ext_contextdb.repository import Repository

load_deployment_secrets(Path(sys.argv[1]), 'api')
settings = Settings.from_environment()

async def schemas():
    conn = await asyncpg.connect(os.environ['HINDSIGHT_API_DATABASE_URL'])
    try:
        await Repository._verify_format(conn)
        await Repository._verify_binding(conn, settings.instance_id, settings.cloud_tenant_id)
        await Repository.verify_background_write_policy(conn)
        busy = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM ctxdb_meta.request_admissions) OR EXISTS(SELECT 1 FROM ctxdb_meta.management_operations WHERE state IN ('pending','running')) OR EXISTS(SELECT 1 FROM ctxdb_meta.workspaces WHERE state<>'active')")
        if busy:
            raise SystemExit('实例尚有未完成工作；先核对排空及恢复，不执行迁移')
        rows = await conn.fetch('SELECT schema_name FROM ctxdb_meta.workspaces ORDER BY schema_name')
        return ['public', *[row['schema_name'] for row in rows]]
    finally:
        await conn.close()

for schema in asyncio.run(schemas()):
    env = os.environ.copy()
    env['HINDSIGHT_API_TENANT_EXTENSION'] = ''
    subprocess.run([sys.executable, '-m', 'hindsight_api.admin.cli', 'run-db-migration', '--schema', schema, '--embedding-dimension', '1024'], env=env, check=True)
PY
```

脚本先核对当前结构、实例归属、原生审计/Webhook限制与管理任务/准入记录，再显式迁移public及各空间；不触发未绑定引擎的通用租户发现。升级后重开全部连接池，逐空间验证REST/MCP，再恢复入口。仅在发布说明要求时运行；不要手改metadata_version绕过检查。

管理员Key遗失时，服务所有者停服务后离线轮换，保留原pepper。此操作更新PG摘要、Admin Key和UI秘密文件，不覆盖业务Key：

```bash
"$PY" -m hindsight_ext_contextdb generate-admin-key \
  --output "$CONTEXTDB_DEPLOY_DIR/admin-key-next.json"
"$PY" -m hindsight_ext_contextdb rotate-admin-key \
  --directory "$CONTEXTDB_DEPLOY_DIR" \
  --admin-key-file "$CONTEXTDB_DEPLOY_DIR/admin-key-next.json"
```

重启UI使用新的后台Key，原Admin Key失效。轮换前后备份配置，不能通过丢掉秘密目录或重新生成pepper恢复；pepper遗失须恢复备份或重新签发业务Key。只改UI密码使用部署合同的改密步骤，无须改PG/API；Compose逐文件挂载原子替换后需force-recreate建立新挂载。

## 本轮本地验证范围

当前版本的验证范围与环境条件见[验证摘要](../testing/contextdb-validation-summary.md)。早期 PGroonga、merged/split 对照及详细过程保留在[整理前指南](../archive/2026-10-19-before-reorganization/design/contextdb-service-integration-guide.md)；首版部署只采用本文的单容器、RDS 基础扩展方案。
