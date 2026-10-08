# ContextDB 方案 3 原型运行手册

日期：2026-10-08

## 1. 环境与入口

- worktree：`/Users/zhuqingping/Work/Database/Context/.local/worktrees/hindsight-scheme3-prototype`
- 命令：`prototypes/contextdb-scheme3/contextdb-scheme3`
- 运行目录：`/Users/zhuqingping/Work/Database/Context/.local/runtime/hindsight-scheme3-prototype`
- 证据目录：`/Users/zhuqingping/Work/Database/Context/ContextDB-Research/hindsight/evidence/scheme3-prototype-2026-10-08`
- 要求：本机 Docker 可用、主仓 `.venv` 可用，固定端口 18080、18081、18101/2、18111/2、18201/2、18211/2、55434/5 空闲。

所有命令从 worktree 根执行：

```bash
cd /Users/zhuqingping/Work/Database/Context/.local/worktrees/hindsight-scheme3-prototype
prototypes/contextdb-scheme3/contextdb-scheme3 start
prototypes/contextdb-scheme3/contextdb-scheme3 status
prototypes/contextdb-scheme3/contextdb-scheme3 smoke --core
prototypes/contextdb-scheme3/contextdb-scheme3 smoke --full
```

`start` 可重复执行。启动失败时只回收本轮 PID 清单内的进程。`stop` 只核对并终止本原型 PID/进程组以及两个精确命名容器：

```bash
prototypes/contextdb-scheme3/contextdb-scheme3 stop
```

## 2. 次日人工验收

1. 执行 `status`，预期 `status=healthy`、`profile=mock`、10 个进程健康、2 个容器 running。
2. 执行 `smoke --core`，预期 T01/T02 PASS。
3. 执行 `smoke --full`，预期 T01-T08 PASS；该命令会安全地停启本原型进程并写入新的合成测试数据。
4. 查看 Gateway 路由：`curl -s http://127.0.0.1:18080/prototype/routes | jq .`。该接口不需要 Key，只输出脱敏 placement。
5. 查看最终证据：`jq . /Users/zhuqingping/Work/Database/Context/ContextDB-Research/hindsight/evidence/scheme3-prototype-2026-10-08/final-environment-status.json`。

真实模型命令为：

```bash
prototypes/contextdb-scheme3/contextdb-scheme3 smoke --real-model
```

本轮 T09 已消耗允许的 tenant1 两次 Retain 复验预算且最终 FAIL；次日默认不要重跑。该命令会暂时切换到 Codex/ONNX，结束后恢复 Mock。

## 3. 流量、Worker 与 schema 证据

- API 分发：`t02-gateway-distribution.json`；期望 tenant1 顺序 20 次为 10/10，并发两节点都非零，tenant3 只出现 Cell2 节点。
- Gateway JSONL：运行目录 `logs/gateway-mock.log`；字段不含 Authorization。
- Worker：`t05-worker-operations.json` 同时保存父操作 API 状态、子任务 PG 三态审计和两个 Worker claim 行。
- schema：`postgres-schema-table-counts.json`；Cell1 只含 `scheme3_tenant1/2`，Cell2 只含 `scheme3_tenant3`。
- PID 与启动摘要：运行目录 `processes.json`；明文测试 Key 仅在 `secrets/tenant-keys.json`，权限 0600，不要复制到报告。

直接查看 schema 名称（不显示数据或 Key）：

```bash
docker exec contextdb-scheme3-poc-20261008-cell1-pg psql -U hindsight -d hindsight -Atc "select schema_name from information_schema.schemata where schema_name like 'scheme3_%' order by 1"
docker exec contextdb-scheme3-poc-20261008-cell2-pg psql -U hindsight -d hindsight -Atc "select schema_name from information_schema.schemata where schema_name like 'scheme3_%' order by 1"
```

## 4. 故障恢复

- 单 API 故障：再次执行 `start` 会按清单恢复缺失节点；也可先 `stop` 再 `start`。
- 端口冲突：不要夺占端口；先确认占用者。若非本原型，保持停止并修改原型固定拓扑后重新验收。
- 进程异常：查看运行目录 `logs/<process>-<profile>.log`，不得使用 `pkill`/`killall`。
- PG 容器停止：`start` 会重新启动精确命名容器并保留命名卷数据。
- 完整安全重启：

```bash
prototypes/contextdb-scheme3/contextdb-scheme3 stop
prototypes/contextdb-scheme3/contextdb-scheme3 start
prototypes/contextdb-scheme3/contextdb-scheme3 smoke --core
```

## 5. 开发检查

```bash
PYTHONPATH=prototypes/contextdb-scheme3 /Users/zhuqingping/Work/Database/Context/hindsight/.venv/bin/python -m pytest -q prototypes/contextdb-scheme3/tests
/Users/zhuqingping/Work/Database/Context/hindsight/.venv/bin/python -m compileall -q prototypes/contextdb-scheme3
/Users/zhuqingping/Work/Database/Context/hindsight/.venv/bin/ruff check prototypes/contextdb-scheme3
git diff --check
git diff -- hindsight-api-slim hindsight-extensions helm
```
