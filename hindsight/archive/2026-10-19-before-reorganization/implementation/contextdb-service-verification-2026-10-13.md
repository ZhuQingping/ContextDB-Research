# ContextDB 首期实现验收记录

日期：2026-10-13。对应源码仓 `hindsight` 基线 `a77c1f3412a7b82f36588dffce1a8d7480e99cc7` 上的本地未提交修改。

> 文档组织与范围澄清：PG 表与新增管理 API 说明已并入主设计。仅新增管理接口采用内部 REST、供管控调用；原生 REST/MCP 接口保持不变，是否裁剪另行评估。下文保留前序原型的真实用例与结果；本轮未修改源码、运行配置或历史证据，不新增关闭 MCP 的部署要求。

结论：首期源码已实现，本地测试通过；不是生产上线批准。主设计见[服务化设计](../member-apikey-bank-service-design.md)，接口见[OpenAPI](../api/contextdb-control-plane.openapi.yaml)，表结构见[PG 设计](contextdb-pg-metadata-design.md)。本次未提交、推送或发布。

## 实现了什么

| 链路 | 已实现与验证 |
|---|---|
| 实例 | 登记、查询部署配置中的既有独享实例；不创建云计算或 RDS 资源 |
| 工作空间 | 动态创建、查询、改名、冻结、删除；每空间独立 schema、唯一 Bank；管理任务与幂等状态持久化 |
| 成员 | admin/member、创建、查询、改角色、停用、软删除；本人/管理员权限及最后管理员保护 |
| 用户 API Key | 随机签发、多 Key、scope、到期、查询、撤销；HMAC 摘要存储、明文只返回一次；签发重放不泄露 secret |
| 管理认证 | 管控专用 Key、连接来源和可信操作人；业务 Key 不能管理，管理 Key 不能访问业务接口 |
| REST/MCP | retain、recall、reflect、知识读取/编辑等原生接口；逐请求校验空间、Bank、Key、用户和权限；MCP 逐消息恢复身份 |
| Worker | 内置及独立 Worker 的空间发现、异步任务、知识刷新、排空；拒绝停用空间的新周期提交 |
| 删除保护 | 等待已准入请求及原生任务；异常/未知执行留下同库持久屏障，不能误报告物理删除成功 |

默认部署不加载扩展时保持原生行为。同 Bank 的用户记忆仍共享；知识只读 Key 不能直接 recall 记忆或读取原始 mental model、审计、LLM trace。

## 代码组织与侵入点

新增实现位于 `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/`。管理 handler 不写 SQL；Repository 负责约束与事务；Tenant、Validator、Http 三类扩展分别处理身份路由、权限和管理 REST。没有新增运行时依赖、外部服务或独立 MetaPG。

必要的原生边界补充如下，不能把“扩展实现”说成零源码改动：

| 原生位置 | 原因与默认兼容方式 |
|---|---|
| HttpExtension / API 挂载 | 可选 ASGI middleware，默认空；统一覆盖 REST 与 MCP，不让 MCP 挂载绕过准入 |
| TenantExtension / queue submit | 默认 no-op 的入队作用域；ContextDB 在取得数据连接前做保护，避免删除竞态和池饥饿 |
| MCP 身份恢复 | 从当前真实 HTTP scope 恢复 ContextVar，避免长会话继承初始化 Key；非 HTTP/default 路径保持原行为 |
| MCP 故障回调 | 可选零参数回调，默认不做事；后端异常被包装为正常协议返回时仍告知扩展，不传异常或正文 |
| MentalModelGetContext | 默认直接读取来源；只有引擎内部知识页路径能标记 knowledge_page，客户不能自报 |
| 原生任务查询 | 可选 statuses 参数，用同一次查询检查 pending/processing；原 status 参数保持兼容 |
| Worker shutdown | 关闭扩展连接池后再关闭引擎，避免资源遗留 |

测试辅助修改包括隔离数据库地址、独立 Python 环境、启动失败清理及公开客户端黑盒测试；CI 已接入新扩展路径。锁文件是测试依赖记录，不是新增产品组件。

## 冻结版本验证

测试只使用新建的临时 PG、合成 Key 和 stub 模型。系统测试启动真实 API/Worker，使用公开 Python SDK 和 MCP SDK；未调用商业服务或真实模型。

| 验证 | 结果 | 最终证据文件 |
|---|---|---|
| 扩展单元/真实 PG 集成，主环境 | 175 passed | components-auth-classification.xml |
| 扩展完整套件，新鲜冻结依赖环境 | 175 passed | components-fresh-frozen.xml |
| ContextDB 系统测试 100–109，新鲜 Python 3.12 冻结环境 | 47 passed | system-postauth-verified.xml |
| 原生 MCP/extension/Worker 定向回归，隔离 worktree | 41 passed | native-postauth-verified.xml |
| 项目完整 scripts/hooks/lint.sh，隔离 worktree | PASS | root-lint-postauth-verified.log |
| 新增源码/测试 Ruff、format、扩展 ty、两仓 diff --check | PASS | 主代理最终复核 |
| OpenAPI schema 校验、管理响应字段与实际 DTO 合同、CI YAML | PASS | 合同回归包含在 175 项中；另运行 CLI/YAML 校验 |

同一批 175 项在两环境重复执行，不能相加为 350 个用例。专家重跑和早期批次也不累加。系统测试包 47 项包含 41 个真实进程场景与 6 个 fixture/错误分类辅助回归，不能说全部 47 项都启动真实服务。另列的 41 项是定向原生回归，不代表全部上游测试。系统测试有两条上游文档导出弃用告警，无失败；这些结果不替代用户检视与验收。

