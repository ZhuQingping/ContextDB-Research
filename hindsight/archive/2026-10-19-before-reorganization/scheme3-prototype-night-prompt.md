# 方案3原型：夜间8小时Agent执行提示词

> **历史执行提示词**：该提示词用于2026-10-08的方案三原型任务，原型已完成，验证结果见[方案三原型验收报告](scheme3-prototype-validation.md)及对应证据目录。它描述“租户1/2共享Cell1、租户3独享Cell2”的验证拓扑；截至2026-10-09，产品首期已明确为独享版，因此不要直接把本提示词当作当前产品开发计划。
>
> 路径说明：文中的本机路径已改为相对于 `ContextDB-Research` 根目录或相邻仓库的路径；命令假设当前工作目录是该仓库根目录。运行旧提示词时，先确认当前工作目录和代码基线，不能把历史固定版本当成当前 HEAD。

生成日期：2026-10-08<br>
任务类型：关键技术选型原型、功能开发、本机多进程端到端验证<br>
预计执行时间：夜间8小时，无人值守<br>

下面正文可以完整复制到一个新的Agent会话执行。

---

你是华为云ContextDB方案3原型的唯一执行Agent。请连续自主工作，完成实现、启动、测试、证据保存和文档更新，不要停留在分析或计划阶段，也不要向用户询问实现细节。遇到普通工程选择时自行作出最小、可验证的决定。只有涉及破坏现有数据、需要真实云凭据、需要向远端提交代码，或无法在允许目录内完成时才停止对应动作，并继续完成不依赖该动作的工作。

## 1. 任务目标

用真实可运行的原型证明以下架构在短期可以实现：

1. 多个租户可以共享一个Data Cell的Hindsight API、Worker和PostgreSQL；
2. Hindsight API和Worker可以使用官方支持的分离进程部署；
3. Gateway与Hindsight代码解耦，客户端只访问Gateway；
4. Gateway根据租户信息选择Cell，并在Cell内的多个API节点之间均匀分发请求；
5. API通过PostgreSQL异步任务表与Worker协作，Gateway不直接调用Worker；
6. 共享型与独享型使用同一套原型代码和Hindsight启动方式；
7. 不修改Hindsight核心代码即可完成核心验证。

固定测试拓扑：

```text
客户端
  |
Gateway：127.0.0.1:18080
  |
  +-- tenant1、tenant2 --> Cell1（共享型）
  |                       |- Hindsight API 1：127.0.0.1:18101
  |                       |- Hindsight API 2：127.0.0.1:18102
  |                       |- Hindsight Worker 1：127.0.0.1:18111
  |                       |- Hindsight Worker 2：127.0.0.1:18112
  |                       `- Cell1 PostgreSQL
  |
  `-- tenant3 ----------> Cell2（独享型）
                          |- Hindsight API 1：127.0.0.1:18201
                          |- Hindsight API 2：127.0.0.1:18202
                          |- Hindsight Worker 1：127.0.0.1:18211
                          |- Hindsight Worker 2：127.0.0.1:18212
                          `- Cell2 PostgreSQL
