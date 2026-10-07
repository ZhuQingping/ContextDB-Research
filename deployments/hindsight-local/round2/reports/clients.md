# 客户端与远程 Coding 集成核验

基线：Hindsight `f7dd3f4fd7420f7beec60c32c965e5e5cf7be066`；2026-10-04；合成数据；真实 API `127.0.0.1:8888` + PG + 服务端真实 GPT 抽取；新建 `round2-client-*` banks。原源码、已有 Bank、用户全局配置与原凭据未改动。

## 结论

1. **远程 Coding Agent 记忆不是新差异化。** 上游 coding-agents 0.8.0 已原生支持云/自托管 URL + bearer token、Claude/Codex 跨客户端每仓库共享 Bank、自动写入、自动上下文注入及知识页。旧独立 Claude/Codex 插件已被统一插件取代。华为云必须做可验收的企业管理/成本/接入体验，不能把远程支持包装成独有。
2. **REST/MCP 可调用、插件单元测试、真实宿主自动生命周期是三层不同证据。** 本次 Codex/Claude 自动链与真实 Hermes runtime 自动链已通过；OpenClaw 真 CLI + Gateway 的自动链也通过（需显式授权 hooks 与提供稳定会话身份）。
3. **默认参数会改变可见行为。** Coding-agents 当前 `autoInject=reflect`（每会话一次）加每轮知识页匹配；云基础档可以选择 `recall`，明确它是配置建议、不是默认。Hermes 当前默认只召回 observation，`recall_sync=false` 是后台预取下一轮注入：验收刚写入事实时应选择 world/experience/observation 并同步召回，或等待 consolidation，不应误报丢数据。
4. **Bank ID/项目路径映射不是租户鉴权。** 客户端可自行改变 URL/Bank，服务端必须独立授权。客户端共享 Bank 能力不能替代团队管理员审批、权限撤销与知识晋升流程。

## 验证矩阵

| 项目 | 版本/方式 | 结果 | 证据 |
|---|---|---|---|
| coding-agents 上游全部普通测试 | 0.8.0；Vitest；真实客户端/模型未参与 | 1288/1288 PASS | `clients-coding-tests-layout-fixed.json` |
| OpenClaw 插件普通测试 | 0.13.0；Vitest | 389/389 PASS | `clients-openclaw-tests.json` |
| Hermes 插件普通测试 | 1.2.1；pytest；fake Hermes core/client | 38/38 PASS | `clients-hermes-tests.xml` |
| Codex 显式 MCP | CLI 0.160.0 + gpt-6.1-sol；独立 retain/recall 会话 | PASS；operation completed；ORCHID-6842/73 | `clients-codex-retain.jsonl`、`clients-codex-operation.json`、`clients-codex-recall.jsonl` |
| Codex 自动 Stop + 新会话自动 UserPromptSubmit | 同上；原生插件 dist，临时命令行 hooks；禁工具 | PASS；WILLOW-3815 | `clients-codex-auto-retain-persistent.jsonl`、`clients-codex-auto-recall.jsonl`、`clients-hook-diag.jsonl` |
| Claude 显式 MCP | CLI 2.1.289 + 用户既有兼容服务 glm-5.3-flash | retain accepted；不能单凭 accepted 宣称完整写入 | `clients-claude-retain-auth-env.jsonl` |
| Claude 自动 Stop + 新会话自动 UserPromptSubmit | 同上；临时 --settings hooks；禁工具 | PASS；BIRCH-6937/57 | `clients-claude-auto-summary.json`、`clients-claude-hook-diag.jsonl` |
| Hermes 自动写入 + 独立新进程自动召回 | 真 AIAgent runtime `af90026aa09949579bd423d24def3d38f743cde0`；Python 3.14；gpt-6.1-sol；源码 SDK/embed 0.10.2 | PASS；LARCH-2074/47；completed=true；两次真实模型请求 | `clients-hermes-runtime-retain.json`、`clients-hermes-runtime-recall.json`、对应 log |
| OpenClaw 真 CLI + Gateway 自动双会话 | OpenClaw 2026.9.8 / Node24.16 / 插件0.13.0 / 既有 glm-5.3-flash | PASS；FIR-8193/39；自动保存 completed，日志 injecting 1 memories | `clients-openclaw-runtime-retain.jsonl`、`clients-openclaw-runtime-recall.jsonl`、`clients-openclaw-operations.json`、`clients-openclaw-gateway-excerpt.log` |

