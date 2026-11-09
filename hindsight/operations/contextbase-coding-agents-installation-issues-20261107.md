# ContextBase 客户端安装问题与排查记录

记录日期：2026-11-07，时区 Asia/Shanghai。

本次为 Claude Code 和 Codex 接入 ContextBase，要求两个本机目录分别使用不同 Bank。安装与 API、MCP 连通性验证已完成；随后发现 Codex 的 Hooks 尚未信任，导致新会话没有自动保存。**安装成功、MCP 可用与自动记忆生效是三个不同的验收结果。** 截至本次排查，Hooks 信任和真实会话自动保存仍待完成验收。

## 环境与目标

| 项目 | 本次环境 |
| --- | --- |
| npm 包 | `@huaweicloud/contextbase-coding-agents`，安装输出版本 `1.1.0` |
| API | `http://127.0.0.1:8892` |
| Claude Code | 用户级 Hooks 与 Skill，项目本地配置及 MCP 注册 |
| Codex CLI | `0.161.0` |
| 桌面客户端内置 Codex | 会话元数据记录为 `0.163.0-alpha.10.2` |

目标关联关系如下。目录白名单同时包含相应目录的子目录。

| 项目目录 | Bank | 独立 ContextBase 配置 |
| --- | --- | --- |
| `/Users/zhuqingping/Work/AI/agent_memory` | `agent_memory` | `~/.contextbase/projects/agent_memory/coding-agent.json` |
| `/Users/zhuqingping/Life/outer_space` | `outer_space` | `~/.contextbase/projects/outer_space/coding-agent.json` |

认证 Token 保存在本机配置中，本文不记录其值。独立配置文件权限已设置为 `0600`。

## 问题一 安装参数容易被误认为目录到 Bank 的映射

最初执行带有 `--bank-id outer_space` 和 `--project-path` 的 Claude Code 安装命令。安装器写入 `~/.contextbase/coding-agent.json`，日志明确显示：

```text
using configured Bank outer_space for all projects
```

版本 `1.1.0` 使用配置文件顶层的一个 `bankId`，不会根据当前目录自动选择不同 Bank。`--project-path` 用于支持项目注册的客户端流程；在本次 Claude Code 安装中，它没有创建目录映射，也没有将用户级 Hooks 限制在该目录。

`banks.outer_space` 只是该 Bank 的行为覆盖配置，不是目录映射。`paths` 可覆盖部分行为，也不能据此切换 `bankId`。安装器选择 Bank 时还会清除旧的 `mapPathToBank` 等字段，因此不能依赖这些字段构建多项目方案。

**处理：** 使用不同的 `CONTEXTBASE_CONFIG` 为两个项目选择独立配置文件。每份文件再用目录白名单限制自己的生效范围。这里的目录关联由客户端项目设置实现，不是插件原生的目录到 Bank 映射。

## 问题二 用户级安装默认影响所有项目

初次安装将 Hooks 写入 `~/.claude/settings.json`，并以 user scope 注册 MCP。仅设置 `bankId` 时，其他目录也可能使用同一个 Bank。

**处理：** 在每份独立配置中加入以下限制，以 `outer_space` 为例：

```json
{
  "optInOnly": true,
  "optInPaths": ["/Users/zhuqingping/Life/outer_space"],
  "resolveWorktrees": false
}
```

| 字段 | 本次值及含义 |
| --- | --- |
| `optInOnly: true` | 仅允许白名单内的目录使用记忆 |
| `optInPaths` | 按路径边界匹配，包含指定目录及其子目录 |
| `resolveWorktrees: false` | 不借助主仓库路径将其他位置的 linked worktree 纳入匹配 |

已用插件实际的路径匹配函数验证：项目目录及 `docs` 子目录匹配；父目录、`outer_space-other` 和 `/tmp` 不匹配。

## 问题三 多次安装可能切换共享 Bank