最终原始 JUnit/日志已复制到本仓库的[证据目录](evidence/contextdb-service-2026-10-13/README.md)，约 84 KB，包含 SHA-256 校验值；尚未提交/推送。原始临时目录 `/tmp/contextdb-implementation-evidence-ldIh3Q` 另保留早期失败批次用于追踪，最终结论只采用上表冻结批次。

复跑核心命令（从源码仓执行；新鲜环境用 `UV_PROJECT_ENVIRONMENT` 指定临时目录，避免同步主环境）：

```bash
UV_PROJECT_ENVIRONMENT=<TEMP_EXTENSION_VENV> uv sync --frozen --project hindsight-extensions/contextdb-service
<TEMP_EXTENSION_VENV>/bin/python -m pytest hindsight-extensions/contextdb-service/tests -q

UV_PROJECT_ENVIRONMENT=<TEMP_SYSTEM_VENV> uv sync --frozen --project hindsight-system-tests
PYTHONPATH=hindsight-system-tests:hindsight-extensions/contextdb-service \
  <TEMP_SYSTEM_VENV>/bin/python -m pytest hindsight-system-tests/tests/test_10*_contextdb*.py -q

# 在不带真实 .env 的隔离 worktree 中执行，lint 会自动格式化文件：
./scripts/hooks/lint.sh
```

关键负例覆盖：跨空间 Bank/alias 拒绝、撤销/停用/到期、最后管理员并发降级、幂等冲突、租约在行锁等待中到期、MCP 同会话换 Key/降权/换空间、非空知识页与原始数据拒绝、同步/异步/MCP 删除竞态、PG 断锁与 HTTP 中断、二次取消、REST500/MCP错误正文保留屏障、预期认证拒绝不误留屏障。后台验证断言真实 operation_id completed，不以“队列为空”代替任务执行成功。

## 五类专家交叉检视

复核以限定范围的 ACCEPT / ACCEPT WITH RISKS 为准，不以多数票覆盖缺陷，也不让修改者独立验收自己的修改。

| 专家 | 独立检视与修复依据 | 最终结论 |
|---|---|---|
| 数据库 | 真实 PG 复现等待锁后过期续租；检查组合外键、状态代次、持久屏障和删除检查顺序；独立重跑组件及 109 故障系统用例 | ACCEPT WITH RISKS；恢复与 DDL 边界保留 |
| agent memory | 知识/记忆权限、模板任务、后台队列和取消；跨验其他专家的持久屏障/删除顺序，核对最终 109/103/108 系统证据 | scoped ACCEPT；其 MCP 修复由 knowledge/Python 验收 |
| knowledge | 非空知识页授权、直接原始 model 拒绝；跨验 MCP 身份和故障屏障，独立确认认证拒绝报告 0 次、真实未知异常 1 次 | scoped ACCEPT；自己实现的知识来源标记由其他专家验收 |
| Python | 逐消息上下文、异步资源关闭、二次取消、错误分类和默认 hook 兼容；独立 16 项认证拒绝测试 | ACCEPT WITH RISKS；自己的 repr/OpenAPI/fixture 修改不计自验收 |
| 注释 | 静态核对新增屏障/故障分类/租约/MCP 注释与实现一致，核对 9 表、最终 XML 和生产边界 | scoped ACCEPT WITH RISKS；自己前期措辞修改不计独立自验收 |

五类专家已达成上述限定范围的一致，没有仍未修复的本期阻塞问题。主代理负责集成验收，并检查其他专家对修改者代码的交叉复核；不把表中 ACCEPT 解读为每个人独立重跑了全部用例。主要问题已按[开发记录 D8–D22](contextdb-service-night-task-2026-10-13.md)修复或明确保留边界。最终一致仅指首期代码和本地证据可交付，以下生产门槛没有被“专家同意”取消。

## 上线前仍需完成

1. 管控登录/云权限、伪造 actor 头替换、私有入口、安全组、HTTPS、禁用 proxy headers、管理 Key 全副本轮换：NOT_RUN。
2. 多副本连接预算、混合负载、请求记录写入开销、限流配额与完整安全审计：NOT_RUN。
3. 崩溃后旧执行者及 PG 工作会话的 fencing、残留准入记录人工恢复流程、整库备份恢复、多 schema 升级：需专项演练；不自动按时间清空屏障。
4. 原生 DDL 不具备强租约 fencing；迁移线程取消须等待退出，本期禁用迁移子进程模式。不能据本地并发用例宣称任意故障均安全。
5. MCP 默认无结果重放存储。自定义 event store/正文通知、session-owner 硬化另行评估。工具成功后 SDK 的后续请求可能因撤权 401，不可直接重试非幂等写入。

同 Bank 的个人记忆隔离不在本期，后续按 tag/ACL 与派生内容风险单独设计。空间改名暂不联动原生 Bank 显示标签，软删除登录绑定暂不支持自动重新加入。初始元信息 DDL 不承诺升级旧原型。

## 操作边界

没有修改全局 Codex/Claude 配置、重启现有服务、迁移已有数据库或提交/推送。一次 lint 误从主仓执行，造成根依赖同步和无关前端格式化；无关文件仅撤回本次格式化，现已不在 diff。根环境同步已经发生，不能宣称完全未动；详情见 D17。后续 lint 均使用隔离 worktree。
