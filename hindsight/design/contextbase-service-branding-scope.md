# ContextBase 改名：服务模式下哪些改动有必要

## 1. 结论

**我们交付的是 REST API、远程 MCP 和 Web UI 服务，不向客户交付部署节点或一整套改名客户端。因此，应保留客户界面的品牌展示，停止扩大内部名称和客户端包的改名。**

**实施前提：当前处于首版开发，没有存量客户、存量实例或需要保留的历史部署配置。可以直接确定首版名称，不需要旧名称兼容期、双前缀过渡或实例迁移方案。**

核对代码后，有一个关键事实：**改名前的代码已经能展示 ContextBase。** 后续 1482 项变更进一步重命名了集成包及其 import、函数和参数，增加了环境变量前缀映射，并修改内嵌 PG 默认身份、内部监控名称和大量文档。这些工作大多不是展示 ContextBase 所必需的。

| 对象 | 建议 | 理由 |
| --- | --- | --- |
| UI 名称、图标、页面标题 | **保留 ContextBase 展示** | 客户直接使用这些页面 |
| REST 文档标题、远程 MCP 服务展示名 | **保留 ContextBase 展示** | 客户通过它们识别服务 |
| REST 路径、JSON 字段、MCP 工具名、SDK import | **沿用上游接口** | 复用现有客户端，降低首次接入和后续维护成本 |
| LangGraph、LiteLLM、OpenClaw 等集成包，以及 CLI/Embed | **不需要为本服务改名** | 客户使用原客户端连接我们的地址即可 |
| 内部环境变量、PG 默认名称、监控指标 | **不需要为品牌改名** | 客户不能操作节点；改这些名字没有直接的客户收益 |
| UI 中“设置服务器环境变量”的提示 | **需要改写提示** | 客户做不了这项操作，应该给出可执行说明 |

**实施建议：直接撤销不必要的品牌命名差异，恢复所采用上游版本的原生名称；保留独立的功能修复。** 不需要兼容开发期的 `agentstratum`、`contextbase` 内部名称，也不需要为它们保留别名。

## 2. 本报告分析的是哪次改动

只比较以下两个固定提交，不使用其他功能分支作为证据：

