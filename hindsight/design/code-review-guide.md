# ContextDB 代码检视指南

> **当前本地实现（2026-10-19）：** 工作空间同步POST201/DELETE204，13个管理操作、6张管理表；自研管理调度、持久在途屏障、额外池和七个原生运行文件差异已撤销。原生运行目录与官方v1.0.0 `39c65ffe2f140d0c84cee58566cad8900c5b9908` 一致。保留正常授权、schema映射、UUID及If-Match，删除前管理员停止访问并等待已有工作结束。
>
> **交付状态：** 本轮采用 amend 保持一个特性提交，本地回归和独立Hindsight/PG专家检视已完成；尚未推送，不替代目标环境验收。最新结果见[验证摘要](../testing/contextdb-validation-summary.md)，逐项实施状态见[简化清单7.8](contextdb-simplification-plan.md#r01-r07-review-plan)。数据库敏感日志恢复原生后仍有风险，由[Issue #3](https://github.com/ZhuQingping/ContextDB-Research/issues/3)独立处理。

## 本轮代码检视入口

先看[完整设计](contextdb-release-design.md)和[规格约束](contextdb-release-design.md#feature-specification)，再看特性提交相对官方基线的差异。不要先阅读旧163项文件清单来理解新实现。

| 范围 | 当前实现与检视重点 |
| --- | --- |
| 原生运行目录 | `hindsight-api-slim/hindsight_api`与官方基线一致；未修改记忆算法、原生MCP错误处理、任务取消重试和Worker终态写入 |
| authorization.py / transport.py | 认证快照、受信用途和目标、REST身份/路由/诊断边界；没有Admission表、长事务和传输执行追踪 |
| lifecycle.py / repository.py | 同步请求、短管理事务与原生DDL分开；六表、普通状态和失败占名、最终清理事务 |
| 四扩展 / ASGI入口 | Tenant/Validator/HTTP/MCP保留正常职责；ASGI复用原生应用lifespan，仍不可绕过自研入口使用原生CLI |
| UI / 管理代理 | 同步响应和未知结果查询；共享名称/描述表单、表格可读性；会话、同源、固定目标和秘密保护 |
| 部署 / 产物 | merged/native/english固定；无旧池/语言/retention变量；manifest及完整启动校验保持，免扫描TODO |
| 回归 / CI | 原生行为、读写和跨空间、当前MCP消息、失败/重建/旧条件；系统故事显式contextdb依赖组 |

```bash
# 在代码仓查看本轮amend后的提交；提交正文固定对应的资料仓快照。
git log -1 --format=fuller
# 旧1b96e975的完整补丁见资料仓archive/patches/，不是当前实现。
git status --short
git diff --stat 39c65ffe2f140d0c84cee58566cad8900c5b9908 HEAD
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 HEAD -- hindsight-api-slim/hindsight_api
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 HEAD -- hindsight-extensions/contextdb-service hindsight-control-plane
# ContextDB系统故事在独立环境显式安装，不能让CI静默跳过。
cd hindsight-system-tests
uv sync --frozen --group contextdb
# 具体测试选择及结果以本轮验证记录为准。
```

## 历史评审与验证说明

以下章节保留上一轮提交的原始统计、意见和当时结果，供追溯；其中“当前”“继续保留”“已推送”等均指该章节固定的历史提交，不是本轮状态。原保护机制的必要性按最新规格已取消，不能将历史表格重新当成保留执行屏障的要求。新结构/API及本轮未关闭事项以上方入口和当前设计为准。

## 历史：PR #1 修复与后续评审（2026-10-19）

**后续实施补充：** 额外扩展连接池及独立Worker的配套关闭补丁按[设计5.2.2.3](contextdb-release-design.md#extension-pool-removal-decision)移除，管理元数据复用原生主库池。数据库日志脱敏从本特性剥离，由[Issue #3](https://github.com/ZhuQingping/ContextDB-Research/issues/3)跟踪独立修复。下文“通用加固保留”等内容描述先前代码/评审快照，不替代这两项最新决策。

本节对应 `9d51cac` 的检视结果，以下修复随本次代码 amend 交付；是否进入远程 CI 以 PR 的 head 提交为准，本地通过不代表远程 CI 已通过。下文固定为 `9d51cac` 的统计保留为历史快照。

本次代码相对官方 v1.0.0 涉及 142 个文件：扩展 69 个、UI 37 个、系统测试 23 个、原生运行代码 7 个、原生回归测试 3 个，另有 CI、扩展索引和原生生成的 OpenAPI 参考副本 3 个。扩展内 32 个为测试文件，UI 内 9 个为测试文件；不能将总文件数理解为原生内核改动数。生成参考副本的一行版本同步、通用日志脱敏、字体与可选部署材料不属于权限业务本身，继续按下文 TODO 评估范围。

| 已确认的问题 | 本地处理 |
| --- | --- |
| 插件 Ruff 导入排序随执行目录变化 | 插件 pyproject 继承原生 Ruff 配置，显式指定本包导入分类；CI 使用该配置，生成器导入按其排序 |
| 部署状态检查未显式选择代理策略 | 节点健康/身份检查设置 `trust_env=False`，直连配置的节点，满足原生会话结构检查 |
| 系统测试 pytest 进程无法导入插件 | 在系统测试 pytest 配置中声明插件源码路径，初始化不再依赖开发者额外设置 PYTHONPATH；API/Worker 子进程继续使用原有隔离配置 |
| 验证时补充发现：OpenAPI 生成器占位对象缺少 tenant_extension | 使用只有该槽位的类型化占位对象，不启动引擎；新增从临时目录、无部署凭据运行生成器的回归用例，检查现有契约不变 |

四个入口的认证共用与重复查询分析见[设计文档：认证与授权复用评审](contextdb-release-design.md#认证与授权复用评审2026-10-19待实施)。本轮不调整权限模型，也不删除引擎或 Worker 安全钩子。缺少 Vertex AI、Cohere 和其他模型凭据造成的远程失败属于独立 CI 配置项，不随这三项修复自动解决。

本地验证（2026-10-19，均已执行）：

| 范围 | 结果 |
| --- | --- |
| 插件全量测试 | 438 passed，1 skipped；原有三项过渡部署测试已迁资料仓，本轮新增一项独立生成器回归 |
| ContextDB 系统测试 100–118 | 67 passed，409.15 秒；新建依赖环境，移除外部 PYTHONPATH，覆盖两种 Worker、REST/MCP、UI、同名重建和原生无扩展兼容 |
| 原生 test_aiohttp_session.py | 11 passed；清除本机代理环境，原生会话结构检查通过 |
| 插件 Ruff、format、ty；根目录 lint | 全部通过；插件配置在根目录和插件目录检查一致 |
| 工作区与测试退出 | git diff --check 通过；用户 verification 文件未改，测试 API/Worker/PG 已退出 |

全新环境复测未完成整个原生系统套件，本轮不将之前中断的尝试算作通过。未重跑真实模型矩阵；缺凭据的远程检查仍需另行配置和复测。

更新：2026-10-19。当前功能基于原生 Hindsight v1.0.0，分支 `contextdb/v1.0.0`；完整功能相对原生集中为一个提交。管理 API 和元数据都从版本 1 开始，历史草稿中的 V1/V2 不代表已发布的升级合同。

## 版本对应

| 内容 | 固定版本 / 位置 |
| --- | --- |
| 原生父提交 | `39c65ffe2f140d0c84cee58566cad8900c5b9908`（v1.0.0） |
| 本次整理前的代码提交 | [c60d409](https://github.com/ZhuQingping/hindsight/commit/c60d409cfb4f879051a4fe258bbcaff8872df09e)；详细文档已移至资料仓，提交内 docs/README.md 为链接入口 |
| 上一轮远程评审快照 | [9d51cacde496baa628408e4b474f0f949220a90f](https://github.com/ZhuQingping/hindsight/commit/9d51cacde496baa628408e4b474f0f949220a90f)；已 amend 并推送到 `contextdb/v1.0.0`，相对原生仍为一个特性提交；本轮收敛见[落实结果](#extension-implementation) |
| 人工文档 | [本目录总入口](../README.md)、[完整设计](contextdb-release-design.md)；以包含本次目录整理的资料仓提交为快照 |
| 机器接口合同 | [OpenAPI](https://github.com/ZhuQingping/hindsight/blob/9d51cacde496baa628408e4b474f0f949220a90f/hindsight-extensions/contextdb-service/schemas/contextdb-control-plane.openapi.yaml)，由代码生成并校验 |

`c60d409` 的详细设计、部署指南、API 用例和运维手册由资料仓维护；本轮整理前完整目录见[备份](../archive/2026-10-19-before-reorganization/README.md)。代码仓只保留入口，不再双份同步人工文档。

先看[原生扩展机制复评与10项原生改动处理建议](#extension-reevaluation)，再按需查[c60d409 的163项逐文件变更说明](#c60-file-review)。逐文件表保留历史实现意图，必要性以复评结论为准。

## 历史：上一轮专家检视顺序

先读[设计](contextdb-release-design.md)，尤其是[第6.1节特性规格约束](contextdb-release-design.md#feature-specification)，再按下表查看相对 v1.0.0 的差异，不需要先通读历史过程记录。精确判断请求/Worker退出及最终状态写入的增强保护已决定随同步管理一并撤销；检视须保留正常鉴权和隔离，不再以违反删除使用前提的并发场景要求恢复该体系。

| 范围 | 代码路径 | 重点 |
| --- | --- | --- |
| 原生接入 | `hindsight-api-slim/hindsight_api` | HTTP/MCP、引擎、Worker 的可选扩展与执行代次保护；其他租户扩展默认保持原生行为 |
| 外围实现 | `hindsight-extensions/contextdb-service/hindsight_ext_contextdb` | 统一 PG 认证、按 Key 授权、生命周期、元数据、管理 REST；记忆算法复用原生 |
| UI 与代理 | `hindsight-control-plane` | 工作空间/用户/Key、管理员登录、固定目标代理及原生 Bank 入口限制 |
| 部署 | 扩展包的 `deployment/`、`scripts/` | 单容器、离线初始化、配置与秘密持久化、RDS 插件及可选 PG SSL |
| 回归 | 扩展包 `tests/`、原生/API/UI/system tests | 权限、重建、在途保护、Append 冲突、进程退出及原生业务 |

```bash
# 先在本地检出下面固定提交；这些命令只读，不运行部署或测试。
git show --stat 9d51cacde496baa628408e4b474f0f949220a90f
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 9d51cacde496baa628408e4b474f0f949220a90f -- hindsight-api-slim/hindsight_api
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 9d51cacde496baa628408e4b474f0f949220a90f -- hindsight-extensions/contextdb-service
git diff 39c65ffe2f140d0c84cee58566cad8900c5b9908 9d51cacde496baa628408e4b474f0f949220a90f -- hindsight-control-plane
```

## 历史：上一轮评审边界

单容器 API 内置 Worker，独立 UI 进程；用户属于实例，Key 独立授权，selected 可逐空间读写/只读，all 包含未来空间。工作空间使用可读 bank_id 与 schema，内部 UUID 区分删除后同名重建对象。

原生 Trace/Audit 正文写入、Webhook 在自研首版关闭。中文分词全文、目标 ECS 容量、RDS 恢复、完整镜像安全验收等尚未完成，见[设计 TODO](contextdb-release-design.md#本轮实现收敛与-todo)及[验证摘要](../testing/contextdb-validation-summary.md)。下文区分历史提交、纯原生复评及本地落实结果；这些生产 TODO 不因本轮功能回归通过而完成。

更早的 V1/V2 对照、未推送本机提交与过程检视见[整理前的版本说明](../archive/2026-10-19-before-reorganization/design/version-comparison.md)，不列为当前检视前置材料。


<a id="c60-file-review"></a>

## 历史：c60d409 的163项文件变更说明

核对日期：2026-10-19。只审视用户指定提交 `c60d409cfb4f879051a4fe258bbcaff8872df09e` 相对其直接父提交原生 v1.0.0 的净差异；当前分支后来仅修改了资料仓导航链接。实际状态为新增112项、修改50项、重命名1项。以下是变更目的、范围与简化判断，不是逐条证明实现正确的安全审计，逐文件说明阶段没有修改运行代码或执行业务测试；后续原生扩展复评另做了隔离验证，见[复评结果](#extension-reevaluation)。

### 先看结论

**这个提交既包含功能实现，也包含整套交付与回归，163项确实偏大，不能把所有变化都解释为工作空间/用户/API Key本身必需。** 原生Python运行文件10项；新增扩展21项；UI实现/构建27项；其余包含67项测试支撑、10项文案、14项部署工具、11项配置/文档支撑、2项生成接口定义、1项测试锁文件。

`git diff --stat c60d409^ c60d409` 为163项，新增29347行、删除533行；Next配置重命名算1项。这里没有160项原生内核修改，也没有修改LLM、Embedding、Rerank或检索算法实现。生成定义和锁文件占新增8060行，测试支撑占11489行；行数不能直接当产品手写复杂度，但新增扩展5197行和UI实现/构建2452行仍需认真审查。

| 分类 | 变更项 | 新增行 | 删除行 |
| --- | ---: | ---: | ---: |
| 原生 Python 运行代码 | 10 | 341 | 44 |
| 新增 ContextDB 扩展 | 21 | 5197 | 0 |
| UI 实现与构建 | 27 | 2452 | 121 |
| 测试与测试支撑 | 67 | 11489 | 32 |
| UI 语言资源 | 10 | 930 | 0 |
| 部署与工具 | 14 | 726 | 0 |
| 配置、文档与其他支撑 | 11 | 152 | 4 |
| 生成的接口定义 | 2 | 3112 | 1 |
| 系统测试锁文件 | 1 | 4948 | 331 |

### 为什么会跨这么多文件

静态Key插件只是认证示例，不能据此判断扩展机制能力不足。原生Tenant/Validator/HTTP已经能承载动态身份、管理API和Bank权限。原生REST/MCP不经过新增管理路由，但仍调用引擎的认证与校验钩子；“绕开管理路由”不是修改内核的理由。当前代码将这些策略放入外围扩展，UI负责用户操作；新增内核钩子的必要性须分别证明，详见[后续原生基线复评](#extension-reevaluation)。

进一步要求“可读bank_id和schema、物理删除、删除后同名重建”，使原本简单的CRUD变成跨请求和后台任务的生命周期协调。旧MCP会话、断连后的任务、Worker最终状态、配置缓存，都不能在新对象出现后继续访问同名schema；这解释了admission/lifecycle及原生Worker、MCP接入，但并不证明目前每一处分支都是最简实现。

原生运行改动共新增341行、删除44行，集中10项。下面说明当时实现范围，不代表这10项均应保留。这里没有增加read_origin；没有修改原生静态租户插件；MaaS复用既有适配器，未修改原生模型算法。默认无扩展钩子为空操作，但MCP当前消息身份恢复、日志脱敏、Worker异常路径及UI字体/构建变更仍触及通用行为，不能说“原生行为完全没有变化”。

### 本轮明确识别的问题与处理建议

| 优先级 | 问题 | 判断与建议 |
| --- | --- | --- |
| 需纠正 | 配置文档和skill参考仍描述HINDSIGHT_API_ENV_FILE，当前代码没有实现 | 这是过期说明，实际托管方案使用PYTHON_DOTENV_DISABLED=1；应删旧说明并同步生成参考 |
| 需纠正 | 原生server导入前加载.env/信号量初始化测试被替换 | 新的dotenv禁用测试不覆盖原断言；恢复原生用例再追加托管测试，不能用总通过数掩盖覆盖减少 |
| 应收敛 | 系统测试uv.lock新增4948/删除331行 | 测试包从38增至209，新增171包、无删除；原因是系统测试直接引入服务端embedded-db，不是生产镜像新增171包。考虑可选extra/独立扩展故事环境或复用锁定服务环境，减少重复固定版本 |
| 应收敛 | 6份非英语contextDB文案大部分重复英文 | 10个语言包各加93行；其中6份非英语包的91个文案中90个与英文相同，仅空间名说明翻译。共享英文fallback可减少重复，但要保持原生locale行为及缺键检查 |
| 已迁移 | 原生官方镜像过渡部署材料 | 四个工具及三项测试迁至资料仓 [tools/](../deployment/native-v1.0.0/tools/)，补齐建库SQL和独立CI；不再随自研扩展交付 |
| 可拆分 | 本地系统字体、Next配置重命名 | 为构建/制品交付服务，不是权限必须；应单独给构建证据，优先评估保留上游配置形态 |
| 可拆分 | 通用数据库日志脱敏 | 有价值，但可独立提交上游；无需与完整产品功能一起解释 |
| 应继续审查 | PGroonga预检、独立Worker启动项及测试 | 首版明确只交付native英文全文和合并Worker；这些不是当前部署前置要求，可独立组织，不要让首版命令暴露过多分支 |
| 应继续审查 | repository/admission/用户UI大文件与重复规则 | 1073/611/915行本身不是错误，但表明复杂度集中；优先复用认证结果、条件头/模型定义与状态处理，不靠拆小文件伪装简化 |

不能为减少文件数直接删除权限检查、旧执行者保护或异常并发测试。若产品明确改为不可复用物理schema、延迟名称复用等方案，可再整体重估生命周期成本；这属于设计变更，不是随手删几个钩子。

### 逐文件说明

下列路径均链接到指定c60d409提交。`+/-`是该提交的行变化，不是当前文件长度；新增文件的`+`恰好是当时行数。“可拆分/收敛”只作本轮评审意见，尚未修改实现。

#### 1. 原生 Python 运行代码

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-api-slim/hindsight_api/api/__init__.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/api/__init__.py) | +6/-1 | 调整扩展中间件安装次序，让保护层包住 REST 和挂载的 MCP；否则 MCP 可绕过空间删除排空保护。 | 保留接入，核对安装顺序 |
| [hindsight-api-slim/hindsight_api/api/http.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/api/http.py) | +5/-0 | 允许 HTTP 扩展提供 ASGI 中间件，并支持延后安装；为扩展观察原生请求完整执行期提供入口。 | 保留可选接口 |
| [hindsight-api-slim/hindsight_api/api/mcp.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/api/mcp.py) | +104/-0 | 为每条 MCP HTTP 消息保存并恢复本次认证身份；转发隐藏的执行故障通知，防止会话复用旧 Key、旧 schema 或误释放删除屏障。 | 重点审查；不是记忆算法变化 |
| [hindsight-api-slim/hindsight_api/engine/memory_engine.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/engine/memory_engine.py) | +62/-15 | 增加异步提交保护域、原生任务多状态查询；PG 单输入 Append CAS 冲突通过既有结果钩子证明写入已结束，避免永久挡住删除。 | 重点审查；最值得收敛的原生接入 |
| [hindsight-api-slim/hindsight_api/extensions/http.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/extensions/http.py) | +11/-0 | 新增默认返回空列表的 get_middleware 钩子；扩展可包住原生请求，原有扩展默认不增加中间件。 | 保留默认无行为约定 |
| [hindsight-api-slim/hindsight_api/extensions/tenant.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/extensions/tenant.py) | +29/-0 | 新增默认无操作的 async_submission_scope/async_execution_scope；分别包住任务入队及完整 Worker 执行/状态写入。 | 保留可选钩子 |
| [hindsight-api-slim/hindsight_api/mcp_tools.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/mcp_tools.py) | +41/-15 | 认证拒绝与未知故障分开处理，并通过可选 failure_reporter 通知扩展；MCP 将异常包装为正常返回时仍能保留未知写入屏障。 | 重点审查；可减少重复 catch 分支 |
| [hindsight-api-slim/hindsight_api/utils.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/utils.py) | +2/-1 | 日志 URL 脱敏额外去掉 query/fragment，防止其中携带凭据。 | 通用安全修复，可独立提交上游 |
| [hindsight-api-slim/hindsight_api/worker/main.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/worker/main.py) | +5/-1 | 数据库启动日志改用脱敏 URL；退出时调用 tenant on_shutdown，关闭扩展资源。 | 脱敏可独立；独立 Worker 属机制支持 |
| [hindsight-api-slim/hindsight_api/worker/poller.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/hindsight_api/worker/poller.py) | +76/-11 | 完整任务及完成/延期状态写入纳入代次保护；过期任务不能向同名新 schema 写状态，取消或故障不冒充执行者已退出。 | 重点审查；需保留并发故事验证 |

#### 2. 新增 ContextDB 扩展

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__init__.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__init__.py) | +5/-0 | 定义新增扩展包入口及版本。 | 必要打包文件 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py) | +138/-0 | 提供离线生成/导入/轮换 Admin Key、预检、准备、启动、构建 UI 命令；API 未启动前完成初始化。 | 必要入口；CLI 选项可继续收敛 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/admission.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/admission.py) | +611/-0 | 实现请求保护域、取消后的工具排空、PG 持久屏障与 ASGI 接入；删除先关准入，确认旧执行者结束后才 DROP。 | 复杂度核心，611 行；应审查而非直接删锁 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/artifacts.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/artifacts.py) | +95/-0 | 给 UI 源码与构建结果计算指纹，启动前拒绝 API/UI 制品错配。 | 部署增强；可评估由镜像版本/CI替代 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/bootstrap.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/bootstrap.py) | +214/-0 | 私密持久文件、pepper、管理员导入与恢复；重复初始化不重新生成凭据。 | 必要安全与初始化 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py) | +90/-0 | 集中读实例归属、pepper、管理/准入池参数；取得共享管理 Repository。 | 必要配置 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/deployment.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/deployment.py) | +335/-0 | 校验管控 intent、读取秘密、渲染环境文件、只读状态核对；让节点 Agent 调已有命令而非新常驻服务。 | 部署配套；与原生 renderer 有可复用部分 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/diagnostics.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/diagnostics.py) | +39/-0 | 裁剪业务任务诊断中的内部或敏感字段，保留客户需要的状态。 | 必要信息边界 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/http.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/http.py) | +506/-0 | 管理 REST 路由、输入/输出/错误模型、管理员校验、ETag/幂等头及生命周期启动。 | 必要；14 个管理操作 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/launch.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/launch.py) | +70/-0 | 加载所需私密配置后启动 API/Worker/UI；避免把 PG/MaaS 密钥全部传给 UI，关闭意外 .env 覆盖。 | 部署配套；独立 Worker 启动项非首版交付要求 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py) | +207/-0 | 领取 PG 管理操作、续租、建空间和删除排空/物理清理；复用原生建表、Bank 操作。 | 必要；异步生命周期带来的成本 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/mcp.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/mcp.py) | +164/-0 | 通过已有 MCP 扩展机制按当前工具参数定位空间，复用原生工具并校验权限/保护域。 | 启用 MCP 时必要 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/migrations.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/migrations.py) | +54/-0 | 首发管理结构初始化、版本/归属核对；拒绝不兼容开发期结构。 | 必要；不是提供旧版本自动升级 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/models.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/models.py) | +254/-0 | 定义工作空间、用户、Key、授权、版本与错误合同；限制名称与输入，默认禁止多余字段。 | 必要；可核对模型重复 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/preflight.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/preflight.py) | +279/-0 | 只读检查代码/构建、PG扩展、维度、全文后端及不支持能力；在启动前暴露错误。 | 预检有用；PGroonga/多语言分支非首版必需 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py) | +1073/-0 | PG 元数据存取、统一 HMAC 认证、授权、批量更新、并发条件、幂等操作和审计。 | 主体必要；1073 行，需继续检查重复事务/SQL |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/routing.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/routing.py) | +107/-0 | 定位本次 Bank、跨 schema 目录聚合及清空语义；不把多空间目录误当单空间授权。 | 必要；列表分页前聚合仍是性能 TODO |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/schema.sql](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/schema.sql) | +265/-0 | 创建8张管理表、索引/约束/触发器及注释；PG负责唯一性、授权一致性和生命周期并发不变量。 | 必要；约束复杂度应逐项有并发依据 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/security.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/security.py) | +58/-0 | 生成随机 Key、HMAC-SHA256、提取 key_id/Bearer；PG 保存摘要而非明文。 | 必要 |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py) | +287/-0 | 实现原生 Tenant 接口：统一认证、schema路由、后台任务/目录身份、空间代次缓存失效。 | 必要；原生静态租户无法直接表达动态多空间 ACL |
| [hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py) | +346/-0 | 实现原生操作校验：读写权限、管理操作限制、内部任务身份及原生 Bank 生命周期阻断。 | 必要；与认证的重复检查仍可继续收敛 |

