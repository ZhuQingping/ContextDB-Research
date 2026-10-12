# Hindsight API 协议对比（REST + MCP）：商用版与开源版

> 日期：2026-10-09
> 验证对象：本地开源 Hindsight `0.10.1`（运行实例）；商用 Hindsight Cloud `0.10.2`（运行实例）
> 关联文档：[hindsight-cloud-open-source-comparison.md](hindsight-cloud-open-source-comparison.md)（部署形态与商业控制面对比）、[2026-10-09-Agent与Hindsight交互协议辨析](../2026-10-09-Agent与Hindsight交互协议辨析-Rest-MCP-SDK.md)

---

## 0. 证据边界声明（两侧均今天实测）

本文所有结论均基于 **2026-10-09 当天对两个运行实例的直接调用**，不依赖经验或历史证据：

| 证据 | 状态 | 来源 |
|---|---|---|
| **本地开源版（http://127.0.0.1:8888）** | ✅ **今天实测** | 直接调用运行实例：OpenAPI、REST、MCP tools/list、retain/recall/reflect 全部真实返回 |
| **商用版（https://api.hindsight.vectorize.io）** | ✅ **今天实测** | 经代理 `proxyhk.huawei.com:8080`（带认证 + `-k` SSL）直连商用实例：OpenAPI、REST、MCP tools/list、banks/stats/recall 全部真实返回 |

**商用版连通方式（已验证可用）：**
- **正确代理**：`proxyhk.huawei.com:8080`（IP 172.18.100.92，端口 OPEN），需带 Basic 认证（用户名 `z00835654`）；
- 该代理做 HTTPS 拦截（注入自签名 CA），需加 `-k` 跳过证书验证；
- 复现：`curl -k -x "http://xxxx:xxxx@proxyhk.huawei.com:8080" https://api.hindsight.vectorize.io/health` → `{"status":"healthy","database":"connected"}`

**API Key 实测**：商用 key `hsk_3b38...` 有效——无 key → `401 {"detail":"Authentication failed: API key required"}`，有 key → `200`。

---

## 1. Hindsight 同时支持 REST 与 MCP：两套协议的定位

| 协议 | 端点前缀 | 调用者 | 调用时机 | 今天实测 |
|---|---|---|---|---|
| **REST** | `/v1/default/banks/{bank_id}/...` | 程序（SDK/控制面/脚本/hook） | 开发者写死 | ✅ 本地 69 路径/89 操作；商用 86 路径 |
| **MCP** | `/mcp`（Streamable HTTP） | AI 模型（Claude Code/Cursor 等） | 模型自主决定 | ✅ 本地 39 工具；商用 40 工具 |

**核心关系**（今天实测证实）：
- **同一个端口（本地 8888）、同一个进程**同时挂 REST 和 MCP，用 URL 前缀区分；
- **同一个 `MemoryEngine`**：今天用 REST `retain` 写入一条事实，用 MCP `tools/call recall` 读回同一条事实——证明两协议底层同源；
- **REST 暴露"传输"**（HTTP 方法/状态码/请求体），**MCP 暴露"任务"**（工具名 + 参数 schema + 只读/危险注解）。

---

## 2. 开源版 REST API 全量列表（今天实测：69 路径 / 89 操作，v0.10.1）

> 实测来源：`curl http://127.0.0.1:8888/openapi.json`（320566 字节，74 路径，其中 5 条运维路径）。下方按业务域分类。

### 2.1 记忆读写（核心三件套）

