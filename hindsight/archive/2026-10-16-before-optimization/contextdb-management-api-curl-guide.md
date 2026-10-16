# ContextDB 管理 API：curl 验证手册

日期：2026-10-16。适用：当前本地运行的首发简化版本。

按“实例初始化 → 工作空间管理 → 用户管理 → API Key 管理 → 清理资源”验证。覆盖全部 14 个自研管理操作，另附健康检查；不包含原生 Retain / Recall / Reflect 的完整业务验收。

本手册生成时已实际确认 API 健康检查、管理员身份检查成功。下面的创建、修改、吊销和删除用例未自动执行，供人工逐步验证。

## 1. 验证前准备

### 1.1 当前部署

| 项目 | 当前值 |
| --- | --- |
| API | `http://127.0.0.1:8890` |
| UI | `http://127.0.0.1:9998` |
| 实例 ID | `ctxdb-simple-20261016_091155` |
| 租户 ID | `local-cloud-tenant` |
| PG | `127.0.0.1:5432/contextdb_simple_20261016_091155` |
| 管理接口前缀 | `/ext/contextdb/v1` |

其他机器验证时，将每条 curl 中的 `127.0.0.1` 替换为部署机器的可达 IP；API 端口保持 `8890`。本手册使用独立的新测试资源，不操作已有 MySQL、PG 等空间。

### 1.2 加载当前可用的 Admin Key

在同一个 Bash 终端中按顺序执行。需要 `curl`、`jq`。下面从当前部署的私有文件读取真实、已验证可用的 Admin Key，不需要自行填写一个示例 Key。

```bash
bash
umask 077

export RUN='/Users/zhuqingping/Work/Database/Context/test/hindsight_test/contextdb-first-release-experience/20261016_091155'
export ADMIN_KEY=$(jq -er '.secret' "$RUN/admin-key.json")
export CASE_DIR=$(mktemp -d /tmp/contextdb-api-demo.XXXXXX)
export DEMO_NAME="api-demo-$(date +%Y%m%d%H%M%S)-$$"

command -v curl
command -v jq
echo "响应文件目录：$CASE_DIR"
echo "测试资源前缀：$DEMO_NAME"
```

所有管理接口都使用 `Authorization: Bearer $ADMIN_KEY`。业务 Key 即使有全部工作空间权限，也不能调用这些接口。UI 登录密码与此 Admin Key 是两个独立凭据。

换到其他机器执行时，先在该机器安全设置 `ADMIN_KEY`，再执行 `CASE_DIR`、`DEMO_NAME` 的初始化；原机器上的 `RUN` 路径不能直接在远端读取。

每条命令执行失败时先停止后续步骤，检查返回值。创建响应及新业务 Key 会保存在私有的 `CASE_DIR` 中；不要把这些文件提交到代码仓库。

## 2. 实例初始化与检查

### 2.1 实例创建：离线部署，没有 HTTP 创建接口

当前没有 `POST /instances` 或实例注册接口。实例由运维/节点 Agent 部署：准备专用 PG 数据库及扩展，生成 Admin Key，写入配置，初始化元数据，再启动 API、Worker 和 UI。

当前实例已经完成初始化，不要为执行本手册重新生成它的 Key 或 pepper。

新部署的两个离线入口如下，属于部署说明，不是本次 curl 验证步骤：

```bash
# 在已安装 ContextDB 扩展的 Python 环境中首次生成运维凭据。
# 输出包含 key_id、secret、sha256，应保存到受保护文件。
python -m hindsight_ext_contextdb generate-admin-key

# 配置好实例/租户 ID、数据库 URL、Admin Key 摘要、pepper 后执行。
# 在 API/Worker 启动前安装并绑定元数据。
python -m hindsight_ext_contextdb migrate
```

API 使用 `CONTEXTDB_ADMIN_KEY_SHA256` 保存摘要；UI 服务端的 `HINDSIGHT_CP_DATAPLANE_API_KEY` 使用对应明文，`HINDSIGHT_CP_ACCESS_KEY` 是独立的 UI 登录密码。数据库连接使用 `HINDSIGHT_API_DATABASE_URL`；离线初始化使用 `CONTEXTDB_BOOTSTRAP_DATABASE_URL`。

完整部署命令见 [首发部署与验收](/Users/zhuqingping/Work/Database/Context/.local/worktrees/contextdb-v2-simple-20261016/hindsight-extensions/contextdb-service/docs/contextdb-first-release-guide.md)。本手册后续只调用已经启动的实例。

### 2.2 健康检查

**接口：** `GET /health/ready`。无需鉴权、无参数。确认数据库连接和服务就绪。