#### 3. UI 实现与构建

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-control-plane/next.config.mjs](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/next.config.mjs) | +8/-7 | 将 next.config.ts 改为可由 Node 直接加载的 ESM 配置，路径改用 import.meta.url；构建、指纹和 Dockerfile 同步。 | 部署便利项；需证明不能复用原生 TS 配置 |
| [hindsight-control-plane/src/app/[locale]/banks/[bankId]/page.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/%5Blocale%5D/banks/%5BbankId%5D/page.tsx) | +83/-26 | 增加用户管理导航；隐藏/拦截 Bank 克隆、导入、删除等与工作空间生命周期冲突入口。 | 必要 UI 适配 |
| [hindsight-control-plane/src/app/[locale]/layout.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/%5Blocale%5D/layout.tsx) | +15/-29 | 下发 ContextDB 模式给组件；移除 next/font/google，改本地系统字体避免构建联网下载字体。 | 模式下发必要；字体调整属独立构建改进 |
| [hindsight-control-plane/src/app/[locale]/login/page.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/%5Blocale%5D/login/page.tsx) | +13/-2 | 在 ContextDB 模式将登录提示表达为 UI 密码，不要求客户感知后台 API Key。 | 必要产品表达 |
| [hindsight-control-plane/src/app/[locale]/users/page.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/%5Blocale%5D/users/page.tsx) | +15/-0 | 新增用户管理页面入口，受 ContextDB 模式及管理登录约束。 | 必要 |
| [hindsight-control-plane/src/app/api/auth/login/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/auth/login/route.ts) | +14/-2 | 登录检查输入类型、同源与后台 Admin 身份，不让业务 Key 替代 UI 密码；禁止缓存登录响应。 | 必要安全边界 |
| [hindsight-control-plane/src/app/api/banks/[bankId]/aliases/[alias]/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/banks/%5BbankId%5D/aliases/%5Balias%5D/route.ts) | +3/-0 | ContextDB 模式拒绝改名/删除原生 Bank alias，避免出现第二套访问地址。 | 必要封堵；数行保护 |
| [hindsight-control-plane/src/app/api/banks/[bankId]/aliases/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/banks/%5BbankId%5D/aliases/route.ts) | +2/-0 | 拒绝原生 alias 创建；读接口继续复用。 | 必要封堵；数行保护 |
| [hindsight-control-plane/src/app/api/banks/[bankId]/clone/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/banks/%5BbankId%5D/clone/route.ts) | +2/-0 | 拒绝通过原生 UI 代理克隆 Bank，防止绕开工作空间映射与授权。 | 必要封堵；数行保护 |
| [hindsight-control-plane/src/app/api/banks/[bankId]/import/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/banks/%5BbankId%5D/import/route.ts) | +2/-0 | 拒绝原生导入入口绕过工作空间生命周期。 | 必要封堵；数行保护 |
| [hindsight-control-plane/src/app/api/banks/[bankId]/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/banks/%5BbankId%5D/route.ts) | +5/-0 | 阻断原生 PUT/DELETE 及名称修改，避免管理映射与实际 Bank 脱节。 | 必要封堵；数行保护 |
| [hindsight-control-plane/src/app/api/banks/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/banks/route.ts) | +2/-0 | 阻断原生 POST 创建 Bank；空间统一走管理接口，列表继续复用。 | 必要封堵；数行保护 |
| [hindsight-control-plane/src/app/api/contextdb/[...path]/route.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/api/contextdb/%5B...path%5D/route.ts) | +167/-0 | 新增固定上游管理代理：白名单路由/字段、同源/会话、条件头与秘密过滤；后台 Admin Key 不交给浏览器。 | 必要；与后端的字段/头校验有重复 |
| [hindsight-control-plane/src/app/globals.css](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/app/globals.css) | +4/-7 | 定义本地系统字体栈，配合 layout 移除远端字体下载。 | 独立构建改进；不是权限逻辑 |
| [hindsight-control-plane/src/components/bank-config-view.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/bank-config-view.tsx) | +4/-1 | ContextDB 模式隐藏 Bank alias 配置行，前端与后端限制一致。 | 必要 UI 边界 |
| [hindsight-control-plane/src/components/bank-selector.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/bank-selector.tsx) | +100/-38 | 空间切换及用户管理入口、状态/操作限制；保留原生模式显示。 | 必要 UI 适配 |
| [hindsight-control-plane/src/components/banks-overview.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/banks-overview.tsx) | +10/-0 | ContextDB 模式切换工作空间管理组件；原生列表另加删除中禁选保护。 | 组件切换必要；原生删除禁选可独立 |
| [hindsight-control-plane/src/components/contextdb-users-view.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/contextdb-users-view.tsx) | +915/-0 | 成员列表、创建/修改/删除，Key列表/签发/撤销/授权，首次明文展示和冲突处理。 | 必要主体；915 行，需检查组件与状态重复 |
| [hindsight-control-plane/src/components/contextdb-workspaces-view.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/contextdb-workspaces-view.tsx) | +432/-0 | 空间列表、创建/删除、异步进度自动刷新、幂等及失败恢复。 | 必要主体；432 行 |
| [hindsight-control-plane/src/i18n/contextdb-messages.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/i18n/contextdb-messages.ts) | +47/-0 | 只替换 UI 文案中的 Bank/记忆库为 workspace/工作空间，保留 bank_id 等协议标识及 ICU 参数。 | 表达必要；全局字符串改写值得收敛 |
| [hindsight-control-plane/src/i18n/request.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/i18n/request.ts) | +6/-1 | 在服务端加载语言包时按模式应用工作空间称谓。 | 配套接入 |
| [hindsight-control-plane/src/instrumentation.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/instrumentation.ts) | +4/-0 | UI 启动等待 API 并核对后台 Admin 身份，防止用不匹配业务 Key启动。 | 部署与安全配套 |
| [hindsight-control-plane/src/lib/contextdb-api.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb-api.ts) | +354/-0 | 浏览器端管理请求、错误处理、分页、ETag及异步操作恢复，统一 UI 请求行为。 | 必要；与页面状态/代理规则应避免重复 |
| [hindsight-control-plane/src/lib/contextdb-mode.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb-mode.tsx) | +16/-0 | React Context下发是否启用ContextDB，客户端不读取秘密环境。 | 必要模式隔离 |
| [hindsight-control-plane/src/lib/contextdb.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb.ts) | +170/-0 | UI服务端模式/配置校验、同源检查、后台Admin验证、固定URL/请求头、原生生命周期拒绝。 | 必要安全核心 |
| [hindsight-control-plane/src/lib/i18n/api-errors.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/i18n/api-errors.ts) | +5/-1 | 错误文案也应用 workspace 称谓，避免页面与错误消息概念冲突。 | 配套；可与文案策略一起收敛 |
| [hindsight-control-plane/src/middleware.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/middleware.ts) | +54/-7 | ContextDB 模式覆盖已有UI/API入口的登录、后台身份、同源和运行时目标约束；防止客户端覆写后台目标。 | 必要；与代理重复认证需评估成本 |