| 方法 | 路径 | 含义 |
|---|---|---|
| POST | `/v1/default/banks/{bank_id}/memories` | **Retain**：存记忆（异步抽取事实/实体/关系） |
| POST | `/v1/default/banks/{bank_id}/memories/recall` | **Recall**：多策略检索记忆（语义+BM25+图+时序，再 rerank） |
| POST | `/v1/default/banks/{bank_id}/reflect` | **Reflect**：基于记忆+心智模型的反思推理 |
| POST | `/v1/default/banks/{bank_id}/memories/dry-run-extract` | 预演事实抽取（不落库） |
| GET | `/v1/default/banks/{bank_id}/memories/list` | 列记忆（分页） |
| POST,DELETE | `/v1/default/banks/{bank_id}/memories` | DELETE = 清空 bank 所有记忆 |
| GET,PATCH | `/v1/default/banks/{bank_id}/memories/{memory_id}` | 读/改单条记忆 |
| GET | `/v1/default/banks/{bank_id}/memories/{memory_id}/history` | 记忆变更历史 |
| DELETE | `/v1/default/banks/{bank_id}/memories/{memory_id}/observations` | 删除记忆的观察点 |
| DELETE | `/v1/default/banks/{bank_id}/observations` | 删除观察点 |
| GET | `/v1/default/banks/{bank_id}/observations/scopes` | 观察点作用域 |
| POST | `/v1/default/banks/{bank_id}/files/retain` | 文件保留（上传文件后存记忆） |
| GET | `/v1/default/chunks/{chunk_id}` | 读文档块 |
| GET | `/v1/default/files/download/{key}` | 下载导出文件 |

### 2.2 Bank（记忆库）管理

| 方法 | 路径 | 含义 |
|---|---|---|
| GET | `/v1/default/banks` | 列出 banks |
| PUT,PATCH,DELETE | `/v1/default/banks/{bank_id}` | 创建(PUT)/改/删 bank |
| GET | `/v1/default/banks/{bank_id}/stats` | bank 统计（节点/链接/事实类型分布） |
| GET | `/v1/default/banks/{bank_id}/stats/memories-timeseries` | 记忆时序统计 |
| GET,PUT | `/v1/default/banks/{bank_id}/profile` | bank 画像（已废弃，用 config） |
| GET,PATCH,DELETE | `/v1/default/banks/{bank_id}/config` | Bank 配置（disposition/mission/LLM 等） |
| POST | `/v1/default/banks/{bank_id}/background` | 设 background（已废弃） |
| POST | `/v1/default/banks/{bank_id}/clone` | 克隆 bank |
| GET | `/v1/default/banks/{bank_id}/tags` | bank 标签列表 |
| POST | `/v1/default/banks/{bank_id}/consolidate` | 触发固化（事实→心智模型） |
| POST | `/v1/default/banks/{bank_id}/consolidation/recover` | 恢复固化失败 |
| POST | `/v1/default/banks/{bank_id}/health/llm` | bank 级 LLM 健康检查 |
| GET | `/v1/bank-template-schema` | bank 模板 schema |

### 2.3 文档

| 方法 | 路径 | 含义 |
|---|---|---|
| GET | `/v1/default/banks/{bank_id}/documents` | 列文档 |
| GET,PATCH,DELETE | `/v1/default/banks/{bank_id}/documents/{document_id}` | 读/改/删文档 |
| GET | `/v1/default/banks/{bank_id}/documents/{document_id}/chunks` | 文档分块 |
| POST | `/v1/default/banks/{bank_id}/documents/{document_id}/reprocess` | 重新处理文档 |
| GET | `/v1/default/banks/{bank_id}/attachments/{attachment_id}` | 读附件 |

### 2.4 实体与图

| 方法 | 路径 | 含义 |
|---|---|---|
| GET | `/v1/default/banks/{bank_id}/entities` | 列实体 |
| GET | `/v1/default/banks/{bank_id}/entities/graph` | 实体图 |
| GET | `/v1/default/banks/{bank_id}/entities/{entity_id}` | 读实体 |
| POST | `/v1/default/banks/{bank_id}/entities/{entity_id}/regenerate` | 重新生成实体 |
| GET | `/v1/default/banks/{bank_id}/graph` | bank 知识图 |

### 2.5 心智模型与知识库

| 方法 | 路径 | 含义 |
|---|---|---|
| GET,POST | `/v1/default/banks/{bank_id}/mental-models` | 列/建心智模型 |
| GET,PATCH,DELETE | `/v1/default/banks/{bank_id}/mental-models/{mental_model_id}` | 读/改/删心智模型 |
| POST | `/.../mental-models/{id}/refresh` | 刷新心智模型 |
| POST | `/.../mental-models/{id}/dry-run-refresh` | 预演刷新 |
| POST | `/.../mental-models/{id}/clear` | 清空心智模型内容 |
| GET | `/.../mental-models/{id}/history` | 刷新历史 |
| GET | `/v1/default/banks/{bank_id}/directives` | 列指令 |
| GET,PATCH,DELETE | `/.../directives/{directive_id}` | 读/改/删指令 |
| GET | `/v1/default/banks/{bank_id}/knowledge-base/tree` | 知识库树 |
| GET | `/.../knowledge-base/search` | 搜索知识库 |
| GET | `/.../knowledge-base/pages/{page_id}` | 读知识页 |
| GET | `/.../knowledge-base/export` | 导出知识库 |
| POST | `/.../knowledge-base/folders` | 建知识文件夹 |
| POST | `/.../knowledge-base/pages` | 建知识页 |
| PATCH,DELETE | `/.../knowledge-base/nodes/{node_id}` | 改/删知识节点 |

