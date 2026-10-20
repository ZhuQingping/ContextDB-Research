# ContextDB 代码检视指南

更新：2026-10-20。本文按模块说明当前实现与检视顺序。本次将 `ddf5c3600` 与四批优化、测试接线及UI简化通过 amend 整理为官方 v1.0.0（`39c65ffe`）之上的单一特性提交，尚未推送。验收源码树为 `ce1c7def06cf26d9450fcef34acbad4e47268e6f`；实际代码提交号用 `git show contextdb/v1.0.0` 核对，提交正文固定本资料仓快照。下列代码链接使用交付分支作路径导航，推送前远程仍为旧代码；正式检视须固定代码与资料提交。

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

包含新增文件的本地完整快照相对官方基线共165个文件，按职责分组如下。文件数增长主要来自测试准备模块、补充回归及明确的UI状态归属；原生Python运行目录仍为零差异，不以“更少文件”代替质量判断。

| 范围 | 文件数 | 说明 |
| --- | ---: | --- |
| 插件运行实现 | 24 | 新增database_checks.py共享检查；认证、事务与生命周期仍在原插件模块 |
| 插件Python测试、合同检查与支撑 | 40 | 27个Python用例文件、共享准备/清理及独立Node合同门禁等 |
| 插件部署、契约、配置与文档入口 | 17 | 原15个文件保留，增加系统测试配置和生产UI结果检查脚本；无新增生产参数 |
| UI实现、构建、文案与工具接线 | 37 | 组件集中contextdb目录、删除辅助扫描及重复入口，保留类型/lint/Vitest/knip接线 |
| UI测试 | 12 | 插件内11个专属文件，另有原生词条检查的自研增补 |
| 插件系统故事与支撑 | 24 | 16个故事/清理用例文件及共享部署、客户端、UI资源owner |
| 原生系统测试框架与配置 | 6 | 单一共享pytest插件、启动工具、依赖/锁和文档；不复制框架 |
| 其他 | 5 | CI、项目测试约定、lint hook、扩展索引及既有OpenAPI参考副本 |

原生dotenv文件已恢复官方内容；托管禁用.env的新增用例位于插件。本文数字对应上述验收源码树；代码提交正文固定同版资料快照。

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
| [models.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/models.py) | 定义空间、用户、Key和授权的数据结构、输入约束 | 名称规范化；selected逐空间权限与all统一权限；未知字段拒绝 |
| [schema.sql](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/schema.sql) | 定义六张管理表、唯一约束、外键、延迟校验及索引 | 空间和用户名称唯一；授权关联UUID；摘要不存明文；反向授权索引 |
| [repository.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py) | 执行管理SQL和事务，统一查询身份与授权 | SQL是否绑定对象身份；事务是否完整；Key批量授权；审计及失败状态 |
| [http.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/http.py) | 注册13个管理操作，解析参数、鉴权和If-Match，构造响应 | 管理员才能访问；201/204及错误码；秘密和原始错误不回显 |
| [lifecycle.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py) | 把空间创建/删除的几个步骤串起来，直接等待原生Bank方法 | 不再自建调度器；原生操作前后释放管理连接；失败不冒充整体回滚 |

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
| [security.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/security.py) | 生成随机Key、计算HMAC摘要、提取Bearer凭据 | 把密码学和Header解析集中在一处 |
| [config.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py) | 读取部署归属及pepper，校验不支持配置；取得原生池并创建Repository | 避免各扩展创建额外连接池或各自解析配置 |
| [authorization.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/authorization.py) | 保存本次目标认证结果、同步管理调用的受信上下文 | 同一请求减少重复查询；客户端不能伪造管理生命周期权限 |
| [asgi.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/asgi.py) | 在原生应用外安装ContextDB中间件 | 使用自研启动入口，不改原生API初始化顺序 |
| [transport.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/transport.py) | 从REST URL识别Bank，处理目录和诊断边界，阻止原生生命周期旁路 | 普通REST、原生Bank路径和MCP挂载均需覆盖 |
| [tenant.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py) | 校验身份，把工作空间映射到PG schema | 回答“这个请求访问哪个schema” |
| [validator.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py) | 把操作映射到只读、读写或管理员权限 | 回答“这个身份能否执行这项操作”；原生内部任务也需校验归属 |
| [mcp.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/mcp.py) | 从当前MCP消息获取Key/Bank，适配目录、工具权限及结果脱敏 | 同一MCP连接可访问多个空间，不能固定沿用初始化时的身份 |
| [routing.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/routing.py) | 保存本次目标Bank，聚合跨schema Bank目录 | 原生单schema列表不能直接代表实例下全部可见空间 |
| [diagnostics.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/diagnostics.py) | 对业务Key可见的原生任务响应裁剪敏感字段 | 正常任务进度可读，不因此暴露后台请求配置 |

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