#### 4. 测试与测试支撑

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-api-slim/tests/test_database_log_redaction.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/tests/test_database_log_redaction.py) | +23/-0 | 核对数据库URL的用户名/密码、query及fragment不会写入日志。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-api-slim/tests/test_dotenv_loading.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/tests/test_dotenv_loading.py) | +10/-31 | 隔离环境中的dotenv禁用开关，并新增托管注入不被覆盖测试；同时删掉原生server导入早于信号量初始化的测试，覆盖不等价，应恢复原测试。 | 应恢复被删原生用例，同时保留新增用例 |
| [hindsight-api-slim/tests/test_worker_execution_scope.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-api-slim/tests/test_worker_execution_scope.py) | +214/-0 | 原生无扩展/自定义执行域下的Worker成功、拒绝、失败、延期、状态写入范围。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/components/contextdb-native-entrypoints.test.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/contextdb-native-entrypoints.test.tsx) | +148/-0 | 原生Bank/alias/导入/克隆入口在ContextDB模式被限制，原生模式不误禁。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/components/contextdb-users-view.test.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/contextdb-users-view.test.tsx) | +484/-0 | 用户/Key管理UI、名称唯一、授权、一次性秘密、撤销及并发冲突。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/components/contextdb-workspaces-view.test.tsx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/components/contextdb-workspaces-view.test.tsx) | +235/-0 | 创建/删除空间、自动轮询、状态及未知结果恢复的UI行为。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/i18n/contextdb-messages.test.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/i18n/contextdb-messages.test.ts) | +62/-0 | 工作空间称谓替换不破坏ICU变量、协议标识或原生模式。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/lib/contextdb-boundaries.test.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb-boundaries.test.ts) | +196/-0 | 管理代理固定目标、路径/字段/条件头白名单及敏感字段过滤。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/lib/contextdb-operation-recovery.test.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb-operation-recovery.test.ts) | +235/-0 | 页面刷新/网络不确定后恢复操作，不重复危险写入。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/lib/contextdb-workspaces.test.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb-workspaces.test.ts) | +77/-0 | 空间生命周期客户端的请求ID、完成轮询和未知结果幂等重试，不走原生Bank创建接口。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/src/lib/contextdb.test.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/lib/contextdb.test.ts) | +488/-0 | UI管理员身份、登录、同源、服务端Key及配置边界。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-control-plane/vitest.config.ts](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/vitest.config.ts) | +1/-1 | Vitest的include增加src/**/*.test.ts和src/**/*.test.tsx，确保新增就近放置的UI测试确实被执行。 | 必要测试发现规则 |
| [hindsight-extensions/contextdb-service/tests/__init__.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/__init__.py) | +1/-0 | 将扩展测试目录作为Python包，支撑测试导入。 | 测试组织文件 |
| [hindsight-extensions/contextdb-service/tests/conftest.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/conftest.py) | +77/-0 | 自有隔离PG、扩展目录及元数据fixture，失败/结束清理，不使用客户库。 | 必要测试基础设施 |
| [hindsight-extensions/contextdb-service/tests/fixtures/development-metadata/development_v1.sql](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/fixtures/development-metadata/development_v1.sql) | +136/-0 | 构造旧开发期结构，证明首发初始化会拒绝接管，不是生产兼容DDL。 | 保留拒绝路径fixture；可缩减到最小复现结构 |
| [hindsight-extensions/contextdb-service/tests/fixtures/development-metadata/development_v2.sql](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/fixtures/development-metadata/development_v2.sql) | +228/-0 | 构造旧开发期结构，证明首发初始化会拒绝接管，不是生产兼容DDL。 | 保留拒绝路径fixture；可缩减到最小复现结构 |
| [hindsight-extensions/contextdb-service/tests/test_admission.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_admission.py) | +524/-0 | 跨连接排空竞争、当前MCP目标和撤销重验、删除阻断新请求。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_authorization_models.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_authorization_models.py) | +53/-0 | 创建默认读写，修改不隐式扩大权限；拒绝空/旧/歧义输入。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_bank_generation_cache.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_bank_generation_cache.py) | +176/-0 | 同名新空间不复用旧配置缓存；代次缓存有界且失败后可重试。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_bootstrap_deployment.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_bootstrap_deployment.py) | +172/-0 | 离线重复初始化、秘密私密/原子持久化、丢失秘密拒绝补生。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_build_artifacts.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_build_artifacts.py) | +40/-0 | 错配、变化或失败UI构建不得生成可用指纹。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_combined_lifecycle.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_combined_lifecycle.py) | +52/-0 | 合并进程收到停止或同伴失败时整体退出，不留孤儿进程。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_credential_repr.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_credential_repr.py) | +51/-0 | repr不泄露明文Key，但创建成功仍按合同首次返回。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_customer_pg_boundary.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_customer_pg_boundary.py) | +260/-0 | 真实社区PG角色ACL、客户自有schema、超级用户不受隔离的反例；不声称云特权用户已验证。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_deployment_contract.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_deployment_contract.py) | +388/-0 | 执行真实渲染边界，特殊字符秘密不被shell执行、当前RDS模板及非法输入拒绝。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_detached_admission.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_detached_admission.py) | +105/-0 | MCP响应取消后，分离工具任务必须取消/排空才释放保护。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_diagnostics.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_diagnostics.py) | +171/-0 | REST/MCP诊断投影与合成敏感哨兵，避免泄露。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_durable_admission.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_durable_admission.py) | +115/-0 | 不确定写入保留持久屏障，不能凭会话丢失或TTL认定安全。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_expired_lifecycle.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_expired_lifecycle.py) | +144/-0 | 过期租约不能续租、完成、失败或在锁等待后重新获得旧权限。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_extensions.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_extensions.py) | +428/-0 | 真实元数据下原生Tenant/Validator钩子、读写及内部任务权限。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_http.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_http.py) | +305/-0 | 全部管理路由认证、参数/错误、Key和空间合同及ETag。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_lifecycle_metadata.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_lifecycle_metadata.py) | +450/-0 | 生命周期领取/租约/CAS/重试的PG并发，不把元数据测试当原生迁移验收。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_mcp_fault_reporting.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_mcp_fault_reporting.py) | +181/-0 | 未知工具故障通知扩展，普通权限拒绝不留下错误屏障。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_metadata_upgrade.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_metadata_upgrade.py) | +269/-0 | 首发建表/注释/约束及不兼容开发结构拒绝；文件名虽叫upgrade，并不提供旧库升级。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_native_deployment_material.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_native_deployment_material.py) | +80/-0 | 原生渲染器独立运行、基础全文、秘密保留及禁止覆盖。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_openapi_contract.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_openapi_contract.py) | +73/-0 | 检查3111行管理机器合同与真实路由生成结果一致。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_pgroonga_preflight.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_pgroonga_preflight.py) | +74/-0 | 检测预检中PGroonga变参签名/TokenBigram；本期RDS不交付PGroonga，属额外诊断分支测试。 | 随非首版预检功能独立评估 |
| [hindsight-extensions/contextdb-service/tests/test_protocol_fault_admission.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_protocol_fault_admission.py) | +129/-0 | HTTP/MCP把故障包装成正常协议返回时仍保留未知执行屏障。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_query_efficiency.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_query_efficiency.py) | +143/-0 | 目标认证只查相关授权，当前操作复用身份，千条授权有界SQL。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_readable_workspaces.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_readable_workspaces.py) | +269/-0 | 可读bank/schema规范、并发占名、同名重建和条件保护。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_release_hardening.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_release_hardening.py) | +263/-0 | 统一管理员认证、pepper一致性、系统管理员保护和成员名唯一。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_repository.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_repository.py) | +133/-0 | 元数据幂等、Key作为授权主体、普通用户无管理权。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_resource_cleanup.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_resource_cleanup.py) | +25/-0 | 元数据初始化失败时关闭已创建连接池。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_security.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_security.py) | +53/-0 | 随机Key、pepper绑定摘要、统一格式解析及离线校验和非运行认证。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_tenant_admin_v2.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_tenant_admin_v2.py) | +354/-0 | 当前首发实例管理员/Key ACL、权限即时变化与删用户；v2只是旧命名，应改名而非当兼容实现。 | 保留语义，清理开发期命名 |
| [hindsight-extensions/contextdb-service/tests/test_webhook_boundary.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_webhook_boundary.py) | +97/-0 | 拒绝首版未纳入代次保护的Webhook/正文诊断写入。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-extensions/contextdb-service/tests/test_worker_execution_admission.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/tests/test_worker_execution_admission.py) | +194/-0 | 任务取消不等于写入结束；旧执行者/最终状态不得进入后继schema。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/server_extensions/contextdb_cancellation_probe.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/server_extensions/contextdb_cancellation_probe.py) | +38/-0 | 仅测试故障注入钩子，挂起/取消实际工具以检验排空竞态。 | 只测试加载，不是产品插件 |
| [hindsight-system-tests/tests/test_100_contextdb_service.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_100_contextdb_service.py) | +385/-0 | 真实API/SDK与Worker：动态Key、共享空间和跨schema隔离。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_101_contextdb_knowledge.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_101_contextdb_knowledge.py) | +202/-0 | 真实知识页、memory、知识CRUD/Worker刷新和关闭原生正文诊断。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_102_contextdb_fixture_cleanup.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_102_contextdb_fixture_cleanup.py) | +85/-0 | 测试fixture初始化失败时停止自有PG及子进程。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_103_contextdb_drain.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_103_contextdb_drain.py) | +374/-0 | 真实同步/异步retain、入队与删除排空竞态，覆盖两种执行模式。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_104_contextdb_mcp_identity.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_104_contextdb_mcp_identity.py) | +102/-0 | 同一MCP会话换Key/换空间，不继承初始化身份。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_105_contextdb_knowledge_scope.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_105_contextdb_knowledge_scope.py) | +101/-0 | MCP知识接口同样使用当前消息的读写/空间权限。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_106_contextdb_default_template.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_106_contextdb_default_template.py) | +55/-0 | 空间初建时默认模型刷新任务可入队，不与激活流程死锁。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_107_contextdb_default_compatibility.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_107_contextdb_default_compatibility.py) | +64/-0 | 未加载扩展的原生匿名REST/Worker/MCP仍工作。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_108_contextdb_mcp_cancellation.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_108_contextdb_mcp_cancellation.py) | +240/-0 | 真实MCP断连/保护丢失，后台分离工具任务停止。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_109_contextdb_fault_retention.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_109_contextdb_fault_retention.py) | +91/-0 | 原生REST/MCP错误封装不抹掉未知写入屏障。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_110_contextdb_tenant_admin.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_110_contextdb_tenant_admin.py) | +282/-0 | 同一Key跨多个授权schema，旧MCP会话也受即时权限变更。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_111_contextdb_business_keys.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_111_contextdb_business_keys.py) | +173/-0 | all业务Key覆盖未来空间但不变管理员；撤销一把不影响同用户其他Key。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_112_contextdb_ui_management.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_112_contextdb_ui_management.py) | +254/-0 | 生产UI产物对真实API完成空间、用户、Key及原生业务流程。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_113_contextdb_optimized_authorization.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_113_contextdb_optimized_authorization.py) | +161/-0 | 同一Key对不同空间读写不同，编辑权限后REST/MCP一致。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_114_contextdb_diagnostic_credentials.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_114_contextdb_diagnostic_credentials.py) | +128/-0 | 原生任务中的合成诊断凭据仅管理员可见。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_115_contextdb_workspace_recreation.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_115_contextdb_workspace_recreation.py) | +110/-0 | 真实删除及同名重建：旧数据和selected授权不继承。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_116_contextdb_cancelled_worker_drain.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_116_contextdb_cancelled_worker_drain.py) | +93/-0 | 真实已取消但仍执行的Worker阻止DROP与名称复用。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_117_contextdb_generation_cache.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_117_contextdb_generation_cache.py) | +86/-0 | API/Worker进程缓存不将旧空间mission/config带到同名新空间。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |
| [hindsight-system-tests/tests/test_118_contextdb_append_contention.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/tests/test_118_contextdb_append_contention.py) | +79/-0 | 适配v1.0.0并发Append冲突，不丢内容且正常结束后可删除。 | 保留覆盖；跨层测试应区分断言，避免机械重复 |