Hermes 本轮启动的是实际 `AIAgent` 核心和真实 memory provider，**不是 fake core，也不是完整交互 CLI/Telegram/Desktop 验收**。OpenClaw 插件 tests、Hermes tests 虽全绿，都不能代表实际宿主/版本已兼容。

## 已复现的反例与修正

- coding-agents 首轮复制包缺 monorepo sibling 文档，4 个 docs-roster tests ENOENT，其余 1284 通过。保持测试不变，恢复目录布局与文档只读链接后 1288 全通过。初始报告 `clients-coding-tests.json` 保留。
- Codex `--ephemeral` 的 Stop payload `transcript_path=null`：hook exit 0 **并不等于自动写入成功**。实际没有该合成事实。普通持久会话提供 transcript 后 retain_ok；本次新会话 ID `01a10756-4e43-7c71-8c8b-61a6c3b717c2`。原会话文件留在默认路径，不移动/删除。
- Claude 隔离 `--setting-sources ''` 会排除用户已配置的模型环境，最初返回 Not logged in。仅在测试子进程内复制原 settings 的模型环境后通过；未登录新账户、未改配置。它证明 **Claude Code 宿主兼容现有 GLM 服务**，不是证明 Anthropic 官方 Claude 模型通过。
- Hermes runtime 需 Python 3.14。本次隔离 venv 安装。直接按包版本从当前 pip index 安装 Hindsight 客户端失败；改为安装固定本机源码副本的 SDK/embed 0.10.2，不改 runtime 源码。
- OpenClaw 2026.9.8 要求 Node >=24.16.0 <25 或 >=26.1.0，本机 Node23.11 不满足；安装独立 Node24.16 后执行。
- OpenClaw 真 Gateway 日志明确阻断未授权外部插件的 `before_prompt_build`/`agent_end`，要求 `plugins.entries.hindsight-openclaw.hooks.allowConversationAccess=true`。**服务已启动、模型正常回复、插件已注册，仍可能没有任何自动记忆**。本次只针对合成验收 profile 开启，不改全局设置。

- OpenClaw `--session-id` 生成 `agent:main:explicit:...`，插件从中无法恢复稳定 message provider，自动 recall/retain 被跳过。改用 CLI 原生 `--session-key agent:main:webchat:direct:round2-claw-<phase>` 后成功。这是**CLI 合成 webchat 身份路径**，没有连接实际 Telegram/Slack/WebChat 页面，也没有对外发送消息。两个会话 key 不同，共用显式静态 Bank。
- OpenClaw 模型请求最初 401：现有兼容模型服务除了 bearer 还要求原配置里的 x-api-key header；子进程仅内存复制既有 header、config 保留环境引用后 HTTP200。没有新账号/新模型凭据。OpenClaw 返回 cost.total=0 是自定义模型没有定价元数据，**不代表真实费用为零**。
- 实际网络边界：客户端连接本机 Hindsight HTTP，Hindsight 与客户端模型调用使用远端真实服务；本轮不是华为云公网/TLS/IAM/跨地域验收。

## 接入路径与证据定位

| 宿主 | 推荐当前入口 | 远程设置 | 自动生命周期 |
|---|---|---|---|
| Claude Code | `@vectorize-io/hindsight-coding-agents` | `apiUrl`、`apiToken`、`bankId`/动态每仓库 Bank | SessionStart、UserPromptSubmit、Stop |
| Codex | 同上 | 同上 | 同上；须启用并信任 hooks，临时测试使用已审查的 hook trust bypass |
| Hermes | `hermes-plugin-hindsight` | `mode=local_external/cloud`、`api_url`、`HINDSIGHT_API_KEY` | memory provider 自动 prefetch/sync；hybrid/context/tools 三种模式 |
| OpenClaw | `@vectorize-io/hindsight-openclaw` | `hindsightApiUrl`、`hindsightApiToken`（SecretRef） | before_prompt_build、agent_end/session_end；需要 runtime conversation access 授权 |

源码依据（均为固定本地版本）：