```bash
curl -fsS \
  'http://127.0.0.1:8890/health/ready' | jq .
```

预期 HTTP `200`，主要字段：

```json
{
  "status": "healthy",
  "database": "connected"
}
```

实际还包含连接池统计，数值会变化。

### 2.3 检查管理员身份（管理操作 1/14）

**接口：** `GET /ext/contextdb/v1/admin/session`。无业务参数。

```bash
curl -fsS \
  'http://127.0.0.1:8890/ext/contextdb/v1/admin/session' \
  -H "Authorization: Bearer $ADMIN_KEY" | jq .
```

当前实例实际返回 HTTP `200`：

```json
{
  "user_id": "instance-admin",
  "role": "admin",
  "instance_id": "ctxdb-simple-20261016_091155",
  "cloud_tenant_id": "local-cloud-tenant"
}
```

`instance-admin` 是运维身份标识，不是通过用户管理接口创建的成员。

## 3. 工作空间管理

一个工作空间对应一个独立 PG schema；`workspace_id` 同时也是原生 REST/MCP 调用中的 `bank_id`。空间 ID 和 schema 由服务生成，客户端不能指定。

### 3.1 创建工作空间（2/14）

**接口：** `POST /ext/contextdb/v1/workspaces`。

| 参数 | 位置 | 约束 |
| --- | --- | --- |
| `Idempotency-Key` | Header，必填 | 1～128 字符，同一次操作重试时复用 |
| `name` | JSON，必填 | 1～64 字符；服务归一化后校验名称冲突 |
| `description` | JSON，可选 | 最多 512 字符，默认空字符串 |

```bash
curl -fsS -X POST \
  'http://127.0.0.1:8890/ext/contextdb/v1/workspaces' \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $DEMO_NAME-create" \
  -d "{
    \"name\": \"$DEMO_NAME\",
    \"description\": \"用于手工验证管理接口\"
  }" \
  | tee "$CASE_DIR/workspace-create.json" | jq .

export WORKSPACE_ID=$(jq -er '.workspace_id' "$CASE_DIR/workspace-create.json")
export CREATE_OPERATION_ID=$(jq -er '.operation_id' "$CASE_DIR/workspace-create.json")
```

预期 HTTP `202`，响应结构如下。尖括号内容均为说明，真实 ID 已由上面的命令自动保存。

```json
{
  "operation_id": "<操作ID>",
  "workspace_id": "<工作空间ID>",
  "action": "create_workspace",
  "state": "pending",
  "error_code": null
}
```

`202` 只表示受理，需要继续查询进度。相同幂等 Key 和相同请求体重试会返回已有操作；同 Key 携带不同内容会冲突。

### 3.2 查询操作进度（3/14）

**接口：** `GET /ext/contextdb/v1/operations/{operation_id}`。URL 参数为创建/删除响应中的操作 ID。

```bash
curl -fsS \
  "http://127.0.0.1:8890/ext/contextdb/v1/operations/$CREATE_OPERATION_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" | jq .
```

预期 HTTP `200`，返回 `operation_id、workspace_id、action、state、error_code`。

| state | 含义 |
| --- | --- |
| `pending` | 等待执行 |
| `running` | 正在执行 |
| `succeeded` | 已完成 |
| `failed` | 失败，检查 error_code |

重复执行直到 `succeeded`，再继续授权。超时未完成时继续查同一个操作，不要换幂等 Key 重复创建。

### 3.3 查询工作空间列表（4/14）

**接口：** `GET /ext/contextdb/v1/workspaces`。

| 查询参数 | 约束 |
| --- | --- |
| `q` | 名称包含匹配，不区分大小写，最多 128 字符，默认空 |
| `limit` | 默认 20，范围 0～100 |
| `offset` | 默认 0，不小于 0 |

```bash
curl -fsS -G \
  'http://127.0.0.1:8890/ext/contextdb/v1/workspaces' \
  -H "Authorization: Bearer $ADMIN_KEY" \
  --data-urlencode "q=$DEMO_NAME" \
  --data-urlencode 'limit=20' \
  --data-urlencode 'offset=0' | jq .
```

预期 HTTP `200`：

```json
{
  "items": [
    {
      "workspace_id": "<工作空间ID>",
      "name": "<测试空间名称>",
      "description": "用于手工验证管理接口",
      "state": "active",
      "version": 1,
      "created_at": "<创建时间>"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

示例版本号以实际响应为准。列表可能包含处于创建、删除等中间状态的空间，已删除空间不返回。

### 3.4 查询单个工作空间（5/14）

**接口：** `GET /ext/contextdb/v1/workspaces/{workspace_id}`。URL 参数为工作空间 ID。

```bash
curl -fsS \
  "http://127.0.0.1:8890/ext/contextdb/v1/workspaces/$WORKSPACE_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" | jq .