#### 5. UI 语言资源

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-control-plane/src/messages/de.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/de.json) | +93/-0 | 在de语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | UI文案必要；6份非英语有90/91条与英文相同，可由fallback合并 |
| [hindsight-control-plane/src/messages/en.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/en.json) | +93/-0 | 在en语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | 保留对应语言文案，核对共享fallback策略 |
| [hindsight-control-plane/src/messages/es.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/es.json) | +93/-0 | 在es语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | UI文案必要；6份非英语有90/91条与英文相同，可由fallback合并 |
| [hindsight-control-plane/src/messages/fr.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/fr.json) | +93/-0 | 在fr语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | UI文案必要；6份非英语有90/91条与英文相同，可由fallback合并 |
| [hindsight-control-plane/src/messages/ja.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/ja.json) | +93/-0 | 在ja语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | UI文案必要；6份非英语有90/91条与英文相同，可由fallback合并 |
| [hindsight-control-plane/src/messages/ko.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/ko.json) | +93/-0 | 在ko语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | UI文案必要；6份非英语有90/91条与英文相同，可由fallback合并 |
| [hindsight-control-plane/src/messages/pt.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/pt.json) | +93/-0 | 在pt语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | UI文案必要；6份非英语有90/91条与英文相同，可由fallback合并 |
| [hindsight-control-plane/src/messages/yue-Hant.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/yue-Hant.json) | +93/-0 | 在yue-Hant语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | 保留对应语言文案，核对共享fallback策略 |
| [hindsight-control-plane/src/messages/zh-CN.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/zh-CN.json) | +93/-0 | 在zh-CN语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | 保留对应语言文案，核对共享fallback策略 |
| [hindsight-control-plane/src/messages/zh-TW.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-control-plane/src/messages/zh-TW.json) | +93/-0 | 在zh-TW语言包增加相同contextDB键结构的93行用户/Key/空间文案，避免next-intl缺键。 | 保留对应语言文案，核对共享fallback策略 |