- 改名前：[`3f2cd188e`](https://github.com/RSIXDB/hindsight/commit/3f2cd188e5315995622b1d7b947b2b761f068e44)。
- 改名合入后：[`57bbfd2d3`](https://github.com/RSIXDB/hindsight/commit/57bbfd2d39685091ce65a4742e43c6efbcb4c78e)。

比较范围包含 `2cef40276` 和 `a73e7b2f2` 两个改名提交。客户访问范围按当前要求确定：REST API、远程 MCP、Web UI；客户不访问部署节点。

恢复内部名称时，以所采用上游版本为准。本报告核对了官方 v1.0.0 [`39c65ffe2`](https://github.com/vectorize-io/hindsight/commit/39c65ffe2f140d0c84cee58566cad8900c5b9908) 的相关原名；比较基点 `3f2cd188e` 已含 `agentstratum` 改名，不能把“改回 agentstratum”作为最终目标。下表仍只统计上述两提交之间的差异。

| 变更位置 | 文件变更数 | 说明 |
| --- | ---: | --- |
| 独立集成 `hindsight-integrations/` | **1028** | 包、模块、工具、测试、安装说明等 |
| 文档站 `hindsight-docs/` | **270** | 文档、示例、站点及历史版本资料 |
| 其余代码、配置、测试与构建文件 | **184** | API、UI、CLI、Embed、监控等 |
| 合计 | **1482** | 按 Git 重命名识别后的差异条目统计 |

集成与文档站占 **87.6%**。这不能说明其中每个文件都不该改，但足以解释为什么一次改名会涉及上千个文件：范围扩展到了客户端生态和完整文档站。

## 3. 判断依据：五个具体例子

### 3.1 客户展示：已经有集中入口，保留即可

在改名前的 `3f2cd188e` 中，`brand_defaults.py` 已经包含：

```python
DISPLAY_NAME = "ContextBase"
```

同一提交的 `brand.py` 已通过展示配置生成 API 标题和 MCP 服务名称：

```python
def api_title():
    return f"{display_config().display_name} HTTP API"

def mcp_server_name():
    return f"{display_config().display_name}-mcp-server"
```

UI 的 `Brand` 组件也已通过 `useProductName()` 读取产品名称。

**判断：展示能力应保留；没有必要为了这个目标重命名集成包、PG 或内核变量。** UI 与 API 使用一致的展示配置，并检查页面标题、图标和 MCP 握手信息即可。上述代码只省略了类型标注，没有改变表达式。

证据：[改名前的品牌默认值](https://github.com/RSIXDB/hindsight/blob/3f2cd188e/hindsight-api-slim/hindsight_api/brand_defaults.py)、[API/MCP 展示入口](https://github.com/RSIXDB/hindsight/blob/3f2cd188e/hindsight-api-slim/hindsight_api/brand.py)、[UI 名称组件](https://github.com/RSIXDB/hindsight/blob/3f2cd188e/hindsight-control-plane/src/components/brand.tsx)。

远程 MCP 的工具本身使用 `retain`、`recall`、`reflect` 等名称。服务展示为 ContextBase，不要求把 `recall` 改为 `contextbase_recall`。客户端插件中的带前缀工具是另一套包装实现，不应混为一谈。 见[原生远程工具定义](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-api-slim/hindsight_api/mcp_tools.py#L1002)。

### 3.2 集成包：改了客户程序的调用方式，没有必要

LangGraph 集成发生了以下变化：

| 项目 | 改名前 | 改名后 |
| --- | --- | --- |
| 安装包 | `hindsight-langgraph` | `contextbase-langgraph` |
| Python 模块 | `hindsight_langgraph` | `contextbase_langgraph` |
| 工厂函数 | `create_hindsight_tools` | `create_contextbase_tools` |
| URL 参数 | `hindsight_api_url` | `contextbase_api_url` |

例如，沿用上游 LangGraph 集成时，接入代码是：

```python
from hindsight_langgraph import create_hindsight_tools
```

改名后的源码包已改用 `contextbase_langgraph` 目录，接入示例必须随之使用新的模块、函数和参数。这会让首版多维护一套与上游不同的客户端接口。

**判断：首版不需要额外发布这套改名集成。** 直接沿用上游集成，显式配置我们的服务 URL 和业务 Key；接入验证也使用这套原生接口。

在本报告比较的两个提交之间，**35 个 Python 集成项目修改了发行包名称**。本次还同时调整了源码路径、公开接口、测试、锁文件和说明，扩大了变更范围。发行包名和 import 模块名可以不同，这些联动不是技术上必须的。

证据：[LangGraph 包名与构建目录](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-integrations/langgraph/pyproject.toml)、[改名后的公开入口](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-integrations/langgraph/contextbase_langgraph/__init__.py)、[函数和参数](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-integrations/langgraph/contextbase_langgraph/tools.py#L40)。

### 3.3 内嵌 PG：改了默认连接对象，没有客户收益

`pg0.py` 中的默认实例、数据库、账号和密码，从 `agentstratum` 改成了 `contextbase`。例如默认数据库名和未指定名称时的实例名都发生了变化。

**判断：不应随产品展示改名。** 这些值决定程序连接哪个本地实例，不是页面上给客户看的名称。客户不能访问节点，修改它们不会改善 REST/MCP/UI 的使用体验。使用外部 PG 的服务部署，也不需要通过修改这组默认值来展示品牌。

**首版处理：恢复上游原生默认值。** 官方 v1.0.0 中这组默认名称为 `hindsight`，不需要兼容开发期的 `agentstratum` 或 `contextbase` 值。按首版最终配置验证启动和数据库连接即可；不设计旧实例迁移。外部 PG 的实际账号和数据库由部署配置指定，不以这里的内嵌默认值代替。

证据：[改名后的 PG 默认值](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-api-slim/hindsight_api/pg0.py#L14)、[默认实例选择](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-api-slim/hindsight_api/pg0.py#L175)。

### 3.4 环境变量：内部不用改，UI 提示应该改

API 当前仍使用原来的内部配置键，只在入口做了映射：

```text
CONTEXTBASE_API_* → HINDSIGHT_API_*
```

这说明改名没有要求把 `HindsightConfig` 和全部内部配置变量改掉。保持原配置实现是可行的。

但 UI 仍向客户显示类似以下提示：

```text
此服务器上的审计日志已禁用。
请设置 CONTEXTBASE_API_AUDIT_LOG_ENABLED=true。
```

**判断：需要改的是提示的内容，不是环境变量的名字。** 客户无法设置服务器环境变量，把前缀换成 ContextBase 后，这条操作指引仍然无法执行。

建议按服务实际能力显示：

- 功能可申请启用：“当前未启用此功能。如需启用，请联系服务管理员。”
- 当前服务不提供：“当前服务未开放此功能。”

**首版内部统一使用 `HINDSIGHT_API_*` / `HINDSIGHT_CP_*`。** 删除仅为改名新增的 `CONTEXTBASE_*` 服务端配置别名及其优先级分支，部署模板、启动脚本和对应测试同步调整。产品展示继续使用现有展示配置，不需要双前缀读取。

证据：[API 配置映射](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-api-slim/hindsight_api/config.py#L51)、[UI 实际插入的变量指令](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-control-plane/src/app/%5Blocale%5D/banks/%5BbankId%5D/page.tsx#L609)、[中文提示](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-control-plane/src/messages/zh-CN.json#L162)。

### 3.5 引擎和监控：改了指标文字，应退出品牌改造范围

`memory_engine.py` 中把追踪名称 `agentstratum.recall` 改成了 `contextbase.recall`；`metrics.py` 和 `tracing.py` 也修改了对应前缀。

**判断：这不属于客户使用本服务所需的改名。** 客户无法访问我们的内部监控，指标改名不会改善客户入口，却会增加看板和告警配置的维护工作，也让引擎文件产生与上游不同的修改。

**首版处理：直接恢复上游的 `hindsight.*` 追踪/指标定义，并同步看板查询和测试。** 无需同时输出旧、新两套指标。内部看板如果需要展示 ContextBase，只修改看板标题。

证据：[引擎追踪名称](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-api-slim/hindsight_api/engine/memory_engine.py)、[指标定义](https://github.com/RSIXDB/hindsight/blob/57bbfd2d3/hindsight-api-slim/hindsight_api/metrics.py)。

## 4. 文件处理建议

本节列出应处理的具体位置。**保留已有展示能力，不意味着这些文件都需要重新修改。** 判断对象是文件中的改名部分，不是整个文件。

### 4.1 保留或调整的文件

UI 文件均位于 `hindsight-control-plane/`：

| 文件 | 建议动作 |
| --- | --- |
| `src/components/brand.tsx`、`src/app/[locale]/layout.tsx`、`public/product-icon.svg` | 保留产品名称、页面标题和实际使用的图标 |
| `src/components/product-runtime.tsx`、`src/lib/product-config*.ts`、`src/lib/brand-defaults.ts` | 复用已有产品展示配置，不增加新的命名系统 |
| `src/app/[locale]/connect/page.tsx` | 展示我们的服务地址和真实可用的 SDK/MCP 示例；保留 SDK 原 import |
| `src/app/[locale]/banks/[bankId]/page.tsx`、`src/messages/*.json` | 改写服务器环境变量操作提示；只修改实际可见的相关文案 |
| `src/lib/control-plane-env.ts` 及其调用处 | 恢复直接读取 `HINDSIGHT_CP_*`；撤销品牌别名和优先级分支，保留登录及会话功能 |

API 文件均位于 `hindsight-api-slim/hindsight_api/`：

| 文件 | 建议动作 |
| --- | --- |
| `product_config.py`、`brand.py`、`brand_defaults.py` | 保留集中展示入口；展示名不能带动 PG、指标等技术名称迁移 |
| `api/http.py` | 保留 API 产品标题和已有产品配置响应；业务路径、字段和错误码不改名 |
| `api/mcp.py` | 保留远程 MCP 服务展示名；版本及能力声明真实，工具名不改 |
| `mcp_tools.py` | 保留原生工具名、参数和返回结构；无需为品牌重写工具注册 |

客户资料只更新实际交付的服务地址、鉴权方法、UI 使用与 MCP 连接说明。若公开 Swagger/OpenAPI，则同步其产品标题；不默认把整个上游文档站变成我们的交付范围。相关测试跟随这些实际行为维护，生成的 OpenAPI/SDK 元数据仍需遵守仓库的一致性检查。

### 4.2 不需要品牌改名的模块

| 模块或文件 | 具体建议 |
| --- | --- |
| `hindsight-integrations/**` | 不要求重命名集成包、模块、函数、参数、插件和本地工具；保留独立的端点配置等功能修复 |
| `hindsight-cli/**`、`hindsight-embed/**`、`hindsight-all*/**` | 不为当前服务发行改名的本地客户端或引擎 |
| `hindsight-clients/**` | 沿用上游包名、import 和方法；仅处理真实生成流程要求的元数据差异 |
| `hindsight_api/config.py`、服务启动命令 | 恢复上游内部配置和命令；撤销仅为品牌新增的前缀映射 |
| `hindsight_api/pg0.py`、`daemon.py` | 恢复上游默认实例、数据库、账号、目录和日志路径；不保留开发期名称过渡 |
| `hindsight_api/engine/**`、`metrics.py`、`tracing.py`、`monitoring/**` | 不为品牌修改算法文件、出站标识或内部指标；保留运行功能 |
| `hindsight-docs/versioned_docs/**` | 保留历史版本事实，不把旧版本验证结果机械改成 ContextBase |
| `scripts/generate-brand.mjs`、`brand/*` | 将服务展示生成与 CLI/插件发行目标分开；不因服务改名强制检查和改名所有客户端 |

表中 `hindsight_api/` 指 `hindsight-api-slim/hindsight_api/`。本报告不要求改变 Webhook 请求头等现有对外协议；若实际提供该能力，应按协议兼容单独处理，不能随展示名切换。

## 5. 建议如何落地

**第一步，确定首版客户入口。** 保留现有 ContextBase 展示，检查 UI 标题、图标、API 标题和远程 MCP 服务名；把客户无法执行的服务器配置提示改成服务说明。REST 路径、MCP 工具和 SDK 沿用上游接口。

**第二步，直接收敛内部和客户端改名。** 将集成包、CLI/Embed、PG 默认身份、内部指标和运维变量恢复为上游原生名称，同步调整部署模板、依赖、锁文件、生成目标和测试。不增加别名、双写或迁移逻辑。只撤销命名改动，不整目录回退；例如 LangGraph 中“未配置服务端点就报错”的连接检查应保留。

**第三步，按首版新部署验证。** 用最终部署配置启动全新实例，验证数据库连接、UI 登录及页面操作、上游 SDK 的 REST 调用、远程 MCP 握手与工具调用；检查指标与看板查询。恢复包路径时执行对应的构建、依赖和测试检查。无需安排存量实例升级、旧配置迁移或新旧名称并存测试。

完整文件清单见附录 CSV（原件本地归档：`appendices/contextbase-service-branding-file-inventory.csv`）。它记录上述 1482 项变更，便于开发者定位文件；分类来自模块规则，**不是逐行审查结论，也不能当作自动回退清单**。不能据此声称可以直接撤销其中某个固定数量的文件。

本报告完成了固定提交的源码和差异核对，尚未执行建议中的代码修改或运行验证。
