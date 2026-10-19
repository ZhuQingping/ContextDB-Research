# V2 管控可执行步骤：命令验证与文档审核

日期：2026-10-15。研究仓基线 `cfe9e61`，实现参照 Hindsight V2 `d5e851b60`。本轮只更新管控联调文档、配套联调客户端与节点函数脚本，没有修改 Hindsight 内核。

## 验证范围

| 检查 | 执行情况 |
| --- | --- |
| 文档中的 Bash 块 | RUN：20 个块通过 bash -n |
| 内嵌 Python 与客户端 | RUN：AST 语法解析通过，CLI --help 可用 |
| HTTP 客户端与节点函数模拟 | RUN：16 个测试通过；本机隔离 HTTP stub 与临时 Node fixture，无实际 PG/模型请求 |
| 新终端环境、UI 凭据隔离与 Next 进程标题 | RUN：新终端恢复与干净 UI 环境通过；真实 Node 临时 fixture 改名、切换 cwd 后仍可停止，错误 PID 被拒绝 |
| PG 编译、初始化、角色/索引与真实 API/Worker/UI 启停 | NOT_RUN：本轮没有执行新部署，不干预现有体验实例 |
| 实际 RDS、节点 Agent 与云 Console | NOT_RUN：需平台提供真实协议与能力 |

本轮命令验证不等于已经按手册完成生产部署。已有 V2 功能自测记录见[本地自测与验收](contextdb-v2-self-test-acceptance-2026-10-15.md)。

## 专家审核

Hindsight 架构师与资料审核均只读检视。首轮结论 REVISE，双方确认 API/Worker 启动与健康、实例登记与 Key 恢复、空间幂等/轮询/删除墓碑均符合 V2 源码；不需要修改内核。

已按首轮意见修正：

- 用节点函数脚本恢复 PY、PYTHONPATH、客户端函数和保存的 PG 目标，新终端可以重启。
- 补齐已有 PG/RDS 的连接输入、管理认证和工具安装/版本检查。
- UI 使用干净环境启动，只加载自身配置，不继承数据库/模型/pepper。
- 预期 404 用条件语句捕获，避免 set -e 中断后续核验。
- 为停止命令增加本次进程归属检查与正常退出等待，禁止超时强杀。

最终复核：**Hindsight 架构师 ACCEPT，资料审核 ACCEPT，无 Critical/Important 遗留，双方达成一致。** 接受范围是可执行文档和配套脚本的静态/模拟验证，不代表生产验收。

二轮还修正了 Homebrew 工具路径跨终端丢失（保存 Node/Python 绝对路径），以及 Next 将进程标题改为 next-server 导致停止归属检查拒绝的问题。停止时核对 PID、记录的启动时间和本次发布目录，不匹配任意同名进程。

## 可复验命令

在研究仓根目录执行，不需要 PG或模型凭据：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s hindsight/scripts/tests -v
bash -n hindsight/scripts/contextdb-v2-node.sh
python3 hindsight/scripts/contextdb-v2-control.py --help
```

主控最终模拟结果：16 tests / 8.842s / OK。资料专家独立执行同一套件也得到 16 tests / OK；架构师完成最终源码与命令核对。辅助 Python 的 Ruff check/format 通过。文档链接、Bash块和 Python语法均通过检查。

交付文件：[联调文档](../contextdb-v2-control-plane-integration.md)、[API 客户端](../scripts/contextdb-v2-control.py)、[节点函数](../scripts/contextdb-v2-node.sh)、[模拟测试](../scripts/tests/test_contextdb_v2_control.py)。节点 Agent调用协议未在本轮新增，Hindsight核心代码未修改。