#### 6. 部署与工具

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-extensions/contextdb-service/deployment/Dockerfile](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/Dockerfile) | +61/-0 | 多阶段构建API+UI自研镜像、非root运行；安装扩展并打包匹配UI产物。 | 部署交付；可核对不必要源码/测试进入镜像 |
| [hindsight-extensions/contextdb-service/deployment/Dockerfile.dockerignore](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/Dockerfile.dockerignore) | +18/-0 | 限制构建上下文，排除运行目录、环境/缓存等非交付内容。 | 必要构建边界 |
| [hindsight-extensions/contextdb-service/deployment/compose.yaml](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/compose.yaml) | +47/-0 | 一个长期容器及一次性初始化命令；秘密只读挂载、缓存tmpfs、健康检查、日志轮转与退出宽限。 | 首版部署必要 |
| [hindsight-extensions/contextdb-service/deployment/intent.example.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/intent.example.json) | +17/-0 | 自研管控输入模板：PG/MaaS/UI秘密路径、实例归属、端口、拓扑。 | 部署合同模板 |
| [hindsight-extensions/contextdb-service/deployment/native-v1.0.0/compose.yaml](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/native-v1.0.0/compose.yaml) | +36/-0 | 官方原生镜像的单容器编排，不加载ContextDB扩展。 | 按用户要求的原生过渡联调材料；非特性运行必需 |
| [hindsight-extensions/contextdb-service/deployment/native-v1.0.0/intent.example.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/native-v1.0.0/intent.example.json) | +12/-0 | 原生过渡部署输入模板，与自研认证/初始化分开。 | 可独立交付 |
| [hindsight-extensions/contextdb-service/deployment/native-v1.0.0/render.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/native-v1.0.0/render.py) | +166/-0 | 不依赖自研Python包渲染官方原生配置，校验秘密、端口/模型，保留PG SSL输入。 | 可独立交付；与自研渲染有重复 |
| [hindsight-extensions/contextdb-service/deployment/native-v1.0.0/run.sh](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/native-v1.0.0/run.sh) | +25/-0 | 启动/停止/检查原生单容器，封装官方入口。 | 可独立交付 |
| [hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql) | +107/-0 | 客户SQL角色与服务schema的ACL边界示例，检查危险角色；明确真正superuser/root无法隔离。 | 示例验证材料；不由服务自动执行 |
| [hindsight-extensions/contextdb-service/deployment/prepare-pg.sql](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/deployment/prepare-pg.sql) | +20/-0 | 管控管理员预建服务角色、专库和vector/pg_trgm/btree_gin，拒绝意外复用已存在对象。 | 部署必要，Hindsight不负责CREATE DATABASE |
| [hindsight-extensions/contextdb-service/scripts/generate_openapi.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/scripts/generate_openapi.py) | +58/-0 | 从扩展路由生成/校验管理OpenAPI，不手工维护另一份接口模型。 | 必要合同工具 |
| [hindsight-extensions/contextdb-service/scripts/node-agent.sh](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/scripts/node-agent.sh) | +8/-0 | 薄封装调用现有部署CLI，给节点Agent统一命令入口；不是新增常驻Agent。 | 部署便利，8行 |
| [hindsight-extensions/contextdb-service/scripts/run_combined.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/scripts/run_combined.py) | +61/-0 | 监督API和UI；信号转发，任一退出停止另一进程，超时后清理进程组。 | 单容器交付必要 |
| [hindsight-extensions/contextdb-service/scripts/service.sh](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/scripts/service.sh) | +90/-0 | 封装init/preflight/build/API/UI/all等操作，加载稳定配置并禁用.env意外覆盖。 | 部署必要；首版不需要的分离启动入口可收敛 |

