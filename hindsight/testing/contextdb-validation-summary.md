# ContextDB 验证摘要

> **最新本地代码（2026-10-22）：`9fb57bc04`，新增提交，父提交`003bbe032`，未推送。** 本轮复检425 Python／560 UI／75系统／484相关原生测试通过；Audit继续关闭。最新状态见文末“2026-10-22 提交前复检与本地新提交”，前文旧提交及“未提交”表述保留作历史记录。


> O01～O08最新方案与状态见[简化清单第16章](../design/contextdb-simplification-plan.md#o01-o08-current-status)。本摘要保留历史验收记录；新增O03/O04/O05方案未实施，O08明确暂不实施，历史测试不能视为新方案通过。

更新：2026-10-20。对象为 `contextdb/v1.0.0` 的完整特性：原 `ddf5c360001f1db46f925b1822803ac9bff1119e` 加四批优化、测试接线与UI简化，通过 amend 归为官方 v1.0.0（`39c65ffe`）之上的单一提交。验收源码树为 `ce1c7def06cf26d9450fcef34acbad4e47268e6f`，已推送为 `a05b80885883b36f879abdb2ce8a9c8f63b0922c`；代码提交正文固定资料快照 `370f8fa`。旧远程快照不能复现本轮新行为。

## O01真实浏览器补验与O02复核（2026-10-21，最新结果）

用户提供的[O01报告](/Users/zhuqingping/Documents/Codex/2026-10-21/pets-plugin-work-pets-openai-curated/outputs/o01-browser/report.md)已读取，与任务证据副本SHA256核对一致。真实Chrome、隔离PG/API及正式UI执行，59张截图；未改源码。**O01已执行，未全部通过**：新增N-P008（390页头溢出）、N-P009（关闭焦点不恢复）、N-P010（超长成员名提示不清楚）；复制反馈通过，但复制内容核对失败、归因未定。三项均待修复，不能沿用前轮独立复核ACCEPT将其关闭。完整复现与清理证据见[质量记录第11章](contextdb-quality-improvement-plan.md#11-o01-补验2026-10-21-真实-chrome)。下文历史“浏览器未执行”保留当时语境，以本节为当前状态。

O02追加最小复核：同一构建镜像在本机Colima（Ubuntu24.04 ARM）中独立运行cryptography50 RSA探针，默认SIGILL/132，临时诊断OPENSSL_armcap=0后通过。无需PG或ContextDB运行即可复现。默认init仍未通过；覆盖后已有完整冒烟通过，云上原样部署尚未验证。见质量记录第12章及`o02-recheck-20261021/results.json`。未改生产默认、依赖或服务。 **用户随后决定跳过本机后续O02验证，转其他开发环境；不是标记通过。** 原因、外部密码库探针及容器验收矩阵见质量记录12.1。

## 夜间质量复核（2026-10-21，独立分支，未提交）

基于c56c7ac17，在`contextdb/quality-20261021-004226`完成新增修复。完整清单、问题闭环、命令与本机证据见[夜间质量记录](contextdb-quality-improvement-plan.md)。下文360/505/67是上一轮，不是本轮计数。

| 本轮最终检查 | 结果 | 边界 |
| --- | --- | --- |
| 插件Python / 全UI / 完整系统 | 391 / 523（54文件） / 73通过，零跳过 | 真实PG/API，模型HTTP替身；包括双Worker |
| 原生相关8文件 / Key合同 | 121 / 1通过 | 非上游全部测试 |
| 生产UI独立2故事及门禁 | 通过，零跳过 | 已包含在73项，不重复累加；生产HTTP不等于浏览器视觉 |
| 正式构建、指纹、类型、lint、knip@5、diff-check | 通过 | 原生Python运行目录无变更 |
| 四项故意破坏保护 | 4/4被目标语义断言检出，控制组通过 | 安全抽样，不是全部变体证明 |
| 独立检视 | 权限/PG、UI/TS、测试有效性均接受 | 本轮必修项关闭，云环境/视觉仍待验 |
| Docker | 原样构建成功；默认ARM启动SIGILL失败；诊断覆盖后业务冒烟通过 | Linux ARM/Node24.22，cryptography50；生产默认未修改，详见N-P007 |
| 完整调用SQL | REST recall 2、MCP recall 6、tools/list 15次元数据语句 | 含遥测；授权1/10空间各3次，非吞吐测试，重复检查待分析 |

修复：空间创建关闭后迟到导航、用户创建损坏201错报成功、prompt preview配置越权、MCP元数据内部异常原文。补强真实初始化默认执行、撤权必须401、拒绝后数据/队列不变、真实原生提交故障恢复；简化User展开ID及无用权限转发。没有新增表、生产参数、原生运行钩子或测试框架。

当前缺口：O01已执行，3项UI待修复及复制内容待归因；默认ARM容器启动、目标x86/ECS/RDS、真实MaaS及生产负载/HA/备份恢复仍未验收。现有服务、用户数据库、源仓及RSIXDB未修改；代码与资料均未自动提交/推送。最终补丁、三份独立复核及测试日志位于任务工件目录。

## 本轮修复验收（2026-10-21，已amend为c56c7ac17，未推送）

以下结果对应S16～S25修复，已amend为`c56c7ac17ff438228d257be42072a12c7f72e7c5`，未推送；不属于旧a05b808。新增夜间质量任务单独记录在[任务清单](contextdb-quality-improvement-plan.md)，不能复用本节结果冒充该任务已执行。原生Python运行目录本轮无修改；实施前的Bank配置响应凭证投影及相关测试保留。生产8888/9999服务和用户数据库未变更，PG5432仅用于创建并销毁随机命名的任务自有部署测试库/角色。

| 范围 | 本轮结果 | 覆盖与边界 |
| --- | --- | --- |
| 插件Python全量 | **360通过，零跳过** | 真实隔离元数据PG；本次显式提供测试管理员URL，包含真实service.sh init、非超级用户新库、重复初始化及public无表 |
| 全部UI测试 | **505通过，54文件，零跳过** | 原生UI与插件测试共同运行；TZ=UTC。含secret保留/清除/复制竞态、读取失败、选择器分页搜索、locale、users空间导航反例 |
| ContextDB完整系统故事 | **67通过，零跳过** | 两Worker、原生SDK/REST/MCP、同步生命周期/重建、默认模板、知识/记忆、真实生产UI代理及权限。模型为确定性替身 |
| 生产UI双Worker独立门禁 | **2通过，零跳过** | 另行重跑112故事，现有JUnit完整性检查通过；已包含在67项范围内，不重复累加 |
| 新增chunk专项 | **4通过** | 两种文档ID×两Worker；SDK异步retain→等待完成→recall含chunks→list/get，三类合法Key、跨空间、匿名/无效/吊销及不存在 |
| 原生相关回归 | **121通过** | chunk codec、扩展上下文、透传、MCP/tenant扩展及schema模式等8文件；本轮未重跑原生全量或模型质量测试 |
| 跨语言Key合同 | **1通过** | 既有提取器、响应字段/required/nullable/enum合同 |
| 正式生产UI构建 | **通过** | 临时隔离源码和依赖克隆构建，Next TypeScript与standalone成功；manifest完整性及与当前源码指纹匹配 |
| 静态检查 | **通过** | 仓库lint hook、类型、diff-check、与CI一致的knip@5 files/dependencies阻断检查；advisory unused保留原生告警 |
| 独立检视 | **代码/自动化范围无阻塞项** | 后端、UI及测试完整性只读检视；导航误判、搜索/日期/public断言问题已补齐并复核 |

S16完整系统fixture不再预迁移public；全部故事完成后、停止自有进程前，明确断言public没有表。因此不是通过测试准备补建public依赖。public仍保留插件类型、函数等对象。没有删除当前用户库中的任何历史表；旧库受控清理由用户另行安排。

本轮出现的验证问题已核对：隔离构建的node_modules外部软链接被Turbopack拒绝，改为任务目录内APFS依赖克隆；随后构建发现测试误用Testing Library的exact参数，已移除并重构建通过。最终全量Python运行需显式PYTHONPATH指向源码扩展，根lint的uv sync后扩展并非根workspace已安装包；修正调用环境后重跑，不以跳过或改产品断言掩盖。早期失败日志保留。

独立UI检视发现`/banks/users`误判，改为完整管理路径/locale白名单并补两项反例。测试检视补强了运行后public断言、Key日期、慢搜索迟到与clear复位。没有新增内核钩子、配置、管理表、测试框架或复杂生命周期保护。

**未验收：** 本机浏览器工具apps/browsers为空，native pipe启动失败，iab不可用；未完成真实浏览器390/1024/1440px、浅深色、焦点/键盘和真实剪贴板验收，不能用JSDOM或HTTP代理故事替代。S25/S26保留此缺口。Node为本机23.11；Node24/Linux、原样Docker、远程CI、ECS/RDS、真实MaaS、生产性能与备份恢复未执行。S13固定镜像启动免扫描仍为TODO。

主要证据：`/tmp/contextdb-python-acceptance.log/xml`、`/tmp/contextdb-ui-acceptance.log`、`/tmp/contextdb-system-acceptance.log/xml`、`/tmp/contextdb-ui-production-acceptance.log/xml`、`/tmp/contextdb-chunk-system-expanded.log`、`/tmp/contextdb-native-regression.log`、`/tmp/contextdb-production-build-final.log`、`/tmp/contextdb-lint-acceptance.log`、`/tmp/contextdb-types-acceptance.log`、`/tmp/contextdb-knip5-acceptance.log`。本机任务工件目录由`/tmp/contextdb-current-a05-fixes-path`定位。日志、秘密和构建产物不进代码仓。

## a05b808原提交验收记录（2026-10-20，历史）

下述结果保留原时点，本轮secret交互和public表初始化行为以上文为准。

## 完整特性提交前复核（2026-10-20）

将原提交与全部最新改动视为同一特性复核，未识别到阻塞提交的问题，可提交供代码评审。空间、用户、Key及UI主流程在首版规格内形成闭环，不代表生产上线验收。再次运行插件334项、UI486项、仓库lint和国际化检查，全部通过；源码与正式构建、系统61项及生产UI双Worker验收所用快照一致。原生Python运行目录对官方仍为零差异，用户verification/、日志、构建产物和临时补丁不纳入提交。

本次复核由主代理执行，没有重新组织独立专家。证据目录：`/var/folders/76/jvhrtkrx7wl0g1tf9jq6_9h00000gn/T/contextdb-combined-review-20261020-muxisl4s`，主要为review.md、review-result.json、plugin-review.log/xml、ui-review.log、lint-review.log和i18n-review.log。设计中删除前停业务、原生并发边界、浏览器视觉、远程CI和ECS/RDS验收等限制继续保留。

## 2026-10-20 四批优化、测试接线与UI简化验收

| 范围 | 已执行结果 | 覆盖与限制 |
| --- | --- | --- |
| 插件Python全量 | **334通过，零跳过** | 隔离真实PG，含非超级用户新库与重复初始化；原317项保留，托管dotenv、CI门禁和MCP目录预算新增 |
| UI完整套件（本轮重跑） | **486通过，54文件，零跳过** | 11个专属文件已迁插件，原生UI回归保留；TZ=UTC。响应/三投影、状态归属、unknown/412、旧UUID、隐藏/迟到secret及返回后新签发 |
| 跨语言Key合同 | **1通过** | TS compiler API提取三种响应投影，对照生成OpenAPI字段/required/nullable/enum；将secret改optional的临时负例确实失败，不依赖脆弱YAML字符串解析 |
| 原生系统fixture相关故事 | **17通过，零跳过；全量收集340项** | 实际隔离API/PG与模型替身，覆盖默认、Typesafe、标签授权、重试及reflect；未声称执行全部340项 |
| ContextDB完整系统故事 | **61通过，零跳过** | 实际API/PG、SDK/REST/MCP、两Worker、生产UI登录/代理、权限与记忆操作；新增代理非法字段、越权权限、旧UUID拒绝与事务回滚断言；模型用确定性桩，无真实MaaS调用 |
| 生产UI强制门禁独立运行 | **2通过，零跳过** | 单独执行内置/独立Worker两个生产UI故事，JUnit完整性检查通过；缺失/跳过/失败负例均被拒绝，CI汇总对该job取消也判失败。此两项已包含在上行61项中，不重复累加 |
| 正式生产UI构建 | **通过** | 隔离快照的正式build-ui、源码/bundle manifest与当前API树匹配；真实Next反向构建拒绝Client Component导入server-only；未替换用户现有UI |
| 原生API相关回归（此前结果，源码未变） | **1303通过，5原生跳过** | 原66文件现均与官方基线一致，包含全部16项取消；真实隔离PG、确定性embedding/rerank及pytest -s；不是上游全套/模型质量/Oracle验收 |
| 静态与收集门禁 | **通过** | 仓库lint hook、类型、ESLint、Prettier、阻断knip和advisory unused；原有pytest/Vitest名称与参数不丢不重复；故意失败的Python/UI/外部类型/lint canary均被发现 |
| 检视 | **本轮自检无必须修复项** | 本轮未重新启动独立专家；此前Hindsight/Python、TS/UI及测试接线独立报告只覆盖当时快照，不能替代本轮自检；正文限制继续保留 |

本次UI简化后重跑插件334项、UI486项、系统61项、生产UI独立2项、Key合同1项、正式构建、类型及仓库lint，均通过且无新增跳过。原生系统故事17项为前一轮测试接线验收结果，原生API 1303+5为四批优化验收结果；这两部分本轮未重跑，相关Python运行源码也未修改。插件从337变为334，是删除重复CI产物校验函数及其3项测试；启动前的唯一校验仍由系统测试中的5个有效/缺manifest/篡改bundle/不同源码/错误布局场景覆盖，未删除JUnit防漏测检查。

共享pytest模块从253行收窄到79行，仅模型替身和调用校验；原生服务、客户端、Bank fixture回原conftest。所有原函数体和装饰器均与官方AST一致。未匹配模型调用、格式错误请求的临时负例确实失败，下一例规则重置正常，已有断言失败不会再被额外teardown错误覆盖。CI脚本从67行减至38行，仅接收JUnit路径；缺失、重复、跳过、failure/error及suite错误继续拒绝。

原生5项跳过为四项原有bespoke MCP工具对照例外和一项缺少可选local-ML extra的直接引擎构造场景。旧1304计数含一项自研托管dotenv测试，该项现移到插件，因此原生变为1303，不是丢失原生覆盖。原生dotenv源文件已恢复官方内容；验证脚本仅在三个明确测试临时.env的原生用例期间解除全局禁用，未修改断言。默认pytest捕获与原生CliRunner的既有冲突仍以-s运行，不声称所有默认捕获场景已验收。

MCP测量限于单次工具目录filter：1/10/1000空间、all/selected均为1次认证fetchrow、1次归属fetchval、1次目录fetch，0次此入口遥测execute；实际完整消息可重复filter并在其他入口写遥测，不能写成“整条MCP仅3SQL”或吞吐提升。工具执行权限另由真实系统故事与撤权回归验证。

### UI简化与安全验收

本轮只调整UI、Node管理代理及相关测试，不改后端运行代码、SQL、接口或依赖。七个组件/hook集中到`components/contextdb/`；错误分类并入已有请求模块，授权比较函数回到唯一调用方，删除两份小工具文件。UI实现净减少241行，用户/Key三个状态组件合计从1360行降到1198行，行数不含测试。

- 授权草稿直接使用Key响应快照，空间目录只分页加载。100条已有授权只发一次初始目录请求，不再逐个GET；保存仍使用原UUID与Key版本，后端拒绝失效目标。目录中同名新空间不会替换旧UUID。
- 用户/Key写入结果未知时，保留目标信息并刷新普通列表，取消全量扫描、自动找页和自动展开；不重放写入。secret一次性展示、60秒清理、页面隐藏/迟到响应保护保留。
- ContextDB删除工作空间统一从管理目录操作；Bank详情提供管理链接。原生模式删除及服务端禁止生命周期旁路的约束保留。
- Node代理取消重复业务字段白名单，保留会话、同源、固定目标、路由/方法、版本头、敏感响应过滤。真实生产UI故事通过Python模型验证：非法字段/权限返回400；当前Key版本搭配旧空间UUID返回409，原授权保持不变。

修改前，真实PG安全回归31项和UI483项通过；两个新增目标场景在旧实现中明确失败。修改后UI增加到486项：100授权无逐项查询、Bank详情集中管理入口、成员请求卸载后取消并忽略迟到响应。原未知结果、412、旧UUID、只读权限与secret安全断言保留；随新交互更新了“扫描所有页/详情直接删除”的旧预期。首轮集成中这些旧预期产生12项失败，日志保留，最终完整重跑全绿。根lint原有glob实际发现全部七个集中后的文件，无须再增加接线。

### 本轮发现并修正的验证问题

- 合法JSON null及缺身份/secret的201先有失败回归，再修响应边界。
- 页面隐藏后回到可见状态的新签发曾误丢secret：交叉检视发现后新增两个先红后绿场景；旧请求迟到仍不显示，Key状态15项通过。
- 整套系统首跑59通过、两UI项失败：旧用例假设新增空间必在默认第一页。改为经UI代理逐页核对，独立运行也强制多页，完整重跑61通过；没有放宽服务断言。
- 旧隔离Python环境的API editable路径失效，修复环境后单项和完整337项重跑通过；不是业务代码修复。
- 本机原有日期用例受时区跨日影响，完整UI使用UTC；不修改原生日期实现或断言。

### 证据与未验证项

本轮UI简化证据：`/var/folders/76/jvhrtkrx7wl0g1tf9jq6_9h00000gn/T/contextdb-ui-simplification-20261020-dj6doe93`。主要为safety-before-edit.log、ui-before-edit.log、ui-target-red.log、ui-final-source.log、plugin-final.log/xml、system-final.log/xml、production-ui-final.log/xml、production-ui-result-gate.json、production-ui-build.log、types-final-source.log、repository-lint-final.log、knip5-final.log、eslint-discovery.json、this-round.patch和review.md。临时构建工作树在验收完成后删除，日志与补丁保留。

测试接线简化证据：`/var/folders/76/jvhrtkrx7wl0g1tf9jq6_9h00000gn/T/contextdb-testing-simplification-20261020-1tzqhk58`。主要为plugin-final.log/xml、system-final.log/xml、native-fixture-stories.log/xml、production-ui-final.log/xml、production-ui-result-gate.json、production-ui-build.log、repository-lint.log、fixture-comparison.json、guard-negative.log/xml和workflow-validation.json。原生故事首跑因macOS代理影响loopback健康检查而中断；临时验证环境显式设置NO_PROXY/no_proxy后17项通过，产品代码和原生断言未修改。

本机证据目录：`/var/folders/76/jvhrtkrx7wl0g1tf9jq6_9h00000gn/T/contextdb-cohesion-implementation-20261020-p2ye7g45`。主要日志：plugin-integrated.log/xml、ui-final.log、system-final.log/xml、production-ui-final.log/xml、ci-summary-probe.log、ui-production-build.log、ui-server-only-negative-build.log、native-final-tests.log/xml、repository-lint.log、ui-final-types.log、ui-final-knip.log，以及三份最终检视报告。测试日志/临时配置不进代码或资料仓。

未操作现有API8888/UI9999/PG5432，所有新服务使用任务自有PG、临时目录和空闲端口，测试后停止。浏览器工具内置浏览器不可用、Chrome连接超时；未登录或完成真实浏览器交互，因此键盘/焦点、剪贴板、窄屏与长表格视觉仍待验收，不能用HTTP或jsdom冒充。本机Node为v23.11.0，CI配置的Node24/Linux尚未实际运行。远程Actions、本次原样Docker镜像、目标ECS/RDS、真实MaaS、生产负载及备份恢复未验证；CI配置/产物和拒跳过机制只作本地验证，不称远程流水线已绿。

## 2026-10-19 上轮记录（历史）

以下保留上一轮原始证据，不替代上面的当前工作区结果。该轮成果后来以ddf5c3600推送；下述“尚未推送”为当时记录。

更新：2026-10-19。本轮验证针对 `contextdb/v1.0.0` 简化后的实现，修改前特性提交为 `1b96e97584fda118efc5dc6c7cb76d5236060563`；官方原生基线为 v1.0.0（`39c65ffe2f140d0c84cee58566cad8900c5b9908`）。本轮通过 amend 整理提交，代码提交正文固定资料仓快照；尚未推送，不代表远程旧提交包含本轮修改。

### 上轮结果

| 范围 | 结果 | 实际覆盖与边界 |
| --- | --- | --- |
| ContextDB 扩展全量 | **317 通过，无跳过** | 真实隔离 PG：认证/授权、同步生命周期、六表约束、schema 归属及依赖、故障清理、同名重建、SQL 次数、部署配置与安全。真实非超级用户新库重复 init 两次，验证秘密不变及原生 public 初始化 |
| UI 全量 | **415 通过，50 个文件** | 两入口名称/描述共享表单、512字符描述、取消重开、同步创建/删除、未知结果、条件删除及原生 UI 回归；固定 TZ=UTC，避免原有相对日期测试受本机时区跨日影响 |
| UI 生产构建 | **通过** | 隔离工作树使用默认 Turbopack，经正式 build-ui 重新构建并生成 manifest，完整校验源码与 bundle 匹配；未替换现有9999产物 |
| ContextDB 黑盒 | **60 通过** | 内置及独立 Worker 两种模式，真实 API/PG、发布的 Python SDK、REST/MCP、生产 UI 登录及代理、工作空间/成员/Key 管理、逐空间权限、记忆/知识库、默认模板及故障后清理。含外部 UI 构建验证边界；模型服务使用确定性替身 |
| 原生相关回归 | **1304 通过，5 原生跳过** | 66个相关文件，覆盖原生 Bank/索引/文件、Worker、MCP、连接池、配置与全部16项取消测试；使用真实 PG 与确定性 embedding/rerank，不是上游全套或模型质量验收 |
| 严格原生 dotenv | **另有5项通过** | 独立导出官方源文件验证；与上行覆盖重叠，不累加为新增覆盖 |
| 静态检查 | **通过** | 仓库 lint 脚本、扩展 Ruff/类型检查、UI 类型检查、OpenAPI 生成一致性、差异空白检查；资料脚本语法/JSON与相对链接检查通过 |
| 独立检视 | **无阻断性问题** | Hindsight 与 PG 专家分别只读检视；已采纳授权表反向索引及过时注释修正，补充指令写权限显式回归。结论以本轮规格为前提，不恢复执行屏障 |

原生回归选取65个测试文件及 conftest 与官方基线一致；另一个是已有特性扩展的 dotenv 文件，官方原版另行导出验证。默认 pytest 输出捕获下有一项原生 CLI `CliRunner` 关闭缓冲区错误，在纯官方 v1.0.0 同样复现；以 `-s` 关闭外层捕获后，原断言通过，未改原生源码或删除该断言。5项跳过是原生自定义 MCP 对照例外及缺少可选本地 ML 依赖的直接构造用例。没有声称默认捕获模式或全部可选后端已验收。

本轮把7个原生运行文件全部恢复为官方内容，原生运行目录相对官方 v1.0.0 无差异。同步管理的实现与回归集中在扩展及 UI；管理异步调度、持久准入、额外连接池、执行代次和故障回调相关测试随已删除的增强承诺移除，普通权限、身份条件及原生取消回归保留。

### 上轮验证环境与证据

测试使用任务自有 pg0 实例、临时目录和随机端口；未停止或替换现有 API8888、UI9999、PG5432，未调用真实 MaaS 或使用客户凭据。生产 UI 的实际 HTTP 登录、同源校验和管理代理故事已通过；本轮未完成浏览器截图验收，操作期间浏览器被用户切换，未继续争用现有窗口。

本机证据目录：`/tmp/contextdb-simplification-night-20261019.L6810v`。关键文件为 `extension-final-second.log`、`system-contextdb-second.log`、`ui-form-review-tests.log`、`ui-build-stamped.log`、`native-final-tests.log`、`native-report.md`、`repository-lint-final.log`、`hindsight-final-review.md`、`pg-final-review.md`。日志和临时配置不提交资料仓；目录不是长期制品存储，转测时应按团队流程留存非秘密报告。

### 历史证据与上线前待完成

此前真实 MaaS、单容器部署、PG SSL 渲染和 PGroonga 试验对应旧实现，保留于[历史验证材料](../archive/2026-10-19-before-reorganization/design/contextdb-service-research-validation.md)。不能以这些结果宣称本轮原样容器、真实模型或目标云环境已经通过。Colima ARM 曾使用 `OPENSSL_armcap=0` 兼容覆盖，正式镜像未写入该覆盖。

目标 ECS/RDS 原样启动、插件版本/权限/网络、混合负载及延迟、备份/PITR和故障恢复、依赖与镜像安全仍须验收。首版 native+english 覆盖英文全文，中文向量可用性不能替代中文关键词全文验收。R05/O03方案已于2026-10-21确认：固定镜像在构建/CI检查一致性，运行时参照原生直接启动；源码部署保留检查。代码待实施，当前仍执行启动扫描；详见简化清单第11章。后续事项统一在[设计 TODO](../design/contextdb-release-design.md#本轮实现收敛与-todo)维护。

工作空间删除前须由管理员停止新业务，并等待已受理请求与原生后台工作结束；本版不提供并发删除重建时的完整执行隔离。手工验证使用[API/curl 手册](../api/contextdb-management-api-curl-guide.md)，部署使用[联调指南](../deployment/contextdb-service-integration-guide.md)。


## 2026-10-22 提交前复检与本地新提交

验证代码：本地新提交`9fb57bc04`，父提交003bbe032；未推送。

| 本轮重新执行 | 结果 |
| --- | --- |
| 插件Python | 425通过，零跳过 |
| UI | 560通过，55文件，TZ=UTC、2 workers |
| 系统 | 75通过，双Worker、真实隔离PG、匹配生产UI |
| 相关原生MCP/扩展/Webhook/Trace | 484通过；缺Groq凭据的真实模型用例在命令中明确排除 |
| 维护函数测试独立执行 | 修复前失败；修复后1通过；完整回归也通过 |
| 静态及构建检查 | TypeScript、lint、blocking knip、当前源码/产物指纹、diff检查通过 |
| 生产UI门禁 | 从完整系统XML提取两个真实执行项，通过严格JUnit检查；不重复累计为新测试 |
| Git提交钩子 | 全部通过；原生运行代码无本轮差异 |

证据目录：`/Users/zhuqingping/Work/Database/Context/test/contextdb-amend-review-20261022/`，见review-report.md。目录沿用先前任务名，实际按最新指令创建新commit，未amend。

未完成项：Audit保持关闭；O02、真实MaaS/ECS/RDS及生产负载/恢复、中文全文、O07、Bank API统一不在本轮验收范围；O04全链路量化和Trace/Webhook完整故障矩阵仍需补验。本轮未重新操作浏览器，先前匹配源码的Chrome证据保留。
