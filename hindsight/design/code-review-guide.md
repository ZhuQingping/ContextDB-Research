# ContextDB 代码检视指南

> **最新本地代码（2026-10-22）：`9fb57bc04`，新增提交，父提交`003bbe032`，未推送。** 本轮复检425 Python／560 UI／75系统／484相关原生测试通过；Audit继续关闭。最新状态见文末“2026-10-22 提交前复检与本地新提交”，前文旧提交及“未提交”表述保留作历史记录。

**后续协作检视从[第11章：六轮协作检视路线](#collaborative-review-route)开始。** 按总体边界、权限、用户与Key、工作空间生命周期、UI、增量与部署的顺序推进；每轮明确三方分工、证据和验收标准。前文保留模块说明及历史记录，不将历史测试通过直接视为六轮检视完成。

> 本地修复补充（2026-10-21，尚未提交/推送）：S16～S25已实施，当前工作区与下列a05b808固定统计不同。先读[实施清单第8章](contextdb-simplification-plan.md#current-optimization-backlog)及[最新验证](../testing/contextdb-validation-summary.md)。新增修复集中在插件transport/初始化脚本/COMMENT及现有管理UI；原生Python运行代码未改。已有Bank配置响应凭证投影改动保留。

更新：2026-10-20。本文按模块说明当前实现与检视顺序。`ddf5c3600` 与四批优化、测试接线及UI简化已通过 amend 整理为官方 v1.0.0（`39c65ffe`）之上的单一特性提交，并推送：[a05b808](https://github.com/ZhuQingping/hindsight/commit/a05b80885883b36f879abdb2ce8a9c8f63b0922c)。代码提交正文固定资料快照 `370f8fa`；本指南在此基础上补充固定提交的规模统计和检视材料。下列代码链接均定位该提交，正式检视不使用浮动分支冒充固定快照。

完整规格和关键取舍见[设计](contextdb-release-design.md)，接口例子见[curl手册](../api/contextdb-management-api-curl-guide.md)，测试结果见[验证摘要](../testing/contextdb-validation-summary.md)。同步/异步管理、同名重建、内部UUID及失败处理的分析继续保留在设计第5.2～5.3节，不在本指南重复一份。

## 1. 先理解代码由什么组成

**本版新增的是工作空间、用户、API Key管理及访问控制。记忆算法和原生Worker继续复用Hindsight。** `hindsight-api-slim/hindsight_api/` 相对官方基线没有运行代码差异；UI、扩展、CI和测试仍有修改。

| 文件或工具 | 初学者可以怎样理解 |
| --- | --- |
| `.py` | Python服务端代码；接收请求、认证、操作PG、调用原生引擎 |
| `.ts` / `.tsx` | TypeScript；`.tsx`包含React界面，`.ts`多为请求、类型和工具。Next.js的`route.ts`运行在UI服务器，不在客户浏览器 |
| `models.py` / TypeScript `interface` | 数据的字段和类型说明。Python的Pydantic模型还会实际校验输入；TS类型不能代替服务端校验 |
| `schema.sql` | 管理表、约束、索引和注释；不是原生记忆表的第二套定义 |
| `*.test.ts(x)` / `test_*.py` | 测试代码，不随请求执行。一个文件可包含多项测试，参数化还会产生多个场景 |
| `conftest.py` / fixture | 测试准备与清理，例如建立临时PG、准备用户；不是生产调度器 |
| pytest / Vitest | 分别运行Python测试、TS/React测试；不是同一套执行环境 |
| `async def` / `await` | 等待I/O时允许处理其他工作，不表示HTTP必须提前返回202。当前工作空间接口等待操作完成才返回 |
| `pyproject.toml` / `uv.lock` | Python项目与依赖配置、锁定结果；不是业务算法。`package.json`是Node工程对应入口 |

<a id="commit-change-statistics"></a>

### 1.1 a05b808 的统计口径与总体规模

统计对象固定为 [a05b808](https://github.com/ZhuQingping/hindsight/commit/a05b80885883b36f879abdb2ce8a9c8f63b0922c)，基线是它的父提交、官方 v1.0.0（`39c65ffe2f140d0c84cee58566cad8900c5b9908`），不是 amend 前的 `ddf5c3600`，也不包含当前未提交文件。比较这两个提交时没有文件删除或重命名。

- **实现代码**：Python、TS/TSX、SQL、shell及CSS，包含部署和契约生成脚本。
- **测试代码**：直接用例、fixture/support、包入口、测试服务支撑及生产UI结果校验脚本。测试配置、CI YAML和依赖锁归到其他材料，避免混成测试逻辑。
- **其他材料**：配置、模板、文案JSON、文档入口、依赖锁和生成OpenAPI。资料仓中的完整设计、部署和运维文档不在这个代码提交中。
- 行数采用 `git diff --numstat`，包含注释和空行；净增＝新增行－删除行。修改文件的新增行不等于整个文件大小，也不以行数评价实现或测试质量。

| 模块 | 文件数 | 新增文件 | 修改文件 | 新增行 | 删除行 | 净增行 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 实现代码 | 61 | 43 | 18 | 7,182 | 169 | 7,013 |
| 测试代码 | 80 | 77 | 3 | 10,095 | 79 | 10,016 |
| 其他 | 24 | 11 | 13 | 8,705 | 354 | 8,351 |
| **合计** | 165 | 131 | 34 | 25,982 | 602 | 25,380 |

### 1.2 实现代码按模块划分

| 模块 | 文件数 | 新增文件 | 修改文件 | 新增行 | 删除行 | 净增行 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 管理API/生命周期/模型/PG | 6 | 6 | 0 | 1,687 | 0 | 1,687 |
| 认证/授权/REST与MCP适配 | 9 | 9 | 0 | 1,173 | 0 | 1,173 |
| 初始化/配置/预检/构建/启动 | 9 | 9 | 0 | 1,280 | 0 | 1,280 |
| UI页面/组件/客户端/服务器代理 | 31 | 13 | 18 | 2,690 | 169 | 2,521 |
| 部署SQL与运行/生成脚本 | 6 | 6 | 0 | 352 | 0 | 352 |
| **合计** | 61 | 43 | 18 | 7,182 | 169 | 7,013 |

管理模块包含`http.py`、`models.py`、`repository.py`、`lifecycle.py`、`migrations.py`和`schema.sql`；认证模块包含Tenant、Validator、ASGI/REST/MCP适配、请求身份、目录聚合及诊断裁剪。初始化模块负责秘密持久化、部署配置、PG预检和构建启动；部署脚本模块包含两个SQL及四个运行/生成脚本。后文第3～6节按这些职责说明实现。

**18个修改过的实现文件全部在UI工程，原生Python运行目录修改为0。** 插件运行模块和部署脚本均为新增文件。UI文案JSON及五个UI配置文件单列在其他材料，所以这里的31个UI实现文件与此前按UI工程范围统计的37个文件并不冲突：31个实现＋1个文案＋5个配置。

### 1.3 测试代码按模块划分

| 模块 | 文件数 | 新增文件 | 修改文件 | 新增行 | 删除行 | 净增行 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 插件Python用例 | 27 | 27 | 0 | 4,236 | 0 | 4,236 |
| 系统测试用例 | 16 | 16 | 0 | 2,048 | 0 | 2,048 |
| UI测试 | 12 | 11 | 1 | 2,786 | 1 | 2,785 |
| 跨语言合同测试 | 2 | 2 | 0 | 117 | 0 | 117 |
| 插件Python准备与支撑 | 11 | 11 | 0 | 276 | 0 | 276 |
| 系统测试准备与支撑 | 8 | 8 | 0 | 473 | 0 | 473 |
| 原生共用测试支撑 | 3 | 1 | 2 | 121 | 78 | 43 |
| 生产UI结果门禁 | 1 | 1 | 0 | 38 | 0 | 38 |
| **合计** | 80 | 77 | 3 | 10,095 | 79 | 10,016 |

仅统计直接包含用例的`test_*.py`和`*.test.ts(x)`文件，是**56个文件：新增55、修改1，新增9,116行、删除1行、净增9,115行**。其余**24个**是准备、支撑、包入口及校验工具：新增22、修改2，新增979行、删除78行、净增901行。跨语言合同的两个文件中，一个是46行Python用例，一个是71行Node类型提取器。

三个被修改的已有测试文件为：

| 文件 | 改动用途 | 新增行 | 删除行 |
| --- | --- | ---: | ---: |
| `hindsight-control-plane/tests/messages/used-keys.test.ts` | 原生词条检查的自研适配 | 5 | 1 |
| `hindsight-system-tests/tests/conftest.py` | 提取共用模型fixture，保留原生服务/客户端准备 | 2 | 74 |
| `hindsight-system-tests/hindsight_system_tests/server.py` | 测试服务启动适配 | 39 | 4 |

文件数不等于运行测试项数：一个文件可有多个用例，参数化还会展开为多个场景。通过数量及未验证范围统一见[验证摘要](../testing/contextdb-validation-summary.md)，不从文件数推断覆盖率。

### 1.4 配置、生成物和文档的占比

| 模块 | 文件数 | 新增文件 | 修改文件 | 新增行 | 删除行 | 净增行 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 系统测试依赖锁 | 1 | 0 | 1 | 4,954 | 331 | 4,623 |
| 生成的管理OpenAPI | 1 | 1 | 0 | 2,888 | 0 | 2,888 |
| UI文案资源 | 1 | 1 | 0 | 400 | 0 | 400 |
| CI/配置/模板/构建描述 | 15 | 7 | 8 | 360 | 22 | 338 |
| 文档入口/测试说明/规范 | 5 | 2 | 3 | 102 | 0 | 102 |
| 原生OpenAPI参考副本 | 1 | 0 | 1 | 1 | 1 | 0 |
| **合计** | 24 | 11 | 13 | 8,705 | 354 | 8,351 |

系统测试依赖锁与生成的管理OpenAPI合计净增**7,511行，占总净增约29.6%**，不属于业务逻辑。检视可先聚焦61个实现文件、净增7,013行，再按功能选择测试；其余材料按依赖、生成一致性和部署契约单独核对。

[逐文件附录：完整165文件清单](appendices/a05b808-file-statistics.md)列出每个文件的职责归类、增改状态和增删行数，便于定位，不在正文展开165行。后续代码版本变化时须重新生成统计，不能继续沿用本提交数字。

复核总量可执行：

```bash
git diff --shortstat a05b80885883b36f879abdb2ce8a9c8f63b0922c^ a05b80885883b36f879abdb2ce8a9c8f63b0922c
git diff --name-status --no-renames a05b80885883b36f879abdb2ce8a9c8f63b0922c^ a05b80885883b36f879abdb2ce8a9c8f63b0922c
git diff --numstat --no-renames a05b80885883b36f879abdb2ce8a9c8f63b0922c^ a05b80885883b36f879abdb2ce8a9c8f63b0922c
```

## 2. 用三条请求路径理解全貌

```text
管理员在UI操作
  浏览器 → UI服务器检查登录会话/同源
         → UI服务器携带后台Admin Key调用Hindsight API
         → HTTP扩展 → 管理仓储或工作空间Lifecycle → PG/原生Bank方法

应用调用原生REST
  应用携带业务Key和bank_id → 外围ASGI识别目标
         → Tenant选schema → 原生引擎调用Validator检查操作权限
         → 原生Retain / Recall / Reflect及任务系统

应用调用MCP
  当前消息的Key和目标Bank → MCP扩展确定本次目标
         → Tenant / Validator使用同一认证和权限规则
         → 原生MCP工具及原生引擎
```

UI的登录密码只用于界面会话；后台Admin Key保留在UI服务器。业务REST/MCP不经过UI。管理接口的前缀是`/ext/contextdb/v1`，原生记忆接口保持原URL和数据结构。

## 3. 模块一：工作空间、用户和Key管理

以下文件均在 `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/`。

| 文件 | 负责什么 | 检视重点 |
| --- | --- | --- |
| [models.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/models.py) | 定义空间、用户、Key和授权的数据结构、输入约束 | 名称规范化；selected逐空间权限与all统一权限；未知字段拒绝 |
| [schema.sql](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/schema.sql) | 定义六张管理表、唯一约束、外键、延迟校验及索引 | 空间和用户名称唯一；授权关联UUID；摘要不存明文；反向授权索引 |
| [repository.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py) | 执行管理SQL和事务，统一查询身份与授权 | SQL是否绑定对象身份；事务是否完整；Key批量授权；审计及失败状态 |
| [http.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/http.py) | 注册13个管理操作，解析参数、鉴权和If-Match，构造响应 | 管理员才能访问；201/204及错误码；秘密和原始错误不回显 |
| [lifecycle.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py) | 把空间创建/删除的几个步骤串起来，直接等待原生Bank方法 | 不再自建调度器；原生操作前后释放管理连接；失败不冒充整体回滚 |

`Repository`可以理解为“管理数据访问层”，`Lifecycle`是“工作空间流程”，`HTTP`是“协议入口”。创建用户/Key主要是元数据事务；创建空间还要迁移业务schema、初始化原生Bank，因此另有Lifecycle组织步骤。

创建路径：`HTTP → Lifecycle.create → Repository登记creating → 原生迁移/Bank初始化 → Repository激活并记审计 → 201`。

删除路径：`HTTP核对If-Match → Lifecycle.delete → 登记deleting/核对归属 → 原生delete_bank → 事务清理schema、授权、空间行和审计 → 204`。授权变更会同步更新关联Key版本。

**UUID仍有必要。** 对外用`jiamu`，对内用UUID区分删除前后的两个同名对象。它保护授权和管理条件，不承担已经删除的执行代次屏障。删除前管理员须停止业务、等待已受理请求和后台工作结束；响应未知先查资源和原UUID，不自动重发写入。详细取舍见[工作空间管理](contextdb-release-design.md#lifecycle)。

`repository.py`目前703行，是本模块最大的文件。建议依次读`authenticate`、`create_user/create_key`、`create_workspace`、`finish_workspace_deletion`，最后再看私有辅助方法。私有方法通常以`_`开头；不是每个`def`都对应一个HTTP接口。

主要测试：`test_repository.py`、`test_http.py`、`test_lifecycle_metadata.py`、`test_readable_workspaces.py`、`test_authorization_models.py`；完整服务流程再看系统测试103、110、111、115。

`database_checks.py` 只负责结构格式、实例/租户归属及后台写入政策检查。migrations、管理员离线轮换和在线启动共用它；调用者继续拥有原连接与事务，不再调用Repository私有检查方法。三项检查的函数体与移动前一致。

## 4. 模块二：统一认证、授权和schema路由

这部分文件较多，因为REST、MCP、引擎及内部任务的接入点不同。公共数据和策略共用，并非分别实现四套认证系统。

| 文件 | 负责什么 | 为什么需要 |
| --- | --- | --- |
| [security.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/security.py) | 生成随机Key、计算HMAC摘要、提取Bearer凭据 | 把密码学和Header解析集中在一处 |
| [config.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py) | 读取部署归属及pepper，校验不支持配置；取得原生池并创建Repository | 避免各扩展创建额外连接池或各自解析配置 |
| [authorization.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/authorization.py) | 保存本次目标认证结果、同步管理调用的受信上下文 | 同一请求减少重复查询；客户端不能伪造管理生命周期权限 |
| [asgi.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/asgi.py) | 在原生应用外安装ContextDB中间件 | 使用自研启动入口，不改原生API初始化顺序 |
| [transport.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/transport.py) | 从REST URL识别Bank，处理目录和诊断边界，阻止原生生命周期旁路 | 普通REST、原生Bank路径和MCP挂载均需覆盖 |
| [tenant.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py) | 校验身份，把工作空间映射到PG schema | 回答“这个请求访问哪个schema” |
| [validator.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py) | 把操作映射到只读、读写或管理员权限 | 回答“这个身份能否执行这项操作”；原生内部任务也需校验归属 |
| [mcp.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/mcp.py) | 从当前MCP消息获取Key/Bank，适配目录、工具权限及结果脱敏 | 同一MCP连接可访问多个空间，不能固定沿用初始化时的身份 |
| [routing.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/routing.py) | 保存本次目标Bank，聚合跨schema Bank目录 | 原生单schema列表不能直接代表实例下全部可见空间 |
| [diagnostics.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/diagnostics.py) | 对业务Key可见的原生任务响应裁剪敏感字段 | 正常任务进度可读，不因此暴露后台请求配置 |

共享认证结果仅在**同一有效调用、同一凭据和同一目标**内使用。新请求、新MCP消息重新认证；不是进程级Key权限缓存。`authorization.py`里的ContextVar可理解为随当前调用传递的变量；它不登记执行者、不持有连接，也不负责取消任务。

四个Hindsight扩展是Tenant、Validator、HTTP、MCP；`asgi.py`是外围应用入口，`authorization.py`等是内部辅助文件，不是更多需要用户配置的插件。Worker继续执行原生记忆任务，不执行新增管理调度。

**原生运行文件零修改，不代表没有原生内部接口依赖。** 当前仍使用`_get_pool`、`_current_schema`、部分Bank目录辅助方法及MCP的`_current_bank_id`等以下划线开头的接口。它们是后续升级的核对点：需要运行路由、目录、MCP及内部任务回归，不能只验证模块还能import。暂不为回避这些依赖再新增内核钩子。

主要测试：`test_security.py`、`test_authorization.py`、`test_transport.py`、`test_extensions.py`、`test_query_efficiency.py`、`test_diagnostics.py`、`test_tenant_admin.py`；系统测试104、105、109、113、114验证入口组合。

## 5. 模块三：UI页面和UI服务器代理

这部分位于 `hindsight-control-plane/`。同一个Next.js工程同时包含浏览器界面和服务器路由，不能把所有TS代码都当成浏览器代码。

| 路径（省略src/） | 负责什么 | 检视重点 |
| --- | --- | --- |
| `components/contextdb/workspaces-view.tsx` | 空间列表、删除及结果核对 | 可读名称、长描述、原对象ETag、未知结果提示 |
| `components/contextdb/create-workspace-dialog.tsx` | 两入口共用的创建表单 | Dashboard和下拉列表均有名称/描述；校验一致、防重复提交 |
| `components/contextdb/users-view.tsx` | 成员目录、搜索、分页和成员操作 | 不再拥有Key草稿、授权缓存或secret |
| `components/contextdb/user-keys-panel.tsx` | 固定user_id的Key列表、吊销、刷新和一次性secret | 按用户身份挂载；切成员清理旧请求和secret |
| `components/contextdb/key-editor-dialog.tsx`、`components/contextdb/use-key-workspaces.ts` | 编辑快照、授权草稿、分页选择及原UUID/版本提交 | 已有授权不逐个GET；保存由后端验证，不按同名替换UUID |
| `components/contextdb/workspace-result-check.tsx` | 创建/删除结果不确定或条件冲突后的只读核对 | 只GET；比较原UUID，不取得新ETag重放DELETE |
| `lib/contextdb-api.ts` | 请求、错误边界与Key三种响应投影 | 合法JSON null也归统一错误；空间创建身份、Key一次性secret先校验再报成功；PATCH不读secret，DELETE204可为空 |
| `lib/contextdb.ts` | UI服务器校验配置、会话、同源及后台管理员 | server-only防误导入浏览器；密码和后台Key分开；成员Key不能登录UI |
| `app/api/contextdb/[...path]/route.ts` | UI服务器到管理API的固定目标代理 | 保留会话/同源及路径/方法白名单、Admin Key和秘密保护；业务字段由Python模型校验 |
| `lib/contextdb-mode.tsx` | 向页面传递是否启用ContextDB模式 | 自研模式和原生模式的展示分支 |
| `app/[locale]/users/page.tsx`、`banks/[bankId]/page.tsx` | 装配页面，选择用户页或空间内原生功能 | 已有记忆、文档和知识库页面继续复用 |
| `components/bank-selector.tsx`、`banks-overview.tsx`、`bank-config-view.tsx` | 接入空间目录和创建入口，限制会绕过映射的管理行为 | 不能从旧Bank创建/删除/配置入口破坏空间授权 |
| `app/api/banks/**/route.ts` | 原生UI代理上的生命周期、克隆、导入和别名限制 | 管理员也不能绕过空间目录直接创建/删除Bank |
| `app/[locale]/login/page.tsx`、`app/api/auth/login/route.ts`、`middleware.ts`、`instrumentation.ts` | 登录、路由保护和启动校验 | UI会话有效且后台Key确为管理员；启动重试不缓存权限 |
| `i18n/contextdb-*`、`i18n/request.ts`、`lib/i18n/api-errors.ts`、`app/[locale]/layout.tsx` | 自研文案装配、错误翻译及页面布局 | 原生词条不批量改写，缺失语言可回退 |
| `app/globals.css`、`vitest.config.ts` | 展示/字体和测试发现配置 | 与业务权限无关，升级或收敛时单独检视 |

`[bankId]`、`[...path]`是Next.js的动态路径写法，不是另一套对象ID。例如浏览器请求`/api/contextdb/workspaces`，由服务器代理转为API的`/ext/contextdb/v1/workspaces`。浏览器拿不到代理配置中的Admin Key。

[固定版本UI目录](https://github.com/ZhuQingping/hindsight/tree/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-control-plane/src)。检视顺序建议：空间页面 → 共享创建表单 → 用户页面 → 请求函数 → 服务器鉴权和代理；不必先读React所有基础组件。

本轮UI简化保留用户目录、Key面板、Key编辑器三个状态边界，组件和局部hook集中在`components/contextdb/`。请求错误分类合入`lib/contextdb-api.ts`，授权比较函数放回唯一使用它的编辑器，删除两份小工具文件。

用户与Key结果未知时只展示原目标信息、刷新普通分页列表，取消全量ID扫描；创建用户成功显示返回名称/ID，不再自动找页展开。Key已返回的授权用于初始化草稿，目录只提供分页选项；保存携带原UUID和版本，后端拒绝过期授权。同名继任若已出现在目录中，只提示旧项不可用，不自动迁移选中项。工作空间删除集中到管理目录，原生Bank详情在ContextDB模式提供管理链接；原生模式删除保留，生命周期API旁路仍拒绝。

## 6. 模块四：离线初始化、部署和版本检查

| 文件 | 负责什么 | 检视重点 |
| --- | --- | --- |
| [__main__.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py) | `python -m hindsight_ext_contextdb`命令入口 | generate-admin-key、migrate等均是本机命令，不是HTTP接口 |
| [bootstrap.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/bootstrap.py) | 生成/读取持久秘密、初始化/轮换管理员 | 首次离线可完成；重复初始化不换pepper或丢失原Key |
| [migrations.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/migrations.py) | 初始化管理结构、检查部署归属和结构格式 | 首发版本1；拒绝开发期旧结构，不虚构历史兼容升级 |
| [deployment.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/deployment.py) | 校验部署JSON、渲染api.env/ui.env、状态检查 | 首版merged/native/english；路径和秘密权限；无任意环境透传 |
| [preflight.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/preflight.py) | 在迁移前检查PG权限、扩展和检索条件 | 不创建数据库；托管固定英文；手工研究的PGroonga检查不等于本期依赖 |
| [launch.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/launch.py) | 按进程加载秘密，校验产物并启动API/Worker/UI | UI进程不注入PG、MaaS及pepper环境 |
| [artifacts.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/artifacts.py) | 构建UI并生成指纹，启动前核对源码/产物 | 当前完整扫描保留；可信固定镜像免扫描仍为TODO |
| [__init__.py](https://github.com/ZhuQingping/hindsight/blob/a05b80885883b36f879abdb2ce8a9c8f63b0922c/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__init__.py) | Python包初始化与管理元数据格式/版本常量 | 不是另一个服务 |

插件的 `scripts/service.sh`、`node-agent.sh`、`run_combined.py` 分别提供服务命令、节点Agent命令入口和单容器进程监督。`deployment/`保存Docker/Compose、PG权限和意图模板；`schemas/`是生成的管理OpenAPI，不是另一个HTTP实现。

MaaS模型调用复用原生适配器；此模块配置地址、模型和Key，没有重写LLM、Embedding或Rerank算法。默认一个容器、API内置Worker加UI两个应用主进程，PG在外部。数据库和插件由管控先准备，Hindsight不会替管控创建RDS或目标数据库。

主要测试：`test_bootstrap_deployment.py`、`test_metadata_initialization.py`、`test_deployment_contract.py`、`test_combined_lifecycle.py`、`test_build_artifacts.py`、`test_customer_pg_boundary.py`、`test_openapi_contract.py`。部署细节按[联调指南](../deployment/contextdb-service-integration-guide.md)执行。

## 7. 自研测试已集中到插件，执行环境继续复用

| 位置（插件目录下） | 职责 | 执行入口 |
| --- | --- | --- |
| tests/python/ | 元数据、认证、管理接口、生命周期、部署与故障清理；334项 | 插件目录执行`uv run pytest -v`，默认只收集该目录 |
| tests/system/ | SDK/REST/MCP、两Worker及生产UI完整故事；61项 | 原system环境配合插件pytest-system.ini执行 |
| tests/ui/ | 11个自研TS/React测试文件 | 原Control Plane同一Vitest配置；完整UI套件486项，包含原生回归 |
| tests/contracts/ | Python OpenAPI与TS Key投影一致性 | 有Node的独立pytest步骤；不混入纯Python默认收集 |

Python共享身份、HTTP装配、生命周期double和PG资源准备位于tests/python/support；系统资源owner位于tests/system/support。测试不再导入其他test文件，也不调用fixture.__wrapped__；初始化失败直接检验普通资源owner的清理。原生与插件系统故事共用server、stub和已发布SDK。pytest_plugin共80行（按本次Git行数口径），保存模型替身、每例规则重置及未匹配/格式错误检查；原生服务器、客户端和Bank fixture放在原tests/conftest.py。所有原函数体及装饰器与官方原版一致，不迁出整套原生fixture。

Vitest只有一份配置、一个Node依赖锁；外部UI测试已接入TypeScript、从仓库根执行的ESLint、Prettier、knip、CI路径过滤。默认收集、类型与lint均用故意失败的临时用例验证过，不能靠文件被忽略而显示绿色。

生产UI新增独立CI job：正式build-ui、直接运行双Worker故事及JUnit结果核对。产物/layout/源码manifest只由UI fixture启动前检查，不再设重复的CI artifact子命令；check_production_ui.py仅38行，接收JUnit路径。两个指定用例须各出现一次且无skip/failure/error，缺产物或缺用例失败，不增加严格模式部署参数。本地无UI产物的快速系统运行仍可跳过相应用例，不能据此声称完成生产UI验收。

迁移前后按名称和Worker参数比较原始清单，原317个插件、60个系统、415个UI场景均保留，新增项另计；原生词条/业务回归留宿主。**物理集中不表示依赖消失，也不表示三种环境可混成一次pytest。** 可执行命令见代码仓插件README，实际结果及限制见[验证摘要](../testing/contextdb-validation-summary.md)。

<a id="专家检视顺序"></a>

## 8. 实际检视顺序与只读核对命令

第一遍只读 `models.py → schema.sql → http.py → lifecycle.py`，理解资源及接口。第二遍读 `repository.py → security.py → tenant.py → validator.py`，核对数据和权限。第三遍补 `transport.py / authorization.py / mcp.py / routing.py` 的跨入口接入，再查看UI和部署。测试按每节列出的行为选读，不从通读所有测试开始。

```bash
cd /Users/zhuqingping/Work/Database/Context/hindsight
git show -s --format=fuller contextdb/v1.0.0
# 确认提交内容对应已验收源码树：预期 ce1c7def06cf26d9450fcef34acbad4e47268e6f
git rev-parse 'contextdb/v1.0.0^{tree}'
# 确认原生Python运行目录没有特性改动：预期没有输出。
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 -- hindsight-api-slim/hindsight_api
# 分别查看插件、UI及测试的差异。
git diff --stat 39c65ffe2f140d0c84cee58566cad8900c5b9908 -- hindsight-extensions/contextdb-service
git diff --stat 39c65ffe2f140d0c84cee58566cad8900c5b9908 -- hindsight-control-plane
git diff --stat 39c65ffe2f140d0c84cee58566cad8900c5b9908 -- hindsight-system-tests
```

提交后的git diff包含新增文件和测试迁移；若继续修改本地工作区，仍须结合git status核对未跟踪内容。CI中插件Python由test-extension-contextdb-service执行；test-system继续运行原生故事及插件系统入口；test-contextdb-system-ui强制生产UI双Worker验收和Key合同。系统环境显式使用--group contextdb，不复制原生执行框架。

其他3个变更也需单独理解：`.github/workflows/test.yml`接入测试，不是运行接口；`hindsight-extensions/README.md`是插件索引；`skills/hindsight-docs/references/openapi.json`仍有一行生成版本信息差异，不是新增原生REST路径，也不是实现权限所必需的算法修改，其生成一致性应单独检视。

## 9. 当前结论和后续事项

四批优化已按[模块内聚建议](contextdb-cohesion-review.md)落地，并选择自研测试全部集中插件。响应边界、Key三投影、生产UI门禁、共享检查、固定SQL投影、MCP目录查询和UI状态归属已实现，并与最新UI简化一同纳入本次amend交付；已推送，固定代码提交见文首。

单次MCP工具目录filter的元数据查询在1/10/1000空间下均为3条：认证、目录归属检查、可见空间；实际工具调用继续按当前Key和目标认证。这不代表一条真实MCP消息总共只有3条SQL，原生可能重复filter，遥测UPDATE另计；无吞吐提升承诺。

继续保留跨schema Bank全局目录、可信固定镜像免扫描、原生私有接口升级、云环境与中文全文验收；用户/Key只读跨页扫描已移除；真实浏览器焦点、剪贴板及窄屏视觉仍待验收。原生DSN敏感日志仍由[Issue #3](https://github.com/ZhuQingping/ContextDB-Research/issues/3)跟踪，不恢复本特性的原生修改。

[旧版完整检视记录](../archive/2026-10-19-before-module-review/code-review-guide.md)保留了c60d409、9d51cac及逐文件分析，仅用于追溯。理解当前代码应从本文开始，不能把旧版执行屏障结论重新套到当前同步方案。旧`1b96e975`完整代码补丁见[归档](../archive/README.md#代码补丁)。


## 10. 2026-10-21夜间增量如何检视

本节对应c56c7ac17上的独立分支`contextdb/quality-20261021-004226`，不是前文a05b808统计范围；工作区和完整证据见[任务记录](../testing/contextdb-quality-improvement-plan.md)。不修改原生Python运行代码，部署包、CI、OpenAPI及元数据结构无新增改动。

| 阅读顺序 | 实现文件 | 检视重点及针对测试 |
| --- | --- | --- |
| 1 | transport.py | prompts/preview限Admin且不扩大GET_BANK_CONFIG权限；system/test_114使用真实SDK验证两Worker及四种业务授权 |
| 2 | database_checks.py → tenant.py / validator.py / mcp.py | metadata_errors只包元数据阶段；原生工具执行在外；tests/python/test_mcp_metadata_errors.py含协议/六hook故障和原生错误透传 |
| 3 | lib/contextdb-api.ts → users-view.tsx | 创建用户返回身份验证、Unicode与后端一致、展开仅存user_id；响应矩阵及组件坏201用例 |
| 4 | create-workspace-dialog.tsx | 卸载/关闭迟到成功无导航、旧finally不清新请求；native-entrypoints UI测试 |
| 5 | repository.py | 删除未调用函数与async转发壳；没有新增SQL、缓存或连接池 |
| 6 | tests/system/test_117_contextdb_management_failures.py | 临时PG故障注入覆盖真实原生提交与元数据接缝；业务验证走HTTP/SDK；清理注册在资源使用之前 |
| 7 | test_deployment_contract.py、system/test_110/111 | 真初始化无opt-in skip；撤权必须401；拒绝后数据及队列不变 |

另有四项控制组/故意破坏实验，证明关键断言确实检出只读越权、旧UUID授权、迟到Secret和敏感配置泄漏。三名独立检视者分别复核权限/PG、UI/TS、测试有效性；“代码及自动化接受”不表示完成真实浏览器或生产云环境验收。原样Docker和完整请求SQL测量详见任务记录，不用旧的单次filter三条SQL替代真实消息开销。


## 2026-10-22 提交前复检与本地新提交

本轮新增代码提交：`9fb57bc0470e7784d8766fdfb19d837f603b9638`（`contextdb/v1.0.0`），父提交为`003bbe032`；**创建新commit，没有amend，没有推送**。本节优先于前文“尚未提交”的历史实施记录。详细代码变更为30个文件：18个实现/部署文件修改、2个实现辅助文件新增，6个测试文件修改、4个测试文件新增；未提交原有`verification/`、日志、截图或构建产物。

| 检视重点 | 结果与证据 |
| --- | --- |
| 权限隔离 | 不同有效Key与Bank不共用授权；同消息读/写范围分别检查，下一消息重新检查授权变更、吊销和用户禁用。缓存只绑定当前HTTP消息、部署身份、凭据HMAC及目标，不建立跨消息权限缓存 |
| 自研逻辑收敛 | 原生Python运行目录没有新差异；没有新增表、连接池、执行屏障或日志框架。新增maintenance.py复用固定版本的原生函数DDL，safe_logging.py集中最小安全诊断 |
| O03性质 | 属于自研部署逻辑优化，不是工作空间/用户/Key管理的必要业务能力。不可变镜像在构建时核对UI、启动不重复扫描；源码仍检查。未宣称启动时延指标或本机容器已验收 |
| 测试有效性 | 发现维护函数测试依赖其他测试先初始化；已改为自行调用初始化，独立运行由失败变为通过。新增有效双Key/目标隔离、下一消息授权降级及用户禁用回归 |
| Trace/Webhook | 完整系统测试覆盖两Worker、两空间、签名、真实503重试、停用/删除、Trace归属和真实过期清理；只恢复已确认能力，Audit仍关闭 |
| 安全诊断 | 固定字段、SQLSTATE白名单、秘密/换行保护、管理响应与日志同ID、去重、取消及logger失败已有测试；O07原生日志问题没有混入修复 |

本轮重新执行：Python **425通过**；UI **560通过/55文件**；系统 **75通过**；相关原生MCP/扩展/Webhook/Trace **484通过**，均零失败/错误/跳过。原生真实Groq Trace用例因无凭据在命令中明确排除，不计为通过；这不是全部社区测试的全量验收。TypeScript、仓库lint、CI阻断范围knip、生产UI当前源码/产物指纹和diff检查通过；两个Worker的生产UI用例从系统报告提取后通过严格JUnit门禁。提交钩子全部成功，advisory扫描保留既有提示。

检视结论：**未发现阻断本次提交的权限隔离或功能问题**。O02镜像、真实MaaS/ECS/RDS、生产负载/恢复、O04完整tools/list性能量化、Trace关闭/写入故障及Webhook重启/重试耗尽完整组合仍未完成；不将其记为通过。Audit优先独立反馈社区，继续关闭；中文全文、O06/O07、Bank API统一未实施，S3没有本轮代码修改。

完整复检报告、命令及输出保存在`/Users/zhuqingping/Work/Database/Context/test/contextdb-amend-review-20261022/`，报告为`review-report.md`。该目录名称沿用中断前任务命名，实际执行已按最新指令改为创建新commit。本次资料提交仅包含本轮相关文档及必要引用资料；其他既有改动保留，未推送。

<a id="collaborative-review-route"></a>

## 11. 六轮协作检视路线

本章是后续检视计划，**六轮均未启动**。本次仅补充文档，不修改代码、不启动服务或执行测试。后续逐轮安排阅读和验证；发现问题先形成明确结论，代码修复另行确认。

### 11.1 检视对象与阅读方法

以最终代码`9fb57bc0470e7784d8766fdfb19d837f603b9638`为主线，不把两个提交逐文件重复阅读：

| 比较范围 | 要回答的问题 |
| --- | --- |
| 官方v1.0.0 `39c65ffe2` → `9fb57bc04` | 整个特性增加了什么，哪些原生接入点发生变化，有哪些维护风险 |
| 特性提交`003bbe032` → `9fb57bc04` | 后续认证复用、Trace/Webhook、诊断和启动优化是否改变权限及原生行为 |

代码根目录为`/Users/zhuqingping/Work/Database/Context/hindsight`。下文Python文件均指`hindsight-extensions/contextdb-service/hindsight_ext_contextdb/`，UI文件均指`hindsight-control-plane/src/`，测试集中在插件`tests/python/`、`tests/ui/`、`tests/system/`。

每轮先讲清“这个请求怎样执行”，再读关键函数和对应测试。Codex提供实际文件、函数及必要的小段代码，解释Python异步、类型和React状态等具体用法；不要求负责人先学习完整语言或框架。原生Python运行目录无差异，只说明该目录没有修改，不能替代对UI、扩展钩子、CI和实际行为的检视。

### 11.2 三方分工

| 参与者 | 主要职责 | 每轮交付 |
| --- | --- | --- |
| 你：设计与验收负责人 | 明确谁能访问什么、失败后客户应看到什么、哪些限制可以接受；重点检查PG约束、事务边界和恢复语义；选择少量真实业务场景复核 | 确认行为符合产品设计，明确接受或拒绝剩余风险。无需逐行掌握Python/TS |
| Codex：代码讲解与整合 | 对照官方基线，追踪入口、授权、SQL和原生调用；指出新增逻辑的必要性；核对测试是否真正覆盖风险；后续获准后统一实施最小修复 | 请求链路、关键文件/函数、风险与证据、对应测试、最小修复建议 |
| Claude Code：独立检视 | 每轮只审一个边界，先独立形成结论，再与Codex交叉核对；重点寻找绕过、错误身份复用、失败残留及原生能力遗漏 | 具体位置、触发条件、实际影响、复现步骤和缺失测试；没有发现也说明检查范围与盲区 |

Claude Code不先阅读Codex的结论，以减少相互附和；随后统一核对分歧。独立检视先只读，不让双方同时编辑相同文件。测试使用隔离环境，不直接操作现有8888/9999服务或客户数据。分工是后续调度约定，不表示本文更新时已启动其他Agent。

### 11.3 六轮顺序与验收标准

#### 第一轮：总体边界——先知道新增了什么

**阅读**：`asgi.py`，再看`tenant.py`、`validator.py`、`http.py`、`mcp.py`的入口，以及插件README、UI代理入口。先分清实现、测试、构建与生成物，不按文件总数判断复杂度。

- 你确认：工作空间与Bank一对一、每空间独立schema、管理员与业务Key的职责，是否与当前产品目标一致。
- Codex说明：REST、MCP、UI三条入口如何进入扩展，四个扩展各负责什么；哪些能力直接复用原生，哪些依赖原生内部函数。
- Claude Code检查：是否存在重复策略、可去除的接入点、绕过扩展的入口，以及无关原生改动。

**验收**：有一份“入口 → 扩展职责 → 原生能力”的对应关系；每处原生接入说明必要性和升级风险；负责人能够说明业务请求、管理请求和UI代理的差别。无法解释的改动进入问题清单，不以“原生Python零修改”直接结案。

#### 第二轮：业务请求与权限隔离——最优先验证

**阅读**：`transport.py`、`repository.py`的`authenticate`、`tenant.py`、`validator.py`、`authorization.py`、`mcp.py`。沿一个Recall请求核对凭据识别、目标空间、授权和最终schema；REST和MCP分别追踪，不能假设回调顺序相同。

- 你给出授权矩阵：空间A/B存不同标记，Key A仅只读A，Key B读写B，管理员按设计访问。
- Codex把矩阵映射到校验和SQL，核查缓存是否只在当前消息内复用，读写检查是否仍分别执行。
- Claude Code尝试跨空间、只读写入、吊销/禁用后的下一请求，以及同一MCP会话由强权限Key切为弱权限Key。

**验收**：正常读取和写入成功；越权请求被拒绝且实际记忆、任务及目标schema没有越权变化；下一消息使用最新授权；旧会话不沿用较强身份。目录可见性和实际执行都要检查，不能只断言HTTP 403。重点参照`test_104_contextdb_mcp_identity.py`、`test_111_contextdb_business_keys.py`及`test_message_reuse.py`。

#### 第三轮：用户与API Key——身份、授权和秘密如何保存

**阅读**：`http.py`的用户/Key路由 → `repository.py` → `security.py` → `schema.sql`，补看离线初始化代码。

- 你确认：用户唯一性、同名重建、一个用户多个Key、全部/指定空间、逐空间读写权限和吊销行为。
- Codex说明：管理员角色来自哪里；Key前缀与数据库身份的区别；HMAC、pepper和明文Secret各保存在哪里；空间授权为何关联内部身份。
- Claude Code检查：伪造管理员前缀、弱Key调用管理接口、过期授权、用户删除后旧Key，以及列表/日志/错误响应泄漏秘密。

**验收**：管理员身份不能靠客户端字段或Key前缀获得；原始Secret不落入元数据及普通日志；pepper与摘要的恢复依赖有明确说明；吊销、禁用和授权变更按规格生效；删除重建用户或空间不继承旧Key授权。首次签发、列表和编辑三类Key响应合同清楚且各有测试。

#### 第四轮：工作空间生命周期——成功与失败都要说清

**阅读**：`http.py` → `lifecycle.py` → `repository.py`，对照原生Bank创建/删除和schema迁移方法；结合`test_117_contextdb_management_failures.py`。

- 你审查PG事务、唯一约束和恢复结果，确认删除前排空任务等已接受的使用约束。
- Codex标出元数据事务与原生DDL/业务删除的边界，解释同步返回、部分成功、名称复用和条件请求。
- Claude Code检查：原生创建成功但元数据失败、业务删除完成但元数据收尾失败、客户端超时但服务器已提交，以及旧UUID授权访问同名新空间。

**验收**：每个失败阶段都明确返回结果、PG残留、重试/人工恢复办法；失败不能导致扩大授权；同名新空间不继承旧对象授权。超时或取消不被解释为后台已停止，删除/重建约束与原生语义及设计一致。检视不恢复已放弃的执行代次、删除屏障或独立准入池。

#### 第五轮：UI与服务器边界——把交互问题与权限问题分开

**阅读**：先看`app/api/contextdb/[...path]/route.ts`、`lib/contextdb.ts`及登录/session处理，再看`components/contextdb/`的用户、Key编辑器、空间创建和结果核对组件；补看`lib/contextdb-api.ts`。

- 你体验创建用户、签发Key、编辑授权和切换空间，确认文案及错误后的操作方式容易理解。
- Codex解释浏览器与UI服务器各保存什么，为什么要区分未知结果、确定失败和成功，以及状态归属如何避免迟到请求污染新弹窗。
- Claude Code检查管理员Key是否进入浏览器、普通Key能否登录UI，以及窄屏、焦点、Secret系统复制/粘贴、关闭弹窗、切换用户和重复点击。

**验收**：后台管理员Key不进入客户端包或响应；首次签发给用户的Secret按设计展示和清除；不确定结果不会自动重放写请求；旧响应不能覆盖当前用户/授权草稿或重新显示已清除Secret。异常JSON、HTML及缺字段成功响应有测试；布局、焦点、复制粘贴有真实浏览器证据，既有证据须说明所测版本和适用范围。

#### 第六轮：增量、部署与故障——确认运行时也成立

**阅读**：聚焦`003bbe032 → 9fb57bc04`，看请求认证复用、`maintenance.py`、`safe_logging.py`、Trace/Webhook适配及插件部署启动逻辑；对照`test_119_contextdb_trace_webhooks.py`和安全诊断测试。

- 你确认运维可获取哪些诊断信息、部署前提和仍不支持的能力，决定哪些外部验证是发布门槛。
- Codex核对SQL次数的测量口径、Trace目标schema、Webhook全局/Bank配置与后台执行，以及不可变镜像构建校验和运行时免扫描的边界。
- Claude Code检查两个Worker模式、跨空间回调、签名/重试、关闭及故障路径，检查日志秘密保护、请求关联和重复记录。

**验收**：认证复用不跨消息泄漏身份；Trace/Webhook的原生能力和空间隔离有实际验证；日志复用原生日志设施，仅固定安全字段，故障诊断不向客户返回内部详情。O03明确属于自研部署优化，不是管理特性的必要能力；固定镜像免扫描依赖构建校验，不扩大到任意源码运行。Audit继续关闭，社区问题单独跟踪，不声称本轮已支持。

实际容器、目标MaaS/ECS/RDS、生产负载与备份恢复等未完成验证，逐项列为外部验收；中文全文、O02、O06/O07及Bank API统一按现有待优化清单处理。不能用本地stub或相关原生测试通过替代生产环境验收。

### 11.4 每轮统一交付与通过条件

每轮只维护一份记录，由Codex汇总、Claude Code独立意见附后，你确认设计和剩余风险。记录至少包含：

| 项目 | 必须写清楚的内容 |
| --- | --- |
| 对象 | 固定提交、检视范围、关键文件/函数；后续有修复则记录新提交/源码版本 |
| 预期与实现 | 客户行为、请求链路、权限和事务边界，实际实现是否符合设计 |
| 发现 | 位置、触发条件、实际影响、复现证据；区分社区问题、自研缺陷、规格限制和环境缺口 |
| 验证 | 用例名称、执行命令、环境、实际结果；既有证据与本轮新执行分开，未执行明确标注 |
| 结论 | 已确认正确、待修复、暂不实施、待外部验证；每个未关闭项写负责人、下一步及是否阻断发布 |

**通过条件**：该轮关键路径已解释清楚；权限绕过、数据泄漏和破坏性残留等阻断问题已修复并复测；其他问题有明确处置及接受理由。没有证据的项目保持待验证，不将测试总数或Agent之间“达成一致”当作通过依据。你确认该轮结论后，再安排下一轮。

对关键拒绝逻辑，可在后续获准的隔离验证中临时移除检查，确认对应测试确实失败，再还原并复测；这用于检验测试有效性，不在当前工作区或运行服务上操作。原生功能还需按“保留、必要限制、遗漏、待支持”核对Validator策略，防止默认拒绝掩盖能力遗漏。

### 11.5 启动与进度

后续可直接提出：“开始第N轮，只读讲解与独立检视，按第11章输出结论，先不修改代码。”如需Claude Code参与，再向其分派同一轮的边界和固定提交；其独立结论形成后交叉核对。测试或修复执行范围在该轮明确，避免一次触发全部工作。

| 轮次 | 状态 | 下一步 |
| --- | --- | --- |
| 1 总体边界 | 待开始 | 确认三条入口与扩展职责 |
| 2 权限隔离 | 待开始 | 对照授权矩阵追踪REST/MCP |
| 3 用户与Key | 待开始 | 核对身份、授权与秘密保存 |
| 4 工作空间生命周期 | 待开始 | 核对原生调用与失败恢复 |
| 5 UI边界 | 待开始 | 核对服务器代理与真实交互 |
| 6 增量与部署故障 | 待开始 | 复核9fb增量及外部验收缺口 |

设计规格以[发布设计](contextdb-release-design.md)为准，实施取舍与延期项进入[待优化清单](contextdb-simplification-plan.md)，实际执行结果进入[验证摘要](../testing/contextdb-validation-summary.md)。本指南负责阅读路线与检视结论，不再复制一套部署或测试操作手册。