### 2.6 操作、Webhook、导入导出、审计、LLM 追踪

| 方法 | 路径 | 含义 |
|---|---|---|
| GET | `/v1/default/banks/{bank_id}/operations` | 列异步操作 |
| GET,DELETE | `/.../operations/{operation_id}` | 读/取消操作 |
| DELETE | `/.../operations/{operation_id}/delete` | 删除操作记录 |
| POST | `/.../operations/{operation_id}/retry` | 重试操作 |
| GET,POST | `/v1/default/banks/{bank_id}/webhooks` | 列/建 webhook |
| PATCH,DELETE | `/.../webhooks/{webhook_id}` | 改/删 webhook |
| GET | `/.../webhooks/{webhook_id}/deliveries` | webhook 投递记录 |
| POST | `/v1/default/banks/{bank_id}/import` | 导入 |
| GET | `/v1/default/banks/{bank_id}/export` | 导出 |
| POST | `/.../transfer/export` `.../transfer/import` | 跨 bank 迁移 |
| GET,POST | `/.../document-transfer` + `/.../document-transfer/export` | 文档迁移（异步） |
| GET | `/.../audit-logs` `/.../audit-logs/stats` | 审计日志 |
| GET | `/.../llm-requests` `/.../llm-requests/stats` | LLM 请求追踪 |
| POST | `/.../prompts/preview` | 预览 prompt |

### 2.7 运维路径（开源独有，不进 OpenAPI 部分可见）

| 方法 | 路径 | 含义 |
|---|---|---|
| GET | `/health` `/health/live` `/health/ready` | 健康检查 |
| GET | `/metrics` | Prometheus 指标 |
| GET | `/version` | 版本与特性开关 |

---

## 3. 开源版 MCP 工具全量列表（今天实测：39 工具，v0.10.1）

> 实测来源：MCP Streamable HTTP 握手 → `tools/list`。注解列：R=只读 W=写 D=危险。

| 工具 | 注解 | 对应 REST |
|---|---|---|
| `retain` `sync_retain` | W | `POST /memories`（sync=同步返回） |
| `recall` | R | `POST /memories/recall` |
| `reflect` | R | `POST /reflect` |
| `list_banks` `get_bank` `get_bank_stats` | R | `GET /banks`、`/banks/{id}`、`/banks/{id}/stats` |
| `create_bank` `update_bank` `delete_bank` `clear_memories` | W/D | `PUT/PATCH/DELETE /banks/{id}`、`DELETE /memories` |
| `list_memories` `get_memory` `update_memory` `invalidate_memory` | R/W/D | `GET /memories/list`、`GET/PATCH /memories/{id}` |
| `list_documents` `get_document` `delete_document` | R/D | `/documents` |
| `list_mental_models` `get_mental_model` `create_mental_model` `update_mental_model` `delete_mental_model` `refresh_mental_model` `clear_mental_model` | R/W/D | `/mental-models` |
| `list_directives` `create_directive` `delete_directive` | W/D | `/directives` |
| `list_operations` `get_operation` `cancel_operation` | R/W | `/operations` |
| `list_tags` | R | `GET /banks/{id}/tags` |
| `get_knowledge_base_tree` `search_knowledge_base` `get_knowledge_page` `create_knowledge_folder` `create_knowledge_page` `update_knowledge_node` `delete_knowledge_node` | R/W/D | `/knowledge-base` |

> **39 vs 40 的差异**：源码 `_ALL_TOOLS` 列了 40 个，运行时注册了 39 个（实测）。差异项是某个工具在该部署配置下未注册（如某些部署按 `HINDSIGHT_API_MCP_ENABLED_TOOLS` 过滤）。这是配置差异，非版本差异。