#### 7. 配置、文档与其他支撑

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [.env.example](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/.env.example) | +6/-0 | 说明托管使用标准 PYTHON_DOTENV_DISABLED，并新增 ContextDB UI 开关示例。 | 配套配置 |
| [.github/workflows/test.yml](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/.github/workflows/test.yml) | +39/-0 | 新增扩展路径触发、扩展 pytest/ruff/ty任务，并纳入 CI 汇总与系统回归触发。 | 必要质量门；属于 CI，不是产品运行 |
| [hindsight-docs/docs/developer/configuration.mdx](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-docs/docs/developer/configuration.mdx) | +4/-0 | 增加 HINDSIGHT_API_ENV_FILE 的说明，但该提交没有对应实现；实际改用标准 PYTHON_DOTENV_DISABLED。 | 应修正：过期参数残留 |
| [hindsight-embed/hindsight_embed/env.example](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-embed/hindsight_embed/env.example) | +6/-0 | 同步仓库根 .env.example 中的托管开关和 UI 模式示例。 | 生成/镜像示例配套；不代表改了嵌入式引擎 |
| [hindsight-extensions/README.md](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/README.md) | +1/-0 | 在扩展索引增加 ContextDB 包入口。 | 必要导航 |
| [hindsight-extensions/contextdb-service/README.md](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/README.md) | +9/-0 | 扩展功能概述、代码/脚本/机器合同路径及资料仓入口。 | 必要入口 |
| [hindsight-extensions/contextdb-service/docs/README.md](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/docs/README.md) | +23/-0 | 设计、API、部署、运维的资料仓链接；没有打包历史过程文档。 | 必要导航；c60 时链接是整理前路径 |
| [hindsight-extensions/contextdb-service/pyproject.toml](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/pyproject.toml) | +24/-0 | 声明独立可选扩展、依赖原生API及新版dotenv；测试依赖和部分版本约束。 | 必要打包；硬编码约束与系统测试重复 |
| [hindsight-system-tests/hindsight_system_tests/server.py](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/hindsight_system_tests/server.py) | +24/-4 | 测试启动器可使用隔离数据库/解释器，并在启动失败时清理进程和描述符。 | 测试基础设施；不改变生产启动器 |
| [hindsight-system-tests/pyproject.toml](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/pyproject.toml) | +12/-0 | 系统测试新增服务端 embedded-db 依赖及版本约束，支持从同一解释器启动自研实例。 | 有测试理由；依赖面可改为可选分组 |
| [skills/hindsight-docs/references/developer/configuration.md](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/skills/hindsight-docs/references/developer/configuration.md) | +4/-0 | 文档 skill 的配置参考同步了 HINDSIGHT_API_ENV_FILE 旧说明。 | 应与源配置文档一起修正 |

#### 8. 生成的接口定义

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-extensions/contextdb-service/schemas/contextdb-control-plane.openapi.yaml](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-extensions/contextdb-service/schemas/contextdb-control-plane.openapi.yaml) | +3111/-0 | 由14个管理操作生成3111行机器合同，含模型、错误与安全定义。 | 保留生成结果；不能按手写业务代码计算 |
| [skills/hindsight-docs/references/openapi.json](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/skills/hindsight-docs/references/openapi.json) | +1/-1 | 仅 info.version 从0.10.3校准为1.0.0；paths/components均相同。 | 生成元信息；不是新增原生 REST 接口 |

#### 9. 系统测试锁文件

