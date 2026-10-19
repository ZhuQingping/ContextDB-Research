# Agent 与 Hindsight 交互协议辨析（Agent / REST / MCP / SDK）

> 分析对象：Agent 客户端（如 Claude Code、Codex、Cursor 等）与 Hindsight 服务端之间的交互协议——到底走 REST 还是 MCP？MCP Server / SDK 又是什么。
> 分析方法：基于 Hindsight 源码实证（`hindsight_api/api/http.py`、`api/mcp.py`、`mcp_tools.py`、`server.py`、`main.py` 及 `hindsight-integrations/coding-agents/`），非推测。
> 日期：2026-10-09
> 关联文档：[[2026-09-29-基于 hindsight 实现 ContextDB 功能]]（前者讲"recall/retain 在 hook 机制里的时序"，本文讲"四个概念的边界与取舍"）

---

## 0. 结论速览（TL;DR）

| 概念 | 一句话定义 | 在 Hindsight 里的落点 | 谁来用 |
|------|-----------|----------------------|--------|
| **Agent** | 调用大模型、能自主决策"何时记忆/检索"的客户端程序 | Claude Code、Codex、Cursor、Cline 等；hindsight 把它们叫 harness | 终端用户 |
| **REST** | 面向**程序**的 HTTP 接口（传输语义：URL/方法/状态码/请求体） | `http.py` 的 `@router`，路径 `/v1/default/banks/{bank_id}/...` | 控制面 UI、SDK、脚本、coding-agents 的自动 hook |
| **MCP** | 面向**模型**的工具协议（任务语义：工具名 + 参数 schema + 注解 + 自描述发现） | `mcp.py` 的 FastMCP，挂在 `/mcp`；`mcp_tools.py` 注册 40 个工具 | 原生支持 MCP 的 Agent（Claude Code/Cursor 等），让模型**自主**调用 |
| **SDK** | 对 REST 接口的**语言封装**（Python/TS/Rust/Go），自动生成 | `hindsight-clients/`，由 OpenAPI spec 生成 | 程序员写代码调 Hindsight 时 |

**最核心的一句话**：

> Hindsight 的 **8888（或部署中的 8420）一个端口、一个进程**，同时挂着 REST 和 MCP 两套协议，用 **URL 路径**区分——`/v1/...` 是 REST，`/mcp` 是 MCP。两者底层调用的是**同一个 `MemoryEngine`**。它们不是冗余，而是**面向两类不同调用者**：REST 给程序（开发者写死调用时机），MCP 给模型（模型自己决定何时调用）。

---

## 1. 四个概念逐个辨析

### 1.1 Agent —— 调用方，不是协议

Agent = **能调用大模型、并能自主决策的客户端程序**。Claude Code、Codex、Cursor、Cline 这些都是 Agent。

关键点：**Agent 是"调用方"，不是一种协议**。它本身可能支持 MCP（如 Claude Code 原生支持），也可能不支持（这时只能靠 hook/SDK 走 REST）。Hindsight 在 `hindsight-integrations/coding-agents/src/harness/` 里把每种 Agent 叫一个 "harness"，目前注册了 claude-code、codex、copilot-cli、cursor-cli、cline-cli 等 18 种。

### 1.2 REST —— 面向"程序"的传输接口

REST 是**面向程序员的 HTTP 接口**，暴露的是"传输语义"：HTTP 方法 + URL 路径 + 请求体 JSON + 状态码 + 鉴权头。

Hindsight 的 REST 表面（`http.py`）：

```
POST   /v1/default/banks/{bank_id}/memories/retain      ← 存记忆
POST   /v1/default/banks/{bank_id}/memories/recall      ← 检索记忆
POST   /v1/default/banks/{bank_id}/reflect              ← 反思推理
GET    /v1/default/banks/{bank_id}/memories             ← 列记忆
PATCH  /v1/default/banks/{bank_id}/memories/{id}        ← 改记忆
...
```

调用一次要处理：拼 URL、选 HTTP 方法、构造请求体、塞 `Authorization: Bearer <token>`、解析返回 JSON、处理 4xx/5xx 和分页。**这些都是给程序员看的传输层细节，跟"我要记/取什么"这个任务无关。**

适合的场景：调用时机是**开发者写代码定死的、确定性的**——控制面 UI 点按钮、SDK 脚本、CI 流水线、coding-agents 的"会话结束自动写入"hook。

### 1.3 MCP —— 面向"模型"的工具协议

MCP（Model Context Protocol）是**面向大模型的工具协议**，暴露的是"任务语义"：一个**语义化的函数签名**，而不是一个 HTTP 端点。

Hindsight 的 MCP 表面（`mcp_tools.py`）把同一个 `recall` 包装成：

```
工具 recall(query: str, max_tokens: int = 4096, budget: str = "high",
            tags: list[str] | None = None, ...)
模型只需产出参数 → 框架执行 → 返回结果
```

