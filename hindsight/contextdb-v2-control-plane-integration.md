# ContextDB 实例运维与管理联调入口

2026-10-16，本次 release-hardening 分支。旧版完整管控联调方案已保留在 [历史文档](archive/2026-10-16-before-release-hardening/contextdb-v2-control-plane-integration.md)。当前工作空间管理已放在 Hindsight UI，不再要求华为云 Console 维护空间目录。

| 场景 | 调用方与入口 | 结果 |
| --- | --- | --- |
| 创建实例 | 管控调已有节点Agent，准备专用UTF8 PG/插件、同版产物、私密配置，运行service.sh init | 离线完成秘密持久化、元数据3和管理员导入，不依赖API |
| 启动/重启 | Agent监督service.sh api，独立模式另起worker；ready成功后service.sh ui | 前台进程交给已有监督器；重启复用秘密，不重新生成 |
| 停止/升级 | Agent停止该实例写入进程、备份PG及秘密配置，离线migrate后按原顺序启动 | API仍v1，结构升级1→2→3/2→3；异常拒绝回滚 |
| 工作空间 | 管理员浏览器→UI后端→Hindsight API管理接口；或运维直接Admin Key调API | UI创建/删除/查询空间；无新增Agent业务转发协议 |
| 用户/Key | 同上，UI实例级“用户管理” | 普通成员无角色选项，业务Key不能管理资源 |

完整可执行命令集中在[部署与升级](implementation/contextdb-optimized-guide.md)，逐接口参数/返回/curl在[管理与业务验证](implementation/contextdb-management-api-curl-guide.md)。避免在多份文档重复命令产生不同合同。

管控只负责已有实例生命周期：配置输入、调用脚本、监督进程、收集不含凭据的退出状态/日志。脚本不是新的常驻Agent，也没有POST /instances。API/Worker用PG和pepper；UI只收到password、后台Admin Key和API URL。Admin Key在API启动前离线生成，经migrate导入PG，再与业务Key统一认证。

交付必须同版API/扩展/UI；build-ui对成功构建写指纹，UI启动强制校验。管理GET空间详情按唯一名称，DELETE/授权仍UUID；原生REST/MCP bank_id=workspace_id。创建/删除空间202后查operations，不把受理当完成。

本轮没有实现新的云端HA/升级调度协议；复用现有Agent。真实入口HTTPS、限流、PGroonga故障恢复/备份复制/切换由部署联调验收，不能用本地功能测试替代。
