# 原生 v1.0.0 接口权限对照与 Bank 管理统一评估

> **Bank 接口设计更新（2026-10-29）：** 第1～8章保留历史基准和讨论；最新拟议合同见[第9章](#bank-api-reuse-design)。REST隔离原型已在团队集成工作树实现，未提交/部署，保留旧创建入口与描述能力，MCP管理关闭；当前范围见第9.10节。第6章关于删除条件、移除全部workspace查询的早期取舍由第9章修订。

> **历史基准（2026-10-22）：** 第1～8章保留当时的问题复现、评审和过程记录；其中本地提交`9fb57bc04`（父提交003bbe032，彼时未推送）及“独立worktree／未提交”等描述不代表当前 main。其他已修复项和边界以[对应设计](contextdb-release-design.md)及[验证记录](../testing/contextdb-validation-summary.md)的版本为准；Bank 接口最新分析基准和拟议合同见第9章。


第1～8章历史更新：2026-10-21。Bank 接口设计更新：2026-10-29，第9章；方案尚未实施。

## 1. 基线、范围和阅读方式

- 原生：官方Release v1.0.0，提交 `39c65ffe2f140d0c84cee58566cad8900c5b9908`。
- 当前策略：`contextdb/quality-20261021-004226`工作树，c56c7ac17基线加本轮未提交质量修复（含提示词预览限制）；不是只读原仓旧提交。
- 枚举原生http.py全部100项显式REST路由、BankReadOperation全部32项、BankWriteOperation全部40项、PrecheckOperation全部7项、原生_ALL_TOOLS全部39个MCP工具。补充生命周期与外围拦截。此范围不包含其他独立MCP程序、扩展自行注册接口、框架自动生成的文档路由或其他可选后端。
- R=已授权空间的只读业务Key；W=读写业务Key；A=实例Admin Key。允许表示自研策略允许，仍受原生参数、配置开关、资源状态和目标授权约束，不等于每个入口已经真实运行验收。A不绕过当前原生生命周期限制。
- 表中的权限是组合策略结果：Transport、Tenant、Validator、MCP工具过滤、部署限制都可能进一步收紧。未知操作默认拒绝与已知能力遗漏需分别判断。
- 本次RUN：AST枚举、源码链路走读、默认拒绝集合差集核对。NOT RUN：100个REST入口和所有MCP工具的逐项在线验证、Bank API新方案原型、性能测试。

## 2. 关键发现及建议

| 级别 | 发现 | 判断及建议 |
| --- | --- | --- |
| Important | 六个原生写操作落入默认拒绝：UPDATE_BANK、CREATE/DELETE_BANK_ALIAS、CREATE/UPDATE/DELETE_WEBHOOK | Webhook已定恢复；UPDATE_BANK需按字段拆分身份与展示属性，不能笼统视为改bank_id；别名需入口解析适配 |
| Important | 原生Bank.name是仍兼容但已标deprecated的展示名，bank_id是稳定标识 | 更新展示名不等于重命名Bank或schema；当前拒绝Admin展示名更新有过度限制，应允许Admin更新展示属性，不能靠放行任意业务Key处理 |
| Important | MCP隐藏Admin的update_bank，而REST对既有Bank的纯config更新路径可能允许 | 工具隐藏、字段授权和REST行为不一致；恢复时逐字段验证，不把整个PUT/PATCH简单标成一律拒绝 |
| Important | 默认拒绝只覆盖一个层面；别名、模板导入、归档导入/克隆被外围先挡住 | 只把操作加入Validator允许集无法恢复这些接口；必须检查Transport及schema初始化 |
| Important | 单Key多schema的Bank创建/删除不可能只靠前置Validator维护完整生命周期 | 创建前需Admin身份认证及schema准备；成功后需元数据状态、授权及schema清理。复用Bank URL可以简化接口，不消除这些职责 |
| Important | 恢复Trace/Audit/Webhook已定案，代码仍拒绝 | 不能把文档目标写成已开放；按O05实施与组合验收 |
| Minor | 文档导入、模板导入、整库恢复不是同一能力 | POST /document-transfer导入现有空间的文档是内容写路径；不应把所有“import”都认作生命周期操作 |

**总建议：REVISE。** 保留动态权限默认拒绝和独立schema的安全边界，纠正已知能力的不必要禁用。对全部已知操作显式分类，增加“枚举全覆盖”测试；以后原生新增操作使测试失败并要求分类，不能用Admin无条件允许所有未知操作掩盖遗漏。

## 3. 原生REST接口完整对照

前缀 `B` = `/v1/default/banks/{bank_id}`。下面逐项列出全部100项。必要性/恢复方式同时列出；“扩展”不代表无需完整生命周期适配。

| # | 原生方法与路径 | 原生用途 | 当前策略 | 限制必要性、恢复方式 |
| --- | --- | --- | --- | --- |
| 1 | `GET /health` | Health check endpoint | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 2 | `GET /health/ready` | Readiness probe | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 3 | `GET /health/live` | Liveness probe | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 4 | `GET /version` | Get API version and feature flags | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 5 | `GET /v1/version` | version_endpoint | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 6 | `GET /metrics` | Prometheus metrics endpoint | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 7 | `GET B/graph` | Get memory graph data | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 8 | `GET B/memories/list` | List memory units | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 9 | `POST B/memories/dry-run-extract` | Dry-run fact extraction (preview, no persistence) | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 10 | `POST B/prompts/preview` | Preview an operation's prompts (no LLM call) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 11 | `GET B/memories/{memory_id}` | Get memory unit | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 12 | `PATCH B/memories/{memory_id}` | Curate memory unit | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 13 | `GET B/memories/{memory_id}/history` | Get observation history | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 14 | `POST B/memories/recall` | Recall memory | R/W/A | 保留，Reflect会调用模型但不据此要求W；是否有副作用遵循原生 |
| 15 | `POST B/reflect` | Reflect and generate answer | R/W/A | 保留，Reflect会调用模型但不据此要求W；是否有副作用遵循原生 |
| 16 | `GET /v1/default/banks` | List memory banks | 动态Key；扩展合并可见空间目录 | 保留可见性隔离；跨schema列表由外围聚合，不能直接读一个schema替代 |
| 17 | `GET B/stats` | Get statistics for memory bank | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 18 | `POST B/health/llm` | Test the bank's LLM connectivity | R/W/A，目标空间认证 | 原生通过GET_BANK_STATS读授权，允许状态探测并可能消耗模型调用；是否进一步限Admin属于产品策略，当前没有这样限制 |
| 19 | `GET B/stats/memories-timeseries` | Memory ingestion time-series | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 20 | `GET B/entities` | List entities | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 21 | `GET B/entities/graph` | Get entity co-occurrence graph | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 22 | `GET B/entities/{entity_id}` | Get entity details | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 23 | `POST B/entities/{entity_id}/regenerate` | Regenerate entity observations (deprecated) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 24 | `GET B/mental-models` | List mental models | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 25 | `GET B/mental-models/{mental_model_id}` | Get mental model | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 26 | `GET B/mental-models/{mental_model_id}/history` | Get mental model history | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 27 | `POST B/mental-models` | Create mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 28 | `POST B/mental-models/{mental_model_id}/refresh` | Refresh mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 29 | `POST B/mental-models/{mental_model_id}/dry-run-refresh` | Dry-run mental model refresh (preview, no persistence) | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 30 | `POST B/mental-models/{mental_model_id}/clear` | Clear mental model content | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 31 | `PATCH B/mental-models/{mental_model_id}` | Update mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 32 | `DELETE B/mental-models/{mental_model_id}` | Delete mental model | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 33 | `GET B/knowledge-base/tree` | Get the knowledge-base tree | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 34 | `POST B/knowledge-base/folders` | Create a knowledge-base folder | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 35 | `POST B/knowledge-base/pages` | Create a knowledge-base page | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 36 | `GET B/knowledge-base/export` | Export the knowledge base as a markdown bundle | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 37 | `GET B/knowledge-base/search` | Hybrid search over knowledge pages (BM25 + vector) | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 38 | `GET B/knowledge-base/pages/{page_id}` | Get a knowledge-base page | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 39 | `PATCH B/knowledge-base/nodes/{node_id}` | Rename/move a knowledge-base node or update a page's options | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 40 | `DELETE B/knowledge-base/nodes/{node_id}` | Delete a knowledge-base node | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 41 | `GET B/directives` | List directives | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 42 | `GET B/directives/{directive_id}` | Get directive | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 43 | `POST B/directives` | Create directive | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 44 | `PATCH B/directives/{directive_id}` | Update directive | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 45 | `DELETE B/directives/{directive_id}` | Delete directive | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 46 | `GET B/documents` | List documents | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 47 | `GET B/documents/{document_id:path}/chunks` | List document chunks | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 48 | `POST B/documents/{document_id:path}/reprocess` | Reprocess document | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 49 | `GET B/documents/{document_id:path}` | Get document details | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 50 | `GET B/tags` | List tags | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 51 | `GET /v1/default/chunks/{chunk_id:path}` | Get chunk details | R/W/A；解析canonical chunk目标 | 保留授权；拒绝歧义旧编码，不遍历schema |
| 52 | `PATCH B/documents/{document_id:path}` | Update document | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 53 | `DELETE B/documents/{document_id:path}` | Delete a document | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 54 | `GET B/operations` | List async operations | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 55 | `GET B/operations/{operation_id}` | Get operation status | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 56 | `DELETE B/operations/{operation_id}` | Cancel a pending or in-flight async operation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 57 | `POST B/operations/{operation_id}/retry` | Retry a failed async operation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 58 | `DELETE B/operations/{operation_id}/delete` | Delete a terminal async operation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 59 | `GET B/profile` | Get memory bank profile (removed — use GET .../config) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 60 | `PUT B/profile` | Update memory bank disposition (removed — use PATCH .../config) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 61 | `POST B/background` | Add/merge memory bank background (removed — use PATCH .../config) | 原生已废弃，合法空间请求通常410 | 不是自研功能遗漏，不恢复已退役端点；非法空间可能被外围先拒绝 |
| 62 | `GET B/aliases` | List the bank's aliases | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 63 | `POST B/aliases` | Add an alias to the bank | A/R/W均被Transport拒绝；写钩子也拒绝 | 别名不是迁移schema；可通过扩展解析alias→canonical并防跨空间冲突后恢复A管理，不直接放行 |
| 64 | `PATCH B/aliases/{alias}` | Show this alias in place of the bank id | A/R/W均被Transport拒绝；写钩子也拒绝 | 别名不是迁移schema；可通过扩展解析alias→canonical并防跨空间冲突后恢复A管理，不直接放行 |
| 65 | `DELETE B/aliases/{alias}` | Remove an alias from the bank | A/R/W均被Transport拒绝；写钩子也拒绝 | 别名不是迁移schema；可通过扩展解析alias→canonical并防跨空间冲突后恢复A管理，不直接放行 |
| 66 | `PUT B` | Create or update memory bank | 新Bank拒绝；既有Bank含name更新拒绝；纯config更新A可通过原生对应路径 | 展示名限制过强；扩展适配创建/更新，保留Admin和schema绑定；空/不同字段组合须补黑盒 |
| 67 | `PATCH B` | Partial update memory bank | 新Bank拒绝；既有Bank含name更新拒绝；纯config更新A可通过原生对应路径 | 展示名限制过强；扩展适配创建/更新，保留Admin和schema绑定；空/不同字段组合须补黑盒 |
| 68 | `DELETE B` | Delete memory bank | A/R/W均不能直接删Bank | 当前统一走workspace管理；建议由原生Bank入口调用同一外围生命周期 |
| 69 | `POST B/import` | Import bank template | A/R/W均被Transport拒绝 | 一刀切过强；模板dry_run/更新现有对象、documents模式、创建新目标需分开适配；仅放Validator不够 |
| 70 | `GET B/export` | Export bank template | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 71 | `GET B/document-transfer` | Export documents (removed — use POST .../document-transfer/export) | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 72 | `POST B/document-transfer/export` | Export documents (async) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 73 | `POST B/document-transfer` | Import documents (async) | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 74 | `POST B/transfer/export` | Export a bank (async) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 75 | `POST B/transfer/import` | Import a bank (async) | A/R/W均被Transport拒绝 | 一刀切过强；模板dry_run/更新现有对象、documents模式、创建新目标需分开适配；仅放Validator不够 |
| 76 | `POST B/clone` | Clone a bank (async) | A/R/W均被Transport拒绝 | 一刀切过强；模板dry_run/更新现有对象、documents模式、创建新目标需分开适配；仅放Validator不够 |
| 77 | `GET B/attachments/{attachment_id}` | Fetch an attachment retained inline with a document | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 78 | `GET /v1/default/files/download/{key:path}` | Download a stored file (async export archive) | 仅A | 运维信息/完整导出边界，保留；文档导出可另评W需要的最小权限，不因此全部开放 |
| 79 | `GET /v1/bank-template-schema` | Get bank template JSON Schema | 沿用原生入口规则；不经Bank CRUD策略 | 健康/版本/metrics及模板schema等服务入口；不声称新增Key保护覆盖所有非Bank路径 |
| 80 | `DELETE B/observations` | Clear all observations | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 81 | `GET B/observations/scopes` | List observation scopes | R/W/A，目标空间认证 | 保留；原生Bank配置、开关/资源存在性仍生效；不是新增禁用 |
| 82 | `POST B/consolidation-strategies/preview` | Preview consolidation strategies | R/W/A，目标空间认证 | 经list_observation_scopes读授权，只做策略匹配预览，不持久写入 |
| 83 | `POST B/consolidation/recover` | Recover failed consolidation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 84 | `DELETE B/memories/{memory_id}/observations` | Clear observations for a memory | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 85 | `GET B/config` | Get bank configuration | A可读允许字段；R/W字段投影为空 | 当前产品策略，保留凭据过滤；是否允许业务读非敏感配置可独立讨论 |
| 86 | `PATCH B/config` | Update bank configuration | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 87 | `DELETE B/config` | Reset bank configuration | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 88 | `POST B/consolidate` | Trigger consolidation | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 89 | `POST B/webhooks` | Register webhook | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 90 | `GET B/webhooks` | List webhooks | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 91 | `DELETE B/webhooks/{webhook_id}` | Delete webhook | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 92 | `PATCH B/webhooks/{webhook_id}` | Update webhook | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 93 | `GET B/webhooks/{webhook_id}/deliveries` | List webhook deliveries | GET仅A；POST/PATCH/DELETE连A也拒绝；当前启用记录阻止启动 | 写拒绝是已确认缺口；已定恢复全局/Bank能力，扩展补A写权限并撤销启动阻断 |
| 94 | `POST B/memories` | Retain memories | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 95 | `POST B/files/retain` | Convert files to memories | W/A；R拒绝 | 内容写或模型处理预算边界，扩展保留；文档导入限已存在空间，不能触发新Bank |
| 96 | `DELETE B/memories` | Clear memory bank memories | 仅A | 当前运维策略；清空、配置、任务控制与维护不授予普通业务W；可按产品需要另讨论 |
| 97 | `GET B/audit-logs` | List audit logs | 仅A可读历史；新增正文强制关闭 | 读权限保留；正文开启按O05恢复，不提供不可丢失保证 |
| 98 | `GET B/audit-logs/stats` | Audit log statistics | 仅A可读历史；新增正文强制关闭 | 读权限保留；正文开启按O05恢复，不提供不可丢失保证 |
| 99 | `GET B/llm-requests` | List LLM request traces | R/W/A按空间可读历史；新增Trace强制关闭 | 开启按O05恢复；现有空间读取权限不等于只给A，正文披露边界须组合测试 |
| 100 | `GET B/llm-requests/stats` | LLM request statistics | R/W/A按空间可读历史；新增Trace强制关闭 | 开启按O05恢复；现有空间读取权限不等于只给A，正文披露边界须组合测试 |

**共同限制：** 所有目标空间先校验已登记的canonical bank_id及格式；不支持借原生Retain隐式建立未登记空间。业务Key的GET任务列表/详情裁剪Webhook敏感诊断，include_payload=true仅A；表格普通任务GET的R/W允许不包含完整负载。模板/归档导出为A，知识库export单独属于knowledge.read，不能一概禁止。配置health、LLM健康等仍可受原生开关与资源状态限制。

## 4. Validator操作完整对照

下表说明外部客户调用；原生internal Worker另按已登记bank/schema、tenant UUID和空间状态校验，不重新用客户Key认证已受理任务。创建/删除的受信管理上下文不等于客户可传internal=true。

### 4.1 BankReadOperation：32项

| 操作 | 当前Validator | 外围附加限制及必要性 | 扩展恢复判断 |
| --- | --- | --- | --- |
| `EXPORT_KNOWLEDGE_BASE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_BANK_CONFIG` | R/W/A，memory.read | 业务GET config字段被投影为空；不回显凭据 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_BANK_PROFILE` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_BANK_STATS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_CHUNK` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_DIRECTIVE` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_DOCUMENT` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_ENTITY` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_ENTITY_GRAPH` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_ENTITY_STATE` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_GRAPH_DATA` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_KNOWLEDGE_BASE_TREE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_KNOWLEDGE_PAGE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_MEMORIES_TIMESERIES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_MEMORY_UNIT` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_MENTAL_MODEL_HISTORY` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_OBSERVATION_HISTORY` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `GET_OPERATION_STATUS` | R/W/A，memory.read | include_payload额外限A；业务Webhook任务诊断裁剪 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_BANK_ALIASES` | R/W/A，memory.read | 只允许canonical目标；别名写入/解析恢复另算 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_DIRECTIVES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_DOCUMENT_CHUNKS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_DOCUMENTS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_ENTITIES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_MEMORY_UNITS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_MENTAL_MODEL_TAGS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_MENTAL_MODELS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_OBSERVATION_SCOPES` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_OPERATIONS` | R/W/A，memory.read | include_payload额外限A；业务Webhook任务诊断裁剪 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_TAGS` | R/W/A，memory.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_WEBHOOK_DELIVERIES` | A，且检查memory.read | 保留Admin诊断权限；Webhook写/启动禁用另算 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `LIST_WEBHOOKS` | A，且检查memory.read | 保留Admin诊断权限；Webhook写/启动禁用另算 | 该读操作无默认拒绝遗漏，维持/按产品细分 |
| `SEARCH_KNOWLEDGE_BASE` | R/W/A，knowledge.read | 保留空间边界；原生参数及资源存在性约束继续生效 | 该读操作无默认拒绝遗漏，维持/按产品细分 |

### 4.2 BankWriteOperation：40项

“必要性”不以代码默认拒绝作为依据；六项默认拒绝均明确列出。

| 操作 | 当前Validator | 限制必要性、恢复方式 |
| --- | --- | --- |
| `CANCEL_OPERATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CLEAR_MENTAL_MODEL` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CLEAR_OBSERVATIONS` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CLEAR_OBSERVATIONS_FOR_MEMORY` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `CREATE_BANK_ALIAS` | 默认拒绝，且Transport先拦截 | 别名可恢复但需canonical解析和跨空间无歧义规则；不需要搬迁schema |
| `CREATE_DIRECTIVE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_KNOWLEDGE_FOLDER` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_KNOWLEDGE_PAGE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_MENTAL_MODEL` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `CREATE_WEBHOOK` | 默认拒绝，A也拒绝 | 非必要永久限制；已确认通过扩展恢复A操作 |
| `DELETE_BANK` | 仅受信workspace删除；内容清空经专用标识允许A | 可由统一Bank生命周期适配入口复用；不可只改为Admin就跳过元数据清理 |
| `DELETE_BANK_ALIAS` | 默认拒绝，且Transport先拦截 | 别名可恢复但需canonical解析和跨空间无歧义规则；不需要搬迁schema |
| `DELETE_DIRECTIVE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_DOCUMENT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_KNOWLEDGE_NODE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_MENTAL_MODEL` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `DELETE_OPERATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `DELETE_WEBHOOK` | 默认拒绝，A也拒绝 | 非必要永久限制；已确认通过扩展恢复A操作 |
| `IMPORT_DOCUMENTS` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `MERGE_BANK_MISSION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `MOVE_KNOWLEDGE_NODE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `RENAME_KNOWLEDGE_NODE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `REPROCESS_DOCUMENT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `RESET_BANK_CONFIG` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `RETRY_FAILED_CONSOLIDATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `RETRY_OPERATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `RUN_CONSOLIDATION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `SET_BANK_MISSION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `SUBMIT_ASYNC_CONSOLIDATION` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `SUBMIT_ASYNC_GRAPH_MAINTENANCE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `SUBMIT_ASYNC_VECTOR_INDEX_MAINTENANCE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_BANK` | 默认拒绝，A也拒绝 | 展示名/mission更新不等于bank_id变更；应补A字段授权。不同入口config路径另算 |
| `UPDATE_BANK_CONFIG` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `UPDATE_BANK_DISPOSITION` | 仅A | 运维/配置策略，当前保留；不是原生不支持 |
| `UPDATE_DIRECTIVE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_DOCUMENT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_KNOWLEDGE_PAGE` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_MEMORY_UNIT` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_MENTAL_MODEL` | W/A | 保留读写边界；后台提交钩子是正常内容处理，不应删掉 |
| `UPDATE_WEBHOOK` | 默认拒绝，A也拒绝 | 非必要永久限制；已确认通过扩展恢复A操作 |

### 4.3 其他钩子和前置操作

| 钩子 | 当前策略 | 结论 |
| --- | --- | --- |
| validate_create_bank | 只允许受信生命周期调用；Admin直接原生创建也拒绝 | 新Bank无schema/元数据，需外围创建流程；不能仅放行钩子 |
| validate_retain / validate_consolidate / validate_mental_model_refresh | memory.write | W/A；原生自动整合和内容派生任务继续保留 |
| validate_recall / validate_mental_model_get | memory.read | R/W/A |
| validate_reflect | reflect | R/W/A，当前权限投影均包含reflect |
| bank_list_scope | 返回当前目标的可读Bank；内部维护按schema取Bank | 根列表由扩展聚合；单schema原生列表不能代表全部空间 |
| filter_mcp_tools | 业务按读写范围；A允许原生工具集减create/update/delete_bank | 目录隐藏不是执行授权，不能用目录出现证明可调用 |
| validate_memory_update | 未覆盖该可选钩子，沿用原生默认 | 不能据此判越权；对应修改仍经UPDATE_MEMORY_UNIT及Tenant，需黑盒组合确认 |
| 其余通知/计量回调 | 沿用原生基类默认，不等于新增权限检查 | 不宣称自研提供原生Cloud完整IAM、审计或配额 |

- `precheck.DRY_RUN_EXTRACT`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.FILES_RETAIN`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.MENTAL_MODEL_CREATE`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.MENTAL_MODEL_REFRESH`：W/A，memory.write；前置检查通过不替代完整操作授权。
- `precheck.RECALL`：R/W/A，memory.read；前置检查通过不替代完整操作授权。
- `precheck.REFLECT`：R/W/A，reflect；前置检查通过不替代完整操作授权。
- `precheck.RETAIN`：W/A，memory.write；前置检查通过不替代完整操作授权。

## 5. 原生MCP工具完整对照

以下为原生工具全集；单Bank模式本来就不提供全部管理工具，这是原生模式差异，不是自研遗漏。原生全局/Bank工具allowlist仍可进一步收窄。表内不把“隐藏”与“执行拒绝”混为同一机制。

| 原生工具 | 业务R | 业务W | Admin | 必要性与恢复 |
| --- | --- | --- | --- | --- |
| `cancel_operation` | 隐藏/拒绝 | 隐藏/拒绝 | 可见，实际执行仍经钩子 | A运维边界，保留；业务如需再单独讨论 |
| `clear_memories` | 隐藏/拒绝 | 隐藏/拒绝 | 可见，实际执行仍经钩子 | A运维边界，保留；业务如需再单独讨论 |
| `clear_mental_model` | 隐藏/拒绝 | 隐藏/拒绝 | 可见，实际执行仍经钩子 | A运维边界，保留；业务如需再单独讨论 |
| `create_bank` | 隐藏/拒绝 | 隐藏/拒绝 | 隐藏/拒绝 | 统一Bank API方案需让MCP也调用同一生命周期，不能只恢复目录 |
| `create_directive` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `create_knowledge_folder` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `create_knowledge_page` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `create_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_bank` | 隐藏/拒绝 | 隐藏/拒绝 | 隐藏/拒绝 | 统一Bank API方案需让MCP也调用同一生命周期，不能只恢复目录 |
| `delete_directive` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_document` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_knowledge_node` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `delete_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_bank` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_bank_stats` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_document` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_knowledge_base_tree` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_knowledge_page` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_memory` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_mental_model` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `get_operation` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `invalidate_memory` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_banks` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_directives` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_documents` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_memories` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_mental_models` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_operations` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `list_tags` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `recall` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `reflect` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `refresh_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `retain` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `search_knowledge_base` | 可见并按目标执行 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `sync_retain` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `update_bank` | 隐藏/拒绝 | 隐藏/拒绝 | 隐藏/拒绝 | 应补Admin更新展示属性，现有整工具隐藏过强 |
| `update_knowledge_node` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `update_memory` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |
| `update_mental_model` | 隐藏/拒绝 | 可见并按目标执行 | 可见，实际执行仍经钩子 | 保留当前读写和目标空间授权，不做跨消息缓存 |

## 6. 复用Bank API作为工作空间管理：明确结论

**长期候选方向，暂不实施：工作空间是产品展示名，评估API统一采用原生Bank资源、减少独立workspace CRUD。现有工作空间管理接口继续保留，不删除、不切换调用方。** 保留ctxdb_meta中的空间身份/授权/schema登记，它是Bank的服务化元数据，不是第二套可独立存在的业务资源。此为候选方案，不是当前实施清单；须先完成隔离原型、充分测试和兼容性评估，再确认是否实施，尚未变更现有接口合同。

| 接口职责 | 建议外部入口 | 外围仍需做什么 |
| --- | --- | --- |
| 创建或更新 | PUT /v1/default/banks/{bank_id} | Admin；新对象登记UUID、创建schema并迁移、调用原生Bank实现、成功激活/失败状态；已有对象按原生字段更新，不重复迁移 |
| 更新已有对象 | PATCH /v1/default/banks/{bank_id} | 按原生create_if_missing=false，不因PATCH隐式创建；Admin更新展示属性/配置，稳定bank_id不变 |
| 列表 | GET /v1/default/banks | 复用现有跨schema目录聚合及Key可见性，不另建workspace列表资源 |
| 删除 | DELETE /v1/default/banks/{bank_id} | Admin；调用同一生命周期，清理Key授权、元数据及专属schema；保留停流量约束 |
| 详情 | 原生列表/已有Bank详情工具，按客户端需要选取 | 原生http.py没有GET /banks/{bank_id}，/profile也已410；不能声称直接复用这个不存在的GET。若确需单对象REST详情，明确只新增一个Bank详情适配或用列表定向查询，另评契约 |

**为什么不能直接删管理代码、只放行Admin。**

1. 原生Tenant认证在Bank操作前执行，现有认证要求目标已经登记且active；新Bank还不存在metadata/schema，不能正常进入原生create。
2. 原生Bank写入只在选定schema操作，不负责给每个Bank新建schema；原生的validate_create_bank是前置校验，并非完整创建事务扩展槽。
3. 原生delete_bank删Bank数据，不负责删除ctxdb_meta授权/登记或DROP专属schema，Validator也没有可靠的“原生删除提交后”通知。把跨资源写入塞进验证钩子会产生失败残留和重复调用风险。
4. 因此，最小方案仍是扩展HTTP适配层在原生URL处接管生命周期分派，复用现有Lifecycle/原生引擎操作；使用原生路径不等于不需要外围实现。MCPExtension的create_bank/delete_bank也必须接入同一服务，否则REST能管理而MCP仍拒绝。

**简化收益与保留成本。**

- 早期候选曾考虑删除全部 workspace CRUD；第9章改为收敛创建/删除入口、保留必要的只读管理查询，不再宣称移除全部四项路由。
- 可恢复Admin通过原生Bank URL及SDK操作，不再要求客户掌握第二套路由。
- 仍保留一次外围创建/删除协调、schema迁移、动态Key权限、UUID、目录聚合、失败状态和元数据清理；不能承诺核心管理代码全部删除或复杂度骤降。
- PUT原生是创建或更新；现workspace POST是严格创建201/冲突409。第9章拟沿用原生PUT/PATCH的BankProfileResponse及DELETE的DeleteResponse，保留必填身份If-Match；这会要求原生删除调用方适配，不再沿用早期“不强制If-Match”的建议。删除前停流量及等待已有工作结束仍是独立前提。
- description不是原生CreateBankRequest的等价现成字段，是否保留metadata描述或映射到独立展示字段需明确；不能把mission当空间描述。展示name（原生已标deprecated，但仍兼容）与稳定bank_id区分，更新name不改schema；命名要求仍受PG schema长度和metadata唯一约束，复用URL不会自动恢复任意原生bank_id。
- 别名仍需全局入口alias→canonical解析，模板导入/恢复/克隆仍需分别适配目标创建、现有内容导入或两空间权限。API统一后这些问题不会自动消失。

## 7. 后续可执行的验证与取舍

1. 枚举40项write、32项read和MCP全集，测试每项都显式归类；增加Admin、R、W的对应负例/正例，避免新枚举静默落默认拒绝。默认拒绝继续保留给未审定的新操作。
2. 优先补UPDATE_BANK的展示名/mission/config字段组合，验证PUT已有/不存在、PATCH已有/不存在；别把展示名修改误当bank_id迁移。
3. 按已定O05恢复Trace/Audit/Webhook，重点检查组合任务正文与诊断凭据边界。
4. Bank API方案先做插件内原型：Admin原生SDK创建、更新、列出、删除，普通Key不能创建；新schema/metadata一致，失败后可查询核对。验证MCP相同能力而非只恢复工具清单。
5. 单独评模板dry_run、更新现有空间、documents/restore模式、克隆新目标、别名；不能用权限放行替代目标schema及metadata协调。
6. 文档接口表的“允许”只是源码结论；逐接口黑盒、取消/超时、并发与失败注入NOT RUN，后续不得据此称原生功能全部验收。

本次只新增检视分析文档，不修改源码、既有设计合同或运行实例，不提交/推送。审核结论为REVISE，待确认Bank API合同及恢复范围后再实施。


## 8. Bank API统一方案暂缓实施决定（2026-10-21）

**暂不删除工作空间管理接口，暂不切换UI、SDK或其他调用方。** 该方案涉及管理入口、创建/更新语义、返回值、schema与元数据生命周期、权限以及MCP入口，属于相对较大的接口调整。第6章保留为后续研究方案，不作为当前获准实施项，也不作为O04/O05的前置依赖。

重新决定实施前，至少完成：

1. 隔离原型证明Admin可通过原生Bank API及SDK创建、更新、列出和删除，MCP使用同一生命周期；普通业务Key不能绕过权限。原型不替换现有服务入口。
2. 新schema、元数据、授权一致性及失败清理测试；创建/删除部分失败、超时、断连和并发场景有明确结果核对方式，符合已接受的生命周期约束。
3. 原生PUT创建或更新、PATCH不创建、响应结构、错误码、名称/描述、详情查询及现有条件请求的合同逐项明确；对UI、管控和SDK调用方进行影响评估。
4. 原生相关回归与插件REST/MCP/UI端到端验证充分通过，覆盖两种Worker、权限隔离、删除同名重建；证据和未完成项可供检视。
5. 基于验证结果另行确认切换范围与步骤，再将候选方案转为实施任务。

现有workspace接口继续维护。接口权限遗漏、Trace/Audit/Webhook恢复等已明确事项可独立推进，但不因此自动允许原生Bank生命周期绕过现有元数据管理。本文其他恢复建议仍按各自决定和验收标准处理。本次仅更新文档，不修改代码、接口或运行环境。

<a id="bank-api-reuse-design"></a>

## 9. 复用 Bank 接口管理空间：设计方案（Issue #53）

状态：REST隔离原型已在本地工作树实现（2026-10-29），未提交、未部署。源码基准为本地HEAD `9a5ba2c61d27a2a6c94cd91b9e3a6089325df6b5`，相关上游实现与已合入main `93640b6c1395423c1669048cef84c4e61a545002`一致。以下合同同时区分已验证的REST原型与后续UI/MCP切换设计；实现与验收范围见第9.10节及VALIDATION第28章。现有workspace POST、description及UI调用完整保留，MCP管理未开放，现网行为未改。

### 9.1 目标与取舍

对外复用 Bank 创建、更新、删除入口，ContextDB 插件负责空间元数据、独立 schema 和授权关系的生命周期。Bank 与 workspace 仍一对一；`ctxdb_meta.workspaces`、不可变空间 UUID、版本及状态继续保留，不能因减少外部接口而删除内部身份模型。

推荐收敛创建、删除入口，同时保留必要的管理员只读空间目录/详情查询，用于失败对象、UUID、版本、描述及删除条件。当前 ContextDB 适配的 Bank 列表只返回 active 对象，原生响应没有这些管理字段，不能替代完整管理目录。保留查询意味着不是一次移除全部四项 workspace CRUD；本方案不以减少接口数量作为验收目标。

复用 Bank 路径有利于 SDK、CLI 和 UI 使用同一资源入口，但不消除外围协调代码，也不代表原生客户端可以无条件迁移。现有 workspace 接口仍是可用方案；若原型必须复制整套原生端点或改写引擎才能成立，应保留现有入口，重新评审收益。

### 9.2 插件模式与 REST 行为

是否改变行为取决于扩展是否实际启用，不取决于是否仅安装 Python 包；沿用现有插件加载条件，不新增生产开关。未启用 ContextDB 时，使用原生应用及原生配置，不能挂载 ContextDB transport 或改变 Bank 合同。启用时继续要求匹配的 Tenant、Validator、HTTP 扩展及自研 ASGI 入口，配置不完整时按既有规则拒绝启动，不能静默退回不受控原生模式。

| 请求 | 未启用 ContextDB | 启用 ContextDB 后的拟议行为 |
| --- | --- | --- |
| `GET /v1/default/banks` | 原生列表 | 保留现有按空间聚合、权限过滤、搜索和分页的 Bank 目录；只返回 active 对象 |
| `PUT /v1/default/banks/{bank_id}`，目标不存在 | 原生创建或更新逻辑 | 仅 Admin 可创建；验证请求后在短事务中处理可选创建条件并登记 UUID/creating，初始化独立 schema，调用一次原生 Bank 创建，完成后激活；成功沿用 `200 BankProfileResponse` |
| 无条件 PUT，目标已 active | 原生更新逻辑 | 仅 Admin 更新，调用 `update_bank(create_if_missing=False)`；不生成 UUID、不重新迁移，Bank 行缺失则404而非隐式重建；成功沿用 `200 BankProfileResponse` |
| PUT 携带 `If-None-Match: *` | 不改变社区原生行为，不额外承诺该条件生效 | 插件严格创建：已登记任何状态的目标返回412；创建条件与身份预留在同一事务，不能先 GET 再创建 |
| `PATCH /v1/default/banks/{bank_id}` | 原生仅更新逻辑 | 仅 Admin 更新本入口管理的属性；保持 `create_if_missing=false`，不存在返回404；成功沿用 `200 BankProfileResponse` |
| `DELETE /v1/default/banks/{bank_id}` | 原生删除及 `DeleteResponse` | 仅 Admin，先校验身份 ETag，再执行完整空间删除；全部成功后返回 `200 DeleteResponse`，不再使用 workspace DELETE 的204 |
| 既有 workspace GET 列表/详情 | 插件路由不存在 | 保留管理员只读管理视图，详情返回身份 ETag；可查询非 active 及部分失败对象 |
| 既有 workspace POST/DELETE | 插件路由不存在 | 调用方迁移完成后下线；迁移期只能调用同一生命周期实现，不维护两套独立创建器/删除器 |

以上 Admin 限制针对这些 Bank 管理入口，不收紧独立 Bank config 接口当前的字段策略，不放开普通只读、读写或 all Key 的管理权限。其他内容接口继续逐请求核对身份、目标和原有读写规则。

`creating/deleting/failed` 不能当作 PUT 的普通“已存在”分支更新，也不能静默重试创建；返回明确冲突并引导管理员从只读视图核对结果。新创建时遇到孤立 schema 或归属冲突同样拒绝，不接管不明对象。

### 9.3 字段、身份条件与兼容边界

1. **保留原生字段语义。** `bank_id` 是稳定地址，继续遵守 ContextDB 当前名称规范化、长度和 schema 归属规则；更新原生 `name` 只改变展示名，不改变 UUID、bank_id 或 schema。原生 `name` 虽已标 deprecated，仍按当前兼容规则处理。管理视图和授权选择器仍使用稳定 bank_id/UUID，不新增一份可漂移的展示名真值。
2. **保留当前描述能力。** 原生 mission/config 会影响业务行为，不是workspace description，description不能映射为mission。本次原型新增Bank REST入口，新Bank的描述为空；旧workspace POST与创建UI继续支持description，已有描述不变。用户未授权删除该能力，因此本次不迁移UI或退役旧POST。以后若统一全部写入口，再评审最小插件描述字段合同或明确产品取舍，不为本次原型预建第二套CRUD。
3. **不扩充原生响应体。** 引擎返回 profile 或计数字典，边界适配层按原生映射构造 `BankProfileResponse` / `DeleteResponse`，不能把引擎返回值直接当作 HTTP 模型。删除计数为 `memory_units_deleted + entities_deleted + documents_deleted`；本次没有执行原生删除的残留清理计数为0，不推算前次已提交的数量，不统计 DROP SCHEMA 对象数。协调器保留一次执行结果，不为凑响应重新执行操作；响应不塞入 UUID/state/description。管理身份与失败状态从插件只读视图获取；原生没有 `GET /banks/{bank_id}`，已退休的 `/profile` 不恢复。
4. **删除仍要求身份 ETag。** 先读取管理详情，取得 `"<workspace_id>:<version>"`，再通过原生 Bank DELETE 路径发送 `If-Match`。保持现有缺失条件428、格式错误400、身份/版本不符412；不存在返回404。已完成删除后重复请求不宣称幂等成功；同名重建的旧 ETag 必须失败。该版本是空间生命周期版本，不随展示名、mission 或业务内容自动递增；它保护对象身份/管理状态，不是 Bank 内容的完整乐观锁。
5. **不能在代理内补取最新 ETag 后自动删除。** 这会丢失用户确认时的目标身份。UI 必须传递确认时的条件，结果未知后只发 GET 核对，不自动重放删除。HTTP 条件并非排空或跨进程执行屏障。
6. **SDK 只部分直接兼容。** 满足名称规则、使用有效 Admin 的无条件创建/更新/列表可按原生路径接入；无条件 PUT 仍是 upsert，不能承诺严格创建。删除客户端须先取得管理身份并显式传 `If-Match`。已核对的逐请求头能力见下表；原型不要求修改生成 SDK 或 CLI。业务 Key 的业务读写按既有合同保留。
7. **未纳入的创建旁路继续拒绝。** retain 等业务请求不能隐式创建未知 Bank。导入、克隆、恢复、别名等按现有限制处理，不因统一 Bank URL 顺带开放。整 Bank 删除与 `DELETE .../memories` 内容清空严格区分：内容清空保留空间和授权，按既有扩展表登记清理统计数据。

8. **创建 UI 保持严格创建。** ContextDB 创建 UI 必须发送单个 `If-None-Match: *`。插件只支持这一种可选条件值，其他格式返回400，不实现通用 ETag 框架；Admin 验证后，在既有身份预留事务内判断规范 bank_id，已有任何状态的登记返回412。同名并发后到请求同样412，不能先 GET 后 PUT；仅映射目标 bank_id 的存在/唯一冲突，孤立 schema 仍409 `schema_conflict`，不能把所有数据库错误改成412。无条件 PUT 遇 creating/deleting/failed 仍409，不等待其完成后自动转为更新。未启用插件时不新增条件语义。

| 当前客户端 | 已核对的条件头能力 | 拟议插件模式下的使用方式 |
| --- | --- | --- |
| Python 高层 `delete_bank/adelete_bank` | 方法只接 bank_id，不暴露逐请求头 | 默认删除不兼容必填条件；使用生成底层或独立 REST 请求 |
| Python 生成 `BanksApi.delete_bank` | 支持逐请求 `_headers` | 从管理详情读取 ETag 后传入 `If-Match`；仍需原型端到端验证 |
| TypeScript 高层 `deleteBank` | 方法仅有 signal；构造时 headers 属于实例全局 | 默认删除不兼容；使用请求级低层适配，不能修改共享实例全局条件头 |
| 现成 CLI Bank 删除 | 命令只有 bank_id/yes，没有 If-Match 参数 | 第一阶段使用 REST 替代，不宣称直接兼容，不为原型修改 CLI |
| MCP 管理工具 | 缺少删除条件参数，现有工具结果也不提供空间 ETag | 第一阶段继续关闭，后续按独立合同接入 |

源码位置：`hindsight-clients/python/contextbase_client/contextbase_client.py:3238`、`hindsight-clients/python/contextbase_client_api/api/banks_api.py:1261`、`hindsight-clients/typescript/src/index.ts:1143`、`hindsight-cli/src/main.rs:290` / `src/api.rs:683`。上述为源码能力核对，不是兼容性运行通过记录。

复用 Bank 路径是插件模式下的行为适配，不是与社区完全等价的协议。插件 OpenAPI/使用说明须显式列出 Bank 根路径的可选 `If-None-Match`、必填 `If-Match`、响应与412/428等错误；不能只更新旧 workspace 路径。原生模式的 OpenAPI 和生成 SDK 不因本方案被强制改变。

### 9.4 插件实现位置与调用链

下表为目标职责；本次仅完成REST原型，具体落地范围见第9.10节，UI/MCP切换仍未实施。插件路径前缀为 `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/`。

```text
原生 Bank REST 路径
  ├─ 原生应用（未启用 ContextDB） → 原生路由/引擎
  └─ ContextDB ASGI → 精确的 Bank 管理请求分派
                       → Admin 身份及完整参数验证
                       → 共享生命周期服务
                       → 新建/删除：限定用途的受信管理上下文
                         已有更新：外部 Admin 上下文与正常目标认证
                       → 原生 Bank 引擎（一次）
                       → 必要元数据收尾及类型化响应
MCP 管理工具（后续接入） ────────────┘
```

| 文件/模块 | 拟议职责 | 需要保留的边界 |
| --- | --- | --- |
| `asgi.py`、`transport.py` | 保留扩展包围原生应用的方式；在常规目标空间认证前，精确匹配 Bank 根资源的 PUT/PATCH/DELETE，交给小型管理适配函数；现有 GET 目录逻辑复用 | 不能前缀匹配所有子路径；不能误接管 config、memories、chunks 等请求；不读取 MCP 消息体猜目标，不重复解码路径 |
| `lifecycle.py` | 最小调整现有共享服务，接受已验证 Bank 参数，区分创建/更新；保留实际原生返回值，由边界构造协议响应 | 新建/删除才使用受信管理上下文；已有 active 更新保持外部 Admin 上下文；不新增 update_workspace 管理用途，不重复转发执行 |
| `repository.py`、`authorization.py` | 复用元数据短事务、归属检查、UUID/版本条件及限定目标/用途的管理上下文 | 客户端不能通过 header、body 或 MCP 参数伪造 internal/schema；管理事务不跨原生 DDL 等待 |
| `tenant.py`、`validator.py` | 仅补足受控管理入口及已有 Bank 更新的策略；业务请求仍按已登记 active 空间授权 | 必须先验证真实 Admin 和请求，才能建立限定管理上下文；沿用原生字段/配置验证，不把受信上下文当作跳过验证的总开关 |
| `http.py` | 保留只读管理视图和 ETag；按切换阶段退役旧 workspace POST/DELETE，并更新插件 OpenAPI | 不改变用户、Key、usage 的既有权限；不把只读管理视图开放给普通业务 Key |
| `mcp.py` | 后续让 create/update/delete Bank 工具通过同一服务；目录与执行策略一致 | 保留当前消息身份、全局/Bank 工具白名单，不跨消息缓存授权 |

不能仅放开 `validate_create_bank()`：原生 `update_bank()` 先认证 Tenant，新目标尚未登记就会被拒绝；该钩子是前置校验，不提供完成激活、失败收尾及删除授权清理的完整生命周期。不要在权限钩子里承担这些副作用。

也不能通过 `HttpExtension.get_root_router()` 注册同名 Bank 路由，假定后注册路径能可靠覆盖原生端点；应沿用现有 transport 入口。不要 monkey patch 引擎、替换 FastAPI 路由表、复制整个原生处理器，或直接写原生 banks 表。

这是“优先不改原生 Python”的实现目标，不是已经证实的零侵入成果。外层 transport 直接响应会绕过原生路由及内层中间件，不只绕过 HTTP 审计装饰器。原型必须逐项核对：请求/响应模型、字段转换、依赖与异常映射、参数错误状态/类型、未知参数报告（包括 `X-Ignored-Params`）、HTTP 指标/追踪及适用审计。仅复用模型和一次引擎调用不自动保留这些能力。

原型用插件内三个FastAPI处理器复用原生请求/响应模型、UnknownParamsRoute、HttpObservabilityMiddleware及GzipMiddleware；原生外层FastAPI instrumentation继续包围分派，追踪不重复安装。异常映射复用原生_internal_error，包括包装的StoreWriteUnavailable→503/Retry-After、稳定JSON500，以及原生AuthenticationError→401。该内部辅助函数是明确的上游耦合点，升级时由故障合同测试约束，不修改其原生源码。

本版Settings及Bank配置策略要求原生Audit关闭；原型不执行原生审计装饰器的逐Bank配置探测，避免新建schema前或删除schema后查询错误目标。Repository的管理审计继续保留。观测/故障单测和真实新库日志补证见VALIDATION第28章，不把Mock审计调用一次等同真实Audit可用。原生断连取消不针对Bank PUT/PATCH/DELETE，不新增管理断连取消器。不复制原生端点/中间件或建立第二套观测框架；原型未保留的重要合同须先报告，不顺带扩大内核修改。

### 9.5 生命周期与失败处理

**创建：** Admin 鉴权、规范化及不依赖目标 schema 的参数/配置验证 → 同一短事务检查可选创建条件并预留 UUID/creating → 验证 schema 归属 → 原生迁移及插件表 provision → 受信目标上下文执行一次原生创建 → 核对 Bank → 激活并记录管理审计。依赖目标 schema 的原生检查在受控初始化后、激活前完成。当前 `Lifecycle.create()` 只传入 name；适配时必须接住原生支持的 disposition/mission/config 字段，不能无声忽略，也不能在验证失败时留下一个 active 空间。

**更新：** 分支以管理目录为准；仅 active 且无严格创建条件的目标进入更新。已有 active PUT 与 PATCH 均使用 `update_bank(create_if_missing=False)`，Bank 行缺失返回404，不在旧 UUID/授权下自动重建。使用外部 Admin RequestContext、bank_target 及正常 Tenant/字段权限检查；仅补足 UPDATE_BANK 的 Admin 策略，不扩张受信管理用途。不改变身份、schema 或 selected 授权，不重复初始化。展示名以 Bank 为准，不改目录稳定地址。

**删除：** Admin 和身份条件验证 → 标记 deleting → schema 归属检查 → 对存在的 Bank 执行一次原生删除 → 清理 selected 授权、递增受影响 Key 编辑版本、删除专属 schema/元数据并记录管理审计。失败空间没有 Bank 行时，只清理已经验证归属的残留；不为不存在的原生操作伪造删除计数。

原生执行成功但激活/删除收尾失败时，不能返回整体成功；创建/删除异常保留 failed 或结果未知状态供管理员核对。超时、断连或取消不代表实际执行停止，不能自动重放 PUT/DELETE，也不新增后台自动修复任务。不要把跨原生事务、DDL、文件清理和管理事务的多步流程描述为整体原子事务。

GET 只用于核对，不是恢复。failed 在确认旧执行已结束后，可持当前 ETag 再次 DELETE；creating/deleting 不会因查询或停服自动解锁，当前没有公开恢复 API/CLI。后两类须在维护窗口按 UUID、schema 归属、实际 Bank/DDL 结果由运维核查处置；未经验证的手工状态修改不算已支持功能。原型必须形成可审阅的停服处置步骤，或明确保留恢复验收缺口，不新建恢复框架。原生数据提交后文件/索引失败的边界继续保留，再次删除不保证修复所有事务外残留。

删除前仍由管理员停止业务访问并等待已有请求及后台工作结束。标记 deleting 只能关闭后续目标准入，不能排空已经接受的工作。本方案不新增删除调度器、租约、代次屏障或准入连接池。同名重建产生新 UUID，旧 selected 授权和旧事件不继承；all 授权继续沿用“当前及未来空间”的既有含义。

### 9.6 MCP 兼容范围

建议先完成 REST 合同和隔离原型，再接入 MCP；MCP 管理工具启用前继续保持现有隐藏/拒绝行为，并在使用说明中明确阶段差异。仅 REST 成功不能声明 MCP 生命周期已支持。

MCP 接入必须在普通 active 目标认证前识别受控管理工具，处理 Admin 零 Bank 冷启动：工具发现与首个 Bank 创建不能先要求已有 active Bank；仍验证消息当前凭据及全局白名单，已有目标继续执行对应 Bank 白名单。不能从外层分派直接调用协调器而绕过原生工具策略。共享生命周期服务，不建设通用工具替换框架。

REST 与 MCP 不共用一个不分协议的字段转换器。当前 MCP create 有 name/mission 时走 `update_bank(mission=...)`，无字段时走 `ensure_bank_profile`；MCP update 原生默认 upsert，而 REST PATCH 是 update-only。后续按各工具原生字段语义和管理目录分支明确转换、条件及缺失目标行为，不能因为工具名为 update 就宣称等同 PATCH。

删除工具既需要条件参数，也需要调用者取得条件的渠道。现有 list/profile 不提供空间 UUID/version/ETag，保留 REST 管理 GET 不等于纯 MCP 客户端已能取得这些信息。后续须明确管理员只读工具或管理结果中的条件获取合同、工具 schema 和白名单，再启用管理工具；REST+MCP 混合客户端也必须先取得并显式传递用户确认时的条件。不能临时补取最新 ETag 替代确认，不承诺原生 MCP schema 完全不变，也不为保持旧 schema 取消删除条件。

### 9.7 必要 UI 改动及原生侵入范围

UI 仍显示“工作空间”产品概念；不改变团队 ContextBase 品牌、locale、productFetch/标签页身份、会话撤销以及 Host/Origin 校验。核心逻辑放在自研组件，原生文件只保留必要接线。

| 位置 | 必要改动 | 是否涉及原生文件 |
| --- | --- | --- |
| `components/contextdb/create-workspace-dialog.tsx`、`workspaces-view.tsx`、`workspace-result-check.tsx` | 原型通过且描述取舍确认后，创建切换到携带 If-None-Match:* 的 Bank PUT，412显示同名冲突；成功后查管理身份并刷新目录，失败/未知只查询 | 自研组件 |
| `components/contextdb/use-key-workspaces.ts` 及授权选择器 | 继续从管理视图取得 workspace UUID，保留服务端搜索、分页、已选授权及同名重建隔离；不能用原生 Bank 列表的 bank_id 替换 UUID | 自研组件 |
| `lib/contextdb-api.ts`、ContextDB 管理代理 | 增加小型 Bank 管理请求适配，识别 PUT/200/BankProfileResponse；保留只读元数据核对、两个条件头、request_id及unknown/conflict判断，不复用仅接受201/Workspace的旧校验 | 自研模块/既有插件接线 |
| `src/app/api/banks/[bankId]/route.ts` | 按后端完成情况调整 ContextDB 模式下现有 PUT/DELETE 及 PATCH name 拦截；受保护地逐请求转发 If-None-Match / If-Match、状态和响应，原生模式保持当前行为 | 原生 UI 文件的必要条件分支修改 |
| `components/bank-selector.tsx`、既有 Bank 创建/删除调用方 | 复用自研创建与确认逻辑；仅在实际调用链需要时调整接线，不额外复制一套原生管理 UI | 可能涉及最小原生 UI 接线，实施前逐项确认 |

创建不能把 BankProfileResponse 强转 Workspace；原生200成功后，从管理 GET 取得 UUID/state 等所需信息。`respondWithSdk` 可能重塑错误体，代理需保留现有管理错误码、request_id和未知结果判断。条件头使用逐请求传递，不改共享 SDK 的全局 headers 或原生 `lib/api.ts` 通用删除 helper。删除确认先获取并保存身份 ETag，确认时携带同一条件。目录刷新、查询失败、弹窗焦点恢复、UUID 授权、主题和窄屏可达等既有修复继续保留。不能吞掉428/412，不能以查询失败伪装为空实例。

后端预期不修改 `hindsight-api-slim/hindsight_api/`、原生 Store、迁移及生成 SDK；UI 则不能承诺零原生改动。原生 Python 或公共 Dialog 等非必要变更不纳入本方案。

### 9.8 切换步骤与验收条件

1. 按本节固定 REST 响应、错误码、条件创建/删除及 MCP 分期，先做隔离原型。UI实际切换前需确认描述产品取舍；尚未确认时保留原创建入口，不替换当前服务。
2. 在独立 PG 和随机端口对照插件启用/未启用，验证 Admin SDK 无条件创建/更新、严格条件创建、列表及低层带条件删除；覆盖同名并发、创建失败保留failed、孤立schema，以及active目录存在而Bank缺失的PUT/PATCH拒绝。逐项比较原生参数/响应/错误/未知字段、HTTP指标追踪和适用审计，原生引擎只执行一次。
3. 覆盖普通 read/read_write、all/selected、跨空间、吊销 Key 和禁用用户；新目标不能绕过 Admin 校验，隐式创建、客户端伪造上下文和内容清空不能误触发空间生命周期。
4. 验证 creating/deleting/failed、孤立 schema、迁移失败、原生成功但收尾失败、断连/取消和同名重建；区分GET核对、failed条件清理及没有公开恢复入口的creating/deleting，形成维护处置依据。创建条件格式错误400、目标已登记412；删除缺失/错误/过期ETag分别428/400/412，不存在404。旧 selected 授权不继承，旧 Key 编辑快照失效。
5. 迁移 UI、两套代理、管理脚本及其他已知调用方。短期旧入口如保留，必须复用同一协调器；盘点完成后下线 POST/DELETE，明确旧请求失败响应。只读目录/详情及现有 usage 路径保留，不因路径包含 workspaces 误删。
6. MCP 单独完成条件获取与传递、工具字段/语义、零Bank、单/多Bank、发现/执行一致、当前消息身份和白名单验证；未完成时保留关闭，不能用REST测试代替。
7. 运行插件 Python/UI、两种 Worker 系统故事、原生 Bank/租户/schema/MCP/chunk 回归、匹配生产 UI 和 Chrome 验收。对未启用插件的原生模式做对照；记录源码、命令、结果及未验项，而不是沿用本次静态分析为通过证据。
8. 原型及调用方验证通过后再决定切换/回退版本；不要求重建现有空间、改 UUID、清空数据或重新发放凭据。保持已部署版本仍能读取现有元数据；旧入口下线带来的客户端回退要求必须明确记录。

### 9.9 独立设计检视结论（2026-10-29）

Hindsight、PG 和 API 三个只读专家视角分别核对当前设计及源码。结论：方向合理，以下技术合同已补齐，可进入 REST 隔离原型；没有发现必须修改原生 Python 的理由，但原型未运行，不能据此批准完整实施或上线切换。

| 检视项 | 修订后的明确结论 |
| --- | --- |
| 外层挂接 | 必须验证路由和内层中间件被绕过后的完整HTTP合同，不只审计；不复制中间件，不增加管理断连取消器 |
| active 更新 | PUT/PATCH均update-only，外部Admin上下文；Bank缺失不沿用旧UUID隐式重建，不扩张受信管理用途 |
| UI严格创建 | Bank PUT支持If-None-Match:*和既有短事务原子预留；未来UI迁移时必传，本轮UI保留严格POST。无条件SDK PUT仍upsert，不把GET预查当并发保证 |
| SDK/MCP | 明列当前客户端实际头能力；CLI/高层删除不直接兼容；MCP需先解决条件获取和传递，第一阶段关闭 |
| 删除/恢复 | 保留身份条件；ETag不是内容版本；GET不等于恢复，creating/deleting缺少公开恢复入口须明确验收限制 |
| 描述与UI | 本轮按授权保留描述及旧创建入口；新Bank入口无description不能作为删功能依据。后续统一写入口时另评描述及UI结果/错误合同 |
| 简化边界 | UUID、只读管理视图及条件头有具体用途，不属于过度设计；不增加表、锁框架、调度器、删除屏障、通用CRUD/工具替换/观测框架 |

本小节记录实施前设计检视，不是运行验收；本地REST原型的后续实现与验证见第9.10节。完整切换仍需明确描述能力的最终合同；MCP如纳入发布还须补齐专门合同与验收。本次授权仅为保留旧入口/描述的REST原型，不包括这两项切换。

### 9.10 REST隔离原型实现与使用（2026-10-29）

本次只实现附加REST管理入口，保留原workspace POST/DELETE/GET及其描述、UUID/ETag响应。旧UI代理与组件没有修改，仍走原入口；MCP的create/update/delete Bank仍隐藏并拒绝。没有新配置变量、表、依赖、原生Python或UI文件修改。

| 文件 | 本轮实现 |
| --- | --- |
| `asgi.py`、`transport.py` | 插件启用时创建Bank适配应用，仅分派规范Bank根路径PUT/PATCH/DELETE；未启用插件仍由原生应用处理 |
| `bank_rest.py` | 3个类型化REST处理器，Admin前置认证、条件头、active更新、错误映射、公共观测复用及插件模式OpenAPI补充 |
| `bank_contract.py`、`models.py` | 原生profile/删除计数到HTTP模型的边界转换，删除计数采用NativeDeletion类型并在最终清理前验证 |
| `lifecycle.py`、`repository.py` | 新旧入口复用同一创建/删除流程，create_only在旧短事务内检查并预留，不改变描述与旧响应 |
| `validator.py` | 将已有Bank展示属性更新明确归入Admin操作；业务Key及MCP生命周期限制保留 |

最小调用示例（仅对已启用插件的原型服务；URL与Admin凭据由部署方提供）：

```bash
# 严格创建：存在返回412；成功200。无此条件则按管理目录执行创建或更新。
curl -fsS -X PUT "$API_URL/v1/default/banks/example" \
  -H "Authorization: Bearer $ADMIN_KEY" -H 'Content-Type: application/json' \
  -H 'If-None-Match: *' --data '{"name":"Example"}'

# 仅更新已存在Bank；不能通过更新重建缺失Bank。
curl -fsS -X PATCH "$API_URL/v1/default/banks/example" \
  -H "Authorization: Bearer $ADMIN_KEY" -H 'Content-Type: application/json' \
  --data '{"name":"Example display"}'

# 读取管理详情及ETag；将响应ETag原样保存为WORKSPACE_ETAG。
curl -fsS -D - "$API_URL/ext/contextdb/v1/workspaces/example" \
  -H "Authorization: Bearer $ADMIN_KEY"

# 删除前停止访问并等待旧请求/后台工作结束；使用上一步确认的ETag。
curl -fsS -X DELETE "$API_URL/v1/default/banks/example" \
  -H "Authorization: Bearer $ADMIN_KEY" -H "If-Match: $WORKSPACE_ETAG"
```

没有生产部署或数据升级操作；已有表结构和凭据不变。测试全部使用独立PG、随机API/Worker端口和临时SDK构建目录，退出时清理进程。实际命令、独立检视及当前限制分别见`docs/contextdb-management/VALIDATION.md`第28章（本地未提交）和`docs/contextdb-management/CODE-REVIEW.md`第27章（本地未提交）。本地文件不是新增修复提交，不能虚构提交SHA。

关联跟踪：[RSIXDB/hindsight#53](https://github.com/RSIXDB/hindsight/issues/53)。