若直接为第二个项目执行 `install ... --bank-id agent_memory`，安装器会修改默认共享配置的 Bank，不能自动保留第一套目录关联。

**处理：** 安装时显式指定独立配置文件。例如，在目标目录下运行：

```bash
mkdir -p "$HOME/.contextbase/projects/agent_memory"

CONTEXTBASE_CONFIG="$HOME/.contextbase/projects/agent_memory/coding-agent.json" \
npx --yes '@huaweicloud/contextbase-coding-agents@latest' install claude-code \
  --bank-id agent_memory \
  --api-url http://127.0.0.1:8892 \
  --project-path /Users/zhuqingping/Work/AI/agent_memory
```

新配置的认证通过事先设置的 `CONTEXTBASE_API_TOKEN` 提供，或复用已存在配置中的 Token。插件的普通环境变量是配置的后备值，文件中已有的同名值优先；`CONTEXTBASE_CONFIG` 则用于选择整个配置文件。

安装后应检查白名单，因为 `--project-path` 本身不生成上述限制。Codex 安装采用同样的独立配置路径，将安装目标替换为 `codex`。再次运行安装器可能重新写入用户级 Hooks 和 MCP，需要复核项目配置与重复注册。

## 问题四 Claude Code 的 Hooks 和 MCP 需要使用同一份配置

只给 MCP 指定 Bank 不够：自动保存由 Stop Hook 执行。如果 Hooks 仍读取默认文件，就可能出现检索与保存使用不同 Bank 的情况。

本次在两个项目下分别创建 `.claude/settings.local.json`，例如：

```json
{
  "env": {
    "CONTEXTBASE_CONFIG": "/Users/zhuqingping/.contextbase/projects/outer_space/coding-agent.json"
  }
}
```

Claude Code 的用户级 Hooks 继承项目环境变量。每个项目还通过 `claude mcp add-json --scope local` 注册同名 `contextbase` MCP，在服务器 `env` 中显式设置相同的 `CONTEXTBASE_CONFIG` 和 `CONTEXTBASE_MCP_HARNESS=claude-code`。