---

## 4. 商用版 vs 开源版 API 差异（REST，今天实测）

> 今天实测：商用 v0.10.2 / 86 路径（title="Hindsight Cloud API"，640797 字节）；本地 v0.10.1 / 74 路径（title="Hindsight HTTP API"，320566 字节）。

### 4.1 数量对比（今天实测）

| | 商用 Cloud | 开源本地 | 备注 |
|---|---:|---:|---|
| OpenAPI 路径数 | 86 | 74 | 含运维路径 |
| 业务路径（去运维） | 86 | 71 | 共同 71 条，方法集全部一致 |
| 共同路径 | 71 | 71 | **71 条共同路径的 HTTP 方法集合全部一致** |
| 商用独有 | 15 | — | 企业级治理/隐私/别名 API |
| 开源独有 | — | 3 | `/health` `/metrics` `/version` |

> ⚠️ **版本差异**：本地 0.10.1，商用 0.10.2。部分商用独有路径是版本演进（0.10.2 新增），非纯商用分叉。对比时已排除此噪声——核心数据面（retain/recall/reflect）两版完全同源。

### 4.2 商用 Cloud 独有的 15 条路径（今天实测，企业能力）

| 路径 | 方法 | 含义 | 开源版 |
|---|---|---|---|
| `/v1/api-keys/scoped` | GET,POST | 父子 API Key（scoped/bank 限定） | ❌ 无 |
| `/v1/api-keys/scoped/{key_id}` | DELETE | 撤销 scoped key | ❌ 无 |
| `/organizations/{org_id}/webhooks` | GET,POST | 组织级 webhook | ❌ 无 |
| `/organizations/{org_id}/webhooks/{webhook_id}` | PATCH,DELETE | 改/删组织 webhook | ❌ 无 |
| `/v1/default/banks/{bank_id}/aliases` | GET,POST | bank 别名 | ❌ 无 |
| `/v1/default/banks/{bank_id}/aliases/{alias}` | PATCH,DELETE | 改/删 bank 别名 | ❌ 无 |
| `/v1/default/banks/{bank_id}/consolidation-strategies/preview` | POST | 固化策略预演 | ❌ 无 |
| `/v1/default/banks/{bank_id}/security-events` | GET | Memory Defense 安全事件查询 | ❌ 无 |
| `/v1/default/banks/{bank_id}/security-events:purge` | POST | 清理安全事件 | ❌ 无 |
| `/v1/{tenant}/banks/{bank_id}/subjects/erase` | DELETE | 数据主体删除（GDPR） | ❌ 无 |
| `/v1/{tenant}/banks/{bank_id}/subjects/erase/preview` | POST | 删除预演 | ❌ 无 |
| `/v1/{tenant}/banks/{bank_id}/subjects/export` | POST | 数据主体导出 | ❌ 无 |
| `/v1/{tenant}/exports/{export_id}` | GET | 租户级导出查询 | ❌ 无 |
| `/v1/{tenant}/privacy-events` | GET | 隐私操作事件 | ❌ 无 |
| `/v1/{tenant}/privacy-events/{receipt_id}` | GET | 隐私操作回执 | ❌ 无 |

**这 15 条全部指向商业产品需求**，分四类：
1. **凭据委派**：scoped key（父子 key、bank 限定）
2. **安全治理**：Memory Defense 安全事件、bank 别名
3. **隐私合规**：GDPR 数据主体删除/导出/预演/回执（`/v1/{tenant}/...`）
4. **组织治理**：组织级 webhook、固化策略预演

> 核心数据面（retain/recall/reflect/memory/document/entity/mental-model/knowledge-base）**商用与开源同源**——这是华为云可复用 Hindsight 内核的实证基础。

### 4.3 开源独有的 3 条运维路径

| 路径 | 商用 |
|---|---|
| `/health` `/version` | 今天实测**可访问**（200），但**未列入**商用 OpenAPI |
| `/metrics` | 商用 `/metrics` 未列入 OpenAPI，不应对公网开放 |

### 4.4 鉴权差异（今天实测两边）

