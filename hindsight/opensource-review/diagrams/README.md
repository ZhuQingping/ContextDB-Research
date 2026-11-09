# 评审图表与可编辑源

更新：2026-11-09。保留正文阅读需要的SVG与可编辑源，不重复提交PNG预览、导出JSON、官方全文快照、生成脚本、编辑备份和ZIP资料包；这些原件已本地归档。

## 华为云部署与修改范围主图

| 内容 | 阅读图 | 编辑源 |
| --- | --- | --- |
| 原生能力在华为云上的部署说明 | [SVG](hindsight-huawei-cloud-native.svg) | [draw.io](source/hindsight-huawei-cloud-native.drawio) |
| ContextDB修改范围 | [SVG](contextdb-huawei-cloud-changes.svg) | [draw.io](source/contextdb-huawei-cloud-changes.drawio) |
| 两图合并编辑版 | 以上两张图 | [合并draw.io](source/hindsight-contextdb-huawei-cloud.drawio) |

主图是根据方案和固定源码整理的部署/改造说明，**不是官方原图**。合并draw.io保留用户手工布局，后续编辑以其为主，再导出SVG。OBS等规划项和已实现修改不得混同，具体状态以[评审正文](../ContextDB开源选型与Hindsight侵入式修改评审.md)为准。

## Hindsight官方原图

官方基线固定为v1.0.0提交39c65ffe2f140d0c84cee58566cad8900c5b9908。SVG是按官方图源使用其绘图依赖导出的阅读版本，原始JSON和页面代码通过固定上游链接复核：

| 图 | 阅读版本 | 官方图源 |
| --- | --- | --- |
| Services | [SVG](official/services.svg) | [JSON](https://github.com/vectorize-io/hindsight/blob/39c65ffe2f140d0c84cee58566cad8900c5b9908/hindsight-docs/figures/services.json)、[说明](https://github.com/vectorize-io/hindsight/blob/39c65ffe2f140d0c84cee58566cad8900c5b9908/hindsight-docs/docs/developer/services.md) |
| What Hindsight Does | [静态SVG](official/what-hindsight-does.svg)、[动画SVG](official/what-hindsight-does-animated.svg) | [JSON](https://github.com/vectorize-io/hindsight/blob/39c65ffe2f140d0c84cee58566cad8900c5b9908/hindsight-docs/figures/what-hindsight-does.json)、[概览源码](https://github.com/vectorize-io/hindsight/blob/39c65ffe2f140d0c84cee58566cad8900c5b9908/hindsight-docs/docs/developer/index.mdx) |

版权与许可见[官方LICENSE副本](official/LICENSE)。保留图片和许可不代表公司内部开源引入审批已完成。

## 补充图

| 内容 | 阅读版本 | 编辑源 |
| --- | --- | --- |
| 原生模块职责 | [SVG](hindsight-native.svg) | [Mermaid](hindsight-native.mmd) |
| ContextDB定制模块 | [SVG](contextdb-customization.svg) | [Mermaid](contextdb-customization.mmd) |
| 信任边界 | [SVG](contextdb-trust-boundaries.svg) | [Mermaid](contextdb-trust-boundaries.mmd) |
| 组件变化矩阵 | [SVG](contextdb-component-change-matrix.svg) | [Mermaid](contextdb-component-change-matrix.mmd) |

这些是源码与方案整理图，非官方原图。目标代码为[2606e883](https://github.com/RSIXDB/hindsight/tree/2606e883168800429c221b9be5a10e8f552b6e07)，差异、模块归属及验证边界见[正文](../ContextDB开源选型与Hindsight侵入式修改评审.md)。

## 本地归档

PNG、原始图源取证副本、导出脚本、编辑备份和资料包保存在本地`.local-archive/2026-11-09-before-push/hindsight/opensource-review/`，不属于远端可下载附件。阅读源码无需取得这些归档；复核当时导出结果或继续使用旧自动化脚本时，需另取对应原件。
