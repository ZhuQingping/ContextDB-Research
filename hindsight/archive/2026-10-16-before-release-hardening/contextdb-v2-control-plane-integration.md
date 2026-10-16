# ContextDB V2 管控联调：实例与工作空间

更新日期：2026-10-15。对应代码：`contextdb/service-management-v2`，固定提交 `d5e851b60315b79696e995874e7edc1e9a7bae23`。

本文给管控开发者提供节点上的可执行操作。先按顺序完成一次新实例部署，再把相同命令接入现有节点 Agent。用户和日常 Key 管理由 UI 完成，不在本文重复。

## 1 管控具体调度什么

```text
创建实例：管控开通 PG/计算 → Agent 安装发布包 → 安装元数据
        → 启动 API/Worker → 登记实例并保存管理员 Key → 启动 UI → 上报可用
空间管理：Console → 管控 → API 节点的 Agent → 本机 Hindsight REST
业务请求：Agent/应用 → Hindsight REST/MCP
```

节点管理 Agent 和业务 Agent 是不同组件。**当前代码提供 Hindsight 接口，未提供节点 Agent 的调度协议。** 下文命令是 Agent 的执行内容；管控到 Agent 的 URL、任务格式、进程托管方式仍使用现有平台协议。确认前可直接调用 Hindsight，不能把本文当作已实现的新 Agent 接口。

| 管控动作 | Agent 执行内容 | 管控判定完成 |
| --- | --- | --- |
| 创建实例 | 第 2–6 节；API/Worker/UI 分别启动并托管 | PG 与配置检查通过，实例登记成功、管理员 Key 已持久保存、UI 健康 |
| 查询实例 | `ctxctl instance-get` + Agent 查询进程/健康 | 分别报告登记信息与运行状态 |
| 创建/删除空间 | 第 7 节 `workspace-create/delete --no-wait` | 保存 operation_id，轮询到 succeeded，再核对空间 |
| 空间列表/详情 | `ctxctl workspace-list/get` | 直接返回 API 结果，不另维护空间目录 |
| 停止/重启/升级/销毁 | 第 8 节进程命令及现有云资源流程 | Agent 运维任务的状态；不是空间 operation 的状态 |

空间请求必须送到有 API 的节点；纯 Worker 节点不能执行空间接口。Agent 只调用配置中的固定本机 API，不接受外部传入任意上游 URL。Agent 调度任务 ID 与 Hindsight `operation_id` 分别保存。

## 2 准备代码、目录和输入

下文使用 Bash、Python 3.11+、uv、Node.js/npm、curl、jq 和 PG 18 客户端。示例端口为 PG 5540、API 8890、Worker 健康 8891、UI 9998，避免占用已有体验服务；正式部署可改为 5432/8888/9999。API/UI 监听 `0.0.0.0`，其他机器可访问。

节点镜像应提供上述工具。macOS 已有 Homebrew 时可安装命令工具；PG 编译还需 Xcode Command Line Tools（`xcode-select --install`）：

```bash
brew install python@3.11 uv node@22 jq lsof
export PATH="$(brew --prefix python@3.11)/libexec/bin:$(brew --prefix node@22)/bin:$PATH"
for tool in bash python3 uv node npm git curl jq make lsof; do command -v "$tool"; done
python3 -c 'import sys; assert sys.version_info >= (3,11)'
node -e 'if (Number(process.versions.node.split(".")[0]) < 22) process.exit(1)'
```

本文采用 Node 22+ 的发布环境；Linux 节点镜像用相同版本要求，先运行工具/版本检查，失败则由镜像发布流程补齐依赖。PG 编译部分是 macOS 源码安装示例，RDS 跳过编译。

在节点上准备独立代码目录，不覆盖现有服务目录：

```bash
bash
set -euo pipefail
umask 077
export CODE="$HOME/contextdb-deploy/hindsight-v2"
export RESEARCH="$HOME/contextdb-deploy/ContextDB-Research"
export DEPLOY="$HOME/contextdb-deploy/runs/ctxdb-integration-001"
mkdir -p "$DEPLOY"

git clone --branch contextdb/service-management-v2 --single-branch \
  https://github.com/ZhuQingping/hindsight.git "$CODE"
git -C "$CODE" checkout --detach d5e851b60315b79696e995874e7edc1e9a7bae23
# 已有研究仓时直接填写它的目录，不重复 clone。
git clone https://github.com/ZhuQingping/ContextDB-Research.git "$RESEARCH"
export CTL="$RESEARCH/hindsight/scripts/contextdb-v2-control.py"
test -f "$CTL"

export INSTANCE_ID=ctxdb-integration-001
export CLOUD_TENANT_ID=tenant-integration-001
export INSTANCE_NAME='ContextDB 联调实例'
export ACTOR=console-admin-001
export API_PORT=8890
export WORKER_PORT=8891
export UI_PORT=9998
export API_URL="http://127.0.0.1:$API_PORT"
# API 节点本机的 psql 路径；Linux 填镜像实际客户端目录。
export PG_BIN=/Users/zhuqingping/Work/Database/PG/pg_18_4/bin
export NODE_BIN=$(command -v node)
export PYTHON_CLI_BIN=$(command -v python3)
```