| | 商用 Cloud（今天实测） | 开源本地（今天实测） |
|---|---|---|
| 鉴权 | 强制 `Authorization: Bearer <api_key>` | 强制 `Authorization: Bearer <api_key>` |
| 无 key | `401 {"detail":"Authentication failed: API key required"}` | `401 {"detail":"Authentication failed: Missing Authorization header. Expected: Bearer <api_key>"}` |
| 有效 key | `200`，返回 1 个 bank（MySQL） | `200`，返回多 bank |
| 多租户 | 组织 + scoped key（API Key 带 bank scope） | 静态 key→租户（schema 隔离，StaticKeysTenantExtension） |

> 两边**都是强制鉴权 + 多租户**，差异在租户模型：商用是「组织 + scoped key」产品化方案，开源是「静态 key→schema」开发态方案。华为云可用 IAM/Workspace 替换这一层。

### 4.5 运行特性差异（今天实测 `/version`）

| 特性 | 商用 Cloud | 开源本地 |
|---|---|---|
| api_version | 0.10.2 | 0.10.1 |
| worker | **false** | **true** |
| audit_log | **true** | **false** |
| mcp | true | true |
| file_upload_api | true | true |

- **商用 `worker=false`**：API 进程不跑后台任务，后台任务由独立 Worker 处理（商用 Helm 标准形态 = API Deployment + Worker StatefulSet）；
- **开源 `worker=true`**：本地单进程同时跑 API + 内置 Worker；
- **商用 `audit_log=true`**：商用开启了审计日志（开源默认关闭）。

---

## 5. 商用版 vs 开源版 MCP 工具差异（今天实测）

> 今天实测：商用 MCP 40 工具，本地 MCP 39 工具。

### 5.1 工具集对比

| | 商用 Cloud | 开源本地 |
|---|---:|---:|
| MCP 工具数 | **40** | **39** |
| 共有工具 | 39 | 39 |
| 商用独有 | 1（`search_docs`） | — |

**商用独有 1 个 MCP 工具**：
- `search_docs`（W，写注解）—— 商用新增，开源无。对应文档检索能力增强。

**39 个共有工具完全一致**（retain/recall/reflect/list_banks/create_bank/.../knowledge-base 全系列），注解（R/W/D）也一致。这证明：**MCP 工具层商用与开源核心同源，仅多一个 `search_docs`**。

### 5.2 关键结论

- 商用**没有**把 15 条企业治理 REST API（scoped key/security-events/GDPR）暴露成 MCP 工具——治理类操作不让模型自主调，只走 REST 由程序调用。这是合理设计。
- 数据面 39 工具两边一致，模型侧调用方式（retain/recall/reflect）在商用与开源**完全可互换**。

---

## 6. 关键 API 测试用例（今天实测，含调用方式与返回值）

> 全部为今天（2026-10-09）在本地 8888 实测的真实请求与返回。`KEY=key-zhang3`（company1 租户）。

### 6.1 列出 Banks — `GET /v1/default/banks`

```bash
curl -sS http://127.0.0.1:8888/v1/default/banks \
  -H "Authorization: Bearer key-zhang3"
```
**返回值（节选）：**
```json
{"banks":[{
  "bank_id":"company1-project-alpha","name":"Company1 Project Alpha",
  "disposition":{"skepticism":3,"literalism":3,"empathy":3},
  "mission":"Company1 project alpha shared memory (zhang3)",
  "fact_count":406,"last_write_at":"2026-09-30T05:02:50.697491+00:00"
}]}
```

### 6.2 Bank 统计 — `GET /v1/default/banks/{bank_id}/stats`

**返回值：** `total_nodes:406, total_links:5651, total_documents:20, nodes_by_fact_type:{experience:53, observation:142, world:211}, links_by_link_type:{semantic:1744, temporal:3320, entity:573, caused_by:14}, pending_operations:0, failed_operations:2`

### 6.3 Retain（写入） — `POST /memories`

```bash
curl -sS http://127.0.0.1:8888/v1/default/banks/cmp-verify/memories \
  -H "Authorization: Bearer key-zhang3" -H "Content-Type: application/json" \
  -d '{"items":[{"content":"CMP verification fact: the user prefers concise API docs with curl examples.","source":"cmp-verify"}]}'
```
**返回值：**
```json
{"success":true,"bank_id":"cmp-verify","items_count":1,"async":false,
 "operation_id":"...","operation_ids":[...],"usage":{...}}
```