| 文件（相对代码仓） | +/- | 修改含义与原因 | 保留/简化判断 |
| --- | ---: | --- | --- |
| [hindsight-system-tests/uv.lock](https://github.com/ZhuQingping/hindsight/blob/c60d409cfb4f879051a4fe258bbcaff8872df09e/hindsight-system-tests/uv.lock) | +4948/-331 | 系统测试依赖图从38包变209包，新增171；FastAPI/Pydantic等受约束变化，本地SDK版本校准。 | 测试锁；增长应通过可选依赖/复用环境收敛 |

### 核对方式与验收范围

依据本地Git对象的stat/numstat、逐类diff、运行入口与测试断言、两份锁文件的解析结果，以及OpenAPI JSON结构比较。固定native父提交为39c65ffe2f140d0c84cee58566cad8900c5b9908。此处67项包含fixture、测试配置和故障探针，不等于67个test_文件；14项部署工具也不全是新服务进程。

历史439项扩展等回归结果见[验证摘要](../testing/contextdb-validation-summary.md)。它们证明当时执行的测试通过，不证明新增代码全都必要，也不能替代本轮识别的原生用例恢复。本文列出的文件目的已全覆盖，163项无遗漏；未声称逐行安全审计完成或TODO已经落地。

本轮建议：**需要修订（REVISE）**。功能安全接入有明确理由，但过期参数、原生用例覆盖减少、重复文案和首版外部署分支应收敛后再作为最终专家评审稿。


<a id="extension-reevaluation"></a>

## 原生扩展机制复评：保留每空间独立 schema

2026-10-19，按用户补充约束重新验证：每个工作空间独立schema；首发只建新库，不提供旧开发实例/旧配置/旧结构的迁移兼容；需要保留当前正式版本将来升级的路径。本节保留复评时的机制判断；已落地部分见[落实结果](#extension-implementation)，尚未替代的生命周期保护继续保留。

### 结论

**动态用户、多Key、多空间读写授权不需要改Hindsight记忆内核。** 保持独立schema，原生Tenant、Validator、HTTP，加外围ASGI入口已完成这组最小验证。跨schema目录和多空间MCP需要适配；可放到外围聚合及原生MCPExtension，不能据此要求修改原生MCP身份上下文。

**当前启用多空间MCP时，保留MCPExtension的职责是合理的。** 它通过原生register_tools入口安装FastMCP中间件，没有另造记忆工具。职责应收敛到当前消息目标Bank、目录及权限/生命周期接入；固定/mcp/{bank_id}/连接在本次测试中不配置MCPExtension也能正确路由，但这不覆盖同一根MCP会话切换多个schema。

**安全物理删除仍有真实缺口。** Worker的processing=0及on_retain_complete都不能证明完整执行和最终状态写入已结束；不能因为基础权限可纯扩展，就删除当前在途/后台任务屏障。保留通用执行生命周期接口候选，重新设计最小接入，避免在内核里混入具体产品恢复规则。

商业版支持相近功能只能作为设计线索。闭源实现不可见，本次没有声称商业版完全零内核差异；本节结论来自未修改的固定开源版本实测。

### 基线、方法和结果

- 原生基线：39c65ffe2f140d0c84cee58566cad8900c5b9908（v1.0.0的实际commit，不能把annotated tag对象ID当commit）。通过git archive导出，1006个原始文件前后SHA-256全部一致。
- 测试环境：复用已锁定CPython3.11依赖，独立临时pg0数据库，真实原生REST、MCP及内置Worker，模型使用确定性HTTP桩；不是真实MaaS、ECS/RDS或效果压测。
- 两组配置：A=Tenant+Validator+HTTP+外层ASGI；B=A+MCPExtension+跨schema目录聚合。两组都不修改原生源码、不替换引擎方法、不使用monkey patch。最终集成读取FastMCP公开的当前Request及原生RequestContext，不导入原生私有ContextVar；仅只读诊断探针读取Worker协程帧以证明它仍存活。
- **22个检查通过，17.49秒，2条上游websockets弃用警告。** 包括预期复现原生能力边界的对照检查，不代表A组的多空间MCP和全局列表也都正确。
- 另将被替换的原生test_server_entrypoint_loads_dotenv_before_engine_semaphores函数原样提取到隔离环境执行：1项通过。因此应恢复原用例，追加托管测试，不能用新测试替代原覆盖。

| 验证组（每组在A/B各运行一次） | 观察 | 结论 |
| --- | --- | --- |
| 动态用户及同用户多Key | 管理HTTP写入PG后立即可用，Key不同 | 原生HTTP/Tenant足够，不需内核用户服务 |
| REST逐空间读写、实际落库、异步任务 | 同Key在alpha读写、beta只读，gamma拒绝；Worker完成，记忆只落各自schema | Tenant+Validator负责认证/授权，ASGI入口负责取得URL中的Bank |
| 即时改授权、停用、吊销、兄弟Key | 旧授权立即拒绝；吊销一把Key后同用户其他Key仍可用 | 动态认证不需要静态插件热更新或内核改动 |
| 根MCP会话连续访问两个空间 | A仅默认schema正确，B两空间均正确；B读写alpha、拒写beta | MCPExtension有明确的跨schema工具路由职责；不需为此新增原生身份恢复中间件 |
| 跨schema Bank目录 | A只列一个schema，B通过公开MemoryEngine.list_banks聚合两空间 | BankListScope是单schema过滤能力，不等于全局目录；聚合可以放外围 |
| 同一MCP会话切换Key | A/B均能读新Key授权空间、拒绝旧空间 | Tenant从FastMCP公开的本次Request取Key，再走原生认证；可避免依赖初始化ContextVars或修改原生api/mcp.py |
| on_retain_complete观察 | 回调触发时仍有1个retain任务processing，之后才写终态 | 结果钩子不包住Worker最终状态写入 |
| 取消执行中的Worker | 模型调用保持挂起；取消全部processing行后，processing=0，仍有1个原生Worker协程未退出 | 任务行cancelled不等于执行结束；不能靠状态轮询直接DROP/复用schema |
| Recall/Retain/Reflect | 原生SDK、MCP调用真实算法路径，读Key可Reflect，写权限由Validator控制 | 核心记忆算法不需要重写 |
| 并发REST跨空间 | 同Key交错8次alpha/beta召回，结果不混空间 | 本次ASGI/ContextVar目标传递通过并发基础验证 |
| 固定Bank的MCP URL | A/B都可从/mcp/beta/召回beta数据 | 固定Bank连接的基础路由不天然需要MCPExtension；当前多空间根会话能力仍需要适配 |

机器结果见[本轮验证摘要JSON](../testing/evidence/contextdb-extension-reevaluation-20261019.json)。原型、校验清单、日志、JUnit及复验说明保存在本机`.local/artifacts/contextdb-extension-reevaluation-20261019/`，不混入产品部署包。原型使用简化管理模型和合成Key，只验证机制，不是当前产品管理API或密码学实现的替代代码。

### 原生扩展的职责应如何划分

```text
REST原生URL
  → 外围ASGI入口提取目标bank_id
  → Tenant查询动态身份并选择该空间schema
  → 原生引擎调用Validator检查目标Bank和读写权限
  → 原生Retain/Recall/Reflect、原生任务系统

根MCP工具调用
  → MCPExtension从实际工具参数确定目标Bank
  → Tenant读取FastMCP本次Request中的Key，走原生认证路径
  → Validator做同一份权限校验
  → 原生工具和算法
```

关键条件：使用Tenant动态认证模式，不开启旧的共享HINDSIGHT_API_MCP_AUTH_TOKEN旁路。该旧模式会令原生引擎跳过Tenant重认证；首版无需为不存在的旧配置保留这个分支，应显式拒绝冲突设置。原生CLI保持不动，外围启动器可使用uvicorn自定义ASGI入口包住原生server:app；正常lifespan和内置Worker继续由原生应用管理。

跨schema目录通过公开引擎接口逐空间查询的正确性已验证，但排序、搜索、分页和大量空间性能尚未做完整替代验收，不能简单用元数据名字列表冒充原生Bank目录。原生操作Validator已有validate_bank_read/write/create、bank_list_scope、filter_mcp_tools，不必再为这些能力新增核心权限钩子。

### 10项原生运行文件的处理建议

| 当前改动 | 复评判断 | 建议 |
| --- | --- | --- |
| api/__init__.py | 为扩展中间件覆盖REST/MCP而改安装次序；外层ASGI已可包住两种传输 | 迁移到外围启动入口，完成现有排空/断流回归后撤销该项原生改动 |
| api/http.py | 新增扩展middleware安装/延后参数；不是管理CRUD必需 | 与外层ASGI一起收敛，无须为本产品增加安装参数 |
| extensions/http.py | 新增get_middleware；公开HttpExtension已有管理路由和生命周期 | 管理接口继续用原有HttpExtension，传输保护放外层ASGI，可撤销新增钩子 |
| api/mcp.py | 当前消息身份恢复已有纯扩展替代证明 | 身份恢复部分移回Tenant/MCPExtension；不能连带宣称未知故障、取消后的保护也已替代 |
| mcp_tools.py | 新failure_reporter不是基础认证/选schema必需 | 先验证MCP中间件对原生错误返回、异常、取消的保守处理；未完成前，不直接删故障反馈部分。异常身份分类可单独评估通用修复 |
| extensions/tenant.py | 原生没有覆盖“任务入队整个事务”“Worker执行加最终写入”的公开保护域 | 保留两个通用生命周期接口作为候选，不能用一次validate回调或任务状态替代；不承诺当前签名就是最终最小方案 |
| engine/memory_engine.py | 多状态列表是便利能力；内部入队与Append失败结束证明是不同问题 | 不因目录/权限保留此改动。多状态查询优先移外围；入队生命周期保留候选；PG Append专门分支应收敛到有明确结果语义的通用结束通知，不先删除保护 |
| worker/poller.py | 真实缺少包含最终/延期状态写入的执行边界 | 保留通用Worker执行保护接入候选；简化具体异常分类和quiescent返回传播，完成故障回归后确定最小改法 |
| utils.py | 数据库URL日志脱敏是通用安全修复 | 独立说明/独立上游补丁，不作为工作空间权限特性必须改内核的理由 |
| worker/main.py | 启动日志脱敏和独立Worker退出清理；首版合并部署的原生HTTP lifespan已调用Tenant shutdown | 日志随通用安全修复处理；独立Worker清理不作为首版必选改动，若未来交付分离模式再按生命周期合同处理 |

**不再认定10项都必须保留。** 基础认证、权限、REST/MCP选空间及目录已经有外围替代证据；真正需要聚焦的原生缺口是内部任务提交/完整执行生命周期及可靠故障结束语义。目前不能宣布最终只需改3个文件，也不能宣布已证明零内核改动：完整删除安全替代尚未完成。

### 首发与未来升级

1. 首发只初始化新建专用库及版本1元数据。不实现旧开发库迁移、旧Key格式转换、旧环境变量别名或按旧结构猜测修复。
2. 现有migrations.py主体是首发初始化、重复初始化核对及结构/归属拒绝，不是旧库迁移兼容。保留这些安全校验；不因文件名migrate或test_metadata_upgrade就全删。
3. 两份development_v1/v2完整SQL样本仅用于验证拒绝旧结构。可缩为最小不支持结构/格式标记测试；保留拒绝行为，不维护不存在的升级链。test_tenant_admin_v2实际验证当前ACL，应改名，不删覆盖。
4. 管理metadata_version从1开始；未来已发布结构升级采用有序迁移，不预实现虚构版本。原生业务表继续用原生Alembic；管理表迁移由扩展负责，不能维护另一套原生表DDL。
5. 未来升级按停写、排空任务、备份数据库和持久秘密、停止全部旧执行者、受控迁移、同版重启及逐空间验收进行。数据库迁移失败不靠重启旧镜像自动回滚，应按经过验证的恢复方案处理。这个流程与本期旧开发版本兼容是两回事。

### 尚未证明的边界与实施顺序

本次没有用原型执行完整物理DROP/同名重建、租约过期迁移线程、API/Worker失联、MCP断连后分离任务、未知异常/协议包装故障、全部原生工具/配置组合和全局目录排序分页验收。公开接口原型验证了基础能力，不能替代现有删除安全回归或生产加固。

先把当前的ASGI目标传递和MCP动态认证迁出新增原生hook，保持现有管理数据模型与对外接口，再迁移目录。迁移时至少跑现有test_admission、test_detached_admission、test_protocol_fault_admission、test_mcp_fault_reporting、test_worker_execution_admission，以及系统故事103/104/105/108/109/110/113/115/116/117/118。保护域与Append冲突结束证明尚未找到完整替代前继续保留，不能先删核心保护再补验证。

评审结论：**需要修订（REVISE）**。外围扩展的能力之前被低估；MCPExtension的多空间适配职责合理；现有10项原生改动并非全部必要，但Worker/内部提交生命周期缺口是真实的。下一步应按最小通用接入收敛实现，不能把本次验证原型当作已经完成的产品重构。


<a id="extension-implementation"></a>
## 历史：复评后的落实结果（9d51cac，已 amend 并推送供评审）

本节对应提交 `9d51cacde496baa628408e4b474f0f949220a90f`；前面的163项表仍描述固定的 c60d409 历史提交，不改写历史统计。当前相对原生净差异为147个文件，其中原生 Python 运行文件7个。

| 项目 | 本轮处理 |
| --- | --- |
| 三个原生 HTTP 接入文件 | 恢复原生；通过扩展自己的 ASGI factory 最后安装外层准入，复用原生应用/生命周期 |
| 原生 MCP 身份快照/恢复中间件 | 删除；Tenant 从当前公开 HTTP Request 读取 Key；原生未知故障反馈保留 |
| 原生 Python 运行文件 | 从10项缩为7项，净差异由+341/-44缩为+234/-43；不以文件数代替安全证明 |
| 原生模板与无效参数文档 | 原生两个 env 模板和两个配置说明文件恢复；扩展模板单独保留托管说明 |
| 被替换的 dotenv 回归 | 原样恢复原生断言，托管禁用用例继续保留 |
| UI 文案 | 十份原生语言包恢复；ContextDB 文案独立，未翻译项共享英文；缺键检查使用实际组合后的目录，原生语言包一致性检查不变 |
| Next 配置 | 恢复原生 next.config.ts；Docker COPY、制品指纹同步；已完成生产构建 |
| 旧开发期完整 DDL 样本 | 删除两份完整 SQL，改最小不支持结构，保留非破坏拒绝断言；测试改名为首发初始化/当前权限 |

### 暂时保留的原因

任务提交、Worker 最终/延期状态写入、MCP 错误封装、Append 并发失败都涉及“是否仍有旧执行者”。这些保护未获得完整替代证据，继续保留。多状态排空必须保持同一快照，不直接拆成两次查询。明确后续判定条件见[设计 TODO](contextdb-release-design.md#本轮实现收敛与-todo)。

原生镜像过渡材料已移至资料仓，原有三项测试随工具迁移，并配置独立CI；代码 amend 移除原位置的材料。依赖锁、PGroonga/独立 Worker 诊断、系统字体仍待划分交付/测试范围；本轮没有为压缩文件数删除已授权能力或改成静默跳过测试。日志脱敏作为通用安全修改继续保留。

### 验证记录

| 验证范围 | 结果 |
| --- | --- |
| 扩展全部测试（含管理 API、真实 PG、权限、排空、元数据及部署合同） | 440通过，1跳过 |
| 原生 MCP、Worker、dotenv及日志相关回归 | 506通过，4跳过 |
| UI 单元/组件、原生语言包及组合目录缺键检查 | 414通过 |
| 实际 API/MCP/Worker 权限、断流、删除重建、缓存及 Append 故事 | 52通过 |
| 生产 UI 对接真实 API、管理工作空间/用户/Key | 2通过 |
| 原生模式兼容、故障清理与诊断身份 | 5通过 |
| 嵌入式 env 模板检查 | 8通过 |
| 项目 lint、扩展 Ruff/类型检查、UI 生产构建与制品指纹 | 通过 |

跳过项未计入通过数。另一次680项原生广选运行已中断，不计为全套原生验收；上表为最终完成的针对性回归。死代码扫描已执行，仍有上游代码和既有 UI 导出的提示，不宣称零告警。

结果摘要见[本轮实现验证 JSON](../testing/evidence/contextdb-extension-implementation-20261019.json)。测试在本机临时 PG / API / Worker 和确定性模型桩上执行；不代表真实 MaaS 质量、RDS/ECS 性能或生产灾备验收。源代码已推送到 `contextdb/v1.0.0`，固定检视提交为 `9d51cacde496baa628408e4b474f0f949220a90f`。其他环境应检出该提交并使用同版扩展、API、UI和部署脚本；分支经过 amend，不应把旧提交的本地分叉误当作新增功能提交。


### 原生部署工具迁移

原代码目录 `hindsight-extensions/contextdb-service/deployment/native-v1.0.0/` 的四个文件已迁到资料仓 [tools/](../deployment/native-v1.0.0/tools/)。原生建库SQL随工具独立交付，自研版仍使用代码仓自己的SQL；原生指南不再引用自研代码仓的相邻文件。

原 `test_native_deployment_material.py` 的三项用例迁到 `tools/tests/`，资料仓新增独立CI，仅安装pytest，不安装Hindsight/ContextDB。迁移后验证：工具3项通过；自研扩展437项通过、1项跳过。Shell语法、Compose配置及Ruff检查通过；未启动容器或连接客户PG，亦未改动服务运行代码。

本轮未调整ContextDB系统测试依赖组织，也未声称原生全量测试或生产验收完成。上面的9d51cac统计和测试结果仍是该固定提交的历史记录。