研究仓中的[辅助脚本](../../scripts/contextdb-v2-control.py)封装请求、幂等值与正文绑定、轮询和私有响应保存；它是联调客户端，不是新增的节点 Agent。当前文档和脚本须从同一版研究仓取得，若尚未发布则使用本地文件交付。上面的实例/租户 ID 由真实管控生成，ACTOR 必须来自管控确认的登录身份。

将非秘密输入保存到节点，重启时加载同一份配置：

```bash
python3 - <<'PY'
import os, shlex
from pathlib import Path
names = ['CODE','RESEARCH','DEPLOY','CTL','INSTANCE_ID','CLOUD_TENANT_ID',
         'INSTANCE_NAME','ACTOR','API_PORT','WORKER_PORT','UI_PORT','API_URL','PG_BIN','NODE_BIN','PYTHON_CLI_BIN']
p = Path(os.environ['DEPLOY'])/'operator.env'
with p.open('x') as f:
    f.writelines(f'export {k}={shlex.quote(os.environ[k])}\n' for k in names)
PY
```

后续新终端加载[节点函数脚本](../../scripts/contextdb-v2-node.sh)，它会读取 operator.env，恢复 PY/PYTHONPATH、固定 Node/Python 客户端路径、函数及已保存的 PG 目标信息：

```bash
export DEPLOY="$HOME/contextdb-deploy/runs/ctxdb-integration-001"
source "$HOME/contextdb-deploy/ContextDB-Research/hindsight/scripts/contextdb-v2-node.sh"
```

第一次也执行上述 source。若目录不同，填写实际路径。不要重新生成 ID、运行目录或 pepper。辅助脚本同一运行目录按顺序执行，实例初始化只设一个执行者；实际 Agent 并发任务使用各自持久任务记录。

## 3 PG：安装、配置、建库

### 3.1 本期安装哪些插件

| 扩展 | 用途 | 本文部署 |
| --- | --- | --- |
| vector（pgvector） | 向量/HNSW；MaaS bge-m3 为 1024 维 | 必装 |
| pg_trgm | 实体字符串匹配及 trigram 索引 | 安装，避免降级 |
| btree_gin | 普通字段与 GIN 组合索引 | 安装；不是分词器 |
| pgroonga | 中英文全文检索 | 本文选用 |
| pg_stat_statements | SQL 统计与排障 | 安装并预加载 |

纯英文可将全文配置改为 `native`；本文不同时部署 pg_search/jieba。扩展文件安装到 PG 的目录后，还要在**实例使用的数据库**执行 CREATE EXTENSION；不用在每个 workspace schema 中重复安装。

### 3.2 自管源码 PG：安装扩展文件

以下命令对应本机源码 PG 18.4。在 **PG 节点**执行，`PG_ROOT` 必须是实际运行的安装目录，`PG_BUILD` 为它对应的 PG 源码构建树。若这些文件已经安装，直接进入 3.3。

```bash
export PG_ROOT=/Users/zhuqingping/Work/Database/PG/pg_18_4
export PG_BIN="$PG_ROOT/bin"
export PG_CONFIG="$PG_BIN/pg_config"
export PG_BUILD="$PG_ROOT/build/postgres"
export PLUGIN_BUILD="$HOME/contextdb-plugin-build"
mkdir -p "$PLUGIN_BUILD"
"$PG_CONFIG" --version
"$PG_CONFIG" --pkglibdir
"$PG_CONFIG" --sharedir

git clone --depth 1 --branch v0.8.6 https://github.com/pgvector/pgvector.git \
  "$PLUGIN_BUILD/pgvector-0.8.6"
make -C "$PLUGIN_BUILD/pgvector-0.8.6" PG_CONFIG="$PG_CONFIG" OPTFLAGS=""
make -C "$PLUGIN_BUILD/pgvector-0.8.6" PG_CONFIG="$PG_CONFIG" install
for module in pg_trgm btree_gin pg_stat_statements; do
  make -C "$PG_BUILD/contrib/$module"
  make -C "$PG_BUILD/contrib/$module" install
done

# macOS 构建依赖；Linux 的对应开发包是 libgroonga-dev、Meson/Ninja/pkg-config。
brew install groonga meson ninja pkgconf msgpack xxhash
export PKG_CONFIG_PATH="$(brew --prefix groonga)/lib/pkgconfig:$(brew --prefix msgpack)/lib/pkgconfig:$(brew --prefix xxhash)/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
pkg-config --modversion groonga
curl -fL https://packages.groonga.org/source/pgroonga/pgroonga-4.1.0.tar.gz \
  -o "$PLUGIN_BUILD/pgroonga-4.1.0.tar.gz"
tar -xzf "$PLUGIN_BUILD/pgroonga-4.1.0.tar.gz" -C "$PLUGIN_BUILD"
meson setup "$PLUGIN_BUILD/pgroonga-build-4.1.0" "$PLUGIN_BUILD/pgroonga-4.1.0" \
  --buildtype=release -Dpg_config="$PG_CONFIG" -Dinstall_to_postgresql=true -Dtest=false
meson compile -C "$PLUGIN_BUILD/pgroonga-build-4.1.0"
meson install -C "$PLUGIN_BUILD/pgroonga-build-4.1.0"
```

