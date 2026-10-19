# ContextDB 租户用户与管理员 UI：夜间开发审阅记录

归档更新：V2 已从与 V1 相同的上游 `a77c1f341` 整理成分支 `contextdb/service-management-v2`，提交 `d5e851b60315b79696e995874e7edc1e9a7bae23`。新分支复核扩展 242 项、UI UTC 343 项及 lint/Ruff/ty 通过；部署、配置、验证和接口合同已在代码仓随版维护。正式分支已推送。最新验证状态见[本地自测与验收记录](contextdb-v2-self-test-acceptance-2026-10-15.md)。以下保留夜间开发时的分支、验证与边界记录，作为历史过程。

夜间阶段（归档前）：2026-10-15。设计与本地开发基于 `cdfc199e5f48b1d9cc9a99119b3efb761f656ef6`；只面向新实例，不迁移旧元数据。没有提交、推送、部署或改动正在验证的 PG5432。

## 建议采用的方案

[完整设计](../member-apikey-bank-service-design-v2.md)已结合 Issue 1/2，以及 Hindsight、阿里 ContextDB、腾讯 Memory Hub、火山 VikingMem 的公开资料完成四方评审。

| 决策 | 本期行为 |
| --- | --- |
| 用户与空间同级 | 一个用户可授权一个、多个或全部空间；每空间仍为独立 schema 内唯一 Bank |
| 用户与 Key 求交 | 用户定义空间上限，Key 定义逐空间操作；改权限不换 secret，停用用户阻断全部 Key 的新请求 |
| 唯一实例管理员 | 初始化生成 all 管理员 Key；可轮换，最后一把有效 all Key 不能撤销 |
| 普通 Key | 多把独立 Key，无子 Key、无自助管理；默认快照当前空间，未来空间不自动加入；显式空 grants 无权限 |
| 管理员 UI | 独立 ACCESS_KEY 口令；服务端固定 admin/all DATAPLANE Key；成员 Key 不可登录 |
| 职责分离 | Console 创建/查询/删除空间；UI 管用户、授权与 Key，以及 Bank 内容；管控不另存空间目录 |
| ID 与名称 | 随机 32 位 hex ID，实例内唯一且不复用；名称 NFKC→trim→casefold 唯一，本期不改名 |
| 客户 PG | 受限 SQL 账号可隔离；真正 SUPERUSER/OS root 或能接管 owner 的云账号不可被同库 ACL/RLS 限制 |

UI 口令是共享管理员口令，不能区分多位真实操作人；若以后需要个人审计，再接 IAM/SSO。管理员 all Key 包含未来空间，普通用户 all 范围也不能令旧 selected Key 自动扩权。

用户目录与 Key 的范围限本独享实例；本期不建设跨多个 ContextDB 实例共享身份/Key 的云账户用户系统。

## 已落地的修改

代码位于本地独立分支 `contextdb/tenant-admin-20261015`：

```text
/Users/zhuqingping/Work/Database/Context/.local/worktrees/contextdb-tenant-admin-20261015
```

- 可选扩展：租户用户、多 Key/逐空间 grants、管理员初始化/恢复、版本并发与审计；REST/MCP 按真实 Bank 路由，列表跨 schema 聚合。
- UI：租户用户及空间筛选、Key 创建/查看/撤销/授权编辑、管理员登录保护；关闭 Console 专属 Bank 生命周期入口。
- PG：受限角色部署示例及权限边界测试，包含真实超级用户可绕过保护的反例。
- [管理 API 合同](../api/contextdb-control-plane.openapi.yaml)从实际扩展路由生成，包含两类凭据、必要请求头和响应模型。

**本轮没有新增原生内核文件修改。** 复用扩展接口及已有固定 UI Key；没有修改 static tenant extension、Recall/Retain/Reflect 算法或原生记忆表。基线已有的 9 个内核文件改动（211 行新增、20 行删除）仍被依赖，用于消息身份、操作来源、入队和取消/排空保护；不能将此扩展直接复制到任意原版 Hindsight 就运行。

