# 独立审阅：cloud-service-architecture.md §9–11

审阅时间2026-10-04；基线f7dd3f4fd。只指出可落地设计/源码之间的差距，不把尚未开发误报为已实现缺陷。

## 必须修改或细化

| 优先级 | 位置 | 问题与证据 | 最小修订 |
|---|---|---|---|
| P1 | §9.4 原生配置接口 | 写成 `bank/config GET/PUT`；当前真实OpenAPI及22项HTTP测试表明更新是 **PATCH**，重置是DELETE。PUT不是该资源更新合同。 | 改GET/PATCH；是否开放DELETE重置单独决定。 |
| P1 | §9.4/参数默认说明 | `recall_max_tokens=2048`不是HTTP无参默认，也不是租户硬上限。运行时 `RecallRequest(query=...)`及live OpenAPI都是4096，http.py:6144把请求值显式传给engine；内部模型刷新才回落到Bank配置2048（memory_engine.py:15289）。 | 分开“HTTP请求默认4096”“内部刷新预算2048”“云层硬限额待实现”；插件可显式传max_tokens，须在兼容层统一上限。 |
| P1 | §9.2 tenant extension/config白名单 | 原生 `get_allowed_config_fields()` 在非ValueError异常时 **fail open**（config_resolver.py:565–568）。不能把扩展抛出超时/网络异常当成可靠拒绝。 | 外层先确定性鉴权，异常拒绝；扩展对权限依赖错误明确返回空允许集合或抛受支持拒绝类型，并加网络故障负测。无需先侵入核心。 |
| P1 | §9.3 api_keys表与§9.5摘要 | 表仅有subject/workspace，没有key自身scope/Bank约束、pepper_version；设计却要求“创建作用域/只读key”、摘要pepper版本化。仅用主体身份无法表达同主体不同key权限，也无法明确摘要轮换用哪个pepper。 | 增加key能力/资源约束字段（或独立关联表）、pepper_version；权限取key约束∩主体当前权限。 |
| P1 | §9.5异步身份 | “执行时重新解析当前策略”方向正确，但属于新增机制。必须明确主体标识如何持久进入任务，内部短期断言不能当长期凭据；撤权后的后台任务行为及费用记录必须验收。 | 在D03/D05写明确交付：持久principal/workspace/bank授权上下文、执行前重验、结果发布前重验、撤权时取消/失败状态；不能仅用入口验证器证明。 |
| P2 | §9.8成本与D07 | 正文正确区分软限额和硬人民币预算，但D07“用量不漏主要路径”无法验收，也不等于供应商精确扣费。 | 首期明确免费/邀请试用或简单固定套餐；列出retain/reflect/consolidation/refresh/embedding/rerank/retry覆盖表；硬预付若不做，移出首期门禁而非笼统写D07必验。 |
| P2 | 本地PG证据 | 主代理已核实pg0使用fsync=off；本轮控制PG事务检查和配置写读只能证明应用事务逻辑/读取隔离。 | 全文不能把本机进程重启升级为断电持久性证明；上线PG fsync=on、目标RDS故障恢复另验。 |

## 已与源码相符的选择

- Cell固定模型profile，避免把不存在的Bank provider/model/key覆盖包装成原生能力；51字段白名单及HTTP拒绝测试支持此判断。
- 客户opaque key只映射身份/授权，不含模型密钥；静态tenant key试验不被宣称生产凭据平台。
- API与Worker分开部署、模型/PG并发独立限额，符合上游进程模型。
- 幂等账本承认原生operation_id不比较正文，并增加payload_hash，避免把重复受理等同模型调用exactly-once。
- 团队KB冻结查询+epoch重验属于明确的新产品机制，正文已声明本轮仅验证PG状态机，没有宣称完整知识发布已通过。
- 不同Embedding空间按profile/Cell隔离，以及源端冻结、维护窗口迁移，适合首期范围；仍需真实RDS/模型测试。

## 新增HTTP证据

[脚本](../scripts/parameters_http.py)、[22项结果](../evidence/parameters-http-results.json)、[汇总](../evidence/parameters-http-summary.json)，退出码0。测试Bank `round2-params-1791124491`，在team_a/team_b两个schema创建同名空Bank；不修改其他Bank，不调用模型。

已验证：允许字段读写、ENV格式键、同名Bank租户隔离、static provider/model/key/database/language字段拒绝、未知字段拒绝、错误类型拒绝、混合合法/非法PATCH整体不生效、None清除一个覆盖后其他覆盖和另一租户不变、配置响应无static凭据字段。不是对全部51字段或全部权限入口的完整证明。

[Recall默认核验](../evidence/parameters-http-recall-default.json)：运行时模型实例+实际HTTP OpenAPI+handler源码三者一致；4096为原生HTTP默认。