项目本地 MCP 注册保存在 `~/.claude.json` 的对应项目条目中，不在 `settings.local.json` 内。同名 local scope 注册优先于 user scope，并使用完整的本地服务器条目。依据：[Claude Code MCP 配置优先级](https://code.claude.com/docs/en/mcp#scope-hierarchy-and-precedence)。

## 问题五 Codex 安装器默认生成用户级注册

Codex 安装器写入：

- `~/.codex/hooks.json`：SessionStart、UserPromptSubmit、Stop。
- `~/.codex/config.toml`：`mcp_servers.contextbase`，并启用 Hooks 特性。
- `~/.agents/skills/contextbase-coding-agent`：插件说明 Skill。

为保持两个项目的 Bank 隔离，本次将生成的 ContextBase Hooks 和 MCP 配置迁移至两个项目各自的 `.codex/` 目录，并移除安装器生成的同一组用户级注册，保留其他用户设置。

项目 `.codex/config.toml` 示例：

```toml
[mcp_servers.contextbase]
command = "node"
args = ["/Users/zhuqingping/.contextbase/coding-agents/dist/mcp-server.js"]
cwd = "/Users/zhuqingping/Life/outer_space"

[mcp_servers.contextbase.env]
CONTEXTBASE_MCP_HARNESS = "codex"
CONTEXTBASE_CONFIG = "/Users/zhuqingping/.contextbase/projects/outer_space/coding-agent.json"
```

项目 `.codex/hooks.json` 内的每条命令都显式设置同一个配置路径，例如 Stop：

```json
{
  "type": "command",
  "command": "CONTEXTBASE_CONFIG=\"/Users/zhuqingping/.contextbase/projects/outer_space/coding-agent.json\" node \"/Users/zhuqingping/.contextbase/coding-agents/dist/codex-stop-hook.js\"",
  "timeout": 60
}
```

两个项目均已在 Codex 用户配置中标记为可信项目。但**项目可信与具体 Hook 被信任是两层独立状态**。项目配置只在可信项目中加载；多个来源的 Hooks 会合并执行，不能依赖项目 Hooks 覆盖同名用户 Hooks。依据：[配置层级](https://learn.chatgpt.com/docs/config-file/config-basic)、[Hooks 加载与信任](https://learn.chatgpt.com/docs/hooks)。

## 问题六 Codex 新会话没有自动保存

### 现象与证据

新会话“规划上海天文馆亲子行程”位于 `/Users/zhuqingping/Life/outer_space`，但 ContextBase 没有记录。

| 证据 | 排查结果 |
| --- | --- |
| 配置文件更新时间 | 2026-11-07 15:31:43 |
| 会话创建时间 | 2026-11-07 15:35:29 |
| 首轮执行时间 | 约 15:37:15 至 15:38:53 |
| 会话目录 | 正确，属于 `outer_space` 白名单 |
| 运行时 Hooks 特性开关 | `feature.hooks=true` |
| 客户端 `hooks/list` 返回 | 三个 Hooks 均 `enabled=true`、`trustStatus=untrusted`，无解析错误 |
| ContextBase 诊断日志 | 没有该会话的 Codex 启动或保存事件；已有记录来自 Claude Code |
| `outer_space` 文档列表 | 排查时 `total=0` |

### 原因

**Codex 尚未信任新增 Hooks，因此跳过了自动执行。** 这不是目录关联错误，也不是 `autoSeed=false` 关闭了会话保存。MCP 负责提供工具，Stop Hook 负责自动写回；MCP 连通性不能证明写回链路正常。

`agent_memory` 项目的三个 Codex Hooks 同样返回 `untrusted`，也存在相同阻断。

### 后续处理

在终端进入对应项目并启动 Codex：

```bash
cd /Users/zhuqingping/Life/outer_space
codex
```

输入 `/hooks`，检查并信任 ContextBase 的 SessionStart、UserPromptSubmit、Stop。`agent_memory` 项目需要单独处理。之后重启桌面客户端会话，完成一次有实质内容的交互，检查 Stop 保存及服务端文档。

截至本次记录，**尚未完成 Hooks 信任操作，尚未验证真实 Codex 会话自动写回，也尚未补录亲子行程会话**。不能将这些待办描述为已修复。

## 其他安装与排查注意事项

### 安装帮助命令进入了安装流程

初次执行 `install claude-code --help` 没有获得通常的参数帮助，而是进入安装流程，并因缺少 Bank ID 中止。输出包含 runtime staged 提示，因此不能将该命令视为完全无副作用的只读帮助查询。本次改为检查安装器实际代码确认参数；全局 usage 可参考包入口的 `--help`，并检查实际输出。

### 错误的 API 路由会误导连通性判断

直接 `GET /v1/default/banks/<bankId>` 在本次服务上返回 `405 Method Not Allowed`。这不等于认证失败或 Bank 不存在。

本次有效检查为：

- `GET /health`：HTTP 200，返回服务 healthy、数据库 connected。
- 带认证的 `GET /v1/default/banks/<bankId>/documents?limit=1`：两个 Bank 均 HTTP 200。

### 三个关闭的行为开关不会关闭正常会话记忆

| 配置 | `false` 的含义 |
| --- | --- |
| `manageBankConfig` | 不自动管理服务端 Bank 配置 |
| `autoSeed` | 不自动运行 Git 历史初始化导入流程 |
| `codebaseSurvey` | 不自动运行代码库概览分析 |

正常会话保存还受 `retainSessions`、`disabled`、目录白名单、Hooks 加载与信任等条件影响。不能把初始化和代码分析的关闭状态解释成停止保存聊天。

## 验证结果与验收缺口

| 验证项 | 本次结果 |
| --- | --- |
| 服务健康与数据库连接 | 通过 |
| 两个 Bank 的认证文档列表查询 | 通过 |
| 两个项目的 MCP 初始化及工具列表 | 通过，各返回 8 个工具 |
| Codex 从各项目读取有效 MCP 配置 | 通过，使用各自独立配置 |
| 项目外 `/tmp` 读取 Codex MCP | 无 `contextbase` 注册 |
| 三个 Hook 命令在白名单外执行 | 返回成功且无上下文输出 |
| 原有 Codex 设置保护 | 结构化比较通过，新增项目可信设置除外 |
| Codex Hooks 信任 | 未完成，两个项目均 `untrusted` |
| 真实 Codex 会话自动保存及可检索性 | 未完成 |
| 亲子行程会话补录 | 未完成 |

前一轮安装验收覆盖了配置、连通性和白名单，但未检查 Hook 信任，也未通过真实会话验收自动写回。后续应先完成 Hooks 信任，再以真实会话的保存事件、服务端文档和检索结果形成完整验证链路。`retain_ok` 表示插件提交成功；若服务端异步提取，仍需等待处理并验证可检索内容。

## 后续排查入口

ContextBase 本机日志目录：`~/.contextbase/coding-agents-logs/`。

| 文件或接口 | 用途 |
| --- | --- |
| `diag.jsonl` | 检查 `session_start`、`retain_ok`、失败事件及对应会话 |
| `plugin.log` | 插件可读日志；本次排查时该文件不存在 |
| `usage.jsonl` | 每轮工具使用与记忆引用统计，不能代替写回成功证据 |
| Codex `/hooks` 或客户端 `hooks/list` | 检查加载来源、enabled、trustStatus、解析错误 |
| `codex mcp get contextbase --json` | 在不同项目下核对有效 MCP 配置 |
| Bank 文档列表与检索 | 确认内容实际进入正确 Bank 并可检索 |

本次还读取了目标会话的本地 transcript 和 Codex 日志数据库用于交叉核对。排查不应只搜索聊天标题：应同时使用会话 ID、保存时间和文档来源确认是否写回。

## 参考

- 本机 `~/.contextbase/coding-agents/dist/installer.js`、各客户端 Hook 和 `mcp-server.js`，安装版本 `1.1.0`。
- 本机 `~/.agents/skills/contextbase-coding-agent/SKILL.md` 的配置、诊断与日志说明。
- [Claude Code 设置文件与优先级](https://code.claude.com/docs/en/settings)。
- [Claude Code MCP 配置优先级](https://code.claude.com/docs/en/mcp#scope-hierarchy-and-precedence)。
- [Codex 配置基础](https://learn.chatgpt.com/docs/config-file/config-basic)。
- [Codex Hooks 加载及信任要求](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks)。

以上是本次环境和版本的安装记录；升级插件后应重新核对安装器生成的全局注册、项目配置及 Hook 信任状态。

## 后续：深度回忆超时与默认值评估（2026-11-07）

后续真实会话抓取已确认 outer_space 的 Hook 自动保存可执行，MCP 调用也可返回；本文开头的“待验收”属于早期安装排查状态。随后发现首轮 Reflect 客户端约 20 秒提前超时、服务端继续执行的问题，已调整本机四层等待预算。具体配置路径、证据和后续修改默认值的评估待办，统一见 [深度回忆超时记录](contextbase-reflect-timeout-20261107.md)。调优后的桌面新会话仍需单独验收。

## 后续优化：不能让 Hook 失效后用户毫不知情（2026-11-08）

已复现：提问 Hook 改为180秒后处于 modified，其他Hook和MCP仍正常，用户看不到服务端失败却实际没有自动回忆。用户要求作为持续优化点：安装与配置变更后检查宿主信任，独立诊断“未执行”，按会话提供读取、工具、保存的可见状态和恢复指引。详细需求与关闭标准统一维护在 [P1可观测性待办](../product-guide/05-backlog.md#优先优化hook-静默失效与客户端接入可观测性)，不把本机重新信任等同于产品优化已完成。
