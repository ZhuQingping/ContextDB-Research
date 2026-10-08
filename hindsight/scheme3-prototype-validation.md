# ContextDB 方案 3 原型验证报告

日期：2026-10-08
最终状态：**PARTIAL**（T01-T08 PASS；T09 FAIL）

## 1. 汇总

| 用例 | 结果 | 实际结果 | 证据 |
|---|---|---|---|
| T01 进程/健康 | PASS | Gateway、4 API、4 Worker 健康；4 API 均报告 `worker=false` | `t01-health.json` |
| T02 Gateway 分发 | PASS | tenant1 顺序 20 次 10/10，并发 20 次 10/10；tenant3 8 次 4/4 且只在 Cell2 | `t02-gateway-distribution.json` |
| T03 共享 Cell 隔离 | PASS | tenant1/2 同 Bank ID、同 Cell1、不同 schema；各自 marker 可见且交叉不可见 | `t03-t04-tenant-isolation.json` |
| T04 独享 Cell | PASS | tenant3 只在物理独立 Cell2 PG，Cell 间 schema 集合无交叉 | `t03-t04-tenant-isolation.json` |
| T05 API/Worker | PASS | API 父操作 pending/completed；两条 Worker 子任务均审计到 pending/processing/completed，并分别绑定 worker1/worker2 | `t05-worker-operations.json` |
| T06 API 故障边界 | PASS | 停 API1 后 6/6 由 API2 成功；恢复后 3/3 分布；非幂等请求零隐藏重试 | `t06-api-failure-boundary.json` |
| T07 零侵入 | PASS | 原 checkout 干净；worktree 核心三目录 diff 为空；变更仅原型目录 | `t07-git-zero-intrusion.json` |
| T08 重启 | PASS | stop/start 后 SQLite、PG 数据保留，T01/T02 再次 PASS | `t08-restart.json` |
| T09 真实模型 | FAIL | Codex + ONNX 请求能运行、Retain 完成；最终 tenant1 Recall 未包含唯一 marker | `t09-real-model*.json` |

自动化业务验收：8 passed / 1 failed / 0 skipped。原型单测：5 passed。`compileall`、`ruff`、`git diff --check` 均通过。

## 2. 证据解释

### T01/T02

命令：`contextdb-scheme3 smoke --core`。真实本地进程和真实 HTTP 验证，不是模拟进程。API 版本为 0.10.2，全部关闭内置 Worker。Gateway 使用每 Cell 独立锁和计数器；响应头证明选中的 Cell/节点。

### T03/T04

命令：`contextdb-scheme3 smoke --full`。模型层使用 `mock` LLM 与 `deterministic-test-embedding`，因此这里只证明服务拓扑、协议链路和隔离，不证明准确率。存储层是真实 PostgreSQL：Cell1/Cell2 是两个独立 Docker 容器和命名卷，不是同实例双库。

### T05

API 返回 batch 父 operation ID；当前 Hindsight 会派生 Worker 领取的 retain 子任务。父操作外部采样为 pending/completed；原型专用 PG 审计触发器保存了两个子任务各自的 pending/processing/completed，processing/completed 行分别带 `cell1-worker1`、`cell1-worker2`。受控方法是暂停另一 Worker 后提交一项任务，再交换角色；未声称自然竞争均匀。

### T06-T08

故障测试只停止清单中的 `cell1-api1`。Gateway 对 GET/HEAD 最多一次同 Cell 重试；对非幂等请求没有隐藏重试。重启测试停止并恢复全部原型进程及两个精确命名容器，PG 命名卷与 SQLite 映射保持。

### T09

执行三次脚本尝试，但真实模型调用预算只产生 tenant1 Retain 2 次、tenant1 Recall 2 次、tenant2 Recall 1 次：

1. attempt1：ONNX 进程误用缺 `transformers` 的主 venv，0 次模型调用；FAIL，保留根因。
2. attempt2：改用既有 Hindsight ONNX 环境；tenant1 Retain/Recall 成功，tenant2 独立 schema 的同名 Bank 不存在并返回 404。旧断言把该正确隔离结果判失败。
3. final：允许 404 作为负向隔离；Retain completed，但 tenant1 Recall 响应未包含唯一 marker，FAIL。

实际配置：`openai-codex / gpt-5.6-sol / low`、`intfloat/multilingual-e5-small / 384`、RRF。认证内容未读取或保存。这个 FAIL 不否定拓扑验证，但意味着本轮不能宣称真实模型 Retain/Recall 内容验收通过，也不评价记忆质量。

## 3. 方案 3 得到证明的结论

- 多租户可共享同一 Cell 的原生 Hindsight API/Worker/PG，并由 schema 隔离。
- 官方 API/Worker 入口可形成 4 API + 4 Worker 分离进程拓扑。
- 独立 Gateway 可只依赖 HTTP 合同完成租户到 Cell placement 和 Cell 内均匀轮询。
- API 与 Worker 通过 PostgreSQL 异步表协作；Gateway 不调用 Worker。
- 共享型和独享型可使用同一套原型与 Hindsight 启动方式。
- 核心源码、Extension 和 Helm 无需修改。

未证明：真实模型召回 marker 验收、OBS、性能/SLO、资源公平性、PG/网关高可用、生产认证授权、迁移与跨 Cell 故障接管。

## 4. 路径与最终运行状态

- worktree：`/Users/zhuqingping/Work/Database/Context/.local/worktrees/hindsight-scheme3-prototype`
- branch：`prototype/scheme3-cell-poc-20261008`
- base：`a77c1f3412a7b82f36588dffce1a8d7480e99cc7`
- evidence：`/Users/zhuqingping/Work/Database/Context/ContextDB-Research/hindsight/evidence/scheme3-prototype-2026-10-08`
- 最终：Mock profile 的 Gateway、Embedding、4 API、4 Worker 与两个 PG 容器均保持健康运行。