```

预期 HTTP `200`，返回上述单个工作空间对象，创建完成后为 `state: "active"`。响应 Header 包含版本 `ETag`。

### 3.5 删除工作空间

删除会清理空间数据，安排在 [第 6.2 节](#62-删除测试工作空间1414) 执行，避免影响后面的用户和 Key 测试。当前没有工作空间修改接口。

## 4. 用户管理

用户是业务 Key 的归属主体。创建时只填写名称，不设置角色或空间权限，也不自动生成 Key。停用用户可以统一阻断其所有 Key。

### 4.1 创建用户（6/14）

**接口：** `POST /ext/contextdb/v1/users`。JSON 参数 `name` 必填，1～64 字符。

```bash
curl -fsS -X POST \
  'http://127.0.0.1:8890/ext/contextdb/v1/users' \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"$DEMO_NAME-user\"}" \
  | tee "$CASE_DIR/user-create.json" | jq .

export USER_ID=$(jq -er '.user_id' "$CASE_DIR/user-create.json")
export USER_VERSION=$(jq -er '.version' "$CASE_DIR/user-create.json")
```

预期 HTTP `201`：

```json
{
  "user_id": "<用户ID>",
  "instance_id": "ctxdb-simple-20261016_091155",
  "name": "<测试用户名称>",
  "status": "active",
  "version": 1,
  "created_at": "<创建时间>"
}
```

响应 Header 包含 `ETag: "1"`。当前没有供普通成员选择管理员角色的参数。

### 4.2 查询用户列表（7/14）

**接口：** `GET /ext/contextdb/v1/users`。`q、limit、offset` 的含义和范围与工作空间列表一致。

```bash
curl -fsS -G \
  'http://127.0.0.1:8890/ext/contextdb/v1/users' \
  -H "Authorization: Bearer $ADMIN_KEY" \
  --data-urlencode "q=$DEMO_NAME" \
  --data-urlencode 'limit=20' \
  --data-urlencode 'offset=0' | jq .
```

预期 HTTP `200`，返回 `items、total、limit、offset`，每项为用户对象。列表包含 active/disabled 用户，排除已删除用户。当前没有单独的 `GET /users/{user_id}`。

### 4.3 修改名称或状态（8/14）

**接口：** `PATCH /ext/contextdb/v1/users/{user_id}`。

| 参数 | 约束 |
| --- | --- |
| `If-Match` Header | 必填，当前版本，双引号是值的一部分，例如 `"1"` |
| JSON `name` | 可选，1～64 字符 |
| JSON `status` | 可选，`active` 或 `disabled` |

至少提供一个非 null 字段，不能空请求体。下面先只修改名称，保持用户 active，以便后续创建 Key。

```bash
curl -fsS -X PATCH \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -H "If-Match: \"$USER_VERSION\"" \
  -d "{\"name\":\"$DEMO_NAME-user-edited\"}" \
  | tee "$CASE_DIR/user-update.json" | jq .

export USER_VERSION=$(jq -er '.version' "$CASE_DIR/user-update.json")
```

预期 HTTP `200`，返回修改后的用户对象，version 更新。版本过期返回 `412`。

可选的停用/恢复测试建议在第 5.1 节创建 Key 后进行，以检查已有 Key 受用户状态影响。停用命令：

```bash
curl -fsS -X PATCH \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -H "If-Match: \"$USER_VERSION\"" \
  -d '{"status":"disabled"}' \
  | tee "$CASE_DIR/user-disabled.json" | jq .

export USER_VERSION=$(jq -er '.version' "$CASE_DIR/user-disabled.json")
```

恢复命令：

```bash
curl -fsS -X PATCH \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -H "If-Match: \"$USER_VERSION\"" \
  -d '{"status":"active"}' \
  | tee "$CASE_DIR/user-restored.json" | jq .