对比同一个 `recall` 的两条路径：

```
REST 路径（给程序）：              MCP 路径（给模型）：
POST /v1/.../memories/recall      工具调用 recall(query="...", ...)
  Headers: Authorization...          │
  Body: {"query":..., "tags":...}  │
  → 200 OK, 解析 JSON, 处理分页     │
        │                           │
        ▼                           ▼
   http.py 的 recall()   ←── 两者都调用 ──→  mcp_tools.py 的 recall tool
                  │                          │
                  └────► MemoryEngine.recall() ◄┘
```

**底层是同一个 `MemoryEngine`，区别只在调用者拿到的是什么形态**：REST 给 HTTP 响应，MCP 给工具调用。

适合的场景：调用时机是**模型自主决定的**——模型在对话中自己判断"这条值得记，调 retain""我现在该回忆，调 recall"。

### 1.4 SDK —— REST 的语言封装

SDK = **对 REST 接口的语言封装**，让特定语言写起来更顺手。`hindsight-clients/` 里有四套（Python/TypeScript/Rust/Go），全部由 OpenAPI spec 自动生成（`./scripts/generate-clients.sh`）。

```
你的 Python 代码  →  client.recall(query="...", bank_id="...")
                       │ SDK 内部就是
                       ▼
                   HTTP POST /v1/default/banks/{bank_id}/memories/recall
                       │
                       ▼
                   Hindsight 8888 端口（REST）
```

**SDK 走的是 REST，不是 MCP。** SDK 是给"程序员写代码调 Hindsight"用的；MCP 是给"AI 模型自己调 Hindsight"用的。

---

## 2. 核心问题：为什么 REST 底层一样还要 MCP？

### 2.1 调用者不同——这是根本原因

- **REST 的调用者是程序**：开发者写死"会话结束就调 retain"。时机确定，不要模型参与。
- **MCP 的调用者是模型**：模型自己判断"这条用户偏好值得记"。时机自主。

coding-agents 集成正好展示了**两种姿态并存**：
- **走 REST**（`daemon-start.ts` / `deepen.ts` 用 `cfg.apiUrl` 直接打 HTTP）：因为它要的是**确定性**——hook 触发就自动写入，**不让模型决定**。
- **走 MCP**（`claude mcp add ... /mcp`）：因为这种场景要**模型自主**——模型在对话中自己判断何时调工具。

### 2.2 MCP 解决了三个 REST + function-calling 的真问题

**问题 1：模型要在"管道"上烧认知和 token。**
用 REST + function-calling，你要给模型一个 `http_request(method, url, body)` 工具，让它自己去拼 URL、猜 body 字段、塞 token、解析返回。这些跟任务无关，却要模型逐字生成，既慢又容易错（URL 拼错、字段名猜错、忘带 token）。MCP 把这些吃掉，只留语义化的函数签名。

**问题 2：没有发现机制，每个 REST 端点都得人工接线。**
用 REST + function-calling：开发者要读 OpenAPI 文档 → 手写每个端点的工具 schema → 处理鉴权 → 部署包装器。Hindsight 有 40 个工具，等于手写 40 份包装。**MCP 的核心价值在这**：

```bash
# 一行命令，服务端通过 list_tools 自描述，客户端自动发现全部 40 个工具，零包装代码
claude mcp add --transport http hindsight http://localhost:8888/mcp
```

**问题 3：REST 是"一对多"孤岛，MCP 是标准协议。**
每个 REST API 形状都不一样（路径风格、鉴权方式、错误格式各异），换一个集成就重写一遍。MCP 是标准协议：任何 MCP 客户端（Claude Code、Cursor、Cline…）都能接任何 MCP 服务器，接口统一。

### 2.3 MCP 还有 REST 没有的"模型友好"元数据

`mcp_tools.py:541` 的 `_tool_annotations()` 给每个工具标了三类注解：

```python
def _tool_annotations(name: str) -> ToolAnnotations:
    if name in _READ_ONLY_TOOLS:       # recall/list_*/get_* → 只读
        return ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    if name in _DESTRUCTIVE_TOOLS:    # clear_*/delete_*/invalidate → 危险
        return ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False)
    return ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)  # retain/create_*/update_*
```

客户端（如 Claude Code）据此决定"这是个删除操作，先弹窗问用户确认"。**REST/OpenAPI 没有这种面向模型的"这个调用危不危险"标准标注。**

---

## 3. 大模型"熟悉"MCP 吗？——一个常见误解的澄清

> **不，模型不"懂"MCP 这个词。**

这是最需要点明的误解：

- **模型会的是 tool-use / function-calling**（产出结构化 JSON 参数），这是模型的能力，MCP 不是。
- **MCP 是基础设施**：规定工具怎么暴露、怎么发现、怎么握手鉴权——这些是给**客户端框架**（Claude Code 等）看的，模型本身根本不感知"MCP"这个名字。

