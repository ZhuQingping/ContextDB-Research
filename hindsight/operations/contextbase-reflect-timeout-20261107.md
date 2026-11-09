# 深度回忆超时：现场处理与默认值评估待办

记录日期：2026-11-07，时区 Asia/Shanghai。

## 结论与状态

outer_space 首轮自动深度回忆出现客户端提前超时；服务端仍在执行模型调用与重试。本次已调整本机实例与项目配置，并通过一次真实 Hook 调用验证。**这些值是现场调优配置，尚未修改产品源码默认值，也未形成通用默认值结论。后续需评估是否修改默认值。**

环境：ContextBase API `http://127.0.0.1:8892`，UI `http://127.0.0.1:9992`；部署代码 `dd5521cb948beff39a24d604f625bc4108d1aac2`；LLM `gpt-6.1-sol / medium`；项目 `/Users/zhuqingping/Life/outer_space`，Bank `outer_space`。

## 问题与证据

2026-11-07 捕获真实三轮会话 `01a1b52a-42e7-73a1-9b84-cd0488820e4c`：

- 首轮自动 Reflect 在客户端等待约 20 秒后超时，随后普通 Recall 返回 15 条观察，完成降级。
- 服务端当时单次 Reflect 模型调用限制为 30 秒，整次 Reflect 上限为 300 秒；客户端已结束等待，后台仍继续执行与重试，直至更晚失败。
- 因而问题包括等待预算不匹配，以及客户端放弃后服务端继续工作的资源消耗。调大客户端超时可以减少过早降级，但不能保证模型更快，也不能替代取消传播修复。
- 第二、三轮没有再次自动 Reflect，是当前集成首次注入后缓存的行为；本次调整超时不改变该策略。MCP 由 Agent 按需调用，不是每轮必调。

抓取材料位于本机 `/Users/zhuqingping/.local/share/contextbase/captures/outer-space-20261107/`，可查 `本次聊天发生了什么.txt`、`target-http.jsonl`、`first-turn-hook-events.json`、`target-backend-evidence.json`。

## 已实施配置与具体位置

| 层级 | 配置键 | 当前配置 | 单位 | 作用范围 |
| --- | --- | --- | --- | --- |
| 服务端单次模型调用 | `CONTEXTBASE_API_REFLECT_LLM_TIMEOUT` | `60` | 秒 | 8892 实例所有 Reflect 请求 |
| 服务端整次回忆 | `CONTEXTBASE_API_REFLECT_WALL_TIMEOUT` | `120` | 秒 | 8892 实例所有 Reflect 请求 |
| 客户端回忆等待 | `reflectTimeoutMs` | `150000` | 毫秒，即 150 秒 | outer_space 专用客户端配置 |
| Codex 提问 Hook | `UserPromptSubmit.hooks[].timeout` | `180` | 秒 | outer_space 项目 |

服务端文件（记录时第 50、51 行）：

`/Users/zhuqingping/.local/share/contextbase/deployments/gpt61-20261107/runtime/api.env`

```dotenv
CONTEXTBASE_API_REFLECT_LLM_TIMEOUT=60
CONTEXTBASE_API_REFLECT_WALL_TIMEOUT=120
```

客户端文件（记录时第 18 行，顶层字段）：

`/Users/zhuqingping/.contextbase/projects/outer_space/coding-agent.json`

```json
"reflectTimeoutMs": 150000
```

Hook 文件（记录时第 20 行，`UserPromptSubmit` 的 command Hook）：

`/Users/zhuqingping/Life/outer_space/.codex/hooks.json`

```json
"timeout": 180
```

这是项目专用配置，不能到全局 `~/.contextbase/coding-agent.json` 或 `~/.codex/hooks.json` 中查找本次改动。行号可能随后续编辑变化，应按键名定位。上述配置文件可能含凭据，本文仅摘录超时字段。

预算关系为：服务端整次 120 秒 < 客户端等待 150 秒 < Hook 上限 180 秒，为传输、返回和降级保留余量。单次模型 60 秒上限仍受整次 120 秒上限约束，不能将多轮调用与重试简单相加。