- `hindsight-integrations/coding-agents/README.md:52–66, 441–443, 585–618`：安装、远程模式、参数默认。
- `hindsight-integrations/coding-agents/src/harness/hook-lifecycle.ts:238–278`：Claude/Codex hooks 与 transcript reader。
- `hindsight-integrations/coding-agents/src/core/hook.ts:1–22`：当前自动注入模式，默认 reflect 不是旧版每轮 recall。
- `hindsight-integrations/hermes/README.md:195–260`：远程模式、types/sync 默认、自动 retain。
- `hindsight-integrations/hermes/tests/conftest.py:1–8`：明确 fake Hermes core，因此测试只能证明插件逻辑。
- `hindsight-integrations/openclaw/src/index.ts:2699,3335`：自动 hooks。
- `hindsight-api-slim/hindsight_api/api/mcp.py:347–369`：多 Bank `/mcp` 与单 Bank `/mcp/{bank_id}/`。
- OpenAI 官方文档：https://learn.chatgpt.com/docs/extend/mcp?surface=cli 、https://learn.chatgpt.com/docs/hooks （已实际打开；hooks 临时/项目信任语义）。

## 可复验命令

从仓库根执行；测试依赖副本已在 `round2/clients-work`。真实模型验收有实际模型调用，所有输入仅合成事实。

```bash
# 插件普通测试；第一项需要保留 clients-work/hindsight-docs 只读链接。
(cd deployments/hindsight-local/round2/clients-work/hindsight-integrations/coding-agents && npm test)
(cd deployments/hindsight-local/round2/clients-work/openclaw && npm test)
(cd deployments/hindsight-local/round2/clients-work/hermes && uv run --frozen pytest)

# Claude：禁用工具，第一进程自动保存，等待 PG 任务完成后第二进程自动召回。
python3 deployments/hindsight-local/round2/scripts/clients_claude_runtime.py retain
python3 deployments/hindsight-local/round2/scripts/clients_claude_runtime.py recall

# Hermes：实际 runtime，独立配置，仅访问令牌，不复制 refresh token。
deployments/hindsight-local/round2/clients-work/hermes-runtime/.venv/bin/python deployments/hindsight-local/round2/scripts/clients_hermes_runtime.py retain
deployments/hindsight-local/round2/clients-work/hermes-runtime/.venv/bin/python deployments/hindsight-local/round2/scripts/clients_hermes_runtime.py recall
```

Codex 逐项完整参数保存在 `clients-codex-auto-retain-persistent-command.json` / `clients-codex-auto-recall-command.json`。不能把等待固定秒数当成写入成功；验收脚本应轮询 operation completed 或断言数据库 API 已可召回，再开启新会话。

## 上线建议与门槛（设计建议，不是已交付产品能力）

首期把“单个已认证插件版本，一份受控配置，一条自检命令”做稳，比新做四个插件性价比高。共享远程 Bank、自动记忆、知识页本身已有上游能力；差异在客户不必自行管理 PG/模型凭据，以及企业权限、审计、预算与恢复的整合。

兼容性流水线分三层：每 PR 插件逻辑测试；每次服务发布通过 HTTP/MCP/鉴权黑盒；每个已支持客户端版本真实宿主合成双会话验收。最后一层固定随机事实（第二会话提示不带答案）、关闭其他记忆来源、校验自动 hook 日志和服务端任务状态，覆盖撤权、超时、重启、限流、失败重试与跨租户反例。**本轮成功只是单一场景冒烟，不代表所有功能完备、准确率领先或企业安全认证。**

## OpenClaw 复验与清理

```bash
# 18879 为专属临时 Gateway；配置和token均在忽略目录 clients-work。
python3 deployments/hindsight-local/round2/scripts/clients_openclaw_runtime.py start
python3 deployments/hindsight-local/round2/scripts/clients_openclaw_runtime.py retain
# 先确认 bank 的 batch_retain completed，然后：
python3 deployments/hindsight-local/round2/scripts/clients_openclaw_runtime.py recall
# 检查 PID 属于此临时路径、gateway run 与18879，才发SIGTERM：
python3 deployments/hindsight-local/round2/scripts/clients_openclaw_runtime.py stop
```

本轮完成后已对专属 Gateway PID 25366 发送 SIGTERM；没有停止主演示 Hindsight。`clients-work` 全目录 gitignored，模型密钥只在测试子进程环境使用，Gateway 随机token文件权限0600。公开客户端证据经精确凭据匹配检查，未发现令牌值；去除了 Claude 中间 thinking 内容，保留工具调用、最终回答和状态。见 `clients-redaction-audit.json`。

最终自动核验：`python3 deployments/hindsight-local/round2/scripts/clients_verify.py` 返回0，11项全部通过；证据 `clients-verdict.json`。脚本语法检查通过；临时Gateway已退出，主演示API仍healthy（`clients-cleanup.json`）。
