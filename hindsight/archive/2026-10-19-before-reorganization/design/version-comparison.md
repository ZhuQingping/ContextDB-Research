# ContextDB 版本与代码对比

当前交付分支为 `contextdb/v1.0.0`，直接基于上游 Hindsight v1.0.0，功能集中为一个提交。管理 API 和元数据均从版本1开始；早期开发分支里的“V1/V2”不代表已发布的升级合同。

| 快照 | 提交 | 用途 |
| --- | --- | --- |
| 早期空间内成员方案 | cdfc199e5 | 保留作历史对照，不能按其配置部署当前版本 |
| 本轮优化前完整特性 | 07028c356 | 对照认证、准入、元数据和文档收敛前的实现 |
| 本机优化对照（未推送） | be6f12c4 | 基于a77c1f341的优化对照；与v1.0.0适配分开验证 |
| 上游v1.0.0 | 39c65ffe2f140d0c84cee58566cad8900c5b9908 | 当前功能提交的直接父提交 |
| 当前实现 | contextdb/v1.0.0 | 包含上述优化及v1.0.0 Append适配 |

下列第三组命令依赖本机尚未推送的be6f12c4对照提交；远程评审直接使用前两组，将当前分支与原生v1.0.0比较即可。

```bash
# 当前特性相对原生v1.0.0的完整改动。
git diff v1.0.0 contextdb/v1.0.0 --stat
# 单看原生内核改动，扩展和UI不会混在里面。
git diff v1.0.0 contextdb/v1.0.0 -- hindsight-api-slim/hindsight_api
# 本轮简化本身：两个固定提交比较，不依赖已清理的临时分支。
git diff 07028c356 be6f12c4 --stat
```

## 专家检视顺序

当前功能提交的直接父提交就是原生 v1.0.0；评审这个提交即可看到完整净改动，不需要追踪开发期提交链。代码、测试、部署材料和当前设计一并提交，运行日志、凭据和过程归档不入仓。

| 范围 | 检视入口 | 关注点 |
| --- | --- | --- |
| 原生内核接入 | hindsight-api-slim/hindsight_api | 仅10个运行时代码文件变化；HTTP/MCP、引擎、Worker接入可选扩展与执行代次保护，其他租户扩展默认保持原生行为 |
| ContextDB外围实现 | hindsight-extensions/contextdb-service/hindsight_ext_contextdb | 统一PG认证、按Key授权、工作空间生命周期、元数据、管理REST和部署命令；记忆算法继续复用原生 |
| UI与代理 | hindsight-control-plane | 工作空间/用户/Key管理、管理员登录、服务端固定目标代理、双语及既有Bank入口边界 |
| 部署交付 | hindsight-extensions/contextdb-service/deployment、scripts | 单容器API/内置Worker/UI、原生官方镜像联调、自研初始化、RDS基础扩展、可选PG SSL |
| 回归验证 | 扩展tests、hindsight-system-tests、原生及UI测试文件 | 权限隔离、同名重建、在途写入和Append冲突、启动停止及原生业务回归 |

```bash
# 原生运行时只有这组文件，先查看文件名和规模，再逐个检视。
git diff v1.0.0 contextdb/v1.0.0 --stat -- hindsight-api-slim/hindsight_api
# 外围服务实现。
git diff v1.0.0 contextdb/v1.0.0 -- hindsight-extensions/contextdb-service/hindsight_ext_contextdb
# UI及服务端代理。
git diff v1.0.0 contextdb/v1.0.0 -- hindsight-control-plane
# 扩展包整体包含设计、部署和测试，可单独检查。
git diff v1.0.0 contextdb/v1.0.0 -- hindsight-extensions/contextdb-service
```

原生 Trace/Audit 正文和 Webhook 在自研首版关闭；中文分词关键词全文、目标ECS容量/RDS恢复和其余收敛工作仍是明确TODO，详见设计。不将此前本机功能通过描述为全部原生可选能力或生产验收完成。

当前采用实例级用户、按Key授权、各空间独立schema、可读bank_id及内部UUID。selected支持逐空间读写/只读，all包含未来空间；删除完成后允许同名重建，但旧selected授权不继承。部署前初始化管理元数据并离线导入管理员Key；原生REST/MCP与UI服务端均走统一认证。

部署以[当前设计](contextdb-release-design.md)、[部署合同](contextdb-deployment-contract.md)和[API验收](contextdb-optimized-curl-guide.md)为准。临时文件、运行凭据、测试日志和旧设计副本不纳入当前代码交付。[早期V1/V2完整对照](https://github.com/ZhuQingping/hindsight/blob/07028c3561bd6601dd72af137ea5d96658210ae9/hindsight-extensions/contextdb-service/docs/version-comparison.md)可从Git历史查看。