源码编译需要 server headers/PGXS 和 Groonga 开发库；PGroonga 4.1.0 要求 Groonga 至少 14.1.0。已有 Meson 构建目录时使用 compile/install，不重复 setup。Linux 发行版的 Groonga 安装方式见[官方源码安装](https://pgroonga.github.io/install/source.html)。生产镜像由 PG 发布流程提前构建这些依赖，不能在 RDS 上执行 make。

### 3.3 选择 PG 目标

**新建本机联调集群**执行下一段。**已有 PG 或 RDS**先填写真实目标和具备建角色/建库/设 owner/安装扩展权限的管理账号，再跳到 3.4；RDS 普通客户账号未必具备这些权限。

```bash
# 仅已有 PG/RDS 分支；替换地址、端口和账号，PG_BIN 为当前机器客户端目录。
export PG_HOST=你的PG私网地址
export PG_PORT=5432
export PG_ADMIN=你的平台数据库管理账号
export DB_NAME=ctxdb_integration_001
export SERVICE_ROLE=ctxdb_service_001
export PGSSLMODE=require
read -r -s -p 'PG 管理员密码: ' PGPASSWORD
printf '\n'
export PGPASSWORD
"$PG_BIN/psql" -X -h "$PG_HOST" -p "$PG_PORT" -U "$PG_ADMIN" -d postgres \
  -v ON_ERROR_STOP=1 -c 'SELECT current_user,version();'
```

自管远程 PG 用实际 TLS 策略；本机旧 PG 可设 PGSSLMODE=prefer。RDS 管理密码可由现有受保护秘密配置提供，Agent 非交互执行不使用 read。

#### 新建独立联调集群

这组命令新建 PG 5540，不停止、不重启现有 PG 5432。用 PG 服务的操作系统账号执行，不能用 OS root 启动 postgres。

```bash
export PG_DATA="$DEPLOY/pgdata"
export PG_SOCKET="$DEPLOY/pgsocket"
export PG_HOST=127.0.0.1
export PG_PORT=5540
export PG_ADMIN=ctxdb_provisioner
export DB_NAME=ctxdb_integration_001
export SERVICE_ROLE=ctxdb_service_001
mkdir -p "$PG_SOCKET"
test ! -e "$PG_DATA"
"$PG_BIN/initdb" -D "$PG_DATA" -U "$PG_ADMIN" --encoding=UTF8 --locale=C \
  --auth-local=trust --auth-host=scram-sha-256 --pwprompt
# 上一命令设置初始化管理员密码。再次输入同一密码，供下文 psql 使用。
read -r -s -p 'PG 管理员密码: ' PGPASSWORD
printf '\n'
export PGPASSWORD

cat >> "$PG_DATA/postgresql.conf" <<EOF
listen_addresses = '127.0.0.1'
port = $PG_PORT
unix_socket_directories = '$PG_SOCKET'
password_encryption = 'scram-sha-256'
max_connections = 100
shared_buffers = '256MB'
shared_preload_libraries = 'pg_stat_statements,pgroonga_wal_resource_manager'
compute_query_id = auto
pgroonga.enable_wal_resource_manager = on
EOF
"$PG_BIN/pg_ctl" -D "$PG_DATA" -l "$DEPLOY/pg.log" -w start
"$PG_BIN/psql" -X -h "$PG_HOST" -p "$PG_PORT" -U "$PG_ADMIN" -d postgres \
  -v ON_ERROR_STOP=1 -c 'SHOW shared_preload_libraries;'
```

256MB/100 连接仅是联调起点，不是生产容量承诺。一个 API 和一个 Worker 均使用下文的 10+10 连接池，还须为迁移、管理与监控留连接；增加节点前重新计算总预算。

PGroonga WAL resource manager 的配置用于 PG15+ 的 WAL/复制方案，主备均需预加载，主库开启上述参数；不同时设置 `pgroonga.enable_wal=on`，备库不启用 crash-safer。它不自动解决主库崩溃恢复；官方 crash-safer 仍为实验能力，本文不默认打开。正式上线另外完成崩溃与备份/复制恢复验收。[WAL 配置依据](https://pgroonga.github.io/reference/modules/pgroonga-wal-resource-manager.html)、[crash-safer 状态](https://pgroonga.github.io/reference/modules/pgroonga-crash-safer.html)。

**使用已有自管 PG 时**跳过 initdb/start：填写实际 PG_HOST/PORT/ADMIN，先 `SHOW data_directory` 和 `SHOW shared_preload_libraries`。合并原 preload 后设置，维护窗口内由 PG 服务账号重启。例如：

```bash
# 仅对已确认归属的自管 PG 执行；PG_DATA 是 SHOW data_directory 的结果。
"$PG_BIN/psql" -X -h "$PG_HOST" -p "$PG_PORT" -U "$PG_ADMIN" -d postgres \
  -v ON_ERROR_STOP=1 <<'SQL'
SELECT format('ALTER SYSTEM SET shared_preload_libraries = %L',
  concat_ws(',', nullif(current_setting('shared_preload_libraries'), ''),
            'pg_stat_statements', 'pgroonga_wal_resource_manager')) \gexec
ALTER SYSTEM SET compute_query_id = 'auto';
ALTER SYSTEM SET pgroonga.enable_wal_resource_manager = 'on';
SQL
"$PG_BIN/pg_ctl" -D "$PG_DATA" -m fast -w restart
```

**使用 RDS 时**不执行上面编译、initdb、pg_ctl 或 ALTER SYSTEM。管控用 RDS 参数组设置合并后的 preload、compute_query_id 与 PGroonga 参数，并通过 RDS 运维接口完成必要重启。先检查 3.4 的五个扩展是否可用；缺失 pgroonga 或 RDS 不支持该 preload 时，本文中文部署不能继续，需 PG 产品侧提供支持或另行确认全文方案。

### 3.4 建服务角色、UTF8 数据库及扩展

管控应准备一个平台持有的服务账号，API/Worker/bootstrap 共用它。客户 SQL 账号不要持有该密码，也不要成为服务数据库/schema 的 owner。

`$PG_ADMIN` 已认证的终端中执行一次。角色和数据库名称示例仅支持小写字母、数字和下划线：

```bash
export PG_HOST PG_PORT PG_ADMIN DB_NAME SERVICE_ROLE PG_BIN DEPLOY
python3 - <<'PY'
import os, re, secrets, subprocess, urllib.parse
from pathlib import Path
r = Path(os.environ['DEPLOY'])
role, db = os.environ['SERVICE_ROLE'], os.environ['DB_NAME']
assert all(re.fullmatch(r'[a-z][a-z0-9_]{0,62}', v) for v in [role, db])
pwfile = r/'pg-service-password'
with pwfile.open('x') as f:
    f.write(secrets.token_urlsafe(32))
pw = pwfile.read_text()
base = ['-h',os.environ['PG_HOST'],'-p',os.environ['PG_PORT'],'-U',os.environ['PG_ADMIN']]
subprocess.run([os.environ['PG_BIN']+'/psql','-X','-q','-v','ON_ERROR_STOP=1',*base,'-d','postgres'],
  input=f'CREATE ROLE "{role}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD \'{pw}\';\n',
  text=True, check=True)
subprocess.run([os.environ['PG_BIN']+'/createdb',*base,'--owner',role,'--template','template0',
  '--encoding','UTF8','--locale=C',db], check=True)
# 远程 RDS 使用 sslmode=require；如平台要求校验证书，改 verify-full 并配置可信 CA。
ssl = '' if os.environ['PG_HOST'] in ['127.0.0.1','localhost'] else '?sslmode=require'
url = f"postgresql://{urllib.parse.quote(role)}:{urllib.parse.quote(pw)}@{os.environ['PG_HOST']}:{os.environ['PG_PORT']}/{db}{ssl}"
with (r/'db-url').open('x') as f:
    f.write(url)
print('Service role/database created; credentials saved privately.')
PY
export DB_URL=$(cat "$DEPLOY/db-url")
# 保存非秘密目标；计算节点也使用此文件，PG_BIN 仍是各机器本地的客户端路径。
python3 - <<'PYTARGET'
import os, shlex
from pathlib import Path
with (Path(os.environ['DEPLOY'])/'pg-target.env').open('x') as f:
    for k in ['PG_HOST','PG_PORT','PG_ADMIN','DB_NAME','SERVICE_ROLE']:
        f.write(f'export {k}={shlex.quote(os.environ[k])}\n')
PYTARGET

"$PG_BIN/psql" -X -h "$PG_HOST" -p "$PG_PORT" -U "$PG_ADMIN" -d "$DB_NAME" \
  -v ON_ERROR_STOP=1 <<'SQL'
SELECT name, default_version FROM pg_available_extensions
 WHERE name IN ('vector','pg_trgm','btree_gin','pgroonga','pg_stat_statements');
CREATE EXTENSION vector WITH SCHEMA public;
CREATE EXTENSION pg_trgm WITH SCHEMA public;
CREATE EXTENSION btree_gin WITH SCHEMA public;
CREATE EXTENSION pgroonga;
CREATE EXTENSION pg_stat_statements WITH SCHEMA public;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
SHOW server_encoding;
SHOW shared_preload_libraries;
SELECT extname, extversion, extnamespace::regnamespace FROM pg_extension ORDER BY extname;
SELECT count(*) FROM pg_stat_statements;
SQL
"$PG_BIN/psql" -X "$DB_URL" -v ON_ERROR_STOP=1 \
  -c 'SELECT current_user, current_database();' -c 'SHOW server_encoding;'
unset PGPASSWORD
```

应看到 UTF8、五个扩展和可查询的 SQL 统计。脚本建角色/建库不是跨步骤事务：中途失败先检查已创建资源，不删除库或更换实例 ID盲重跑；密码保存在 `pg-service-password`，失败后由 PG 操作者按已完成步骤继续。新库的扩展在空间初始化前安装，避免已完成迁移使用降级索引。

跨机器 PG 还需在 PG 节点配置 `listen_addresses`、只允许 API/Worker 私网 CIDR 的 `pg_hba.conf`、TLS 和安全组；RDS 使用平台连接地址与参数组。不要把 PG 5540 暴露给业务客户端。

## 4 节点配置与元数据初始化

在 **API 节点**按第 2 节加载节点函数脚本。PG 在另一节点时，管控交付私有 `db-url` 和非秘密 pg-target.env，不用把 PG 数据目录复制到计算节点。API 节点按 operator.env 中的 PG_BIN 使用自己的客户端。准备独立 Python 环境和 UI 发布包：

```bash
cd "$CODE"
export UV_PROJECT_ENVIRONMENT="$DEPLOY/venv"
uv sync --frozen
export PY="$DEPLOY/venv/bin/python"
export PYTHONPATH="$CODE/hindsight-extensions/contextdb-service"
"$PY" -c 'import hindsight_api, hindsight_ext_contextdb'
# UI 构建时不继承 PORT，避免 Next 使用不同 .next 目录。
npm ci
env -u PORT npm run build -w @vectorize-io/hindsight-control-plane

# 一次性生成；目标已存在时不覆盖。
(set -o noclobber; "$PY" -m hindsight_ext_contextdb generate-control-key > "$DEPLOY/control-key.json")
export DB_URL=$(cat "$DEPLOY/db-url")
read -r -s -p 'MaaS API Key: ' MAAS_API_KEY
printf '\n'
export MAAS_API_KEY
ctxctl configure
unset MAAS_API_KEY
```

`configure` 一次性写 `api.env`、`ui-password.json`；已有文件拒绝覆盖。默认使用 MaaS 的 deepseek-v4.1-flash、bge-m3、bge-reranker-v2-m3；Embedding 不传 dimensions，启动时从响应探测 1024。API 和 Worker 均使用动态 ContextDB 扩展，关闭内嵌 Worker（下文单独启动 Worker）；管控来源默认只允许 loopback，适用于同机 Agent。

加载配置，唯一初始化执行者安装元数据：

```bash
source "$DEPLOY/api.env"
unset HINDSIGHT_API_EMBEDDINGS_OPENAI_DIMENSIONS HINDSIGHT_API_MCP_AUTH_TOKEN
"$PY" -m hindsight_ext_contextdb migrate
"$PG_BIN/psql" -X "$DB_URL" -v ON_ERROR_STOP=1 \
  -c 'TABLE ctxdb_meta.schema_versions;'
```

应仅有版本 2。migrate 只安装 `ctxdb_meta`，不生成管理员、不创建工作空间。V1 或未版本化旧元数据会拒绝，不能覆盖继续。

**直连联调**：控制请求来自其他计算机时，在生成 api.env 前设置 `CONTROL_NETWORKS='127.0.0.1/32,::1/128,实际管控私网CIDR'`。已有 api.env 则编辑该变量并重启 API；不要重新 configure。来源必须是实际 TCP 对端；管控/Agent 转发时去掉 `Forwarded`/`X-Forwarded-For`，当前 API 会拒绝这些头。业务 Key 不能替代管控 Key。

## 5 启动 API、Worker，登记实例

下面是可立即执行的单节点联调启动方式。正式 Agent 应将**同样的配置与前台命令**接入现有进程托管，不依靠 nohup 实现高可用。初次执行前确认目标端口空闲，不重复启动相同服务。

```bash
# 已 source 节点函数脚本；每个函数加载原配置，检查端口并等待健康。
ctxdb_start_api
ctxdb_start_worker
ctxctl instance-register --instance-id "$INSTANCE_ID" --cloud-tenant-id "$CLOUD_TENANT_ID" \
  --name "$INSTANCE_NAME" --request-id instance-bootstrap
ctxctl instance-get --instance-id "$INSTANCE_ID"
```

登记成功 HTTP 201，私有完整响应在 `$DEPLOY/requests/instance-bootstrap/response.json`；stdout 不输出 secret。**先持久保存这份文件，才能向管控上报初始化成功。** 同一 request-id 再执行脚本复用已保存响应，不覆盖管理员 Key；API 对同实例、同名称重复登记返回 `admin_key=null`，不同名称 409，配置身份不符 403。

`/health/ready` 只表示 API readiness；还未登记、未启动 UI 时不能向客户宣布实例可用。`POST /instances` 不申请 PG/计算、不启动进程、不自动建默认空间。Worker 执行业务任务；空间管理任务由 API 内的执行器完成。

初次响应丢失且本地没有管理员 secret 时，先 instance-get 确认登记，再**明确执行一次**恢复：

```bash
ctxctl admin-key-recover --instance-id "$INSTANCE_ID" \
  --name 'Initialization recovery' --request-id admin-recovery-001
```

恢复响应是独立 KeyIssued（顶层 `secret`），保存在对应 response.json。恢复接口没有服务端幂等性，超时结果未知时脚本拒绝同一 request-id 再提交；检查 API 审计后再决定是否签新 Key。恢复不是取回旧明文。

## 6 配置 UI，实例开通完成

正常初始化用 bootstrap 响应；走过恢复时改用其 response.json：

```bash
ctxctl configure-ui --bootstrap "$DEPLOY/requests/instance-bootstrap/response.json"
ctxdb_start_ui
ctxdb_status
```

节点脚本以干净环境启动 UI，只加载 ui.env 的四项配置和必要运行变量，不继承 PG、模型或 pepper。应得到登录页面。管控再检查登记身份、进程和 UI，保存 API/UI 对外地址，将实例置可用。外部访问 UI 用节点实际 IP或域名，API 也用节点地址；正式部署的 HTTPS/反向代理由已有平台提供，需按真实 Host 检查登录。UI 服务端到 API 仍用 loopback。仅管理员输入 UI 独立口令；成员 API Key 不能登录，浏览器不持有 UI 的固定管理员 Key。

管控安全交付 UI 口令，例如操作者本机查看：

```bash
python3 -c 'import json,os; print(json.load(open(os.environ["DEPLOY"]+"/ui-password.json"))["password"])'
```

管理员业务 Key 在私有 bootstrap/recovery 响应中，按管控现有秘密交付机制提供。不要写普通任务日志。恢复/轮换固定 Key 时执行 `configure-ui --bootstrap 新响应文件 --replace`，再按第 8 节重启 UI；该命令复用原 UI 口令。

## 7 工作空间：具体请求、查询和重试

新终端按第 2 节 source 节点函数脚本，即可使用 ctxctl；空间操作不需要 MaaS/PG 密码。脚本只从 control-key.json 读取管控服务 Key，所有管理请求带可信 ACTOR。

### 7.1 创建 MySQL、PG：同步等待示例

```bash
ctxctl workspace-create --name MySQL --description 'MySQL 业务记忆' --request-id create-mysql-001
ctxctl workspace-create --name PG --description 'PG 业务记忆' --request-id create-pg-001
ctxctl workspace-list --limit 20 --offset 0
export MYSQL_ID=$(python3 -c 'import json,os; print(json.load(open(os.environ["DEPLOY"]+"/requests/create-mysql-001/workspace.json"))["workspace_id"])')
export PG_ID=$(python3 -c 'import json,os; print(json.load(open(os.environ["DEPLOY"]+"/requests/create-pg-001/workspace.json"))["workspace_id"])')
ctxctl workspace-get "$MYSQL_ID"
ctxctl workspace-get "$PG_ID"
```

POST 返回 202后脚本每 2 秒查询操作，最多等 300 秒；只在 `succeeded` 后查询空间、确认 active 并保存 workspace.json。`workspace_id=bank_id`，客户端用这个 ID 调原生 REST/MCP，不传 schema。名称在实例内规范化后唯一，ID 不变；没有空间改名 PATCH。

### 7.2 管控调度：先受理，再独立查询

实际管控任务不要等待一个长 HTTP 请求。Agent 执行以下调用，将 202 的原始结果返回管控；管控保存 operation_id 和 workspace_id，再发查询任务：

```bash
ctxctl workspace-create --name Demo --request-id create-demo-001 --no-wait
export OP_ID=$(python3 -c 'import json,os; print(json.load(open(os.environ["DEPLOY"]+"/requests/create-demo-001/response.json"))["operation_id"])')
ctxctl operation-get "$OP_ID"
# 手工联调可以等最终结果；管控采用定时 operation-get。
ctxctl operation-wait "$OP_ID"
```

| 脚本命令 | 实际 HTTP（前缀 `/ext/contextdb/v1`） |
| --- | --- |
| instance-register | POST /instances：instance_id、cloud_tenant_id、name |
| instance-get | GET /instances/{instance_id} |
| admin-key-recover | POST /instances/{instance_id}/admin-keys：name |
| workspace-create | POST /workspaces：name、description；Idempotency-Key |
| workspace-list/get | GET /workspaces?limit=&offset= / GET /workspaces/{id} |
| workspace-delete | DELETE /workspaces/{id}；Idempotency-Key |
| operation-get/wait | GET /operations/{operation_id} |

**当前没有 Agent 专属转发接口。** Agent 团队可复用脚本，也可按上表实现同样请求；应保留 HTTP 状态码、JSON 响应、X-Request-ID。脚本 stdout 是便于联调的 JSON，失败返回非零；生产 Agent 如需精确 HTTP 状态和请求 ID，直接按 OpenAPI 转发，不能仅把脚本退出码当成全部响应合同。

创建/删除超时，重试原命令、原 request-id、原 ACTOR、原正文，取得同一 operation；本地 request.json 会拒绝把同 ID 用于另一个正文/URL/操作人。不要重跑 configure、更换 Key或生成新的创建幂等值。已明确 failed 并修复原因后，重用原请求可触发后端重试；未知旧执行者必须先完成隔离。

### 7.3 删除：用独立临时空间演示

不删除上面的 MySQL/PG，单独建立一次性空间：

```bash
ctxctl workspace-create --name DeleteDemo --request-id create-delete-demo-001
export DELETE_ID=$(python3 -c 'import json,os; print(json.load(open(os.environ["DEPLOY"]+"/requests/create-delete-demo-001/workspace.json"))["workspace_id"])')
ctxctl workspace-delete "$DELETE_ID" --request-id delete-demo-001 --no-wait
export DELETE_OP=$(python3 -c 'import json,os; print(json.load(open(os.environ["DEPLOY"]+"/requests/delete-demo-001/response.json"))["operation_id"])')
ctxctl operation-wait "$DELETE_OP"
ctxctl workspace-list
# 预期 404 用 if 捕获，避免 set -e 提前结束；其他失败不能冒充删除成功。
if ctxctl workspace-get "$DELETE_ID" > "$DEPLOY/deleted-get.json" 2> "$DEPLOY/deleted-get.err"; then
  printf '错误：已删除空间仍可查询\n' >&2; exit 1
elif [[ $(cat "$DEPLOY/deleted-get.err") != *'HTTP 404:'* ]]; then
  cat "$DEPLOY/deleted-get.err" >&2; exit 1
fi
```

DELETE 202后空间进入 deleting，API 阻断新请求，等待已有准入与业务任务排空，再清理 Bank，保留 schema/表和墓碑。`waiting_for_tasks`/`waiting_for_admissions` 是等待原因，即使 error_code 非空也不表示 failed；以 state 为准。查询超过展示超时后继续后台跟踪，操作不会因客户端停止等待而取消。

原生 Hindsight UI 支持删除 Bank，但 ContextDB 模式禁止该入口；管理员业务 Key也不能直接删 Bank。不要调用原生 DELETE /banks 或手动 DROP SCHEMA，工作空间关系与授权必须由上述流程处理。

PG 核验可由持有服务 DB_URL 的节点执行：

```bash
source "$DEPLOY/api.env"
"$PG_BIN/psql" -X "$HINDSIGHT_API_DATABASE_URL" -v ON_ERROR_STOP=1 \
  -c 'SELECT workspace_id,name,schema_name,state FROM ctxdb_meta.workspaces ORDER BY created_at;' \
  -c "SELECT schemaname,indexname,indexdef FROM pg_indexes WHERE schemaname LIKE 'ctxdb_ws_%' AND indexdef ILIKE '%pgroonga%';"
```

应看到 MySQL/PG active、DeleteDemo deleted；每个 active schema 有实际 PGroonga 索引。是否高质量检索仍需手册中的中英文业务样本验证，不能只检查扩展存在。

## 8 停止、重启、升级与销毁

API没有停止/重启/升级/DELETE instances 的接口。它们由节点 Agent 和云资源流程实现。以下 PID 命令仅用于上面的 nohup 联调部署，**先核对进程确属本次 DEPLOY/CODE，不直接信任历史 pid 文件**：

```bash
ctxdb_status
# 管控先关闭新流量、暂停空间操作，确认已受理任务排空，再停止。
# 函数检查 PID、记录的启动时间及本次代码归属；兼容 Next 的 next-server 进程标题，SIGTERM 后等待退出，超时不强杀。
ctxdb_stop_service ui
ctxdb_stop_service worker
ctxdb_stop_service api
# 重启时不执行 migrate/register/凭据生成。
ctxdb_start_api
ctxdb_start_worker
ctxdb_start_ui
ctxctl instance-get --instance-id "$INSTANCE_ID"
```

管控先关闭新业务流量、暂停空间变更，等待已受理任务排空，然后停止服务；确认进程退出后才能重启。不要用 SIGKILL、宽泛 pkill 或直接清理 admission 来代替正常关闭。工作空间删除不是实例销毁。

| 操作 | 可执行内容 / 完成判定 |
| --- | --- |
| 重启 API/Worker | source 节点函数脚本，复用原 api.env、原 DB；执行 ctxdb_start_api/worker 及健康检查，随后 instance-get；不重复 migrate/register/凭据生成 |
| 重启 UI | source 节点函数脚本，执行 ctxdb_start_ui 及检查，自动加载原 ui.env；不重新生成 UI 口令 |
| 升级 | 先备份 PG与私有配置，停止空间变更、排空并停止旧服务；Agent切换已审核发布包，以唯一迁移执行者执行兼容迁移，再启动检查。当前 V2不支持 V1 元数据就地升级，不能将本手册套用于 V1旧库 |
| 高可用恢复 | 由已有 Agent机制隔离旧执行者，恢复同一实例配置和 PG，再检查已有空间/操作；未知旧执行者未隔离前不强行重试 DDL或删除屏障 |
| 销毁 | 先关闭客户入口及自动恢复，确认备份/保留策略，停止全部节点服务，再由资源管控回收计算/PG；不提供一键删库脚本 |

升级/HA 的发行包、迁移与隔离协议取决于平台现有能力，本文未宣称已经验收。

## 9 联调检查与待填合同

| 用例 | 判定 |
| --- | --- |
| 实例完整开通 | PG UTF8/插件/角色 → metadata2 → API/Worker健康 → 登记与秘密持久化 → UI → 实例可用 |
| 首次响应丢失 | 登记可查；重复登记不取回秘密；恢复调用不盲目重复；UI 使用已安全保存的新 Key |
| 两空间创建 | 202受理，operation succeeded，空间 active；不同 ID/schema，各唯一 Bank |
| 创建重试 | 原 request-id 返回同 operation；换正文/操作人/重复名称不当成成功 |
| 删除与重试 | 等待在途任务；成功后详情404、墓碑/空 schema表保留、原幂等值可查原 operation |
| Agent/API异常 | 分清 Agent不可达、API未启动、API已受理、operation失败；恢复后查询，避免重复资源 |
| UI | 管理员口令可进入，两空间可见，用户/Key管理可用；空间生命周期入口关闭 |

联调前管控与 Agent 团队只需补齐：实际 Agent 调度接口、实例到 API 节点的路由、运维任务与 operation_id 的关联、凭据由谁保管与交付、RDS 是否支持本文扩展/参数。尚未有实际 Agent协议时，以上 localhost命令可直接执行，但端到端云管控仍为 NOT_RUN。

完整响应和错误合同见 [V2 OpenAPI](../../api/contextdb-control-plane.openapi.yaml)。业务/权限验证见 [验证与演示手册](../../implementation/contextdb-v2-local-validation-guide.md)，模型/环境变量见 [部署手册](../../implementation/contextdb-v2-deployment-usage-guide.md)。[SQL统计配置依据](https://www.postgresql.org/docs/18/pgstatstatements.html)。本文辅助脚本的模拟验证与专家审阅结果另见 [命令与文档审核记录](../../implementation/contextdb-v2-control-plane-executable-review-2026-10-15.md)。
