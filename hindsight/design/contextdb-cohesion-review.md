# ContextDB 模块内聚与测试组织检视

> 实施状态（2026-10-20）：四批优化及后续UI简化已完成验收，已通过amend整理为单一特性提交 `a05b808` 并推送。测试组织已选择方案B（自研测试物理集中插件），不再是待决项。本文第1～6节保留实施前的评审与取舍，当前实现看[检视指南](code-review-guide.md)，实际验收看[验证摘要](../testing/contextdb-validation-summary.md)。后端与UI交叉检视已完成，发现的secret重置问题已修复并补回归；没有恢复复杂删除保护。

2026-10-20。对象：[ddf5c3600](https://github.com/ZhuQingping/hindsight/commit/ddf5c360001f1db46f925b1822803ac9bff1119e)，分支`contextdb/v1.0.0`，已推送；官方基线`39c65ffe`（v1.0.0）。本轮由Hindsight、Python、TS、测试、UI五个角色先独立审查，再交叉质疑，根Agent复核证据和裁定范围。**以下都是待实施建议，本轮没有修改代码、配置或测试，没有提交推送。**

[模块阅读指南](code-review-guide.md) · [完整设计](contextdb-release-design.md) · [上轮实现及验证结果](../testing/contextdb-validation-summary.md)

## 1. 先看结论

**现有基本架构可以保留，下一步应做局部修订。** 工作空间同步管理、六张元数据表、UUID授权、原生记忆算法与Worker复用的方向不变。真正值得收敛的是响应边界、持续验收、共享检查依赖、MCP目录查询、测试准备代码和UI状态归属。

当前124个变更文件包含测试、部署、文案和生成材料；原生Python运行目录是零差异。四个扩展、外层ASGI和若干UI接入点承担不同职责，不能仅为了少几个文件将它们合并。后续合理拆出几个内聚模块，文件数可能增加，原生维护负担仍可下降。

建议分批如下；每批独立验证，不能把可靠性修复与大规模搬文件混在一起。

| 批次 | 具体事情 | 预期结果 |
| --- | --- | --- |
| A，先做 | Q01异常JSON/创建结果校验；Q02生产UI强制CI；Q03准确Key返回类型 | 用户不会把不完整响应当成功；CI持续验证真正的生产UI代理 |
| B，随后 | Q04按操作补未知结果核对；Q05共享数据库检查；Q06固定SQL投影；Q07消除MCP目录2N查询 | 减少易误操作、反向依赖和不必要查询，不增加管理平台 |
| C，整理 | Q08先抽测试support/资源owner，再按特性归组；Q09按状态归属提取Key编辑器 | 测试不再互相导入测试文件；用户页不再同时持有所有状态 |
| 小步独立做 | Q10服务器模块加server-only标记和原生生命周期入口覆盖检查 | 误把后台Key代码引入浏览器时能尽早发现 |
| 后置 | 配置政策复用、MCP消息helper、HTTP同文件整理、窄上下文复位、文案和字体维护 | 有明确收益再做，不连环增加服务层和配置文件 |

上轮本地317/415/60/1304项测试证据仍有效。本轮发现的是此前未覆盖的异常JSON，以及本地验收未被CI持续强制的问题，不代表常规接口已经全部失效。没有发现需要越过只读授权立即修复的紧急越权或明文Key泄露；也不据静态审查声称安全问题已被穷尽。

## 2. 范围和证据

本文`P/`指`hindsight-extensions/contextdb-service/hindsight_ext_contextdb/`，`U/`指`hindsight-control-plane/src/`，`S/`指`hindsight-system-tests/`。行号对应固定的ddf5c3600，后续修改后以函数定位。

| 本轮检查 | 状态 | 可以说明什么 |
| --- | --- | --- |
| 五角色读代码、官方基线对照、设计和CI路径审查 | 已执行 | 说明调用链和当前实现；不能代替完整动态验证 |
| Node内存转译当前contextdb-api.ts，仅替换fetch/withBasePath | 已执行 | 复现异常响应解析；没有启动浏览器、服务或网络请求 |
| Python超时异常继承检查 | 已执行 | 排除一项误报：TimeoutError已被OSError捕获 |
| pytest、Vitest、类型检查、构建、PG、模型、远程CI | 本轮未执行 | 文中命令是实施后的验收建议，不是本轮通过证据 |
| 浏览器真实交互和不同宽度截图 | 本轮未执行 | 不从CSS或组件测试推断实际布局已验收 |

主控探针结果：

| 输入 | 当前结果 | 判断 |
| --- | --- | --- |
| POST收到503，正文为合法JSON `null` | TypeError，无法进入ContextDBError的unknown分类 | 已确认的异常响应边界缺陷 |
| POST收到503，正文为`{}`或HTML | 正确的ContextDBError及未知结果提示 | 已有机制有效，应保留 |
| POST收到201，正文为`{}`或`null` | 直接当作泛型T返回 | 关键成功字段没有运行时校验 |
| POST收到201，正文为截断JSON | 正确的response_unknown | 已有测试覆盖的是这类语法错误 |

该探针只证明客户端在相应输入下的行为。正常Python管理路由按Pydantic模型生成响应；本轮没有证明正常API日常会返回null，更没有模拟真实DOM点击。

## 3. 可实施建议

### Q01 先修响应解析，不先引入新验证框架

**位置：** `U/lib/contextdb-api.ts:112–144,148–158`；`U/components/contextdb-create-workspace-dialog.tsx:59–71`；`U/components/contextdb-users-view.tsx:792–798`。

当前error JSON直接读取`.error`等属性，合法JSON null不触发JSON解析catch。成功响应只要是合法JSON就被转为T。TS的`Promise<ContextDBWorkspace>`只表示编译期约定，不会替服务端检查实际数据。

**最小修改：** 在现有请求函数把JSON接作unknown；只有非null、非数组对象才读取合法string错误字段，否则使用HTTP状态和Header回退，始终抛ContextDBError。空间POST在`workspaceMutation`校验消费者必需的`workspace_id/bank_id/etag`及成功合同，bank_id对应已提交的规范化名称；Key POST在签发边界要求`key_id/user_id/secret`等必要字段。丢失关键字段归response_unknown，先核对，不能关闭成成功或导航undefined。

不对所有T增加通用深度schema引擎，不安装新验证库，不生成第二套SDK。PATCH不要求secret，DELETE204继续允许空正文。保留request_id、原ETag、脱敏和“不自动重发写入”。

**验收：** 在现有请求与组件测试补null/数组/字符串/HTML/截断JSON；补201缺身份/缺secret/错误目标/有效资源；断言正确错误类型、一次fetch、未知提示、未成功关窗，正常PATCH和204不变。预计0.25–0.75工程日，与Q03共用工作不重复计算。

### Q02 让生产UI黑盒在CI中真正必跑

**位置：** `.github/workflows/test.yml:3579–3624,1450–1515,5883附近`；`S/tests/test_112_contextdb_ui_management.py:43–65`。

当前test-system只准备Python环境，不构建生产UI，也不下载带manifest的产物；112缺Node/server时skip。build-control-plane在另一个runner，文件不会自动共享。test-system的触发条件也没有control-plane/clients-ts，因此只改UI不会触发这组组合测试。这是由静态配置确认的持续验收缺口；未在线读取某次Actions日志，不能声称已观测某次具体skip。

**推荐最小方案：** 增加独立`test-contextdb-system-ui` job，避免全部原生系统测试都承担UI构建成本。准备匹配的Node、锁定Node依赖、Python系统环境及插件导入路径；用正式build-ui从同一SHA构建并写指纹，沿用已有`CONTEXTDB_UI_SERVER`/`CONTEXTDB_TEST_NODE_BIN`选择该产物。

触发范围覆盖扩展、core、system-tests、control-plane、TS和Python客户端、CI及手工运行。新job进入最终required汇总needs。迁移测试目录后同步路径。

**无需新增部署参数或严格模式开关。** CI先校验同一个Node可执行、server存在、manifest/源码/bundle与本次API checkout匹配；再只跑112故事并输出JUnit；最后要求embedded-worker、standalone-worker两个明确testcase各出现一次，无skip/failure/error。XML缺失、用例缺失或跳过均使job失败。本地快速Python运行仍可保留既有可选skip。

普通`npm run build`不会产生ContextDB manifest，不能代替正式build-ui。将skip改fail但不给构建产物也不是完整方案。

**验收：** UI-only变更能触发该job；两个Worker组合项零skip；故意缺产物、坏manifest、缺一个参数化项时关口失败；插件/原生其他测试保留。预计0.5–1.5工程日，不修改原生运行文件。

### Q03 准确区分签发、编辑和列表三种Key响应

**位置：** `P/models.py:183–200`；`U/lib/contextdb-api.ts:28–37`；`U/components/contextdb-users-view.tsx:792–798`。

Python已经区分KeyEditable、KeyMetadata和KeyIssued；TS却用带last_used_at的ContextDBKey，再与可选secret拼接表示POST/PATCH。实际POST/PATCH没有列表统计字段，POST的secret也不应是optional。这是确定的类型合同漂移，尚不等于所有现有Key操作都失败。

**最小修改：** 在现有contextdb-api.ts定义对应三种类型，创建和编辑分别调用并处理结果；POST校验一次性secret，PATCH按编辑投影，列表保留last_used_at。UI要求workspace_id的更严格输入类型继续保留。增加消费字段/required/enum合同检查。

不先拆四层contracts/client/server/policy文件，不为13接口再生成完整transport SDK。types-only OpenAPI生成可后续试验，须证明union和输入/展示差异可用后再选。

**验收：** POST类型secret必填，PATCH不读取secret，列表统计类型准确；缺secret不误报成功；OpenAPI所消费字段发生不兼容变化会使合同检查失败；原生SDK零额外差异。约0.5–1工程日，可和Q01同批。

### Q04 未知结果核对按操作语义做，先留在现有弹窗

**位置：** `U/components/contextdb-users-view.tsx:229–238,615–649,792–799,829–874`；空间创建`:136–145`；`contextdb-workspaces-view.tsx:71–95,228–231`；空间详情`page.tsx:198–256`。

当前用户/Key请求**没有自动重发**；问题是错误后原Save很快恢复，缺少可靠的核对路径。Key名称不唯一，人工再次签发可能多出一把Key；secret又只返回一次。空间创建虽已有unknown锁，但核对不带提交名称，只回目录第一页，资源多时不容易找到目标。

| 操作 | 最小核对行为 | 不能做什么 |
| --- | --- | --- |
| 创建Key | 当前签发尝试转只读unknown，查看该成员Key元数据；解释明文无法补取 | 不能按同名自动认领、自动吊销、自动重发；管理员辨认key_id/尾缀/时间后显式处理 |
| 创建用户 | 保留提交名称，显示当前同名成员/ID或查询失败 | 同名存在不能证明就是本次POST结果；404也不证明原调用结束 |
| 用户/Key修改 | 412为conflict，重新读取并让用户确认新快照；unknown仅核对 | 不把新version自动套进旧草稿重发；不把400和412全锁成unknown |
| 删除成员/吊销Key | 在原目标ID上只读核对；必要时由管理员明确再次操作 | 不机械套空间ETag语义；不阻止其他成员浏览 |
| 空间创建 | callback带提交的规范化bank_id，用详情GET核对 | 未拿到原UUID时只能说明当前同名对象存在，不能自动认定同一次创建成功 |
| 空间删除 | 保留原bank_id、UUID、ETag，区分404/同UUID/继任UUID | 不能用同名新对象ETag重发旧删除，不能把GET成功当作已排空证明 |

先做小型错误分类和当前dialog的pending/unknown/conflict状态，不造统一CRUD恢复hook、不增加幂等Key/管理operation表或持久轮询。GET失败是unavailable，不永久锁整个页面。核对文案放ContextDB catalog，不在请求函数另写一份中英文。

**验收：** Key签发超时不能直接以原按钮重复POST；只读核对不发送写请求；列表无secret；管理员显式处理候选Key后才能新发；400可修正，412重新确认；空间>20条及原搜索存在时仍能核对目标。约1–2工程日，先做Key签发，再补空间核对；与Q01/03共用项不累计。

### Q05 提取共享数据库检查，纠正离线对在线仓储的反向依赖

**位置：** `P/repository.py:79–135`；`migrations.py:14,42–54`；`__main__.py:56–57`。

离线初始化和管理员轮换为了格式/归属检查导入完整Repository，并调用其私有静态方法。这三类检查不需要在线CRUD实例。

**最小修改：** 新增database_checks.py，迁出格式、部署归属、后台写入政策三个无状态公共函数，显式接收现有Connection/Pool。Repository和离线模块共同调用；verify_schema仍组合在线检查。删除原实现，不留长期兼容转发。

保留原Connection、同一离线事务、旧试验结构拒绝、后台功能边界。_require_binding热路径、CRUD、锁、审计和schema删除事务不顺带重构。

**验收：** 离线代码不再仅为检查依赖Repository；初始化、重复初始化、归属/旧布局拒绝、审计/Webhook限制保持；SQL和事务语义不变。约0.5–1工程日。

### Q06 移除认证SQL的字符串替换，保持单条快照查询

**位置：** `P/repository.py:156–160,303–312`。

当前authenticate通过对_GRANTS的`.replace()`插入目标条件。现在确实能工作；维护者改空白或别名时，替换可能静默不发生，重新聚合所有授权。不能因此报告当前已有越权。

**最小修改：** 同文件固定模板，用一个内部bool选择“全量投影/目标投影”的固定predicate；只拼源码常量，不接受外部SQL字符串。TypeAdapter可顺带定义为模块常量。保留单条认证SQL同快照核对部署、用户、Key与目标；不加载全部grant后再过滤。

不造通用SQL builder、ORM或第三个认证仓储，不复制两份长聚合逻辑。**验收：** 目标认证只含目标grant、目录认证含完整授权、HMAC/撤销/停用/UUID隔离不变；查询次数保持有界。约0.25–0.75工程日。

### Q07 MCP工具目录用当前消息数据纯计算，去掉2N查询

**位置：** `P/validator.py:254–261`；`repository.py:292–350,376–383`；`mcp.py:65–129`。

当前先得到无目标Principal的完整workspace_permissions和active可见空间，再对每个空间调用select_workspace。该方法又做部署检查和空间查询，只为得到scope，增加2N条元数据SQL；**N是可见空间数量，不是工具数量。** 原生可能重复过滤，因此不把整条MCP消息总SQL写成恰好2N。

**最小修改：** 在现有authorization.py用纯函数计算permission对应scope，再按可见active UUID与workspace_permissions求并集。all只有存在可见空间时贡献scope；selected按UUID匹配，不能按名称。不创建新的Snapshot、权限缓存、连接池或policy框架。

目录并集只决定广告哪些工具，不成为执行权限。每次tools/call仍用当前消息Key和实际Bank重新认证；保留Tenant/schema及引擎Validator。原生middleware退出后的外层过滤仍要从当前HTTP scope取消息意图，不能删除这一时序适配。目录在同一消息内可能短暂多显示工具，后续实际调用必须拒绝已撤权限；不承诺工具目录响应全时刻原子一致。

**验收：** 1/10/1000空间下不再出现逐空间select_workspace线性增长；分别记录认证、目录、遥测UPDATE及原生多次filter的全消息查询。混合读写、空active、all、旧UUID/同名重建、同会话换Key/撤销、固定Bank路径冲突均保持。SQL测量放插件集成层，黑盒故事不加数据库窥探。约0.5–1工程日；只能承诺查询数降低，不报未测吞吐提升。

此项与routing.py的跨schema Bank目录全扫描是两个问题。后者仍需保持全局q/最近写入排序/total，不在此批提前分页或无界并发。

### Q08 先让测试准备独立，再决定物理目录

**位置：** 插件conftest.py:59；test_http/test_extensions/test_repository中的共享fixture；`S/tests/test_100_contextdb_service.py:34–252`、102、106，以及101/104/105/109中的pytest_plugins。

当前测试准备反向导入test文件；test_100又同时承担故事、PG/服务owner和客户端fixture；106使用fixture.__wrapped__，102动态装载测试文件验证清理。这比目录本身更值得去耦。

**第一步不移动测试。** 插件共享身份、HTTP装配、生命周期辅助迁到tests/support；conftest只注册fixture。系统测试提取普通contextmanager/asynccontextmanager资源owner（deployment/clients/ui），fixture薄包装，错误清理测试直接测owner，模板故事传明确配置。复用原hindsight_system_tests的server/stub/SDK，不复制框架。不要求一开始为每个小helper各建一个文件。

**第二步选择目录。** 当前共有7个专属UI测试、16个ContextDB系统测试文件和原生dotenv中的1项托管增补可进一步归组；原生词条检查和其他原生回归留宿主。已有24个插件Python测试不必为了分类全部重排。

| 方案 | 可实施目录与接线 | 取舍 |
| --- | --- | --- |
| A，主推荐 | 插件tests/；UI/tests/contextdb/；system-tests/tests/contextdb/；dotenv新增项回插件 | 保留三运行环境与黑盒仓库约定，移动和配置代价较小；预计1–2日，含主要support梳理 |
| B，全部自研测试物理归插件 | 插件tests/python/、tests/system/、tests/ui/；Python/system分入口；UI仍由原CP工程执行 | 可行，适合明确插件独立交付诉求；约2–4日，接线完整后质量可与A等价 |

B不用第二Vitest工程：当前CP的vitest.config追加外部include即可，现有@别名已指向CP/src；保留三个组件文件的jsdom声明。只有确有不同执行策略时才需要第二config/projects。无新package.json、lock、React依赖副本。所有迁移修相对imports/ROOT/pytest_plugins，非顶层conftest不新增pytest_plugins声明。

A也不是零接线：目前lint.sh只扫CP/src，移动到tests会掉ESLint/Prettier。B还须显式纳入外部tsconfig、flat ESLint范围、CI触发和unused检查；不能文件被ignored却仍称lint通过。CLAUDE的黑盒位置规则是项目约定，用户选择B时可明确调整或保留唯一运行入口，不是技术禁令。

**验收：** 迁前后pytest/Vitest收集清单按路径映射归一化，参数化场景不丢、不双收集；故意失败的专属测试能使默认命令/CI失败；单文件与全套均可跑；双Worker生产UI必跑；owner初始化失败无残留进程/PG。新增回归可增加项数，不要求永远等于317/415/60。

### Q09 用户页按状态所有权提取，先不做通用CRUD

**位置：** `U/components/contextdb-users-view.tsx`约915行，持有成员目录、Key目录、授权空间缓存、编辑/删除草稿、secret及全局busy/error。

**最小拆分：** 先提取授权快照/序列化纯函数，以及KeyEditorDialog和其workspace picker hook；保留现有外层成员列表及DOM。后续再提KeyPanel。只移动JSX、所有状态仍在父级，不算解除耦合。

| 对象 | 应拥有的状态 | 不应承担 |
| --- | --- | --- |
| UsersView | 用户搜索、分页、选定user_id、用户管理 | 不再持有授权缓存和secret |
| KeyPanel | 固定user_id的Key目录/刷新/吊销目标、一次性secret；以user_id为挂载身份 | 不替其他用户保留在途请求 |
| KeyEditorDialog | name、selected/all、逐空间权限、草稿/原版本、当前写入结果 | 不让父列表同时维护同一份草稿 |
| KeyAuthorizationEditor（若需要） | 受控展示，通过props/onChange编辑 | 不另持草稿、不取数据，不形成第二状态源 |
| workspace picker hook | 追加分页、UUID按需核对、Abort/generation和局部缓存 | 不是全局授权缓存，不把404与网络失败混同 |

secret始终留内存，离页/hidden/到时清理，不能转到URL/storage。保留name-only编辑不重发授权、selected旧UUID不变继任UUID、切用户旧响应不落新面板。继续用已有React状态工具，不加状态库、表单DSL或generic useResource。

**验收：** 切成员/快速关闭重开/翻页时旧响应不覆盖新编辑；读写切换、已删除空间和网络错误区分；一次性secret清理；未知结果行为保持。授权editor+picker约1–2日，KeyPanel另0.5–1日，视真实代码接缝决定，不一次拆六文件。

### Q10 标清服务器边界，保留必要的双层保护

**位置：** `U/lib/contextdb.ts`、middleware.ts、原生Bank生命周期route，以及现有边界测试。

首期只给现有服务端helper加server-only标记，保留路径和导入点；测试在现有Vitest配置做仅测试适配，真实Next构建检查客户组件误导入应失败。当前导入图没有证明Admin Key已泄露，这是一项防回归措施。

middleware与handler中的生命周期deny各有职责，保留handler的一行guard；新增生命周期同类route时应有覆盖检查。管理代理已经通过requireContextDBAdmin(request,false)避免额外identity查询，不再为消除不存在的重复查询改架构。原生UI数据接口仍需每请求后台管理员检查。

同一middleware里两次cookie HMAC可局部复用，但没有性能数据支持大收益，列为顺带小改。不开跨请求角色缓存，不信客户端“已鉴权”Header，不把Admin Key给浏览器，也不为包住所有原生route新造代理框架。约0.5–1日，真实构建/原生模式/直接handler/下一请求撤权均需验证。

## 4. 后置项与明确不建议

| 项目 | 结论与理由 |
| --- | --- |
| 把pool/catalog/MCP/schema等私有访问全部搬进native_compat | 不采纳：成为职责混杂Gateway。pool等留职责模块；重复set/reset最多先同文件窄helper，保留升级清单 |
| 合并四扩展或仅在HTTP/MCP鉴权 | 不采纳：不同原生槽位、Worker和内部调用仍需引擎授权 |
| 按User/Key/Workspace拆三个Repository | 不采纳：共享事务、单行锁、审计和schema清理会被切碎 |
| 配置policy/MCP context/pure tool policy分层 | 方向可行但暂缓；先必要小纯函数，不连续增加runtime/policy/容器模块 |
| HTTP拆13 router或新DI容器 | 暂缓；先同文件共享If-Match常量/小route factory，保留auth-before-body-validation和脱敏 |
| 全量生成管理SDK/运行时schema体系 | 暂缓；先修三个Key投影及真正消费字段 |
| UI词库全量自然语言重写 | 先把unknown/conflict/secret丢失文案进catalog；基于使用面清单再决定缩小覆盖，不复制10套原生词库 |
| 系统字体改动 | 与权限特性不同，是离线构建适配；独立标注，不能为净diff立即恢复Google字体外网获取。未来本地字体资产需许可/大小/视觉验收 |
| 原生DSN日志 | 独立Issue #3跟踪；不借本轮收敛恢复通用原生补丁 |
| 构建免扫描、跨schema目录重写 | 保留已有TODO；无可信镜像身份不跳扫描，无规模测量不加全局缓存/水位/并发平台 |
| 执行屏障/代次/管理异步任务/强并发删除保障 | 不恢复，本版接受原生边界；UUID/If-Match和普通授权继续保留 |
| 只搬测试/只减少文件/只把所有JSX拆小组件 | 不能单独作为质量验收；要看状态、事务、依赖和收集边界 |

误报更正：Python TimeoutError是OSError子类，asyncio.TimeoutError也是对应别名；http.py现有OSError捕获已覆盖。该候选已撤回，不增加修复或测试工作。

## 5. 实施时的检查清单

下列均为**建议，尚未执行**。以每批相关测试先行，新增缺口用例应先在现代码上失败，再修实现；变更后再跑相关广度，不重复运行无关模型矩阵。

1. 固定代码SHA、记录原pytest nodeid与Vitest清单（含Worker参数）；依赖使用隔离环境，不能读取开发.env或占用现有PG/端口。
2. A批先保持文件位置，补Q01/Q03回归、Q02构建与强制关口。正规UI构建后验证manifest；两Worker故事均pass且零skip。
3. B批每项独立改动/验收。Q05不改变事务；Q06不放大grant查询；Q07真实MCP与空间规模SQL预算同时通过。
4. C批先抽support owner并验证失败清理，再移动测试；检查默认命令、CI触发、type/lint/unused与构建，不只确认文件存在。
5. UI补齐隔离浏览器验收：两入口名称/描述；长名称/描述和窄屏；键盘/焦点；Key签发unknown；旧ETag/继任对象核对；secret一次性展示与离页清理。HTTP代理故事不能替代这些真实交互。
6. 最后核对原生运行目录仍与39c65ffe一致；没有新管理接口、元数据表、生产参数、共享权限缓存或删除平台。若选择测试全插件，要明确修改测试组织约定，不将其偷带成实现细节。

### CI生产UI构建的可执行准备示例

这是Q02拟采用的同版构建步骤，**本轮未执行**。运行前已准备匹配Node、Node锁定依赖及系统Python依赖；`CODE`为本次job的同SHA检出，不是用户正在运行UI的目录。

```bash
export CODE=/absolute/isolated-checkout
cd "$CODE/hindsight-system-tests"
# pytest.ini中的pythonpath只作用pytest，构建CLI需要显式模块路径。
PYTHONPATH="$CODE/hindsight-extensions/contextdb-service" PYTHON_DOTENV_DISABLED=1 uv run --frozen --group contextdb python -m hindsight_ext_contextdb build-ui --source-root "$CODE"
export CONTEXTDB_UI_SERVER="$CODE/hindsight-control-plane/standalone/server.js"
export CONTEXTDB_TEST_NODE_BIN="$(command -v node)"
# 实施Q02时先校验Node、verify_ui_build与同源码匹配，再运行：
PYTHON_DOTENV_DISABLED=1 uv run --frozen --group contextdb pytest   tests/test_112_contextdb_ui_management.py -v --junitxml=/tmp/contextdb-production-ui.xml
# 此后必须解析JUnit，核对两个指定Worker testcase均成功；退出0不够。
# 若已迁移到tests/contextdb，改用对应路径，不能保留旧glob。
```

所有工量都是含相关回归的工程量粗估，不是当前已实施工期承诺；重叠项不能相加。建议先独立完成A批，确认收益后再授权B/C，避免一次整理把初版复杂度重新堆高。

## 6. 五角色讨论后的取舍记录

| 角色 | 交叉讨论后的明确结论 | 从初稿收窄/保留的分歧 |
| --- | --- | --- |
| Hindsight | 保留四扩展/ASGI；Q07纯计算可做，实际目标认证不删；CI先于结构重排 | 撤回全包native_compat，窄复位后置；目录短暂广告滞后须按上述边界验收 |
| Python | 支持Q05/Q06；Repository事务保留；可靠性与CI优先 | 配置policy和HTTP新容器降级，TimeoutError误报撤回 |
| TS | Q01/Q03优先；server-only小步；双层guard保留 | 撤回第二Vitest config和四层源码拆分的默认建议；字体独立处理 |
| 测试 | CI同SHA产物+JUnit双Worker必跑；先support再搬迁，必须核对收集/类型/lint | 不加严格模式新参数；全插件可用现Vitest外部glob，非技术禁令 |
| UI | 关键成功字段校验先于关窗；Key丢secret需人工核对；按状态归属拆KeyEditor/Panel | unknown按操作处理，不锁死所有CRUD；默认三宿主，接受物理全插件备选 |

达成共识的是A批优先、B批窄改、现有安全与原生边界不变，以及拒绝通用框架/双依赖/删除平台。**测试物理目录仍是可选决策：主推荐A，用户明确要求插件独立交付时选B；没有伪称所有方案已经唯一确定或已经落地。**

各角色原始报告及两轮回应保留在本机`/tmp/contextdb-cohesion-review-20261020-000713/`：hindsight-review.md、python-review.md、ts-review.md、testing-review.md、ui-review.md。主控证据为ts-response-probe.json、timeout-type-check.json、python-inventory.json、test-inventory.json。临时材料不是产品部署文件，本轮综合结论以本文为人工检视入口。