那"模型对 MCP 调用更好"的说法从哪来？准确说法是：**模型对"描述清晰的工具"调用得更好。** MCP 强制的结构（工具名 + 参数 schema + 面向模型的 description + 注解）容易产出模型友好的描述。REST 文档通常写给程序员（讲 auth flow、分页、状态码），直接喂给模型反而容易把它绕晕。

> **本质**：MCP 不是"模型说的新语言"，而是把"REST 端点 → 模型可用工具"这个**人工包装步骤标准化、服务端化**了。以前每个集成要手写包装，MCP 让服务端提供一次，所有客户端零代码接入。

所以不是"模型更懂 MCP"，而是 **MCP 产的描述更对模型的胃口**——但一份精心写的 function-calling 工具描述效果一样。MCP 的真正赢家是**集成成本**。

---

## 4. 8888 端口同时是 REST 和 MCP 吗？——实证

**是的，同一个进程、同一个端口、同一个 app 对象。** 用 URL 路径区分：

```
http://localhost:8888/v1/default/banks/...    ← REST  （http.py 的 @router）
http://localhost:8888/mcp                     ← MCP   （FastMCP，Streamable HTTP 传输）
http://localhost:8888/mcp/{bank_id}/          ← MCP 单 bank 模式
```

代码证据链：

1. **`server.py:80-85`** —— app 是"unified app with both HTTP and optionally MCP"：
   ```python
   # Create unified app with both HTTP and optionally MCP
   app = create_app(..., mcp_api_enabled=config.mcp_enabled, mcp_mount_path="/mcp", ...)
   ```

2. **`main.py:439`** —— uvicorn 跑的就是这一个 app：
   ```python
   uvicorn_config = {"app": "hindsight_api.server:app" ...}  # 同一个 app 对象
   ```

3. **`mcp.py` 的 `MCPMiddleware`** —— 拦截 `/mcp` 前缀的请求转给 FastMCP，其余请求透传给 FastAPI：
   ```python
   # mcp.py:397-399 —— MCP 用 Streamable HTTP 传输
   self.multi_bank_app = self.multi_bank_server.http_app(path="/", stateless_http=stateless)
   self.single_bank_app = self.single_bank_server.http_app(path="/", stateless_http=stateless)
   ```

4. **鉴权方式相同** —— MCP 也用 `Authorization: Bearer <token>` 头（`mcp.py:364-368` 注释写明）：
   ```bash
   # 多 bank 模式
   claude mcp add --transport http hindsight http://localhost:8888/mcp \
     --header "Authorization: Bearer <token>"
   # 单 bank 模式
   claude mcp add --transport http my-agent http://localhost:8888/mcp/my-agent-bank/ \
     --header "X-Bank-Id: my-bank" --header "Authorization: Bearer <token>"
   ```

> 注：当前部署端口被改为 **8420**（见 `INSTALL_REPORT.md`），原理完全一致，把 8888 换成 8420 即可。

---

## 5. MCP 暴露了哪些工具？——40 个（与 REST 端点一一对应）

`mcp_tools.py:36-78` 的 `_ALL_TOOLS` 集合是 MCP 暴露的全部工具。它们和 REST 端点是**一一对应**的——同一个操作两种调用姿态：

| 类别 | MCP 工具 | 对应 REST |
|------|---------|-----------|
| 记忆读写 | `retain` / `sync_retain` / `recall` / `reflect` | `POST /memories/retain` / `recall` / `/reflect` |
| 记忆管理 | `list_memories` / `get_memory` / `update_memory` / `invalidate_memory` | `GET/PATCH /memories` |
| Bank 管理 | `list_banks` / `create_bank` / `get_bank` / `update_bank` / `delete_bank` / `clear_memories` / `get_bank_stats` | `/banks` 系列 |
| 知识库 | `get_knowledge_base_tree` / `search_knowledge_base` / `get_knowledge_page` / `create_knowledge_folder` / `create_knowledge_page` / `update_knowledge_node` / `delete_knowledge_node` | `/knowledge-base` 系列 |
| 心智模型 | `list_mental_models` / `get_mental_model` / `create_mental_model` / `update_mental_model` / `delete_mental_model` / `refresh_mental_model` / `clear_mental_model` | `/mental-models` 系列 |
| 指令 | `list_directives` / `create_directive` / `delete_directive` | `/directives` 系列 |
| 文档 | `list_documents` / `get_document` / `delete_document` | `/documents` 系列 |
| 异步操作 | `list_operations` / `get_operation` / `cancel_operation` | `/operations` 系列 |
| 标签 | `list_tags` | `/tags` |

每个工具都通过 `_tool_annotations` 标注了只读/危险/写入，客户端据此做权限确认。

