# 开源评审依据摘要

更新：2026-11-09。保留评审结论的固定版本与复核方法；原始差异、锁文件清单、官方全文快照、元数据及生成验收JSON本地归档，不作为资料仓正文持续维护。

| 依据 | 固定版本/含义 | 复核入口 |
| --- | --- | --- |
| 官方引入基线 | Hindsight v1.0.0，39c65ffe2f140d0c84cee58566cad8900c5b9908 | [官方代码](https://github.com/vectorize-io/hindsight/tree/39c65ffe2f140d0c84cee58566cad8900c5b9908) |
| 评审目标 | ContextDB 2606e883168800429c221b9be5a10e8f552b6e07 | [团队代码](https://github.com/RSIXDB/hindsight/tree/2606e883168800429c221b9be5a10e8f552b6e07) |
| 资料基线 | 5f9993c2c1d9eb68a83decdb99590f4dfe7d76dd | [资料代码](https://github.com/ZhuQingping/ContextDB-Research/tree/5f9993c2c1d9eb68a83decdb99590f4dfe7d76dd) |
| 模块差异 | M01—M09的职责、风险与取舍见评审正文；静态统计不等于生产安装组件清单 | [评审正文](../ContextDB开源选型与Hindsight侵入式修改评审.md) |
| 依赖与许可 | 以目标提交uv.lock、package-lock.json、包内LICENSE/NOTICE为准 | [目标锁文件](https://github.com/RSIXDB/hindsight/blob/2606e883168800429c221b9be5a10e8f552b6e07/uv.lock)、[官方许可](https://github.com/vectorize-io/hindsight/blob/39c65ffe2f140d0c84cee58566cad8900c5b9908/LICENSE) |

## 复核方式

在具有上述两个提交的代码仓中执行，使用固定SHA，不用当前HEAD替代：

```bash
git diff --shortstat 39c65ffe2f140d0c84cee58566cad8900c5b9908 2606e883168800429c221b9be5a10e8f552b6e07
git diff --stat 39c65ffe2f140d0c84cee58566cad8900c5b9908 2606e883168800429c221b9be5a10e8f552b6e07 -- hindsight-api-slim/hindsight_api
git show 2606e883168800429c221b9be5a10e8f552b6e07:uv.lock
```

完整原始附件在本地`.local-archive/2026-11-09-before-push/hindsight/opensource-review/evidence/`保留。只有获取归档后才能逐条核对原附件的hash、文件清单和当时的导出结果；远端保留的摘要不能替代这些原件。正文已有固定官方引用继续可用，不重复提交上游源码全文。

[图源与版权说明](../diagrams/README.md)。图表用于解释架构和修改范围，正式法务/安全/发布批准仍待相应评审，不能把附件归档当作验收已完成。