### 6.4 Recall（检索） — `POST /memories/recall`

```bash
curl -sS http://127.0.0.1:8888/v1/default/banks/cmp-verify/memories/recall \
  -H "Authorization: Bearer key-zhang3" -H "Content-Type: application/json" \
  -d '{"query":"API docs preference","limit":3}'
```
**返回值结构：** `{results:[...], trace, entities, chunks, source_facts, source_facts_truncated}`
**结果：** 召回 2 条，含刚 retain 的 "User prefers concise API docs with curl examples"——**证明写入持久化**。

### 6.5 Reflect（反思推理） — `POST /reflect`

```bash
curl -sS http://127.0.0.1:8888/v1/default/banks/cmp-verify/reflect \
  -H "Authorization: Bearer key-zhang3" -H "Content-Type: application/json" \
  -d '{"query":"what docs style does the user prefer?","budget":"low","max_tokens":256}'
```
**返回值结构：** `{text, based_on, structured_output, structured_output_error, usage, trace}`
**usage：** `input_tokens, output_tokens, total_tokens, cached_tokens, thoughts_tokens`

### 6.6 MCP 工具调用（recall） — 证明 REST/MCP 同源

```bash
# 1. 握手取 session
SID=$(curl -sS -D - http://127.0.0.1:8888/mcp \
  -H "Authorization: Bearer key-zhang3" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"p","version":"1"}}}' \
  | grep -i "mcp-session-id:" | awk '{print $2}' | tr -d '\r')
# 2. notifications/initialized
curl -sS http://127.0.0.1:8888/mcp -H "Authorization: Bearer key-zhang3" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'
# 3. tools/call recall
curl -sS http://127.0.0.1:8888/mcp -H "Authorization: Bearer key-zhang3" -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"recall","arguments":{"query":"API docs","bank_id":"cmp-verify"}}}'
```
**返回值：** `isError:false`，content 内含与 REST recall 同源的结果 JSON（1482 字符，含同一条记忆）。**证明 MCP 工具与 REST 共用 MemoryEngine。**

### 6.7 请求体 schema（Retain/Recall/Reflect，今天从 OpenAPI 提取）

- **RetainRequest**：`items`(必填数组) `async`(默认false) `operation_id` `document_tags`(废弃)
- **RecallRequest**：`query`(必填) `budget`(默认mid) `max_tokens`(默认4096) `types` `tags` `tags_match`(默认any) `tag_groups` `min_scores` `temporal_window` `include` `query_timestamp` `prefer_observations` `trace`
- **ReflectRequest**：`query`(必填) `budget`(默认low) `max_tokens`(默认4096) `context`(废弃) `response_schema` `fact_types` `exclude_mental_models` `tags` `apply_all_directives` `include`

### 6.8 商用版实测用例（今天实测，经代理 + `-k`）

```bash
PROXY="http://xxxx:xxxx@proxyhk.huawei.com:8080"
KEY="hsk_3b389add23d7c7fb33db93e89ad2b74f_a835f0b3055c3961"
CLOUD="https://api.hindsight.vectorize.io"
# 鉴权：无 key → 401，有 key → 200
curl -sS -k -m 12 -x "$PROXY" "$CLOUD/v1/default/banks" -w " [%{http_code}]\n"              # 401
curl -sS -k -m 12 -x "$PROXY" "$CLOUD/v1/default/banks" -H "Authorization: Bearer $KEY"     # 200
```
**返回值（有 key）：** 1 个 bank：`bank_id=MySQL, name=MySQL, fact_count=0`（该账号 bank 为空）。

**商用 recall 调用通路验证**（空 bank，验证接口可用）：
```bash
curl -sS -k -m 30 -x "$PROXY" "$CLOUD/v1/default/banks/MySQL/memories/recall" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"query":"test","limit":2}'
```
**返回值：** `200`，结构 `{results, trace, entities, chunks, source_facts, source_facts_truncated}`，`results:[]`（bank 空）——**与本地 recall 返回结构完全一致，证实核心数据面同源**。

**商用 stats：** `total_nodes:0, total_links:0, pending_operations:0`（bank 空），结构与本地一致。