删除空间会等待已受理任务，清理 Bank 数据并保留 schema/表与 tombstone。未知旧执行者/执行后异常的屏障保留，不能用定时过期替代排空。

## 验证与审阅中的关键修复

实际联调和独立审阅发现并修复了：

- UI 动态资源 ID 的 `.json` 等后缀曾跳过登录/CSRF 中间件，现所有 API 路径强制匹配。
- UI 代理 ID 格式与真实后端不一致，曾导致用户创建成功后 Key 创建 404；已统一为 32 位 hex。
- 浏览器版本头曾未加引号，无法满足后端 If-Match 合同；已修正并验证实际请求头。
- MCP 工具被拒绝但尚未进入引擎时，应清除准入记录；真正执行后的取消/未知异常仍保留屏障。
- MCP HTTP 断开需要取消并等待脱离传输任务的真实工具处理器；每工具 Bank 准入与每消息传输生命周期分别处理。
- 原生 Bank 导入/clone/alias 写入口需在请求体解析前拒绝；文件 Retain 与普通文档操作继续按业务 scope 执行。
- 名称规范化顺序及跨空间分页成本按合同校正，统计/config 只对最终页补全。

最终集成验证均通过：

| 验证 | 结果 |
| --- | --- |
| 可选扩展完整测试 | 242 项通过，无 skip/xfail；包含 41 项 PG 权限边界与实际 OpenAPI 合同对照 |
| ContextDB REST/MCP/Worker 黑盒 | 49 个故事通过；覆盖嵌入式与独立 Worker、旧会话撤权、取消/排空、知识与多空间权限 |
| UI 套件 | 45 个文件、338 项通过（UTC） |
| 生产 Next + 真实后端 + 临时 PG | 两种 Worker 模式通过；用户/Key 创建、412、停用、未来空间可见、撤销后旧 UI 会话拒绝 |
| 正式构建与质量检查 | Next production build、根 lint、扩展 Ruff/格式/类型检查通过 |
| 原生定向回归 | 41 项扩展/MCP/Worker 测试通过 |
| 本地外部 Host/TLS 代理模拟 | 通过；不代表实际云代理已验收 |

独立后端与 UI 审阅均已关闭发现项。真实超级用户反例不算测试失败，而是证实必须接受的部署边界。原始日志和含全部新增文件的最终补丁 `integration-final.patch` 保存在：

```text
/Users/zhuqingping/Work/Database/Context/.local/night-runs/contextdb-tenant-admin-20261015
```

## 仍须确认的边界

1. 接受“用户空间上限 ∩ Key 逐空间操作”，以及普通 Key 不自动包含未来空间。
2. 接受唯一管理员、独立共享 UI 口令；管理员 Key 的恢复/轮换由可信管控兜底。
3. Console 独占空间生命周期，UI 代管用户与 Key；本期 Bank 名称不可改。
4. 客户拿受限 PG 账号，还是必须提供真正 root；后者应明确接受服务数据可被篡改。
5. 接受新实例专用元数据 v2、保留既有内核 hook，以及下列生产验收限制。

尚未验证真实华为 RDS 的高权限角色、云 Console 联调、实际云反向代理、生产故障切换/性能和浏览器视觉布局。本地标准 PG、模型 stub、生产 Next HTTP 联调不能代替这些验收。现有 Asia/Shanghai 相对日期用例有跨日问题；UI 套件以 UTC 执行。Next16 的旧 `npm run lint` 脚本无效，实际 ESLint 和根 lint 单独执行。

旧版 `contextdb-v1-local-validation-guide.md` 仍是旧模型的验证手册，不应直接用于此元数据 v2 分支。后续本机体验已使用独立新数据库和新管理员凭据；完整验证范围以最新自测记录为准。
