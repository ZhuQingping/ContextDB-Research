# 首期实现最终原始证据

日期：2026-10-13。本次本地未提交代码的冻结批次，完整结论见[实现验收记录](../../contextdb-service-verification-2026-10-13.md)。这些结果不是生产验收，也不是上游全部测试。

使用新建临时 PG、合成凭据与 stub 模型。复制前扫描了真实格式 API Key 及含密码的 PostgreSQL URL，无匹配。XML 保留运行时间、测试名及主机名，不包含客户记忆或真实模型调用。

| 文件 | 内容 | 结果 |
|---|---|---|
| [components-auth-classification.xml](components-auth-classification.xml) | 主环境扩展测试 | 175 passed |
| [components-fresh-frozen.xml](components-fresh-frozen.xml) | 新鲜冻结依赖环境扩展测试 | 175 passed，重复复核，不累加 |
| [system-postauth-verified.xml](system-postauth-verified.xml) | 系统包：41 个真实进程场景 + 6 个 fixture/错误分类辅助回归 | 47 passed，前序代理自测 |
| [native-postauth-verified.xml](native-postauth-verified.xml) | 隔离 worktree 的定向原生回归 | 41 passed |
| [root-lint-postauth-verified.log](root-lint-postauth-verified.log) | 隔离 worktree 完整根 lint | PASS |

复制时 SHA-256：

```text
0900da3885524aae8b1bedafa9a24b9d762b00b5b4aeae5905cc651fdec8f97b  components-auth-classification.xml
487274f4f7f1bae346bc726b80b9645e60452b8927b5b3d8f9628fcf5a92178c  components-fresh-frozen.xml
db60978cf89e460a2623070296d04f08120fc2a50a43579b4af5bf3cb3309fdd  system-postauth-verified.xml
cb36c3dda5869cc404171f3152c56801e3077259b2ee5ce9542a91cda9bcc496  native-postauth-verified.xml
f1f32bdee68d5d5bd41cd53a130f8ed330243b34b05fa8cba5d73a417154f927  root-lint-postauth-verified.log
```

早期失败批次仍位于本机 `/tmp/contextdb-implementation-evidence-ldIh3Q`；修复原因与差异见[开发记录](../../contextdb-service-night-task-2026-10-13.md)。不以删去失败日志或累加批次掩盖修复过程。