```

目标是验证服务化拓扑、租户隔离、Gateway路由和API/Worker分离。模型使用替身时，不评价记忆准确率、召回率或生成质量。

## 2. 必读材料和代码基线

本任务的唯一实现基线是Hindsight源码。开始写代码前必须按顺序阅读：

1. `../hindsight/AGENTS.md`
2. `../hindsight/CLAUDE.md`
3. `../hindsight/hindsight-api-slim/hindsight_api/extensions/tenant.py`
4. `../hindsight/hindsight-extensions/static-keys-tenant/README.md`
5. `../hindsight/helm/hindsight/templates/api-deployment.yaml`
6. `../hindsight/helm/hindsight/templates/worker-statefulset.yaml`
7. `./hindsight/Hindsight Architecture.md`

可优先参考以下本机实测材料，以发现已经可用的Codex LLM、ONNX Embedding、RRF和服务启动方法：

- `./deployments/hindsight-local/README.md`
- `./deployments/hindsight-local/round2/README.md`
- `./deployments/hindsight-local/round2/MODEL-HANDOFF.md`
- `./hindsight/Huawei ContextDB Service Develop.md`
- `./hindsight/contextdb-design-expert-review.md`

`ContextDB-Research`中的其他文档也允许只读参考，但不能自动继承结论。每项影响实现的历史信息都要核对文档日期、当时Hindsight提交、当前提交`a77c1f...`源码和本机实际运行状态，并在新文档中标记为`当前源码确认`、`本机重新验证`、`历史证据`、`推断`或`已过时`。HTML、旧Agent结论和旧成功日志不能代替本轮运行。

以下两个仓库只用于理解另一候选方案和最后做差异说明，不是本任务的代码基线，不得复制、导入或依赖其中的实现：

- `../ContextArk`
- `../agentstratum`

启动时记录而不要猜测：

```bash
git -C ../hindsight status --short
git -C ../hindsight branch --show-current
git -C ../hindsight rev-parse HEAD
```

编写本提示词时观察到的基线，仅用于发现漂移：

- Hindsight源码：`a77c1f3412a7b82f36588dffce1a8d7480e99cc7`，版本`0.10.2`

若HEAD已经变化，记录实际值，继续从本机Hindsight当前`main`创建原型worktree；不要自行fetch、pull、rebase或reset。Hindsight必须以本机实际HEAD为运行基线，不能退回旧提交。当前新提交修改了Worker启动恢复逻辑，实施前应阅读`hindsight_api/worker/main.py`和`hindsight_api/worker/poller.py`的当前实现，不沿用旧代码行号。

## 3. 权限和范围

### 已授权操作

- 读取三个仓库和本机进程、端口、PostgreSQL可用性；
- 在独立worktree中创建原型代码和测试；
- 在明确的新文档中写设计、运行手册和验证结果；
- 创建原型专用SQLite、日志、PID、临时数据库和非敏感测试数据；
- 启动和停止本原型创建的进程；
- 运行单元测试、集成测试和端到端测试；
- 若本机已有Docker，可创建名称带`contextdb-scheme3-poc-20261008`前缀的原型专用PostgreSQL容器；
- 任务结束时，在全部健康检查通过的前提下保留原型服务运行，便于用户次日验收。

代码修改权限：**GRANTED，仅限下面的允许目录。**<br>
夜间执行权限：**GRANTED。**

### 代码worktree

主仓：`../hindsight`<br>
建议worktree：`../.local/worktrees/hindsight-scheme3-prototype`<br>
建议分支：`prototype/scheme3-cell-poc-20261008`

若该worktree或分支已存在，先核对来源和脏状态。不能证明属于本任务时不要覆盖，改用带时间后缀的新worktree，并在报告中记录实际路径。

### 允许修改的文件

Hindsight独立worktree中仅允许新增或修改：

- `prototypes/contextdb-scheme3/**`

调研仓中仅允许新增或修改：

- `./hindsight/scheme3-prototype-design.md`
- `./hindsight/scheme3-prototype-runbook.md`
- `./hindsight/scheme3-prototype-validation.md`
- `./hindsight/evidence/scheme3-prototype-2026-10-08/**`

运行数据只允许写入：

- `../.local/runtime/hindsight-scheme3-prototype/**`

### 禁止操作

- 不修改Hindsight原始checkout；只允许在独立worktree的`prototypes/contextdb-scheme3/**`中增加原型；
- 不修改Hindsight现有`hindsight-api-slim/**`、`hindsight-extensions/**`、`helm/**`、客户端或其他核心目录；
- 不修改、导入或复制AgentStratum和ContextArk中的代码；这两个仓库只读；
- 不读取或打印个人`.env`、浏览器凭据、GitHub凭据、Hindsight商业版账号或API Key；允许按本机既有Hindsight运行方式引用已配置的Codex认证文件或本地模型配置，但不得显示、复制或写入证据；
- 不调用Hindsight商业Cloud；除用户已经授权的本机Codex模型配置外，不调用其他收费模型或上传数据；
- 不执行`git reset --hard`、`git clean`、广泛`killall/pkill`、删除现有数据库或容器；
- 不提交、push、开PR、merge、rebase或改变远端；
- 不使用未锁定的`latest`依赖，不升级Hindsight；
- 不把Mock模型的结果写成真实模型效果结论；
- 不为追求测试通过修改Hindsight核心代码。

## 4. 必须遵守的实现边界

### 4.1 Hindsight保持原生

运行时使用Hindsight独立worktree中的源码：

`../.local/worktrees/hindsight-scheme3-prototype`

优先复用现有Hindsight Python环境和源码入口。不得修改Hindsight核心源码。API和Worker必须使用官方入口：

```text
hindsight-api
hindsight-worker
```

每个API进程必须设置：

```text
HINDSIGHT_API_WORKER_ENABLED=false
```

每个Worker必须设置唯一且稳定的：

```text
HINDSIGHT_API_WORKER_ID
```

### 4.2 多租户使用官方Extension

共享Cell优先使用Hindsight源码中的：

```text
hindsight_ext_static_keys_tenant:StaticKeysTenantExtension
```

Cell1配置tenant1和tenant2，映射到两个独立PostgreSQL schema；Cell2只配置tenant3。API和Worker必须使用完全相同的Tenant Extension配置，使Worker的`list_tenants()`能够发现相同租户。

测试API Key运行时随机生成。SQLite只保存Key哈希和Key ID；明文测试Key只写入权限为`0600`、位于`.local/runtime/scheme3-prototype/secrets/`的文件，绝不能进入Git或证据文档。

如果现有StaticKeysTenantExtension可以满足原型，不得另写HuaweiTenantExtension。只有实际接口缺口阻塞验证时，才在原型目录实现最小独立Extension，并在设计文档中记录缺口、源码证据和新增代码量。

### 4.3 Gateway必须独立

Gateway放在`prototypes/contextdb-scheme3/`，不得导入Hindsight内部模块。它只使用HTTP合同与Hindsight通信。

Gateway原型至少完成：

1. 从Authorization Bearer Key计算哈希；
2. 从SQLite读取tenant、Cell和API后端列表；
3. 拒绝未知Key；
4. 按Cell维护独立、并发安全的round-robin计数器；
5. 将请求路径、查询参数、方法、请求体和必要Header转发到选中的Hindsight API；
6. 删除客户端伪造的内部路由Header；
7. 响应增加不含秘密的原型诊断Header，例如`X-ContextDB-Cell`和`X-ContextDB-Upstream`；
8. 输出JSON lines访问日志，包含request_id、tenant_id、cell_id、backend_id、状态码和耗时，不记录Authorization值；
9. 提供Gateway自身的`/health`和只读`/prototype/routes`诊断接口；
10. 对非幂等请求不做隐藏重试。

原型不实现组织、成员、账单、审计、复杂RBAC和生产密钥生命周期。

### 4.4 Metadata使用SQLite

SQLite适合本次单Gateway原型。至少保存：

- tenants：tenant1、tenant2、tenant3及共享/独享类型；
- cells：cell1、cell2；
- placements：tenant到Cell映射；
- api_backends：Cell内API节点ID和HTTP地址；
- api_keys：Key哈希、Key ID和tenant；
- schemas：tenant对应的PostgreSQL schema名称。

SQLite不保存PostgreSQL密码、OBS密钥或模型密钥。设计文档必须明确：SQLite只用于单节点原型，生产需替换为高可用元数据库及配置发布机制。

### 4.5 PostgreSQL和对象存储

优先为Cell1和Cell2使用两个独立的本机PostgreSQL实例或两个原型专用容器。若本机条件不允许，可在同一个PostgreSQL服务中创建两个独立数据库作为替代，但必须在报告中标为“逻辑Cell隔离验证”，不能声称验证了物理实例故障隔离。

Cell1中的tenant1和tenant2必须位于同一个数据库的不同schema。Cell2的tenant3必须位于另一个数据库。两个Cell不能共用Hindsight连接地址。

本轮不要求真实OBS。文件存储保持Hindsight本地或PostgreSQL方式，并把OBS列为未验证项。

### 4.6 本机真实模型与低成本替身

用户已授权本轮使用本机现有的Hindsight模型配置做验证。按以下两层执行并分别记录结果：

**第一层：无费用拓扑验证。** 使用Hindsight内置`mock` LLM和确定性Embedding替身，先完成Gateway、API/Worker、Cell路由、PostgreSQL任务和租户隔离验证。替身必须命名为`deterministic-test-embedding`，不能用于准确率结论。

**第二层：本机真实模型小样本复验。** 在第一层通过后，使用本机当前实际可用的模型配置复跑最小Retain/Recall链路。历史材料显示曾使用：

- LLM：`openai-codex` provider，通过本机现有登录凭据调用Codex模型；历史运行模型为`gpt-5.6-luna`、low reasoning；
- Embedding：本机ONNX `intfloat/multilingual-e5-small`，384维；
- 排序：RRF，不是神经网络Rerank模型。

这些只是历史线索。必须先通过当前服务状态、当前启动配置和`a77c1f...`源码确认，不能照抄旧参数。允许让新进程引用本机Hindsight专用的现有Codex认证文件或模型缓存路径，但不得读取、打印、复制认证内容，也不得修改用户的全局Codex登录配置。

真实模型验证必须控制消耗：

- 只使用合成短文本；
- 每个租户至多2次Retain、2次Recall；默认不执行Reflect；
- LLM并发设为1，关闭自动Consolidation和非必要Mental Model刷新；
- 记录调用次数、成功/失败和耗时，不记录Prompt中的秘密；
- 若认证失效或本机模型不可用，标记真实模型用例`NOT_RUN`或`FAIL`并保留原因，不能自行登录、刷新或寻找其他密钥；
- Mock链路通过与真实模型链路通过必须分别报告，不能互相替代。

本机ONNX模型若被多个API/Worker进程重复加载导致内存压力，可以复用已有loopback TEI兼容包装或在原型目录启动一个共享的本地Embedding服务；必须核对向量维度一致性。Rerank首期继续使用RRF，除非本机已有经过确认的Rerank服务且无需新增下载。

## 5. 实施步骤

### 阶段A：勘察和设计

1. 核对三个仓库的Git根、HEAD、分支和脏状态；
2. 检查目标端口是否占用；冲突时选择一组连续的新端口并记录；
3. 检查本机PostgreSQL、Docker和Hindsight Python环境，只记录能力，不读取秘密；
4. 阅读Hindsight的TenantExtension、Worker启动、任务领取和StaticKeys实现；
5. 检查本机Hindsight服务的非敏感模型信息和模型缓存可用性；不得输出认证内容；
6. 从`ContextDB-Research`筛选与本任务有关的历史实测材料，并逐项标记当前有效性；
7. 不阅读或复用AgentStratum Gateway实现来编写原型；原型完成后才可只读比较接口和改动量；
8. 先创建`scheme3-prototype-design.md`，写出实际进程、端口、数据库、schema、请求路径、任务路径、模型配置来源、文件位置和已知限制；
9. 设计发生变化时直接修正文档当前章节，不在文末堆叠互相冲突的历史结论。

### 阶段B：最小代码

在允许目录实现：

- SQLite元数据初始化和查询；
- Gateway HTTP服务；
- 确定性Embedding替身，以及对本机真实模型配置的非敏感引用；
- Cell/API/Worker进程配置生成器；
- `start`、`status`、`smoke`、`stop`命令；
- 只终止本任务PID清单中的进程；
- 原型诊断和证据采集工具；
- 单元测试。

启动器必须为每个进程保存：角色、Cell、节点ID、PID、端口、启动命令的脱敏摘要和日志路径。启动失败必须回收本次已启动的子进程，不得影响现有服务。

### 阶段C：启动真实多进程拓扑

至少启动并验证：

- Gateway × 1；
- Cell1 API × 2、Worker × 2；
- Cell2 API × 2、Worker × 2；
- 两个逻辑独立的PostgreSQL Cell；
- 无费用Embedding替身 × 1；第一层通过后按资源情况启用本机真实Embedding配置。

如果机器资源不能稳定运行Cell2的2个API和2个Worker，可以降级为Cell2 API × 1、Worker × 1，但必须同时满足：

1. Cell1仍保持API × 2、Worker × 2；
2. 记录实际CPU/内存或启动失败证据；
3. 报告状态为PARTIAL，不得写成完整拓扑PASS。

### 阶段D：测试和证据

必须实现自动化验收脚本，一条命令可重复执行。至少覆盖以下用例：

#### T01 进程和健康状态

- Gateway健康；
- 所有API健康；
- 所有Worker健康；
- 每个进程的Cell和节点ID与PID清单一致；
- API返回`worker=false`，证明没有内置Worker。

#### T02 Gateway均匀分发

- 使用tenant1连续发出至少20个无副作用或只读请求；
- Cell1 API1和API2都收到请求；
- 单线程连续请求时两节点计数差不超过1；
- 并发请求时两节点都非零，保存实际计数；
- tenant3的请求只能到Cell2，不能到Cell1。

#### T03 共享Cell租户隔离

- tenant1和tenant2使用相同的Bank ID；
- 两者分别创建或写入不同测试标识；
- tenant1只能看到tenant1的数据，tenant2只能看到tenant2的数据；
- PostgreSQL中存在两个不同schema；
- 查询证据只保存表名、schema名和计数，不保存测试Key。

#### T04 独享Cell路由和存储隔离

- tenant3的全部请求进入Cell2；
- Cell2数据库存在tenant3 schema；
- Cell1数据库不存在tenant3 schema；
- Cell2数据库不存在tenant1/tenant2 schema；
- tenant3使用与tenant1相同Bank ID仍不能读取tenant1数据。

#### T05 API与Worker协作

- 通过Gateway提交异步Retain或其他真实Hindsight异步操作；
- API返回操作ID；
- Worker从PostgreSQL领取并完成任务；
- 保存操作状态变化`pending -> processing -> completed`的证据；
- 证明Cell1两个Worker进程都健康；
- 尽量提交足够任务并从操作表或日志证明两个Worker都至少处理一个任务；
- 如果正常竞争下只有一个Worker领取任务，用受控方法分别暂停另一个Worker并提交一项任务，证明两个Worker都具备执行能力，然后恢复两个Worker；不得伪造均匀任务分配结论。

#### T06 Cell内故障边界

- 只停止Cell1的一个API节点；
- Gateway后续只读请求仍可通过另一个API节点完成；
- 恢复该API节点并重新进入round-robin；
- 不对正在执行的非幂等请求做自动重试。

#### T07 Hindsight零侵入

执行并保存：

```bash
git -C ../hindsight status --short
git -C <hindsight-worktree> status --short
git -C <hindsight-worktree> diff -- hindsight-api-slim hindsight-extensions helm
```

预期Hindsight原始checkout无本任务修改，独立worktree中的现有Hindsight核心目录也无修改。新增代码只能出现在`prototypes/contextdb-scheme3/**`。

#### T08 重启和可重复验收

- 执行原型`stop`，确认只停止清单内进程；
- 再次执行`start`；
- 重跑核心smoke；
- SQLite映射和PostgreSQL数据仍可使用；
- 最终健康时保持服务运行，供次日验收。

#### T09 本机真实模型小样本

- 第一层Mock拓扑验证通过后才执行；
- 使用本机已配置的Codex LLM和本地ONNX Embedding，至少对tenant1完成一次短文本Retain并等待操作完成；
- 对同一Bank执行Recall，确认请求成功并返回来自本租户的数据；
- tenant2使用相同Bank ID不能取到tenant1的唯一标识；
- 记录实际provider、模型名称、Embedding模型、维度、请求次数、耗时和操作状态；
- 不记录认证文件内容、Token或Authorization Header；
- 若本机认证或模型环境不可用，如实标记`NOT_RUN`或`FAIL`，Mock结果仍只代表拓扑验证。

### 阶段E：文档和晨间交付

持续更新并最终完成：

1. `scheme3-prototype-design.md`
   - High Level Design；
   - Low Level Design；
   - 实际进程和端口；
   - Gateway选择Cell和API节点的算法；
   - API写任务、Worker领取任务的链路；
   - SQLite表结构；
   - Hindsight扩展与环境变量；
   - 实际代码改动边界；
   - 历史调研材料的采用、淘汰及重新验证清单；
   - 原型与生产方案的差距。
2. `scheme3-prototype-runbook.md`
   - 环境要求；
   - 一键start/status/smoke/stop命令；
   - 次日人工验收步骤；
   - 日志和PID位置；
   - 如何确认两个API都收到流量；
   - 如何确认两个Worker工作；
   - 如何查看三个租户的schema隔离；
   - 故障恢复方法。
3. `scheme3-prototype-validation.md`
   - 每个用例的命令、预期、实际结果和证据路径；
   - `PASS / FAIL / PARTIAL / NOT_RUN`，不得只写笼统成功；
   - Mock、真实本地进程、真实PostgreSQL分别标记；
   - Mock模型结果与Codex/ONNX真实模型结果分别标记；
   - 失败和限制必须保留；
   - 最终说明方案3哪些结论得到证明、哪些仍未证明。

证据目录至少保存：

- 脱敏进程清单；
- 健康检查结果；
- Gateway节点分发计数；
- tenant到Cell和schema的脱敏映射；
- PostgreSQL schema/表计数；
- Worker领取与操作状态证据；
- 自动化测试日志；
- Git零侵入检查；
- 最终环境状态JSON。

所有证据不得包含API Key、数据库密码、Authorization Header或商业账号信息。

## 6. 验证命令要求

根据最终实现补齐真实路径，但至少执行：

```bash
# 原型单元测试
python -m pytest -q prototypes/contextdb-scheme3/tests

# 静态检查，只检查本原型
python -m compileall prototypes/contextdb-scheme3

# 启动、状态、端到端、重启
<prototype-command> start
<prototype-command> status
<prototype-command> smoke --full
<prototype-command> smoke --real-model   # 本机Codex/ONNX可用时执行；否则记录NOT_RUN原因
<prototype-command> stop
<prototype-command> start
<prototype-command> smoke --core

# 修改范围
git status --short
git diff --check
git diff -- hindsight-api-slim hindsight-extensions helm
```

若仓库已有适用且不要求真实云资源的Gateway测试，可以额外运行；不要运行整个历史75AT或全部Hindsight测试来消耗夜间窗口。

## 7. 时间分配

不要为追求完美耗尽时间。建议：

- 第0～1小时：源码核对、端口和环境勘察、设计文档初稿；
- 第1～3小时：SQLite、Gateway、Embedding替身、真实模型配置接入和进程启动器；
- 第3～5小时：两个Cell和API/Worker多进程启动、修复集成问题；
- 第5～6.5小时：自动化端到端测试、负载分发、隔离和Worker证据；
- 第6.5～7.5小时：重启复验、失败修复、证据整理；
- 最后0.5小时：文档定稿、最终健康检查、晨间交接。

如果时间不足，优先级为：

1. Cell1两租户、API × 2、Worker × 2真实运行；
2. Gateway路由和均匀分发；
3. Cell2独享租户隔离；
4. 自动化重启和验收文档；
5. 非核心诊断体验。

## 8. 停止条件

遇到以下情况停止对应危险动作，但继续文档和不依赖工作：

- 目标端口或数据库属于其他任务，无法安全隔离；
- 需要读取未知秘密或调用收费服务；
- 需要修改Hindsight现有核心目录或使用AgentStratum实现才能继续；
- 需要删除、重建或迁移现有数据库；
- 同一阻塞连续三次出现，且没有新的安全替代路径；
- 发现worktree有他人未提交改动且不能隔离。

不得为了“夜间完成”隐藏失败、跳过证据或扩大权限。

## 9. 提交策略

- 不commit；
- 不push；
- 不创建PR；
- 保留独立worktree中的完整可审diff；
- 最终报告实际worktree路径、分支、基线HEAD、修改文件和测试结果。

## 10. 最终回复格式

最终回复必须简洁并包含：

1. **原型状态**：PASS、PARTIAL或FAIL；
2. **实际拓扑**：Gateway、各Cell的API/Worker/PG数量与端口；
3. **核心证据**：Gateway分发、租户隔离、Worker处理和零侵入结果；
4. **测试汇总**：passed/failed/skipped以及未运行项；
5. **次日验收入口**：runbook绝对路径和一键命令；
6. **代码位置**：worktree和修改文件；
7. **文档位置**：三个Markdown文档及证据目录；
8. **已知限制**：明确Mock模型、PostgreSQL是否物理独立、OBS和性能是否验证；
9. **运行状态**：哪些进程仍在运行，如何安全停止。

完成的判据不是“写完代码”，而是用户第二天能按照runbook在本机复验以下事实：tenant1/tenant2共享Cell1，tenant3使用Cell2；Gateway在正确Cell的API节点间分发请求；API与Worker是独立进程；两个Worker具备任务处理能力；租户数据隔离；Mock拓扑结果与本机Codex/ONNX真实模型结果清楚分开；Hindsight现有核心源码没有被修改，所有新增实现都位于独立的原型目录。

---

## 提示词制定时采用的关键假设

这些假设已写入执行提示词，不需要新Agent再次向用户确认：

1. API × 2、Worker × 2首先是每个Cell的目标；资源不足时只允许Cell2降级，且必须标PARTIAL。
2. SQLite仅用于单Gateway原型，不代表生产元数据库选择。
3. 两个本机PostgreSQL数据库可以证明路由和逻辑数据隔离；只有两个独立实例才能证明实例级隔离。
4. 先用Mock LLM和确定性Embedding证明拓扑，再用本机Codex LLM和ONNX Embedding完成少量真实复验；两类证据分开报告。
5. OBS、商业鉴权、账单、审计和性能压测不属于本次核心范围。
6. 本次原型直接基于Hindsight源码和官方Extension机制开发；不基于、不导入、不接入同事在AgentStratum中实现的方案四代码。
7. `ContextDB-Research`和ContextArk中的材料允许参考，但旧文档必须与当前源码和本轮运行交叉核验后才能作为结论依据。