export USER_VERSION=$(jq -er '.version' "$CASE_DIR/user-restored.json")
```

两次均预期 HTTP `200`。停用阻断全部 Key 的后续认证；恢复只恢复未吊销 Key 的使用资格，不恢复已吊销 Key，不表示撤销已经执行中的请求。

删除用户放在第 6.1 节，避免提前删除导致后面的 Key 管理失败。

## 5. API Key 管理

授权配置在 Key 上，一个用户可以有多个 Key；一个 Key 可以访问单个、多个或全部工作空间。

### 5.1 创建业务 Key（9/14）

**接口：** `POST /ext/contextdb/v1/users/{user_id}/keys`。用户必须 active。

| JSON 参数 | 约束 |
| --- | --- |
| `name` | 必填，1～64 字符 |
| `access_mode` | `selected` 或 `all`，默认 selected |
| `workspace_ids` | 默认空数组，最多 1000 项，不重复，每项为 32 位小写十六进制 ID |
| `permission` | `read_write` 或 `read`，默认 read_write |

selected 必须指定至少一个 active 空间；all 必须为空数组，表示全部空间，包括未来创建的空间。

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID/keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -d "{
    \"name\": \"$DEMO_NAME-key\",
    \"access_mode\": \"selected\",
    \"workspace_ids\": [\"$WORKSPACE_ID\"],
    \"permission\": \"read_write\"
  }" \
  | tee "$CASE_DIR/key-create.json" | jq .

export KEY_ID=$(jq -er '.key_id' "$CASE_DIR/key-create.json")
export KEY_VERSION=$(jq -er '.version' "$CASE_DIR/key-create.json")
export BUSINESS_KEY=$(jq -er '.secret' "$CASE_DIR/key-create.json")
```

预期 HTTP `201`：

```json
{
  "key_id": "<Key ID>",
  "user_id": "<用户ID>",
  "name": "<Key名称>",
  "access_mode": "selected",
  "workspace_ids": ["<工作空间ID>"],
  "permission": "read_write",
  "revoked_at": null,
  "version": 1,
  "created_at": "<创建时间>",
  "last_used_at": null,
  "status": "active",
  "secret": "ctx_live_..."
}
```

`secret` 是业务调用的 API Key，只在创建时返回；`key_id` 只是管理标识。上面的示例会展示明文并保存到私有文件，便于本次人工验证。

多空间授权请求体示意（将 ID 换成实际空间 ID）：

```json
{
  "name": "多空间读写Key",
  "access_mode": "selected",
  "workspace_ids": ["<空间A的ID>", "<空间B的ID>"],
  "permission": "read_write"
}
```

全部空间授权请求体：

```json
{
  "name": "全部空间读写Key",
  "access_mode": "all",
  "workspace_ids": [],
  "permission": "read_write"
}
```

当前一个 Key 的 permission 对全部授权空间统一生效，暂不支持“A 读写、B 只读”。read 支持 Recall、Reflect 和已有内容读取；read_write 额外支持 Retain 等内容写入。两者都不包括工作空间、用户、Key 管理；归档和 webhook 等敏感管理能力保留给运维管理员。

### 5.2 查询用户的 Key 列表（10/14）

**接口：** `GET /ext/contextdb/v1/users/{user_id}/keys`。查询参数 q、limit、offset 的含义和范围同前。

```bash
curl -fsS -G \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID/keys" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  --data-urlencode "q=$DEMO_NAME" \
  --data-urlencode 'limit=20' \
  --data-urlencode 'offset=0' | jq .
```

预期 HTTP `200`，返回分页列表，每项为 Key 元数据，不包含 secret 或摘要。当前仍返回已吊销记录，通过 status/revoked_at 区分。

### 5.3 修改 Key 授权（11/14）

**接口：** `PATCH /ext/contextdb/v1/users/{user_id}/keys/{key_id}`。

必填 Header If-Match（当前 Key 版本，带双引号）；JSON 必须完整提供 access_mode、workspace_ids、permission 三个字段。字段约束与创建相同。当前不支持修改 Key 名称。

下面将测试 Key 从读写改为只读：

```bash
curl -fsS -X PATCH \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID/keys/$KEY_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H 'Content-Type: application/json' \
  -H "If-Match: \"$KEY_VERSION\"" \
  -d "{
    \"access_mode\": \"selected\",
    \"workspace_ids\": [\"$WORKSPACE_ID\"],
    \"permission\": \"read\"
  }" \
  | tee "$CASE_DIR/key-update.json" | jq .

export KEY_VERSION=$(jq -er '.version' "$CASE_DIR/key-update.json")
```

预期 HTTP `200`，返回修改后的元数据，permission 为 read，version 更新。原 BUSINESS_KEY 不变，不重新返回明文；过期版本返回 `412`，已吊销 Key 不能再编辑授权。

### 5.4 吊销 Key（12/14）

**接口：** `DELETE /ext/contextdb/v1/users/{user_id}/keys/{key_id}`。无请求体，无需 If-Match。

```bash
curl -sS -X DELETE \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID/keys/$KEY_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -o /dev/null \
  -w 'HTTP %{http_code}\n'
```

