# Hindsight 本地体验与验收

2026-10-04。**服务已安装并完成真实 GPT 调用验证。** 先打开 [管理界面](http://127.0.0.1:9999)，进入 `huawei-contextdb-demo`。本地服务仅监听回环地址；没有修改原有 5432 数据库，也没有修改 Hindsight 源码或你的 Agent 全局配置。

| 入口 | 地址／用途 |
|---|---|
| 管理 UI | <http://127.0.0.1:9999> |
| 演示库 | <http://127.0.0.1:9999/banks/huawei-contextdb-demo> |
| API／接口文档 | <http://127.0.0.1:8888/docs> |
| 健康状态 | <http://127.0.0.1:8888/health> |
| 单库 MCP | `http://127.0.0.1:8888/mcp/huawei-contextdb-demo/` |
| 本次独立 PG | `127.0.0.1:55432`；数据目录 `~/.pg0/instances/contextdb-research-20261004/` |

## 明早先体验这三件事

1. 在演示库查看 `incident-2048-v1`：它是合成的数据库连接池故障复盘。搜索“海星项目连接耗尽的原因、处理措施和负责人是什么？”；查看检索事实及原文来源。
2. 查看知识页“验收复盘／连接池排查经验”。这是 Hindsight 从记忆生成的页面，**尚不是本报告建议的华为云人工审批发布功能**。
3. 在 `huawei-contextdb-knowledge` 查看合成规范 `runbook-17-v1`，问“是否可以直接终止生产连接？”。这个库使用 chunks 模式保存原文，未走事实提取。

`huawei-contextdb-isolation` 是空库对照。`huawei-contextdb-clone` 是删除语义实验：原文已删，既有知识页面仍在；用于直观看到云产品必须补齐的派生数据治理边界。全部内容都是合成样例，不应当作生产操作手册。

## 启停和快速复验

以下命令在调研仓库根目录执行：

```bash
python3 deployments/hindsight-local/scripts/service.py status
python3 deployments/hindsight-local/scripts/service.py start

# 只读复验：健康、来源、两类召回、空库隔离、知识树和统计。
deployments/hindsight-local/.venv/bin/python \
  deployments/hindsight-local/scripts/acceptance.py \
  --check-only --output manual-read-check.json

# 如需停止，仅停止本次 API/UI；保留 PG 数据。
python3 deployments/hindsight-local/scripts/service.py stop
```

进程已在后台运行；机器重启或退出导致服务停止时运行 start。没有安装系统开机任务。电脑睡眠时服务也不可访问。API 初次启动需下载依赖／模型，本次已缓存并固定 Embedding 快照；后续启动通常更快，以 health 为准。

直接调用已部署服务：

```bash
curl --noproxy '*' -sS \
  http://127.0.0.1:8888/v1/default/banks/huawei-contextdb-demo/memories/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"海星项目如何处理连接耗尽？","budget":"low","max_tokens":1200}'
```

给接受 `mcpServers` 配置的客户端，可参考 [MCP 示例](mcp-client.example.json)。本次已经用真实 MCP 客户端完成工具发现与 recall；没有替你改现有 Agent 的配置。是否自动记忆仍由客户端的工具调用或 hook 决定；连接 MCP 后可先明确要求“调用 Hindsight recall 查询海星项目”。

## 实际安装组成

| 项目 | 本机实际配置 |
|---|---|
| API | 用户源码 `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`，版本字符串 0.10.2 |
| UI | npm `@vectorize-io/hindsight-control-plane@0.10.2`；独立安装目录 |
| Python | 本任务 `.venv`，Python 3.12.13 |
| PG／向量 | pg0 管理的 PostgreSQL 18.1，pgvector 0.8.5；另有 pg_trgm、btree_gin |
| 提取／整合／回答 | `openai-codex` provider，`gpt-5.6-luna`，low reasoning（2026-10-04晚按成本要求切换） |
| Embedding | 本机 ONNX `intfloat/multilingual-e5-small`，固定快照 `614241f...` |
| 排序 | `rrf`，未部署 CrossEncoder Reranker；这是体验配置，不是 AMB 配置 |
| Worker | 内置，2 槽位；整合保留 1、共享 1 |
| 原件 | 本次 native PG 存储；未连接 OBS 或华为云 RDS |

**GPT 使用本机现有登录凭据调用远端模型，不是离线运行 GPT。** 仅复制 access token 与必要账户标识到 `.secrets/codex/auth.json`，不复制 refresh token，不改写原始登录文件。当前凭据记录的到期时间为 2026-10-13 14:35 UTC，也可能提前失效。若失效，确认本机 GPT 登录有效后执行下列命令，再重启本次 API：

```bash
python3 deployments/hindsight-local/scripts/refresh_local_access.py
python3 deployments/hindsight-local/scripts/service.py stop api
python3 deployments/hindsight-local/scripts/service.py start api
```

模型远端连接依赖本机当前代理配置。`.secrets`、`.venv`、`.runtime` 均被本目录 `.gitignore` 排除；交付证据日志做了脱敏。请勿把 `.secrets` 加入版本库。

初次安装执行的核心命令：

```bash
uv venv --python 3.12 deployments/hindsight-local/.venv
uv pip install --python deployments/hindsight-local/.venv/bin/python \
  '/Users/zhuqingping/Work/Database/Context/hindsight/hindsight-api-slim[embedded-db,local-onnx]'
npm install --prefix deployments/hindsight-local/.runtime/ui --save-exact \
  @vectorize-io/hindsight-control-plane@0.10.2
```

这两条安装命令中的传递依赖会随时间变化；复现当前环境需对照 [Python freeze](evidence/python-freeze.txt)、[UI lock](evidence/ui-package-lock.json)、[配置](config.json) 和 [源码哈希](evidence/source-manifest.json)。浏览器测试另装了 Playwright，使用机器已有 Chrome；它不参与服务运行。

## 验证结果及证据

| 验证 | 结果 | 证据 |
|---|---|---|
| API／UI 启动 | 均返回 HTTP 200 | [启动日志](evidence/api-sanitized.log)、[UI 日志](evidence/ui-sanitized.log) |
| 真实浏览器 | 首页与演示库可显示，捕获的 JS 异常为 0 | [首页](evidence/browser-home.json)、[演示库](evidence/browser-bank.json) |
| 写入、幂等重试、召回、reflect、原文、无效输入 | 20 条 HTTP 记录；结构验收通过 | [运行结果](evidence/acceptance-run.log)、[请求结果](evidence/acceptance.json) |
| 中文回答 | 本样例正确保留原因、500→120、复测 85、负责人林岚，并说明为合成历史记录 | [reflect 原始返回](evidence/acceptance.json)；这是单样例核对，不是准确率评测 |
| 知识页面 | 后台生成正文，可导出 | [生成内容](evidence/knowledge-page-ready.json)、[导出响应](evidence/knowledge-export-response.json) |
| MCP | 单库发现 36 个工具，真实 recall 成功 | [MCP 记录](evidence/mcp-verification.json)；文档中的工具数量与运行版本不同 |
| 第二 PG 的多租户 | 同名 Bank／文档读写隔离、外租户 memory ID 404、删除 A 不影响 B | [13 条 HTTP 记录](evidence/tenant-checks.json)、[结果](evidence/tenant-checks-run.log) |
| MCP 鉴权 | 第二单元匿名访问返回 401 | [拒绝记录](evidence/mcp-auth-rejection.json) |
| Bank 克隆 | 异步完成，原文及页面可读取 | [克隆记录](evidence/clone-check.json) |
| 源文档删除边界 | recall 为 0，但旧知识页面仍可读 | [实测证据](evidence/source-delete-check.json)；作为风险，不记成“彻底清除通过” |
| 停止并重启 API／PG | 数据保留；8 条只读复验通过 | [重启健康记录](evidence/restart-health.json)、[复验](evidence/restart-read-check.json) |
| PG 逻辑恢复 | 六张核心表行数、内容 SHA256 全部相等 | [恢复记录](evidence/backup-restore-check.json)、[命令日志](evidence/backup-restore-command.log) |
| 服务单元故障边界 | 停止第二单元后，主单元 health 仍 200 | [记录](evidence/cell-stop-isolation.json)；没有实现自动路由或在线迁移 |

完整测试会写入、调用 GPT 并生成页面；仅需日常验收时用 `--check-only`。重复运行完整测试保留每次证据，避免把新增同名页面误认为产品故障。

快速复核可先看[关键日志摘录](evidence/key-service-lines.log)；[证据索引](evidence/artifact-manifest.json) 记录文件大小和 SHA256。

## 部署中发现并处理的问题

1. **Worker 容量配置。** 总槽位 2 配默认整合保留槽 2，普通异步 retain 一直 pending。改为保留 1 后，重启恢复待处理任务并完成提取／整合。[诊断](evidence/worker-slot-diagnosis.log)。首次测试因主动重启出现连接错误，保留了 [原始失败](evidence/initial-slot-interrupted.log)，没有算进通过结果。
2. **多租户公共维护函数。** 第二单元的租户表已可用、health 正常，但 public 中维护发现函数缺失。显式执行 `hindsight-admin run-db-migration --schema public` 后，函数存在且 SQL 调用成功。[迁移日志](evidence/cell-b-base-migration.log)、[复验](evidence/cell-b-maintenance-after.json)。云服务开通流程应验证基础 schema 和租户 schema 两部分。
3. **删除派生内容。** 删除源文档不能等同于清除既有知识页面；产品需要定义清除／撤回语义并补齐控制。
4. **中文全文。** 本机 English tsvector 未命中连续中文中的“连接池”；当前中文体验依赖多语言向量，不能宣称中文全文完整可用。[PG 检查](evidence/pg-inspection.json)。

没有进行：8 小时稳定性压测、华为云 RDS／OBS 适配、HA／PITR、商业费用测算、完整依赖许可／漏洞审计、完整多租户权限审计、竞品同条件实跑或 AMB 重测。本次使用了夜间任务窗口完成部署和研究，未将耗时不足 8 小时的实验包装成 8 小时压测。

## 实验环境的保留位置

主 API/UI 保持运行。第二单元已停止以节省资源，PG 数据保留在 `~/.pg0/instances/contextdb-research-cell-b/`。需要复现时：

```bash
python3 deployments/hindsight-local/scripts/cell_b.py start
deployments/hindsight-local/.venv/bin/python deployments/hindsight-local/scripts/tenant_checks.py
python3 deployments/hindsight-local/scripts/cell_b.py stop
```

逻辑备份在 `.runtime/backups/hindsight-local.dump`；恢复目标是第二 PG 上的 `contextdb_research_restore` 数据库。[恢复脚本](scripts/backup_restore_check.py) 故意拒绝覆盖已有恢复库。没有建立客户业务资源，也没有删除机器上其他项目的数据。

服务化决策请看[架构](../../hindsight/archive/2026-10-19-before-reorganization/cloud-service-architecture.md)、[竞争力与投入](../../hindsight/archive/2026-10-19-before-reorganization/cloud-service-priorities.md)、[来源核验](../../hindsight/archive/2026-10-19-before-reorganization/cloud-service-evidence.md)。

成本控制更新：LLM并发1，自动整合默认关闭；8个现有Bank有效配置均关闭自动整合。启动最小模型调用与服务健康通过，见[运行证据](round2/evidence/runtime-cost-control.json)。历史客户端测试使用此前模型，未为此次切换重跑收费测试。
