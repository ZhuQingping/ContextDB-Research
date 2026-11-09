# 案例演示：看见经验如何被接手

**先演示一次已经验收的工作接力，再决定是否从头调用模型重做。** 背诵随机口令无法证明开发价值。

## 演示入口

打开已有交互演示（本机现场路径：`/Users/zhuqingping/Work/Database/Context/hindsight/verification/contextbase-real-world-demo-20261105/index.html`）

此页面有实际任务、回答、代码、独立测试、配置和来源。证据发生于2026-11-05，不是今天重新运行的结果。原始验收结论（本机现场路径：`/Users/zhuqingping/Work/Database/Context/hindsight/verification/contextbase-real-world-demo-20261105/docs/验收结论.txt`）

## 案例一：修过的坑，换Agent仍能接手

**业务背景**：支付通知可能重复投递，同一事件并发到达时不应重复入账，也不应让普通重投抛异常。

| 你做什么、讲什么 | 给观众看什么 | 证明到哪 |
| --- | --- | --- |
| 展示Claude正常开发任务，不说“记住” | 实际生成的代码和自测 | 第一位Agent确实工作过 |
| 展示第二轮004031的真实失败 | 独立验收抓到UNIQUE异常；原自测允许异常通过 | Agent自测全绿不代表业务契约满足 |
| 展示修复及独立复测 | 事务边界修复后5项独立支付验收通过 | 测试证明该代码问题得到修复 |
| 展示新Codex的接手回答 | 3次MCP、0文件/命令工具，说明旧失败、修复和未验证范围并给来源 | 记忆把已核验教训交给新Agent |

讲解句：“测试负责抓问题；记忆负责把修过的坑交给下一个任务。”

第二轮真实UNIQUE缺陷与第三轮005124的返回字符串门禁误约束是两件事。第三轮门禁由验收方纠正、同会话撤回错误归因，不能当作产品代码缺陷宣传。

### 现场快速跑代码验证

```bash
cd /Users/zhuqingping/Work/Database/Context/hindsight/verification/contextbase-real-world-demo-20261105
python3 scripts/replay_concurrency.py
```

它运行保存的真实修复前/后代码，不调用模型或PG。应看到“修复前重现异常、修复后通过”。并发时序最多尝试10次；未复现会报失败，不播放固定结果。**这步验证代码，跨Agent记忆的真实性另看实际MCP记录。**

## 案例二：同事接手真实故障

历史本机合并任务反复收到上游拒绝。成员A分析取证，工作记录经过采集，再由操作员生成团队知识页。成员B用独立只读身份查询。

自然提问：“我接手合并任务403，请找团队已有诊断指南，读原文后告诉我先查什么、以前怎样验证过、现在还缺什么证据。”

演示顺序：打开“同事接手真实事故” → 展开实际回答与知识页 → 指出来源会话、当时有效的措施和当前待核查条件 → 展示B共享读200、写403、越权读403。

讲解句：“我们共享的是带条件和来源的经验，不是让新成员盲目照着旧记录操作。”知识页是明确发起生成的，不宣传每次Hook都会自动生成一页。

## 案例三：公司、家里换电脑

这是最容易理解的讲解场景，但**双机实测仍待补充**：

1. 公司电脑A接入同一服务与项目bank，完成正常任务；核对存下的原文含领域结论。
2. 用Git同步代码；家里电脑B使用自己的客户端与授权Key接入该bank。
3. 新会话查以前的取舍/排障经验，要求给来源，再继续开发并独立验收。
4. 换成未授权bank做反例，确认读不到。

不把同机隔离profile冒充跨网络、跨物理电脑验证。工作进程、未提交文件和完整聊天现场不会自动同步。

## 从头完整复演

```bash
cd /Users/zhuqingping/Work/Database/Context/hindsight/verification/contextbase-real-world-demo-20261105
python3 scripts/rehearse.py --new
```

前提：现有PG/API/UI、固定PR90 release、已登录Codex/Claude、Python/Node及模型网络均可用。脚本新建隔离bank/用户/profile，真实调用模型，不改全局客户端配置；会产生模型费用和新演示数据。它不负责安装整套服务，换机器需先配置依赖。

完成后刷新原演示页面，看运行编号和本轮证据。失败会保留并停止；先定位，再决定是否用`--continue-run`接续。最新历史完整复跑是纠正门禁后继续完成，不是无干预一次通过。现场预计时间应彩排测量，不作固定时长承诺。

逐步操作、提示词与后台查看（本机现场路径：`/Users/zhuqingping/Work/Database/Context/hindsight/verification/contextbase-real-world-demo-20261105/docs/现场演示手册.txt`） · 固定客户端配置与安装（本机现场路径：`/Users/zhuqingping/Work/Database/Context/hindsight/verification/contextbase-real-world-demo-20261105/docs/团队客户端配置.txt`）

## 演示验收标准

- 客户端确实采集，异步操作完成，原文含实际领域结论；不能只看记忆总数。
- 新Agent实际查询/获得注入，能说清来源与边界；纯记忆接手排除本地材料旁路。
- 涉及代码就跑独立业务验收；涉及共享就用不同身份核验权限。
- 有记忆/空记忆均成功就如实讲。本机样本未证明提速或质量优势。
- PR90历史实测有Claude单轮最后答复漏采；本次未修复，也未确认今天运行版本是否已消除该缺陷。