---

## 6. 四者关系总图

```
                    ┌─ REST (8888)  ─→ http.py @router ──────────────┐
                    │   /v1/default/banks/{bank_id}/...              │
                    │                                                │
你的调用方 ─────────┤   SDK = REST 的语言封装 (Python/TS/Rust/Go)    ├─→ MemoryEngine
                    │   (给程序员写代码用，走 REST，不走 MCP)         │   (retain/recall/reflect
                    │                                                │    底层唯一实现)
                    └─ MCP  (8888) ─→ FastMCP tools (40个) ─────────→┘
                        /mcp            (工具名+schema+注解)
                            ↑
                       AI 模型自主调用
                  (Claude Code / Cursor / Cline 等原生支持 MCP)
```

**三条接入路径：**

1. **程序写死调用** → SDK 或直接打 REST → `http.py` → `MemoryEngine`
   - 例：控制面 UI、CI 脚本、coding-agents 的"会话结束自动 retain"hook
2. **模型自主调用** → MCP → `mcp_tools.py` → `MemoryEngine`
   - 例：Claude Code 里模型自己决定何时 recall/retain
3. **Agent 自动 hook** → 多数走 REST（如 coding-agents 的 deepen/daemon 走 `apiUrl`）
   - 少数 harness 用原生工具注册（如 opencode：`Register ... natively (no MCP server needed)`）

---

## 7. 决策表：什么场景该用哪条路径？

| 你的需求 | 调用时机谁定 | 选什么 | Hindsight 的例子 |
|---------|------------|--------|----------------|
| 控制面 UI 点按钮检索/存记忆 | 开发者写死 | **REST / SDK** | 控制面 `recall`/`retain` 路由代理到 8888 |
| CI 流水线批量灌入记忆 | 开发者写死 | **REST / SDK** | 脚本调 `POST /memories/retain` |
| Agent 会话结束自动沉淀 | hook 触发（确定性） | **REST**（hook 调） | coding-agents 的 `deepen.ts`/`daemon-start.ts` 用 `apiUrl` |
| 让模型在对话中自己记忆/检索 | **模型自主** | **MCP** | `claude mcp add ... /mcp`，模型自己调 retain/recall |
| 写代码集成到自己的应用 | 开发者写死 | **SDK** | `client.recall(...)`，内部走 REST |

**一句话决策**：**调用时机你想写死 → REST/SDK；想让模型自己决定 → MCP。**

---

## 8. 给后续学习的记忆锚点

- **8888 一个端口双协议**：`/v1/...` 是 REST，`/mcp` 是 MCP，同一 app 同一进程（`server.py:80`）。
- **底层同源**：REST 和 MCP 都调 `MemoryEngine`，区别只在调用者（程序 vs 模型）。
- **MCP 不改变模型能力**：模型靠 tool-use 能力调工具，MCP 是"把 REST 包装成工具"的标准化基础设施，不是模型的新语言。
- **SDK ≠ MCP**：SDK 是 REST 的语言封装，给程序员用；MCP 给模型用。
- **coding-agents 走 REST**：因为要 hook 触发的确定性，不要模型决定——这是"该用 REST 不用 MCP"的典型例证。
- **MCP 的核心价值是集成成本**：服务端提供一次，所有 MCP 客户端零代码接入；REST 则每个集成都要手写包装。

---

## 附录 A：实证文件索引

| 断言 | 代码位置 |
|------|---------|
| 8888 同端口挂 REST + MCP | `server.py:80-85`（unified app）、`main.py:439`（uvicorn 跑同一 app） |
| REST 路由表面 | `hindsight_api/api/http.py` 的 `@router`（recall/retain/reflect 等） |
| MCP 挂载路径 `/mcp` | `main.py:414`、`api/mcp.py` 的 `MCPMiddleware`（`/mcp` 前缀拦截） |
| MCP Streamable HTTP 传输 | `api/mcp.py:397-399`（`http_app(path="/", stateless_http=...)`） |
| MCP 40 个工具清单 | `mcp_tools.py:36-78`（`_ALL_TOOLS`） |
| MCP 工具注解（只读/危险） | `mcp_tools.py:541-548`（`_tool_annotations`） |
| MCP 工具内部调 MemoryEngine | `mcp_tools.py:327`（`_run_tool`） |
| MCP 鉴权用 Bearer 头 | `api/mcp.py:364-368` 注释 |
| coding-agents 走 REST 不走 MCP | `hindsight-integrations/coding-agents/src/daemon-start.ts`、`deepen.ts`、`core/knowledge-tools.ts`（用 `cfg.apiUrl`） |
| SDK 自动生成 | `./scripts/generate-clients.sh`，产物在 `hindsight-clients/` |
| Claude Code 接 MCP 命令 | `api/mcp.py:363-368` 注释示例 |