预期 `HTTP 204`，返回体为空。永久吊销，不能恢复；后台保留记录及 revoked_at。

执行第 5.2 节列表查询，应仍可看到该 Key，其 `status` 为 revoked、`revoked_at` 非空。删除用户之前，重复吊销同一个已吊销 Key 仍返回 204。

## 6. 清理测试资源

只删除本手册生成的 USER_ID、WORKSPACE_ID。第 5.4 节已经吊销测试 Key。

### 6.1 删除测试用户（13/14）

**接口：** `DELETE /ext/contextdb/v1/users/{user_id}`。无请求体，无需 If-Match。

```bash
curl -sS -X DELETE \
  "http://127.0.0.1:8890/ext/contextdb/v1/users/$USER_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -o /dev/null \
  -w 'HTTP %{http_code}\n'
```

预期 HTTP `204`，无返回体。用户软删除，其全部 Key 无法通过后续认证；空间和记忆数据保留。重新查询用户列表不再展示该用户。

### 6.2 删除测试工作空间（14/14）

**接口：** `DELETE /ext/contextdb/v1/workspaces/{workspace_id}`。必填 Header Idempotency-Key，1～128 字符，无请求体。此操作会清理该空间的数据。

```bash
curl -fsS -X DELETE \
  "http://127.0.0.1:8890/ext/contextdb/v1/workspaces/$WORKSPACE_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -H "Idempotency-Key: $DEMO_NAME-delete" \
  | tee "$CASE_DIR/workspace-delete.json" | jq .

export DELETE_OPERATION_ID=$(jq -er '.operation_id' "$CASE_DIR/workspace-delete.json")
```

预期 HTTP `202`：

```json
{
  "operation_id": "<删除操作ID>",
  "workspace_id": "<工作空间ID>",
  "action": "delete_workspace",
  "state": "pending",
  "error_code": null
}
```

查询删除进度，重复到 succeeded：

```bash
curl -fsS \
  "http://127.0.0.1:8890/ext/contextdb/v1/operations/$DELETE_OPERATION_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" | jq .
```

确认空间已删除：

```bash
curl -sS \
  "http://127.0.0.1:8890/ext/contextdb/v1/workspaces/$WORKSPACE_ID" \
  -H "Authorization: Bearer $ADMIN_KEY" \
  -w '\nHTTP %{http_code}\n'
```

预期 HTTP `404`。如操作仍 pending/running，继续查同一个操作；如 failed，先检查 error_code，不要据 202 判断删除已完成。

## 7. 返回码、重试与接口边界

| HTTP | 说明 |
| --- | --- |
| 200 | 查询或修改成功 |
| 201 | 用户或 Key 创建成功 |
| 202 | 空间操作受理，需查询进度 |
| 204 | 用户删除或 Key 吊销成功，无响应体 |
| 400 | 参数、幂等 Header 或版本 Header 不合法 |
| 401 | 缺少或无效凭据 |
| 403 | 有效业务 Key 调用了管理员接口 |
| 404 | 目标不存在 |
| 409 | 名称、幂等请求或资源状态冲突 |
| 412 | If-Match 版本过期，需要重新获取当前版本 |
| 503 | 元数据服务不可用 |

错误体统一为：

```json
{
  "code": "<错误标识>",
  "message": "<错误说明>",
  "request_id": "<请求追踪ID>"
}
```

管理请求响应包含 X-Request-ID 和 Cache-Control: no-store；单个用户、Key、空间对象响应包含相应 ETag。`curl -fsS` 遇 HTTP 错误会报错；需要查看错误 JSON 和状态码时，将该条改为 `curl -sS -i` 并去掉末尾 jq 管道。

工作空间创建/删除支持幂等重试。用户和 Key 创建当前没有幂等参数；请求超时、结果未知时先查询列表，避免直接重试造成重复创建。若 Key 已创建但明文丢失，列表无法找回 secret，需要吊销后重新签发。

原生 Bank 创建、删除等生命周期接口被限制，管理员也必须使用工作空间接口，以维护空间和 schema 映射。原生 REST/MCP 内容操作另行使用 bank_id=workspace_id 调用。

## 8. 已有的整组自动测试入口（可选）

若要一次顺序验证 14 个管理操作，可手动执行同目录已有脚本：

```bash
bash "$RUN/api-design-review/management-api-cases.sh"
```

脚本自行创建临时空间、用户和 Key，最后吊销并删除自己创建的资源；不复用本文手工创建的对象。中途失败会停止并保留结果与临时资源，便于排查。脚本默认访问 8890，读取同目录私有 admin.curl；本手册生成时未运行其写入用例。