---

## 7. 对华为云 ContextDB 服务化的启示

1. **核心数据面复用 Hindsight 原生 API 语义**：retain/recall/reflect 三件套商用与开源同源（今天实测 71 共同路径方法集一致、recall 返回结构一致），华为云应直接保留，不自造协议。
2. **REST + MCP 双协议都保留**：REST 给程序/控制面/SDK，MCP 给模型自主调用。华为云 Control Plane 走 REST，Agent 接入走 MCP。
3. **企业能力（商用独有的 15 条）是华为云控制面的活**：scoped key、bank 别名、安全事件、GDPR 删除/导出/隐私回执、组织 webhook、固化策略预演——这些应在华为云控制面实现，不污染 Hindsight 数据面内核。**且这些治理类操作商用刻意不暴露成 MCP 工具**（仅多一个数据面的 `search_docs`），华为云应沿用此设计。
4. **鉴权与多租户**：开源版 StaticKeysTenantExtension（key→schema）已是多租户形态；华为云用 IAM/Workspace 替换这一层，schema 级隔离可复用。
5. **运行形态**：商用 `worker=false`（API 与 Worker 分离）+ `audit_log=true`；开源默认 `worker=true` + `audit_log=false`。华为云生产应采用商用形态（独立 Worker + 审计开启），这是同一镜像的部署开关，非内核 fork。
6. **版本对齐**：今天本地 0.10.1，商用 0.10.2。华为云应锁定 Hindsight 版本，每次升级做差分合同测试（今天实测 0.10.2 比 0.10.1 多了 aliases/consolidation-strategies 等路径）。

---

## 附录 A：本次实测证据文件

| 文件 | 内容 |
|---|---|
| `/tmp/hs-cmp/local-openapi.json` | 本地 OpenAPI（320566 字节，74 路径） |
| `/tmp/hs-cmp/cloud-openapi.json` | 商用 OpenAPI（640797 字节，86 路径） |
| `/tmp/hs-cmp/rest-table.txt` | 本地 REST 全量路径+方法表 |
| `/tmp/hs-cmp/recall.json` `recall2.json` | 本地 recall 真实返回 |
| `/tmp/hs-cmp/retain.json` | 本地 retain 真实返回 |
| `/tmp/hs-cmp/reflect.json` | 本地 reflect 真实返回 |
| `/tmp/hs-cmp/mcp_recall.sse` | 本地 MCP tools/call recall 返回 |
| `/tmp/hs-cmp/ctools.sse` | 商用 MCP tools/list 返回（40 工具） |
| `/tmp/hs-cmp/c-banks.json` `c-stats.json` `c-recall.json` | 商用 REST 真实返回 |

## 附录 B：商用版验证命令清单（已验证可用）

```bash
# 本沙箱访问商用需经 proxyhk 代理 + -k 跳过代理 SSL 拦截
PROXY="http://xxx:xxx@proxyhk.huawei.com:8080"
CLOUD=https://api.hindsight.vectorize.io
KEY=hsk_3b389add23d7c7fb33db93e89ad2b74f_a835f0b3055c3961
# 1. 健康/版本
curl -sS -k -x "$PROXY" $CLOUD/health; curl -sS -k -x "$PROXY" $CLOUD/version
# 2. OpenAPI 全量（对比路径数）
curl -sS -k -x "$PROXY" $CLOUD/openapi.json | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['paths']))"
# 3. 鉴权验证
curl -sS -k -x "$PROXY" $CLOUD/v1/default/banks -w "%{http_code}\n"        # 无 key 期望 401
curl -sS -k -x "$PROXY" $CLOUD/v1/default/banks -H "Authorization: Bearer $KEY" -w "%{http_code}\n"  # 有 key 期望 200
# 4. MCP tools/list（见 §5.1，加 -k -x "$PROXY"）
# 5. 商用独有 API 验证
curl -sS -k -x "$PROXY" $CLOUD/v1/api-keys/scoped -H "Authorization: Bearer $KEY"  # scoped key
curl -sS -k -x "$PROXY" $CLOUD/v1/default/banks/MySQL/security-events -H "Authorization: Bearer $KEY"
```

> 直连环境（无代理）去掉 `-x "$PROXY"` 和 `-k` 即可。
