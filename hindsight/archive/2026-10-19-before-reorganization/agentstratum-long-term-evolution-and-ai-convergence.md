# AgentStratum 长期演进与 AI 工程收敛建议

> 核对日期：2026-10-08
>
> 代码基线：[RSIXDB/agentstratum `a066dde9c1a2727b625f918c1456a1193d58187f`](https://github.com/RSIXDB/agentstratum/tree/a066dde9c1a2727b625f918c1456a1193d58187f)
>
> 文档性质：基于2026-10-08固定源码、设计文档和已有验证记录的工程判断；不是新的完成声明，也不替代 S1 验收。AgentStratum 后续提交可能改变实现状态，应以文内固定 SHA 复核。
>
> **选型边界（2026-10-09）**：本文评估 AgentStratum 的工程状态和长期价值，不代表选定它作为当前实现基线。当前实现方向仍是基于 Hindsight 源码开发；AgentStratum 只用于对比和借鉴。

## 1. 结论

如果团队确定沿 AgentStratum 继续走，方向是合理的，但下一步不应继续横向扩展更多长期能力。当前最应该解决的是一条明确的主矛盾：

> AgentStratum 已经形成较完整的长期产品边界、合同和大量局部实现，但当前默认装配仍只完成原件完整性校验，尚未形成一条由真实 Gateway、Handler、Worker、模型服务、PostgreSQL 和对象存储共同支撑并被整体验收的产品业务主链。

这个判断有直接源码依据：

- `src/contextdb/handler/app.py` 当前公开的主路径只有 ingest/status，响应明确标记 `capability="original-integrity-only"`。
- `src/contextdb/control/runtime.py::worker_service` 当前固定装配 `VerifyOnlyProcessor()`。
- `src/contextdb/k02/worker.py::VerifyOnlyProcessor` 只做 UTF-8 解码、SHA-256 和长度校验，注释明确说明“不发送 provider、不抽取 fact”。
- 当前规划文档也把“将 VerifyOnly 装配接到获权原生 Worker”列为 MP-04 的具体缺口，并明确指出不能在此缺口存在时宣称 S1 已贯通。

因此，近期目标应从“继续补齐各模块”改成“交付一条最小产品主链”：

```text
Client
  -> Gateway（身份、Bank 权限、Unit 放置）
  -> Handler（受理 Retain、查询 operation、执行 Recall）
  -> OBS + DataPG（原件和持久任务）
  -> 独立 Worker（领取任务、原生 Retain）
  -> Model Service（generate/embed，固定模型空间）
  -> DataPG（facts/索引）
  -> Handler Recall（返回同 Bank 的真实结果）
```

先让这条链在两个租户、两个 Unit、多 H/多 W、真实 PostgreSQL 和受控模型配置下通过，再按既定 S1 义务依次接通 Reflect、图/时间检索、观察归纳、Mental Model/知识页和必要管理。这里改变的是实施顺序，不是删除 S1 已定义的六项业务和 75/157 验收分母。

对 AI 生成代码和设计的核心约束也应随之改变：AI 的任务单位必须是“一个可观察行为 + 一个必须保持的不变量 + 一条可复现验收命令”，不能再以“完成某模块”“完善架构”作为开放式任务。新增抽象、表、状态和服务必须能对应当前主链的失败用例或经接受的 ADR，否则不进入当前版本。

## 2. 事实基线与证据分级

本文使用四类表述，避免把计划、局部结果和整体验收混在一起。

| 标记 | 含义 | 本文示例 |
|---|---|---|
| 当前源码确认 | 直接从当前 `main@a066dde9` 的代码或配置确认 | Handler 仅有 ingest/status；Worker 默认装配 VerifyOnly；CI 当前只运行 K01 小集合 |
| 当前文档确认 | 当前仓库已接受的架构、范围或工作流约束 | S1 九模块、六业务、75 父用例/157 步、共享核心单写 |
| 历史证据 | 仓库保存的某次固定 profile、日志或验证 JSON；只证明当时限定范围 | K01/K02 有限链、Gateway 230 项、PG45 记录中的 `realSQL_pass: 0` |
| 建议决策 | 本文提出、需要团队接受后执行的安排 | 先完成最小产品主链、建立三层 CI、限制 AI WIP |

当前仓库的事实状态如下：

1. AgentStratum 不是只有设计文档。当前代码已经包含 Gateway、Handler、控制面合同、模型适配、原生 Retain/Query/Pages 接缝、PostgreSQL 存储和运维/验收工具。
2. S1 的正式目标仍然是九个模块和六项业务：Retain、Recall、Reflect、观察归纳、Mental Model/知识页及必要管理操作；固定验收分母仍是 75 个父用例/157 个步骤、99 个原生路由、68 个 UI 文件和 Gateway 补充项。
3. K01/K02 等有限范围已有代码和受控证据，但当前文档仍将 J1、J2、J3 和完整 S1 标为未接受。局部 `ACCEPTED` 不等于产品主链已通过。
4. 当前 GitHub CI `.github/workflows/k01.yml` 只执行 `ruff`、`ty` 和 `tests/contextdb/test_kernel.py -m 'not native'`。测试源码统计为 766 个测试函数（`tests/contextdb` 94、`tests/a01` 71、`tests/l01` 62、`tests/planning` 118、`tests/stage1` 421）；上述数字是静态计数，不代表本轮执行。`pyproject.toml` 的默认 `testpaths` 只指向 `tests/contextdb`，因此其他目录不会由默认 pytest 发现。
5. 历史 PG45 `verification.json` 记录 `realSQL_pass: 0`；它说明当次登记没有形成真实 SQL 通过证据，不能用于断言当前代码必然失败，也不能用于断言数据库链已通过。
6. AgentStratum 固定的 Hindsight 上游是 `eb021da`。上游升级会同时影响 Worker 恢复行为、公开接口和数据库假设，不能当作普通依赖升级处理。

主要依据见：

- [AgentStratum README](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/README.md)
- [S1 分阶段能力与模块](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/docs/architecture/STAGED-CAPABILITIES-AND-MODULES.md)
- [Handler 当前入口](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/src/contextdb/handler/app.py)
- [Worker 当前装配](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/src/contextdb/control/runtime.py)
- [VerifyOnlyProcessor](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/src/contextdb/k02/worker.py)
- [当前 CI](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/.github/workflows/k01.yml)
- [PG45 历史验证记录](https://github.com/RSIXDB/agentstratum/blob/a066dde9c1a2727b625f918c1456a1193d58187f/docs/operations/stage1/pg45/verification.json)

## 3. 当前需要解决的三个问题

### 3.1 主矛盾：局部实现多，整条产品主链未接受

当前缺少的不是另一版总体架构，而是把已有合同、存储和原生适配装配成可重复运行的业务结果。继续增加 Skill、计费、全局配额、在线迁移或更多控制面对象，不会自动让 Retain/Recall 主链成立，反而会增加尚未被真实消费者验证的接口数量。

判定这个问题是否解决，不看新增文件数或单元测试数，而看同一个发布候选是否同时满足：

- 用户经 Gateway 进入正确 Unit 和 Bank；
- Handler 先保存原件并持久受理 operation；
- Handler 停止后，独立 Worker 仍能领取已受理任务；
- Worker 通过唯一模型边界完成原生 Retain 并持久写入 facts；
- Recall 从相同 Bank 返回真实写入结果；
- 同名 Bank 的另一租户无法读取该结果；
- 多 Worker、重启和提交结果未知时不隐藏重试、不复活原 operation；
- 所有结果来自同一套固定源码、依赖、配置和证据清单。

### 3.2 次要矛盾：长期产品合同与当前运行装配脱节

AgentStratum 已经定义身份、Bank、Unit、授权、持久 operation、模型边界、未知效果和恢复语义，也已经存在相应的有限 provider 和合同测试。但当前产品入口只公开有限 ingest/status，默认 Worker 仍停留在原件校验。这意味着设计完整度和可运行产品面并不同步。

解决方式不是删除长期合同，而是为每个合同补齐一个当前消费者和一项组合验证。没有当前消费者的合同继续保持关闭，不继续向外扩展；已经进入主链的合同必须由真实服务装配和故障用例约束。

同时需要建立 Hindsight 上游兼容轨。每个发布候选固定一个 Hindsight 提交，对公开 API、Worker 启动/恢复、Tenant Extension、operation/schema、模型接口和启动配置形成版本清单；只有主链回归通过后才改变固定提交。

### 3.3 工程控制问题：当前真相和 CI 没有覆盖代码增长速度

AgentStratum 已经具备 ADR、固定验收分母、证据分级、共享核心单写、默认关闭未支持能力等良好基础。问题在于当前状态分散在 README、阶段计划、任务卡、handoff 和历史 receipt 中，工程师或 AI 很难用一个入口回答：当前真正支持什么、什么关闭、下一条主链缺什么。

与此同时，必过 CI 仍主要覆盖早期 K01 内核。代码的实际覆盖面已经超过 CI 的默认保护面。这会产生两个客观风险：

- AI 容易根据某份历史计划继续扩展已经变化的接口；
- 局部测试通过容易被误写成模块完成或 S1 接受。

## 4. 下一阶段的唯一主目标：最小产品主链

建议把下一阶段候选定义为 `MPS-1（Minimum Product Spine 1）`。它不是新的产品阶段，而是 S1 的第一条纵向集成切片。

### 4.1 支持范围

首个候选只打开：

- 输入：显式 UTF-8 短文本；
- 写：异步 Retain 和 operation status；
- 读：facts-only Recall；
- 隔离：两个租户使用同名 Bank，分别位于两个 Unit；
- 模型：一个固定 generate 模型、一个固定 embedding 模型和维度；
- 进程：至少两个 Gateway 或可证明共享 session 的等价部署、每 Unit 多 Handler/多 Worker；
- 存储：真实 MetaPG、DataPG 和已批准的 OBS/本地等价原件存储；
- 故障：H 停止、单 H 故障、W 重启、提交回执丢失或等价 UNKNOWN 窗口。

Reflect、图/时间检索、自动 consolidation、知识页刷新、完整文件类型和 Skill 运行不应被伪装成已支持。它们仍在 S1 义务中，按同样方法在后续切片接入。

### 4.2 必须完成的代码接线

按当前仓库已有缺口，顺序应为：

1. 完成生产 MetaPG session adapter 和 Bank/action 能力目录，使多个 Gateway 共享会话与授权权威。
2. 在 Handler 接入异步 Retain、status 和 facts-only Recall；保持 Handler 不 claim 后台任务、不自动 DDL。
3. 将 `worker_service` 从 `VerifyOnlyProcessor` 切换到已经获权的原生 Retain processor；保留 VerifyOnly 作为受控诊断能力，而不是默认产品能力。
4. 将 Worker 到模型的调用统一经过 L/Models 边界，固定 Bank、operation、用途、deadline 和 retry owner；禁止 H/W 持有绕过 L 的 provider 路径。
5. 只补主链真实需要的 PostgreSQL provider/SQL 装配，实际执行 catalog、权限、DML、claim、hold 和 UNKNOWN/CAS 用例，不扩建通用执行平台。
6. 构造 AgentStratum 自身的双 Unit、多 Handler、多 Worker 验收环境，统一使用其身份、placement、operation 和恢复语义。

### 4.3 MPS-1 退出条件

以下条件必须来自同一候选版本，缺一项就保持 `NOT_ACCEPTED`：

| 类别 | 退出条件 |
|---|---|
| 正常业务 | Retain 返回持久 operation；Worker 完成真实抽取/向量化；Recall 返回该租户写入的唯一标识 |
| 隔离 | 两租户同名 Bank 不串读；跨租身份、Bank、模型用途和数据库角色均被拒绝 |
| 进程边界 | Gateway 不加载 Engine；Handler 不领取任务；H 全停后已受理任务仍由 W 完成 |
| 并发与故障 | 两个 W 都能领取任务；单 H 故障不破坏幂等语义；UNKNOWN 不自动重试或复活 |
| 配置 | 服务配置版本不一致时不进入 READY；上游提交、依赖、模型和维度均固定 |
| 证据 | Mock 拓扑、真实 PG、真实模型小样本分别标记；失败、跳过和 NOT_RUN 不从分母删除 |
| 接手 | 非作者从干净环境按固定制品启动、执行主链、定位一次受控故障并安全停止 |

## 5. 让 AI 代码和设计不发散的具体机制

### 5.1 建立一个“当前真相”入口

仓库已经存在 `execution-workflow/CURRENT.md`。评审发现它描述的是较早 epoch/revision，且当前工作流的权威运行状态位于原开发机 `.local/runtime/.../state.json`，干净 clone 中不存在该文件。不要再创建一个并列的 `CURRENT-S1.md` 作为第二个真相源；应先明确现有 `CURRENT.md` 的职责，并从受控工作流数据与当前 Git HEAD 生成/更新它。可附带机器可读摘要，但它必须由同一生成器产出、可校验，不取代 `.local` 中的执行账本。

当前真相摘要应列出 HEAD、上游固定提交、支持/关闭能力、当前候选、PASS/NOT_RUN、阻塞、下三个任务和活动 run ID。历史 receipt 只链接，不复制到当前状态正文；CI 校验生成摘要与代码/工作流输入一致。不要把易变账本或秘密复制进 Git。这样是在更新现有入口，而不是另建规划体系。

### 5.2 把 AI 任务压缩为可判定合同

每个实现任务必须写清：

```text
目标行为：用户或相邻服务能观察到什么
必须保持的不变量：权限、幂等、UNKNOWN、deadline、隔离中的哪一项
基线：base SHA、固定上游、依赖/profile hash
允许文件：精确目录或文件
禁止文件：共享 schema/Engine/http/poller 等非本任务写集
消费者：谁会在当前主链调用新增接口
验收命令：一条离线命令 + 必要的一条真实环境命令
证据分类：MOCK / REAL_PG / REAL_MODEL / NOT_RUN
停止条件：需要新表、改变状态机、扩大数据外发、修改公共合同等
交付：diff、测试结果、失败项、未验证项
```

如果无法写出消费者和验收命令，任务还不是可实施工作，不应让 AI 自由补设计。

### 5.3 保持共享核心唯一写者

当前 `AGENTS.md` 已要求共享 schema、Engine、HTTP、poller 和公共接口单写，应继续执行。当前执行计划中集成写者仍标记为“待登记”，多个模块候选又会触及共享文件；这会让叶子并行产出无法稳定进入集成。应登记一个集成负责人、共享文件到负责人的映射和固定集成窗口。模块开发可以并行编写叶子 provider、测试和文档，但一个集成候选只能有一个人或一个 Agent 负责公共装配。该建议是约束代码所有权和节奏，不是对任何个人产能的判断。

合并顺序建议固定为：

```text
合同/失败用例冻结
  -> 叶子 provider
  -> 唯一集成者接线
  -> 受影响回归
  -> 真实组合验证
  -> 非作者接手
```

这比让多个 AI 分别“完成 Gateway/Worker/模型模块”更不容易产生重复状态机、相互不兼容的 DTO 和隐藏重试。

### 5.4 对新增设计设置准入条件

任何新增持久表、后台任务类型、服务、状态或跨服务 API，至少满足以下一项才进入当前候选：

- 它关闭 MPS-1 或当前 S1 切片中的一个已编号失败用例；
- 它是已接受 ADR 明确要求的唯一实现；
- 它替换已确认不满足不变量的现有实现，并同时删除或关闭旧路径。

每个新增持久对象还必须写明：权威来源、唯一写者、读者、事务边界、恢复方法、删除/导出责任。每个 retry 必须写明幂等前提和唯一 retry owner；每次模型发送必须继承原始 deadline，并说明返回结果未知时的处理。

“未来可能需要”“便于扩展”“统一抽象”本身不构成准入依据。

### 5.5 建立三层验证门禁

| 层次 | 触发时机 | 必须覆盖 |
|---|---|---|
| PR Fast | 每个 PR | ruff、ty 和所有明确标记为无外部资源的离线套件；默认 pytest 发现应覆盖预期的测试目录。真实 PG/模型/OBS 测试仍需单独授权，不得通过 skip 被算作通过 |
| Merge/Nightly | 合并或夜间 | 从锁定依赖构建 wheel；native ABI/合同；真实 PostgreSQL；Mock 模型下的双 Unit、多 H/多 W 主链和故障注入 |
| Release | 发布候选 | 真实模型小样本、权限与隔离、UNKNOWN/重启、有限备份恢复、完整支持矩阵和非作者接手 |

当前 CI 的 35 个纯测试只覆盖静态盘点 766 个测试函数中的一小部分；其余源码计数并不等于其测试均适合 CI。先给测试分类为 `offline-no-resource` 与 `resource-bound`，把可离线稳定复现的 Gateway loopback、Query contract、Retain 离线和 K02 protocol 纳入必过 CI。真实模型和重型数据库测试不必塞进每个 PR，但必须在有资源授权时进入可机器校验的候选验收，而不能只保存在历史日志中。测试专家核对的 TEST-PLAN 中 75 个父用例/157 步是规划分母，不是一个已实现并执行的 75 项自动化套件；本轮所有正式发布项仍为 NOT_RUN/OPEN。

### 5.6 用支持矩阵约束 API 和 UI

由同一份能力目录生成或校验：

- Gateway 可转发的 action；
- Handler 可接受的 route；
- UI 可展示的入口；
- 文档中的支持表；
- 未支持能力的稳定错误。

默认关闭，只有真实验收通过的组合才能从 `disabled` 变为 `supported`。单元测试通过、路由存在或 UI 菜单可见都不能单独改变支持状态。

### 5.7 控制在制品和设计文档数量

建议执行以下规则：

- 同一时间只允许一条纵向集成主链；叶子工作必须明确服务于这条主链。
- 未被当前消费者调用的接口不合入主线；实验代码留在独立分支或测试 fixture。
- 普通实现选择直接更新当前任务卡，不新增 ADR；只有服务边界、权威存储、任务语义、支持范围或上游版本变化才写 ADR。
- 重构与行为/schema 改变拆成不同变更，避免 AI 同时“整理代码”和改变语义。
- 输入 hash 未变化的历史重型证据可引用，不机械重跑；但最终组合必须实跑，不能用旧局部结果拼成一次新 PASS。

## 6. 推荐执行顺序

### P0：冻结当前候选和真相入口

- 固定 AgentStratum、Hindsight、依赖、模型/embedding 空间和运行 profile。
- 更新现有 `execution-workflow/CURRENT.md`，并建立可机器校验的支持矩阵摘要。
- 建立当前 `eb021da` 的 API/Worker/schema 基线和后续上游升级检查表。
- 将已合入的稳定离线测试纳入 PR CI；不改变业务语义。

退出标准：任何开发者或 AI 能从一个入口回答当前支持项、关闭项、唯一候选、真实证据和下三个任务，而不需要综合多份历史 handoff 猜测。

### P1：接通 MPS-1

- 完成生产 session adapter 与 Bank/action 目录。
- 接通异步 Retain/status/facts-only Recall。
- 用获权原生 processor 替代默认 VerifyOnly 装配。
- 接通 L 和 NativePGStore 的真实主链。
- 在双 Unit、双租户同名 Bank 下形成业务正常结果。

退出标准：满足第 4.3 节全部条件。

### P2：关闭正确性和恢复缺口

- H 全停、单 H 故障、W 重启、双 W 领取、配置漂移拒 READY。
- PostgreSQL 提交回执丢失、UNKNOWN 持久 hold、旧 Worker 不复活任务。
- 验证 G/H/W 不持有不属于自己的数据库或 provider 凭据。
- 非作者用固定制品复演。

退出标准：MPS-1 不仅能成功，而且失败语义可预测、可定位、可恢复。

### P3：按一个业务一个切片完成剩余 S1

建议顺序为：Reflect → 图/时间和原文检索 → observations/consolidation → Mental Model/知识页 → 必要管理与选定客户端。每个切片复用同一套身份、operation、模型、UNKNOWN 和证据规则，不为新业务复制基础设施。

最终仍需按原 75/157、99/68、J1/J2/J3 和非作者接手关闭完整 S1，不能用 MPS-1 代替。

## 7. 明确暂缓的工作及重新启动条件

| 暂缓项 | 现在不做的依据 | 重新启动条件 |
|---|---|---|
| 完整 Skill 生命周期和运行平台 | 当前 Skill 边界已定义，但基础 Retain/Recall 产品主链未接受 | S1 主链稳定，且有具体客户端消费者和验收场景 |
| 多供应商计费、硬预算和故障切换 | 首版固定模型即可验证边界；多供应商会引入额外重试和 UNKNOWN 语义 | 单供应商模型边界通过真实错误/超时/usage 验收，且出现明确商业需求 |
| 全量自助控制面和在线配置发布 | S1 允许受控初始化；当前先需要生产 session/Bank 目录 | 人工配置成为可量化的交付瓶颈，且版本一致性/回滚合同已确定 |
| 在线 schema 迁移、HA、自动伸缩和跨 Unit 联邦检索 | AgentStratum 当前主链、恢复和容量基线尚未接受 | 单 Unit/双 Unit 主链、恢复和容量基线完成，出现明确 SLO/容量目标 |
| 完整 Publication、原子跨对象版本和精确派生失效 | 当前 S1 文档已明确不同提交点不宣称同一原子版本 | 页、观察、删除等业务完成当前 CAS 和来源验收后再立 ADR |

暂缓不是否定长期价值，而是防止尚未验证的基础语义被更多产品能力放大。

## 8. 客观收益与代价

沿 AgentStratum 继续走的收益是明确的：

- 它给出了长期身份、Bank、授权、Unit 放置和配置权威；
- 把 Gateway、Handler、Worker、模型和存储的权限与故障责任分开，能表达非幂等请求、UNKNOWN、持久 claim 和恢复；
- 能在同一产品模型下逐步增加归纳、知识页、管理和客户端能力，而不把这些责任塞入 Hindsight 核心或一个 Gateway；
- 已有默认关闭、证据分级、固定上游和非作者接手机制，适合长期持续建设。

代价也同样客观：

- 它不再是“给 Hindsight 外挂一个 Gateway”，而是在建设一套产品服务、控制面和交付体系；
- 每个长期边界都增加合同、持久状态、升级和故障组合，局部代码完成不代表产品可交付；
- 固定上游会降低短期漂移，但后续升级需要持续维护兼容验证；
- 如果没有唯一当前真相、纵向主链优先级和强制 CI，更多 AI 并行投入会提高代码产量，但不必然提高可交付能力。

因此，“如果 Token 足够、团队能力强，是否值得做”的客观回答是：**值得，但前提不是资源无限，而是产品确实需要长期多租户、授权、恢复、模型治理和持续演进；同时必须用纵向验收约束投入。** AgentStratum 的长期边界有必要，但不需要一次完成所有远期能力。

## 9. 提炼后的团队决策建议

1. 长期产品主线继续采用 AgentStratum，并以当前仓库中的产品合同和验收记录作为唯一实现依据。
2. 下一候选只解决 MPS-1，不新增远期产品面；这改变实现顺序，不删除 S1 义务。
3. 把默认 `VerifyOnlyProcessor` 替换为获权原生 Retain 主链，作为当前最高优先级代码目标。
4. 更新现有 `execution-workflow/CURRENT.md` 作为唯一当前状态入口，并维护机器可读支持矩阵；历史证据按 hash 引用。
5. AI 任务必须绑定具体消费者、失败用例、不变量、允许写集和验收命令；没有这些信息不进入实现。
6. schema、Engine、HTTP、poller、operation 状态机继续由唯一集成写者修改；其他工作只写叶子 provider、测试和文档。
7. 将已稳定的阶段代码纳入分层 CI；Mock、真实 PG、真实模型和历史证据保持分开报告。
8. 建立 Hindsight 上游兼容轨，发布候选一次只固定一个提交，升级必须通过主链回归。
9. Skill、计费、全量控制面、HA、在线迁移等按明确触发条件逐步构筑，不用它们阻塞当前主链，也不提前宣称已支持。

最终判断标准应始终是：用户是否能从真实入口完成被声明支持的业务；系统是否在租户隔离、非幂等调用、进程故障和配置漂移下保持已定义语义；另一位开发者是否能从固定制品和一份当前文档复现。这三个问题如果没有同时得到证据，代码和设计仍只能算阶段材料，不能算产品能力。

## 10. 专家检视结果与可提交问题

### 10.1 检视范围与结论可信度

本轮固定基线为 `main@a066dde9c1a2727b625f918c1456a1193d58187f`，仓库检查为 clean。Claude Code 以只读方式检查代码、文档和已有收据；没有运行真实 PostgreSQL、OBS、模型、部署或完整产品验收。五个视角中，测试、集群运维、协作/并行研发三份报告完整返回；记忆与 PostgreSQL 两份在运行超过 25 分钟后仍未给出最终报告，为避免无期限等待已停止。两份未完成报告只使用其已核实的源码事实作为补充，不宣称五位专家达成一致。

三份完整报告的共同结论是：合同/局部实现已存在，但可移植、可重复的产品组合验收和运行生命周期证据不足。下列发现区分“源码/文档事实”与“建议”，提交 issue 前应由维护者确认优先级和负责人。

### 10.2 问题候选（按独立验收边界拆分）

1. **P0 — 扩大无资源 PR CI 的发现与覆盖范围。** 事实：CI 只运行 K01 的 35 个非 native 测试；默认 `pytest` 发现路径仅为 `tests/contextdb`。建议：增加 offline-no-resource 测试分类，纳入稳定的 Gateway loopback、Query/Retain 合同和 K02 protocol 测试；CI 输出测试目录清单并验证发现数。验收：干净环境下一条命令发现并运行声明的离线集合；真实资源测试不被伪装成 pass。
2. **P0 — 生成/更新唯一当前状态入口。** 事实：现存 `execution-workflow/CURRENT.md` 与当前 HEAD/工作流状态不一致；权威执行账本位于本机 `.local`，干净 clone 无该状态。建议：明确账本与 Git 摘要的边界，并从当前工作流数据生成 CURRENT 摘要，包含 HEAD、支持/关闭、PASS/NOT_RUN、阻塞和下步任务。验收：新 clone 能从单一文档定位当前状态，CI 能检测摘要过期；不复制本机运行账本或秘密。
3. **P1 — 建立纵向主链发布证据门禁。** 事实：TEST-PLAN 记录 75 父用例/157 步，但不是现成的完整自动化套件；J1/J2/J3 不完整，发布用例为 OPEN/NOT_RUN。建议：建立可机器读取的候选收据校验器，校验 commit/profile/build/attempt/pass/fail/skip/NOT_RUN、时间与结果引用；真实 PG、模型和非作者接手只按授权执行。验收：失败或缺收据会阻止候选接受，mock/真实结果不能互相代替。
4. **P1 — 登记共享核心集成写者与固定窗口。** 事实：执行计划中的集成写者仍为“待登记”，多个模块候选输出会交叠共享 schema/Engine/HTTP/poller。建议：文件/目录 owner 映射、单一集成 owner 和固定整合窗口；叶子接口/测试/文档继续并行。验收：共享写集均有 owner；两个连续窗口可接入叶子候选且无公共状态机双写。
5. **P1 — 提供无资源的干净克隆开发路径。** 事实：资源型 Stage 1 测试需要 grant；当前没有独立的 offline-no-resource 快速路径和简短锁定环境 quickstart；本机系统 Python 环境也不能作为可移植测试环境证据。建议：提供锁定 Python/uv 环境和 15 分钟内可运行的离线测试步骤，不降低资源测试保护。验收：非作者从 clean clone 不申请 DB/OBS/model grant 即可跑离线集。
6. **P1 — 为 PG 权限/claim/UNKNOWN/idempotency 建立真实数据库验收。** 事实（已完成核对部分）：K02 SQL 有安全角色、`SECURITY DEFINER` 与 hold 语义；PG45 的 45 项 `actual_pg` 均为 NOT_RUN（39 项代码存在、6 项受输入阻塞），既不能据此说代码失败，也不能说生产 SQL 已通过。建议：对目录中权限边界、事务、claim、hold/CAS 和重复投递行为补真实 PG 用例；`request_hash` 的唯一性/重复提交合同应显式验证。验收：固定 PG 版本与授权 profile 下有机器可读执行收据；重复请求结果确定，未知提交保持 hold。
7. **P1 — 完成服务安装、启动、停止和升级生命周期。** 事实：当前运维路径是单机 loopback runner；Ops 的真实 start/stop/export/restore 返回未实现/未授权；部署制品和安装路径仍有本机绝对路径假设。建议：先建立参数化的单机、非作者可执行生命周期，不扩张到集群编排。验收：clean host 安装、启动、健康、停止、重启的记录和故障清理；不误称 HA。
8. **P1 — 分离 readiness、liveness 和 drain。** 事实：Gateway `/health` 静态返回，不能说明 MetaPG 可用；目前没有明确的请求排空及停止接纳合同。建议：引入依赖检查的 `/ready`、信号停止时停止接新请求、在 deadline 内排空并留下证据。验收：权威服务不可用时 readiness 失败；停止期间无新 admission，未完成非幂等请求不被隐式重放。
9. **P1 — 明确对象存储耐久性及 held-task 恢复。** 事实：当前测试 bucket 配置 versioning disabled；Worker 对原始对象缺失采用 hold 语义，但没有闭环 restore 验收。建议：商用数据进入前定义备份/versioning 保证、恢复流程和对象 hash 验证；恢复动作不能暗中释放 hold。验收：在专用测试环境执行恢复演练并核对 hash/任务状态；不操作生产 bucket。
10. **P2 — 明确多 Gateway 的冷却/配额协调语义。** 事实：UNKNOWN 冷却当前是每进程局部，不能等同全局协调；共享冷却/全局 quota 属于未实现或延期项。建议：文档声明当前是 best-effort per-G，并为将来统一权威定义触发条件。验收：支持矩阵和运行文档一致，不暗示全局强一致配额。

### 10.3 GitHub 提交记录

避免重复开卡后，六项独立问题已新建；PG、服务生命周期、规模语义、恢复和 evidence reader 的相邻增量则补充到现有 Issue。所有提交均针对远端仍为 `a066dde9c1a2727b625f918c1456a1193d58187f` 的 `RSIXDB/agentstratum`，并逐项核对返回链接。

| 内容 | GitHub 记录 |
|---|---|
| 扩大无资源 PR CI 与 pytest 发现 | [#89](https://github.com/RSIXDB/agentstratum/issues/89) |
| CURRENT 状态摘要可从 clean clone 复现 | [#90](https://github.com/RSIXDB/agentstratum/issues/90) |
| 集成写集负责人及并行边界 | [#91](https://github.com/RSIXDB/agentstratum/issues/91) |
| clean-clone 开发 Quickstart | [#92](https://github.com/RSIXDB/agentstratum/issues/92) |
| 可机器判定的候选发布门禁 | [#93](https://github.com/RSIXDB/agentstratum/issues/93) |
| G/H readiness 与 graceful drain | [#94](https://github.com/RSIXDB/agentstratum/issues/94) |
| PG 真实验收增量 | [#16 评论](https://github.com/RSIXDB/agentstratum/issues/16#issuecomment-6063960452) |
| 部署生命周期与非作者复演增量 | [#34 评论](https://github.com/RSIXDB/agentstratum/issues/34#issuecomment-6063961242) |
| 跨 Gateway cooldown/quota 语义 | [#42 评论](https://github.com/RSIXDB/agentstratum/issues/42#issuecomment-6063962009) |
| 原始对象恢复与 held-task 增量 | [#69 评论](https://github.com/RSIXDB/agentstratum/issues/69#issuecomment-6063962839) |
| 证据 reader 与 acceptance gate 边界 | [#73 评论](https://github.com/RSIXDB/agentstratum/issues/73#issuecomment-6063963624) |
| 总控评审索引及未完成专家报告说明 | [#18 评论](https://github.com/RSIXDB/agentstratum/issues/18#issuecomment-6063959455) |
| shared Gateway session 与 Unit/Handler 放置合同 | [#21 架构评论](https://github.com/RSIXDB/agentstratum/issues/21#issuecomment-6064250369) |
| Hindsight 原生 Processor/WorkStore 产品纵切 | [#18 架构评论](https://github.com/RSIXDB/agentstratum/issues/18#issuecomment-6064251151) |
| contract-first 写集、集成窗口与流量度量 | [#91 并行开发评论](https://github.com/RSIXDB/agentstratum/issues/91#issuecomment-6064251822) |

记忆专家最终意见未完成；记忆质量基准、派生数据删除/更新血缘等候选不作为本轮共识，也未另建 Issue，避免从未完成的检视中推断结论。五份专家意见没有全部收齐，因此文档与 Issue 均不声称“五方一致”。

## 11. Codex 追加检视：架构边界与并行研发

### 11.1 评审状态和六个 Issue 的价值分布

2026-10-09 追加了只读 Codex 审查，补齐记忆/PG源码检查，并单独检查架构与并行开发。固定基线仍是 `a066dde9c1a2727b625f918c1456a1193d58187f`，AgentStratum 工作树 clean；没有运行 PG、OBS、模型或部署，也没有改产品仓。此前两份 Claude 专家报告确实没有最终产出；这次的 Codex 复核补上了证据，但不能倒称为那两份 Claude 报告已完成，也不能称五位 Claude 专家一致。

用户对六个新 Issue 的观感有一部分依据：#89 是 PR CI/测试发现，#93 是发布证据门禁；它们主要属于验证。其余四项分别触及当前运行状态入口（#90）、共享核心写集及集成责任（#91）、干净克隆接手（#92）、多实例健康/排空边界（#94）。其中 #91 是并行开发问题，#94 是运行架构问题，但这六项确实没有充分呈现本节的产品/数据架构判断。因此不应把“已提 Issue 数量”误当成架构评审完整度。

### 11.2 当前源码与已接受方向的架构差额

| 范围 | 当前源码/已接受方向 | 客观判断与建议 |
|---|---|---|
| Gateway 会话 | `gateway/app.py::create_gateway` 为每个 Gateway 建立自己的 `Sessions(snapshot)`；`gateway/auth.py::Sessions` 使用进程内字典。ADR-0003 与阶段计划要求 G 可扩展、共享登录，计划里也明确有生产 MetaPG session adapter 与双 G 会话验收 | 这不是“加测试即可”的差异，而是运行状态权威与拓扑合同尚未接通。先把 session store 设为显式可替换边界，写清共享状态、注销/撤销、快照版本失效和不可用时拒绝策略；跨 G 登录/撤销应由该合同定义。源码依据：`src/contextdb/gateway/app.py`、`src/contextdb/gateway/auth.py`、`docs/decisions/ADR-0003-tenant-stateless-pg-model-goals.md`、`docs/architecture/STAGED-CAPABILITIES-AND-MODULES.md` |
| Unit→Handler 放置 | `Unit` 只有一个 `handler_id/handler_origin`；`Forwarder` 对每个 Unit 选唯一 target；`create_handler` 要求一个 Handler 进程绑定一个 Unit | 已接受架构说 Handler 是独立可扩展集群，但具体副本/故障切换合同未定。商用前需要明确：每 Unit 单进程、一个 Unit 多副本经 LB，还是一个 Handler 承载多 Unit；并定义 readiness、故障后读请求恢复及非幂等请求不重试规则。当前只能说源码模型为单目标，不能直接判为违背已接受 ADR。源码依据：`src/contextdb/control/snapshots.py`、`src/contextdb/gateway/forward.py`、`src/contextdb/handler/app.py`、ADR-0002 |
| Hindsight 原生处理接缝 | `control/runtime.py::worker_service` 实际装配 `VerifyOnlyProcessor`；`k02/worker.py` 的处理只校验 UTF-8、hash 和长度，不抽取 facts、不调模型。仓内已有 `Processor`、`WorkStore` 协议，但尚未形成原生业务装配 | 这是当前产品纵切最关键的架构缺口。先冻结有类型的 Worker 输入/输出、状态、错误、scope 和 UNKNOWN 行为；通过窄 adapter 接入 Hindsight 原生 Retain，不让 Gateway 依赖 Hindsight 内部实现。共享 Engine/schema/poller 挂点继续单写，外围 adapter 与独立契约实现可并行。源码依据：`src/contextdb/control/runtime.py`、`src/contextdb/k02/worker.py`、`src/contextdb/contracts/` |
| 记忆能力/产品表面 | `native/query.py` 当前查询仅开放 semantic/keyword 两路、RRF 与 cross-encoder；observations、chunks、temporal 等参数显式拒绝。`native_pages_sql.py` 的页写路径限定为 `HUMAN_ASSERTION`。测试计划对完整业务结果仍标未验证 | 这是支持面边界，不应把拒绝路径描述成实现故障，也不应把已存在合同描述成完整产品。建议由单一 capability registry 输出每版的 supported/disabled 能力、入口、数据范围和模型空间；先交付可验收的 Retain→facts-only Recall 纵切，Reflect、观察归纳、图/时间、chunk 与自动页刷新分别建独立消费与接受条件，不改变原 S1 总义务。源码依据：`src/contextdb/native/query.py`、`src/contextdb/storage/native_pages_sql.py`、`docs/architecture/hindsight/TEST-PLAN.md`、`docs/architecture/STAGED-CAPABILITIES-AND-MODULES.md` |
| PG 幂等语义 | native catalog 对 `request_hash` 做格式检查，但主身份是 `operation_id`；K02 按稳定 operation UUID 和输入冲突保护，并对 UNKNOWN 采用 append-only hold | 当前证据支持“同 operation key 重放保护/输入冲突拒绝”，不支持按内容去重或跨多个写点 exactly-once。需把这三种保证命名区分，并为不同 operation ID、相同内容的行为定合同；跨服务去重若需要应另加权威 ledger，而非假设 hash 列已经提供。源码依据：`src/contextdb/storage/native_catalog.py`、`src/contextdb/k02/schema.py` |
| PG/OBS 恢复 | `native_pair.py` 有成对存储/迁移规划和拒绝未知 lineage 的保护；当前只能确认 planner/manifest 设计，不能据此声称真实 rt/ud 成对备份还原、OBS 原件与 held operation 已打通 | 商用数据进入前要定义恢复单元和恢复序：Meta 配置/版本、DataPG rt+ud、OBS raw、operation/hold、page history 与模型空间如何核验及何时解除 hold。真实恢复演练需要独立授权；已有 #69 只覆盖其登记范围，本轮评论补充了对象/held-task要求。源码依据：`src/contextdb/storage/native_pair.py`、`docs/operations/stage1/pg45/`、现有 Issue #69 |

也有明确的正向架构约束：Recall 将 `space_id`、维度和配置摘要绑定到向量，projection 保留来源 lineage；迁移遇到未知 lineage 会拒绝猜测并要求显式处理。这些是可保留的护栏，但本身不证明模型质量或检索效果。

### 11.3 如何实质加快多同事/多 Agent 并行

当前仓已经有并行结构：`TASK-CARDS.md` 将 P-INTEGRATION、P-MODEL、P-ACCEPTANCE、P-UI 作为独立准备工作；`PLAN.md` 记录四路准备会话；MP-01 至 MP-09 将交付分成 Gateway、Handler、PG、Model、Query、Pages、UI 等边界。真正的阻塞来自“准备可并行，公共实现接线仍串行”：`AGENTS.md` 要求共享 schema/Engine/http/poller 与公共接口单写，`PLAN.md` 第 109 行又把唯一集成写者标为“实际身份待登记”。任务卡明确 C-PG/C-MODELS/Retain/Query/Pages 会重叠 Engine 等路径，不能按模块名直接并发写。

建议采用以下工程模型，而不是继续简单增加测试任务或 Agent 槽位：

1. **先冻结可消费合同，再并行写叶子。** 对 `Processor/WorkStore`、ModelProvider、Gateway session、Unit/Bank scope、operation 状态和错误/UNKNOWN 语义固定版本化接口及小型 contract fixture。提供方和消费者先对同一合同 ACK；合同变更由 owner 提交，不让每个叶子分支同时改共享类型。
2. **两类写集，两个节奏。** 共享 Engine/schema/http/poller/registry 有一个具名 integration owner，串行合入；叶子目录由独立 owner 并行交付，例如模型适配、Gateway session adapter、PG 授权适配、UI 薄客户端、gold/fixture、文档和启动器。一个任务触及共享文件时，先交接口/patch给 owner，不以“改不同函数”作为多人并写豁免。
3. **按依赖 DAG 和可交付切片派工，不按模块名称平均分人。** 先列 provider→consumer→integration→system-acceptance 依赖。G session provider 与 UI consumer 可基于 fixture 并行；PG/模型 adapter 可以离线并行准备；Retain/Query/Pages 的共享 Engine 接线则等公共合同与核心 owner 的集成窗口。这样避免多团队同时完成“自己的模块”，最后发现 DTO、权限 scope 或状态机不兼容。
4. **解除“完整集成验收阻塞接口开发”的潜在环。** Issue #21 记录了 C-UI 等待 G review，而完整 Gateway 验收又包含 UI 消费；仓库 `post-merge/parallel-work.md` 的同类分析明确是 revision90 历史观察，不能单独当作当前任务状态。由当前总控核对活动任务图后，可将接受拆两段：先接受接口合同与固定 fixture，UI/客户端据此开工；最后再做双 G、真实 UI 的组合验收。不得把阶段接口 ACK 伪装成完整 J1/S1 通过。
5. **固定短集成窗口和异步 review SLA。** 例如每天两个集成窗口，由 owner 只合已冻结合同、写集无冲突、测试可复现的小 PR；独立 reviewer 按风险并行审，不等一整个模块完工后再排单审。失败返工只重开受影响写集，其他叶子继续推进。
6. **度量系统流量，不排行个人。** 每个任务/PR 记录 queued→started→candidate→reviewed→integrated 时间、blocked 等待、共享文件冲突、返工次数、首次 contract compatibility 和每周可集成切片数。用这些数据判断瓶颈是集成 owner、外部资源还是接口变更；不要用 commit/token 数推断个人效率。

这是对当前共享核心单写政策的落实和切分，不是简单放松安全约束。若共享核心继续由一位 owner 修改但 owner 未登记、无固定窗口，名义上的 4 路准备并发不会转化为可集成的产品代码；反过来，先把协议边界和叶子写集做实，可以在保持单写安全的情况下提高真正可合并的并发。

本轮没有新建架构 Issues；上述三类高价值架构/并行意见已分别补充到现有 [#21](https://github.com/RSIXDB/agentstratum/issues/21)、[#18](https://github.com/RSIXDB/agentstratum/issues/18) 和 [#91](https://github.com/RSIXDB/agentstratum/issues/91)，避免重复开卡。其余问题优先并入现有 #16/#34/#69 与 #91，避免 Issue 数量继续膨胀。

### 11.4 多同事加入与 AI 产物对齐：具体问题、方法和试点

**团队背景（用户提供，非仓库可验证事实）**：当前代码仓是同事 `zcimon57-svj` 调度 Agent team 开发的初期可用版本；其他同事较难直接并发参与，希望借多人协作加快进度，并确认 AI 生成结果符合团队实际预期。本节不评价个人表现，只把它作为接手与并行机制的输入。仓库侧可核实的对应事实是：现行计划有四路并行“准备”会话，但共享核心集成写者仍待登记，且多个交付任务会触碰相同 Engine/公共接口。因此，真实问题不是“没有并行”，而是并行准备尚未被稳定地转成多位同事可独立交付、可组合验收的代码切片。

| 具体问题 | 依据与影响 | 可落地的解决方法 |
|---|---|---|
| 接手依赖原始 Agent 会话上下文 | 新同事若不知道当前基线、决策、合同、运行命令和未决项，就必须重新读大量材料或向原编排者追问；AI 对话本身不是可共享的交付接口 | 每个任务附一页 contribution packet：基线 SHA、目标行为、允许/禁止路径、接口链接、依赖任务、验收例、复现命令、owner/reviewer、已知不做事项。合并后的事实回写仓库文档，不能只留在聊天记录 |
| 并行任务仍是准备而非独立实现 | `PLAN.md` 将四路定义为独立准备会话；`TASK-CARDS.md` 同时指出公共 Engine 等写集重叠 | 将每项工作标成 `contract/prep`、`leaf implementation` 或 `shared-core integration`。只有写集互斥、依赖明确且消费合同已冻结的任务才标 `parallel-ready`；每张卡列出精确路径白名单，不按“PG/模型/查询”等模块名推断可并写 |
| 多人同时生成不同接口，最终由集成人肉适配 | DTO、scope、错误/UNKNOWN、operation 状态若在各分支各自演进，PR 即使各自通过测试也可能无法组合 | 先由产品/合同 owner 发布版本化协议与固定 contract fixtures；提供方和消费者各自跑同一 fixtures。公共合同只由具名 integration owner 修改，变更须给兼容策略和迁移窗口 |
| 共享核心形成单点排队 | 当前共享核心单写是合理的安全护栏，但计划未登记实际集成负责人；所有核心接线等一个人时，增加 Agent 数并不会提高合入吞吐 | 明确一位 shared-core integration owner 和替补；每个工作日安排两个短集成窗口；叶子 PR 异步 review，核心 PR 按窗口串行合入。集成 owner 负责组合与冲突，不包揽所有叶子实现 |
| AI 产物“测试通过”但产品预期未对齐 | 单元测试可验证既定实现，却不能证明实现的行为就是团队期望；尤其 scope 隔离、撤销、UNKNOWN、重试和故障恢复易出现隐含假设 | 任务卡必须含 Given/When/Then 正例、反例、边界条件及明确不做项；由非作者同事先审行为例，再审实现。关键路径提供可执行 contract test/黄金 fixture，并将决策理由写回 ADR 或接口文档 |
| 并发收益无法判断 | 只看 Agent 数、commit 数或代码行数，会把等待、返工和集成成本隐藏起来 | 以两周试点记录 queued/blocked/review/integration 时长、共享写集冲突、返工次数、首次合同兼容率、每周被系统验收的切片数；不做人效排名，也不预设并发等于线性提速 |

**建议试点**：选一条窄但端到端的异步纵切（Gateway 接受请求→Handler/operation 合同→Worker 的 `Processor` adapter→可查询结果），不把试点说成完整 S1 能力。由合同 owner 先写一个成功例、一个拒绝/UNKNOWN 例和状态迁移 fixture；随后把工作拆给 3–4 位同事：一位做独立叶子 adapter，一位做消费端/薄客户端，一位补 contract 与故障 fixture，一位担任共享核心集成 owner。若参与者数量不足，可一人承担多个互不重叠写集，但同一时段仍不多人改共享核心。

试点开始前检查以下“可并行”门槛：

1. 每张任务卡有固定基线 SHA、单一可观察交付行为、精确路径写集、接口版本与依赖图。
2. 提供方和消费者都能在独立 worktree 里用同一 fixture 验证，不依赖原 Agent 会话或未公开本机状态。
3. 任务有正例、负例、权限/scope 边界和明确的验收人；涉及外部资源时标明可替代的本地验证及未验证项。
4. 共享核心 owner、reviewer、集成窗口及冲突升级路径已经登记；合同变更不由多个并行分支各自决定。

两周后的判定看系统结果而非主观感受：至少两份互不重叠的叶子实现能并行启动并被集成；新参与者仅凭任务包可在 30 分钟内运行对应验证；每份交付都能追溯到冻结合同和验收例；报告实际排队、review、集成、返工和冲突数据。若主要时间仍耗在公共核心排队，应优先缩小核心写集或稳定扩展点，而不是继续增加 Agent 并发数。若出现合同不兼容，则先修任务拆分/contract fixture，再讨论团队吞吐。

这套方法不要求把单写政策改成多人同时编辑核心，也不要求一次性建设大型平台。它把“同事容易接手”“AI 输出可审”“成果能合并”落实为可检查的任务包、合同门槛、owner 责任和两周数据。仓库现有 `PLAN.md`/`TASK-CARDS.md` 已有部分基础，下一步是把准备会话升级成有精确写集和验收收据的实现任务，并登记真正的集成责任人。