服务端已重启，通过与启动入口一致的配置加载器确认生效为 60/120。检查时需先执行 `load_dotenv_for_entrypoint()`，再读取配置，避免遗漏 `CONTEXTBASE_API_` 到内部 `HINDSIGHT_API_` 的别名转换。客户端真实复验前需重启 Codex。8891 旧实例未修改；模型、embedding、RRF 与数据未因本次调优改变。

## 验证结果与边界

直接运行已安装的 Codex `UserPromptSubmit` Hook，查询已有火星讨论：

- `reflect_ok`：18512 毫秒；Hook 进程约 18.6 秒，退出码 0。
- 返回上下文非空，此次未触发降级。
- 使用独立验证会话，只执行提问 Hook，没有执行 Stop，也没有写入验证会话内容。

这证明调整后的调用链可成功执行一次；不能据此判断耗时分布或默认值合理性。此次成功调用本身也在原 20 秒等待范围内，不能单独证明放宽超时带来的改善。**调优后桌面客户端新会话验收仍待用户复验。**

实施与验证证据目录：

`/Users/zhuqingping/.local/share/contextbase/deployments/gpt61-20261107/tuning/reflect-timeout-20261107/`

重点查看 `changes.json`、`hook-verification.json`、`实施与复验说明.txt`。目录中的原配置备份含凭据，不应复制到资料仓或公开分享。

## 后续评估修改默认值

状态：待评估、待实施；以下项目尚未完成。

1. 用真实桌面新会话验证 Hook 新配置加载、Reflect 成功/超时、降级、最终自动保存；区分首轮自动注入与后续按需 MCP。
2. 覆盖不同 Bank 大小、问题复杂度、网络延迟、模型与 reasoning 配置，记录样本量、Reflect 与首轮等待的 P50/P95/P99、成功率、降级率及调用成本。不要从一次成功推广全局默认值。
3. 单独评估四层预算：服务端单次模型、服务端整次任务、客户端等待、宿主 Hook；把 60/120/150/180 秒作为当前候选组合，评估交互等待是否可接受。
4. 验证客户端超时或取消后，服务端是否及时停止模型请求与重试；必要时另立取消传播修复。检查整次上限是否覆盖所有子操作，以及重试是否消耗剩余预算。
5. 评估是否按模型或场景提供预设，以及首轮普通 Recall、深度 Reflect 按需调用的体验与质量。此项是候选方案，本次没有切换。
6. 若决定修改默认值，核对服务端配置定义与环境模板、coding-agents 配置默认值、Codex Hook 安装生成器及对应文档；验证新安装与已有配置升级路径，保留用户显式覆盖。以实际实施分支源码位置为准，不将本机配置改动当作产品修复。

验收要求：可复现的慢调用在预算内成功，超限时可控降级，客户端取消后的后台资源消耗有明确处理，典型首轮等待与成本符合评审约定；记录证据后再确定发布默认值。

## 2026-11-08 补充：重启之外，还须重新确认 Hook 信任

后续真实三轮核验发现，UserPromptSubmit 的 `timeout=180` 配置对应当前哈希与可信哈希不一致，宿主 `hooks/list` 返回 `trustStatus=modified`。SessionStart、MCP 与 Stop 正常，但自动提问回忆没有执行。因此“仅重启后验证”的步骤不完整，须先在 Codex 核对命令与超时并重新确认信任，再验证自动 Reflect。原来直接执行 Hook 的成功结果不能替代宿主调度验收。详见 [本次真实交互分析](../product-guide/07-agent-knowledge-interaction-20261108.md)。本轮没有修改可信哈希或替用户确认信任。

## 重新信任后的实际复验结果（2026-11-08）

三个Hook均trusted后的真实新会话，首轮Reflect耗时30991ms、返回950字，未降级，后两轮目录均成功更新；三轮最终回答完整保存，后台处理完成。该次超过旧20秒上限，当前预算允许其完成，但不代表通用默认值或延迟分布已验收。详见 [完整复验](../product-guide/07-agent-knowledge-interaction-20261108.md)。