[交付分支UI目录](https://github.com/ZhuQingping/hindsight/tree/contextdb/v1.0.0/hindsight-control-plane/src)。检视顺序建议：空间页面 → 共享创建表单 → 用户页面 → 请求函数 → 服务器鉴权和代理；不必先读React所有基础组件。

本轮UI简化保留用户目录、Key面板、Key编辑器三个状态边界，组件和局部hook集中在`components/contextdb/`。请求错误分类合入`lib/contextdb-api.ts`，授权比较函数放回唯一使用它的编辑器，删除两份小工具文件。

用户与Key结果未知时只展示原目标信息、刷新普通分页列表，取消全量ID扫描；创建用户成功显示返回名称/ID，不再自动找页展开。Key已返回的授权用于初始化草稿，目录只提供分页选项；保存携带原UUID和版本，后端拒绝过期授权。同名继任若已出现在目录中，只提示旧项不可用，不自动迁移选中项。工作空间删除集中到管理目录，原生Bank详情在ContextDB模式提供管理链接；原生模式删除保留，生命周期API旁路仍拒绝。

## 6. 模块四：离线初始化、部署和版本检查

| 文件 | 负责什么 | 检视重点 |
| --- | --- | --- |
| [__main__.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py) | `python -m hindsight_ext_contextdb`命令入口 | generate-admin-key、migrate等均是本机命令，不是HTTP接口 |
| [bootstrap.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/bootstrap.py) | 生成/读取持久秘密、初始化/轮换管理员 | 首次离线可完成；重复初始化不换pepper或丢失原Key |
| [migrations.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/migrations.py) | 初始化管理结构、检查部署归属和结构格式 | 首发版本1；拒绝开发期旧结构，不虚构历史兼容升级 |
| [deployment.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/deployment.py) | 校验部署JSON、渲染api.env/ui.env、状态检查 | 首版merged/native/english；路径和秘密权限；无任意环境透传 |
| [preflight.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/preflight.py) | 在迁移前检查PG权限、扩展和检索条件 | 不创建数据库；托管固定英文；手工研究的PGroonga检查不等于本期依赖 |
| [launch.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/launch.py) | 按进程加载秘密，校验产物并启动API/Worker/UI | UI进程不注入PG、MaaS及pepper环境 |
| [artifacts.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/artifacts.py) | 构建UI并生成指纹，启动前核对源码/产物 | 当前完整扫描保留；可信固定镜像免扫描仍为TODO |
| [__init__.py](https://github.com/ZhuQingping/hindsight/blob/contextdb/v1.0.0/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__init__.py) | Python包初始化与管理元数据格式/版本常量 | 不是另一个服务 |

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

Python共享身份、HTTP装配、生命周期double和PG资源准备位于tests/python/support；系统资源owner位于tests/system/support。测试不再导入其他test文件，也不调用fixture.__wrapped__；初始化失败直接检验普通资源owner的清理。原生与插件系统故事共用server、stub和已发布SDK。pytest_plugin仅79行，保存模型替身、每例规则重置及未匹配/格式错误检查；原生服务器、客户端和Bank fixture放在原tests/conftest.py。所有原函数体及装饰器与官方原版一致，不迁出整套原生fixture。

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

四批优化已按[模块内聚建议](contextdb-cohesion-review.md)落地，并选择自研测试全部集中插件。响应边界、Key三投影、生产UI门禁、共享检查、固定SQL投影、MCP目录查询和UI状态归属已实现，并与最新UI简化一同纳入本次amend交付；尚未推送。

单次MCP工具目录filter的元数据查询在1/10/1000空间下均为3条：认证、目录归属检查、可见空间；实际工具调用继续按当前Key和目标认证。这不代表一条真实MCP消息总共只有3条SQL，原生可能重复filter，遥测UPDATE另计；无吞吐提升承诺。

继续保留跨schema Bank全局目录、可信固定镜像免扫描、原生私有接口升级、云环境与中文全文验收；用户/Key只读跨页扫描已移除；真实浏览器焦点、剪贴板及窄屏视觉仍待验收。原生DSN敏感日志仍由[Issue #3](https://github.com/ZhuQingping/ContextDB-Research/issues/3)跟踪，不恢复本特性的原生修改。

[旧版完整检视记录](../archive/2026-10-19-before-module-review/code-review-guide.md)保留了c60d409、9d51cac及逐文件分析，仅用于追溯。理解当前代码应从本文开始，不能把旧版执行屏障结论重新套到当前同步方案。旧`1b96e975`完整代码补丁见[归档](../archive/README.md#代码补丁)。