## 复核与故障注入补证

已复核修订后的主开发文档§3/§7和架构§9：HTTP Recall4096/内部2048已分开；GET/PATCH已修正；key表已补scope、Bank约束、pepper版本；授权异常拒绝及持久异步主体已进入设计。参数与模型表未发现新的事实性错误。LLM_MAX_CONCURRENT确是进程级全局信号量（llm_wrapper.py:62–68），不能据此认为集群全局限额已经实现。

[最小故障注入脚本](../scripts/parameters_failopen.py)执行退出码0，[结构化结果](../evidence/parameters-failopen.json)。调用真实 `ConfigResolver.update_bank_config()`，只将数据库替换为记录写入的fixture，未修改Hindsight源码。向同一个允许的retain_mission字段注入五种权限查询结果：

| 权限扩展结果 | 真实Resolver行为 | 是否调用持久写入 |
|---|---|---|
| TimeoutError | 继续允许 | 是 |
| RuntimeError | 继续允许 | 是 |
| 返回空set | ValueError拒绝 | 否 |
| 显式ValueError | 拒绝 | 否 |
| 明确允许retain_mission | 允许 | 是 |

这证实异常fail-open不只是注释推断；记录backend不等于本次向真实PG写入。配合前述22项真实HTTP/PG字段校验，二者覆盖范围分开。产品扩展应在依赖失败时明确拒绝/返回空允许集合，外层鉴权同时拒绝，增加同类故障测试后方可上线。

## 参考控制DDL与真实PG约束验证

新增[control_schema_reference.sql](../scripts/control_schema_reference.sql)与[执行脚本](../scripts/control_schema_probe.py)。只在已有 `contextdb_round2_control` 中创建独立 `round2_design_*` schema，不修改Hindsight表或既有研究表。执行退出码0，**21项检查通过**；实际schema及结果见[control-schema-results.json](../evidence/control-schema-results.json)。

参考DDL落实workspace/member/cell/placement/bank/grant/key/ledger/job/source/publication/usage表，并补充model_profiles与Cell的upstream SHA、镜像摘要、schema版本字段。主要验证：复合FK阻止跨workspace授权和来源引用、placement唯一、幂等键唯一、来源版本唯一、key scope/pepper/expiry字段读回及非法值约束、发布状态与job同事务提交/回滚、模型维度正数。

DDL是设计参考，不是生产migration：`bank_constraints`和job的多态resource_id由服务层校验，JSON中的Bank引用没有自动复合FK；key是否已过期/撤销仍需每请求判断，CHECK不会随时钟主动撤销；模型profile需发布后不可变或新建profile，并不能仅凭表字段阻止运维修改；跨region放置、publication目标必须为KB、字段级scope词汇与epoch变更均需应用协议与并发测试。生产角色/DDL权限/RLS、索引容量、审计、备份恢复尚未认证。实例fsync=off，事务测试不证明断电持久性。

与架构§9.3保持一致的补充约定：Bank内部增加`id`供复合FK引用；所有跨workspace对象引用显式带workspace_id；source revision的唯一键采用`(workspace_id,source_id,revision)`避免跨租户同名冲突；publication增加job_id，将发布记录关联到同workspace工作项。正式迁移应在D02交付中统一这些字段，而不是直接复制参考DDL投入生产。

补齐request_ledger的subject_id/key_id/created_at后重新执行：21项全部通过。增加(workspace,subject,key)复合FK，阻止跨workspace主体或key写入；已有ledger引用的key不能物理删除，可以设置revoked_at保留撤销tombstone及审计归属。为支持该FK，api_keys补相同列组合的唯一约束，不改变既有业务字段。

## D04最小权限假设的实际验证

新增运行期权限实验：预迁移schema + DML-only非owner账号（USAGE=true/CREATE=false）+ RUN_MIGRATIONS_ON_STARTUP=false，API health200，但建Bank500，原因是同步创建per-Bank向量索引要求表owner权限。见[结果](../evidence/parameters-privilege-results.json)。仅提供MIGRATION_DATABASE_URL不足以让首次建Bank无DDL运行。

可行边界已补测：管理身份先经原生API预建Bank，然后停管理API、以DML-only身份重启，chunks配置/同步写入/Recall全部200且返回合成canary；[4步结果](../evidence/parameters-privilege-prebank.json)。D04/D02应明确特权开通job及索引生命周期接口，普通运行API不能直接承担首次建Bank。删除和重建索引、所有维护路径仍需后续验收。临时API8894及本轮额外启动PG55433已停止，数据/schema/role保留；非RDS生产权限认证，fsync=off不证明断电持久性。
