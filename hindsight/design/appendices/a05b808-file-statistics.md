# a05b808 逐文件统计附录

[返回检视指南：统计口径与汇总](../code-review-guide.md#commit-change-statistics)。本附录是代码检视清单，不是设计说明或测试执行报告。

提交：`a05b80885883b36f879abdb2ce8a9c8f63b0922c`。父提交：`39c65ffe2f140d0c84cee58566cad8900c5b9908`（官方v1.0.0）。所有路径相对代码仓根目录；文件状态和行数来自这两个固定提交的Git差异。包含注释和空行，净增＝新增－删除。当前工作区和资料仓文档不计入。

总计165个文件：新增131、修改34、删除0；新增25,982行、删除602行、净增25,380行。实现61文件、测试80文件、其他24文件，三个分类互斥且覆盖全部文件。

## 实现代码（61文件）

新增43、修改18；新增7,182行、删除169行、净增7,013行。

| 文件路径 | 模块 | 状态 | 新增行 | 删除行 | 净增行 |
| --- | --- | --- | ---: | ---: | ---: |
| `hindsight-control-plane/src/app/[locale]/banks/[bankId]/page.tsx` | UI页面/组件/客户端/服务器代理 | 修改 | 43 | 31 | 12 |
| `hindsight-control-plane/src/app/[locale]/layout.tsx` | UI页面/组件/客户端/服务器代理 | 修改 | 15 | 29 | -14 |
| `hindsight-control-plane/src/app/[locale]/login/page.tsx` | UI页面/组件/客户端/服务器代理 | 修改 | 13 | 2 | 11 |
| `hindsight-control-plane/src/app/[locale]/users/page.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 15 | 0 | 15 |
| `hindsight-control-plane/src/app/api/auth/login/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 14 | 2 | 12 |
| `hindsight-control-plane/src/app/api/banks/[bankId]/aliases/[alias]/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 3 | 0 | 3 |
| `hindsight-control-plane/src/app/api/banks/[bankId]/aliases/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 2 | 0 | 2 |
| `hindsight-control-plane/src/app/api/banks/[bankId]/clone/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 2 | 0 | 2 |
| `hindsight-control-plane/src/app/api/banks/[bankId]/import/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 2 | 0 | 2 |
| `hindsight-control-plane/src/app/api/banks/[bankId]/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 5 | 0 | 5 |
| `hindsight-control-plane/src/app/api/banks/route.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 2 | 0 | 2 |
| `hindsight-control-plane/src/app/api/contextdb/[...path]/route.ts` | UI页面/组件/客户端/服务器代理 | 新增 | 142 | 0 | 142 |
| `hindsight-control-plane/src/app/globals.css` | UI页面/组件/客户端/服务器代理 | 修改 | 4 | 7 | -3 |
| `hindsight-control-plane/src/components/bank-config-view.tsx` | UI页面/组件/客户端/服务器代理 | 修改 | 4 | 1 | 3 |
| `hindsight-control-plane/src/components/bank-selector.tsx` | UI页面/组件/客户端/服务器代理 | 修改 | 134 | 88 | 46 |
| `hindsight-control-plane/src/components/banks-overview.tsx` | UI页面/组件/客户端/服务器代理 | 修改 | 10 | 0 | 10 |
| `hindsight-control-plane/src/components/contextdb/create-workspace-dialog.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 156 | 0 | 156 |
| `hindsight-control-plane/src/components/contextdb/key-editor-dialog.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 313 | 0 | 313 |
| `hindsight-control-plane/src/components/contextdb/use-key-workspaces.ts` | UI页面/组件/客户端/服务器代理 | 新增 | 54 | 0 | 54 |
| `hindsight-control-plane/src/components/contextdb/user-keys-panel.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 383 | 0 | 383 |
| `hindsight-control-plane/src/components/contextdb/users-view.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 448 | 0 | 448 |
| `hindsight-control-plane/src/components/contextdb/workspace-result-check.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 108 | 0 | 108 |
| `hindsight-control-plane/src/components/contextdb/workspaces-view.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 277 | 0 | 277 |
| `hindsight-control-plane/src/i18n/contextdb-messages.ts` | UI页面/组件/客户端/服务器代理 | 新增 | 55 | 0 | 55 |
| `hindsight-control-plane/src/i18n/request.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 6 | 1 | 5 |
| `hindsight-control-plane/src/instrumentation.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 4 | 0 | 4 |
| `hindsight-control-plane/src/lib/contextdb-api.ts` | UI页面/组件/客户端/服务器代理 | 新增 | 229 | 0 | 229 |
| `hindsight-control-plane/src/lib/contextdb-mode.tsx` | UI页面/组件/客户端/服务器代理 | 新增 | 16 | 0 | 16 |
| `hindsight-control-plane/src/lib/contextdb.ts` | UI页面/组件/客户端/服务器代理 | 新增 | 172 | 0 | 172 |
| `hindsight-control-plane/src/lib/i18n/api-errors.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 5 | 1 | 4 |
| `hindsight-control-plane/src/middleware.ts` | UI页面/组件/客户端/服务器代理 | 修改 | 54 | 7 | 47 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__init__.py` | 初始化/配置/预检/构建/启动 | 新增 | 5 | 0 | 5 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/__main__.py` | 初始化/配置/预检/构建/启动 | 新增 | 138 | 0 | 138 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/artifacts.py` | 初始化/配置/预检/构建/启动 | 新增 | 95 | 0 | 95 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/bootstrap.py` | 初始化/配置/预检/构建/启动 | 新增 | 214 | 0 | 214 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/config.py` | 初始化/配置/预检/构建/启动 | 新增 | 73 | 0 | 73 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/database_checks.py` | 初始化/配置/预检/构建/启动 | 新增 | 64 | 0 | 64 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/deployment.py` | 初始化/配置/预检/构建/启动 | 新增 | 323 | 0 | 323 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/launch.py` | 初始化/配置/预检/构建/启动 | 新增 | 89 | 0 | 89 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/preflight.py` | 初始化/配置/预检/构建/启动 | 新增 | 279 | 0 | 279 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/http.py` | 管理API/生命周期/模型/PG | 新增 | 434 | 0 | 434 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/lifecycle.py` | 管理API/生命周期/模型/PG | 新增 | 68 | 0 | 68 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/migrations.py` | 管理API/生命周期/模型/PG | 新增 | 54 | 0 | 54 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/models.py` | 管理API/生命周期/模型/PG | 新增 | 243 | 0 | 243 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/repository.py` | 管理API/生命周期/模型/PG | 新增 | 703 | 0 | 703 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/schema.sql` | 管理API/生命周期/模型/PG | 新增 | 185 | 0 | 185 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/asgi.py` | 认证/授权/REST与MCP适配 | 新增 | 21 | 0 | 21 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/authorization.py` | 认证/授权/REST与MCP适配 | 新增 | 153 | 0 | 153 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/diagnostics.py` | 认证/授权/REST与MCP适配 | 新增 | 39 | 0 | 39 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/mcp.py` | 认证/授权/REST与MCP适配 | 新增 | 153 | 0 | 153 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/routing.py` | 认证/授权/REST与MCP适配 | 新增 | 107 | 0 | 107 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/security.py` | 认证/授权/REST与MCP适配 | 新增 | 58 | 0 | 58 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/tenant.py` | 认证/授权/REST与MCP适配 | 新增 | 128 | 0 | 128 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/transport.py` | 认证/授权/REST与MCP适配 | 新增 | 197 | 0 | 197 |
| `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/validator.py` | 认证/授权/REST与MCP适配 | 新增 | 317 | 0 | 317 |
| `hindsight-extensions/contextdb-service/deployment/pg-role-boundary.sql` | 部署SQL与运行/生成脚本 | 新增 | 107 | 0 | 107 |
| `hindsight-extensions/contextdb-service/deployment/prepare-pg.sql` | 部署SQL与运行/生成脚本 | 新增 | 20 | 0 | 20 |
| `hindsight-extensions/contextdb-service/scripts/generate_openapi.py` | 部署SQL与运行/生成脚本 | 新增 | 66 | 0 | 66 |
| `hindsight-extensions/contextdb-service/scripts/node-agent.sh` | 部署SQL与运行/生成脚本 | 新增 | 8 | 0 | 8 |
| `hindsight-extensions/contextdb-service/scripts/run_combined.py` | 部署SQL与运行/生成脚本 | 新增 | 61 | 0 | 61 |
| `hindsight-extensions/contextdb-service/scripts/service.sh` | 部署SQL与运行/生成脚本 | 新增 | 90 | 0 | 90 |

## 测试代码（80文件）

新增77、修改3；新增10,095行、删除79行、净增10,016行。

| 文件路径 | 模块 | 状态 | 新增行 | 删除行 | 净增行 |
| --- | --- | --- | ---: | ---: | ---: |
| `hindsight-control-plane/tests/messages/used-keys.test.ts` | UI测试 | 修改 | 5 | 1 | 4 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-boundaries.test.ts` | UI测试 | 新增 | 196 | 0 | 196 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-key-state.test.tsx` | UI测试 | 新增 | 376 | 0 | 376 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-key-types.test.ts` | UI测试 | 新增 | 26 | 0 | 26 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-messages.test.ts` | UI测试 | 新增 | 91 | 0 | 91 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-native-entrypoints.test.tsx` | UI测试 | 新增 | 175 | 0 | 175 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-responses.test.ts` | UI测试 | 新增 | 191 | 0 | 191 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-users-view.test.tsx` | UI测试 | 新增 | 678 | 0 | 678 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-workspace-result-check.test.tsx` | UI测试 | 新增 | 79 | 0 | 79 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-workspaces-view.test.tsx` | UI测试 | 新增 | 323 | 0 | 323 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb-workspaces.test.ts` | UI测试 | 新增 | 93 | 0 | 93 |
| `hindsight-extensions/contextdb-service/tests/ui/contextdb.test.ts` | UI测试 | 新增 | 553 | 0 | 553 |
| `hindsight-system-tests/hindsight_system_tests/pytest_plugin.py` | 原生共用测试支撑 | 新增 | 80 | 0 | 80 |
| `hindsight-system-tests/hindsight_system_tests/server.py` | 原生共用测试支撑 | 修改 | 39 | 4 | 35 |
| `hindsight-system-tests/tests/conftest.py` | 原生共用测试支撑 | 修改 | 2 | 74 | -72 |
| `hindsight-extensions/contextdb-service/tests/__init__.py` | 插件Python准备与支撑 | 新增 | 1 | 0 | 1 |
| `hindsight-extensions/contextdb-service/tests/conftest.py` | 插件Python准备与支撑 | 新增 | 15 | 0 | 15 |
| `hindsight-extensions/contextdb-service/tests/paths.py` | 插件Python准备与支撑 | 新增 | 6 | 0 | 6 |
| `hindsight-extensions/contextdb-service/tests/python/__init__.py` | 插件Python准备与支撑 | 新增 | 1 | 0 | 1 |
| `hindsight-extensions/contextdb-service/tests/python/conftest.py` | 插件Python准备与支撑 | 新增 | 46 | 0 | 46 |
| `hindsight-extensions/contextdb-service/tests/python/support/__init__.py` | 插件Python准备与支撑 | 新增 | 1 | 0 | 1 |
| `hindsight-extensions/contextdb-service/tests/python/support/http.py` | 插件Python准备与支撑 | 新增 | 48 | 0 | 48 |
| `hindsight-extensions/contextdb-service/tests/python/support/identities.py` | 插件Python准备与支撑 | 新增 | 37 | 0 | 37 |
| `hindsight-extensions/contextdb-service/tests/python/support/lifecycle.py` | 插件Python准备与支撑 | 新增 | 34 | 0 | 34 |
| `hindsight-extensions/contextdb-service/tests/python/support/metadata.py` | 插件Python准备与支撑 | 新增 | 72 | 0 | 72 |
| `hindsight-extensions/contextdb-service/tests/python/support/native_doubles.py` | 插件Python准备与支撑 | 新增 | 15 | 0 | 15 |
| `hindsight-extensions/contextdb-service/tests/python/test_authorization.py` | 插件Python用例 | 新增 | 96 | 0 | 96 |
| `hindsight-extensions/contextdb-service/tests/python/test_authorization_models.py` | 插件Python用例 | 新增 | 58 | 0 | 58 |
| `hindsight-extensions/contextdb-service/tests/python/test_bootstrap_deployment.py` | 插件Python用例 | 新增 | 170 | 0 | 170 |
| `hindsight-extensions/contextdb-service/tests/python/test_build_artifacts.py` | 插件Python用例 | 新增 | 51 | 0 | 51 |
| `hindsight-extensions/contextdb-service/tests/python/test_combined_lifecycle.py` | 插件Python用例 | 新增 | 54 | 0 | 54 |
| `hindsight-extensions/contextdb-service/tests/python/test_credential_repr.py` | 插件Python用例 | 新增 | 37 | 0 | 37 |
| `hindsight-extensions/contextdb-service/tests/python/test_customer_pg_boundary.py` | 插件Python用例 | 新增 | 262 | 0 | 262 |
| `hindsight-extensions/contextdb-service/tests/python/test_deployment_contract.py` | 插件Python用例 | 新增 | 443 | 0 | 443 |
| `hindsight-extensions/contextdb-service/tests/python/test_diagnostics.py` | 插件Python用例 | 新增 | 163 | 0 | 163 |
| `hindsight-extensions/contextdb-service/tests/python/test_extensions.py` | 插件Python用例 | 新增 | 452 | 0 | 452 |
| `hindsight-extensions/contextdb-service/tests/python/test_http.py` | 插件Python用例 | 新增 | 292 | 0 | 292 |
| `hindsight-extensions/contextdb-service/tests/python/test_lifecycle_metadata.py` | 插件Python用例 | 新增 | 227 | 0 | 227 |
| `hindsight-extensions/contextdb-service/tests/python/test_managed_dotenv.py` | 插件Python用例 | 新增 | 15 | 0 | 15 |
| `hindsight-extensions/contextdb-service/tests/python/test_mcp_discovery.py` | 插件Python用例 | 新增 | 162 | 0 | 162 |
| `hindsight-extensions/contextdb-service/tests/python/test_metadata_initialization.py` | 插件Python用例 | 新增 | 288 | 0 | 288 |
| `hindsight-extensions/contextdb-service/tests/python/test_openapi_contract.py` | 插件Python用例 | 新增 | 95 | 0 | 95 |
| `hindsight-extensions/contextdb-service/tests/python/test_pgroonga_preflight.py` | 插件Python用例 | 新增 | 74 | 0 | 74 |
| `hindsight-extensions/contextdb-service/tests/python/test_production_ui_gate.py` | 插件Python用例 | 新增 | 45 | 0 | 45 |
| `hindsight-extensions/contextdb-service/tests/python/test_query_efficiency.py` | 插件Python用例 | 新增 | 118 | 0 | 118 |
| `hindsight-extensions/contextdb-service/tests/python/test_readable_workspaces.py` | 插件Python用例 | 新增 | 173 | 0 | 173 |
| `hindsight-extensions/contextdb-service/tests/python/test_release_hardening.py` | 插件Python用例 | 新增 | 219 | 0 | 219 |
| `hindsight-extensions/contextdb-service/tests/python/test_repository.py` | 插件Python用例 | 新增 | 112 | 0 | 112 |
| `hindsight-extensions/contextdb-service/tests/python/test_resource_cleanup.py` | 插件Python用例 | 新增 | 26 | 0 | 26 |
| `hindsight-extensions/contextdb-service/tests/python/test_security.py` | 插件Python用例 | 新增 | 53 | 0 | 53 |
| `hindsight-extensions/contextdb-service/tests/python/test_tenant_admin.py` | 插件Python用例 | 新增 | 354 | 0 | 354 |
| `hindsight-extensions/contextdb-service/tests/python/test_transport.py` | 插件Python用例 | 新增 | 101 | 0 | 101 |
| `hindsight-extensions/contextdb-service/tests/python/test_webhook_boundary.py` | 插件Python用例 | 新增 | 96 | 0 | 96 |
| `hindsight-extensions/contextdb-service/scripts/check_production_ui.py` | 生产UI结果门禁 | 新增 | 38 | 0 | 38 |
| `hindsight-extensions/contextdb-service/tests/system/__init__.py` | 系统测试准备与支撑 | 新增 | 1 | 0 | 1 |
| `hindsight-extensions/contextdb-service/tests/system/conftest.py` | 系统测试准备与支撑 | 新增 | 54 | 0 | 54 |
| `hindsight-extensions/contextdb-service/tests/system/support/__init__.py` | 系统测试准备与支撑 | 新增 | 1 | 0 | 1 |
| `hindsight-extensions/contextdb-service/tests/system/support/clients.py` | 系统测试准备与支撑 | 新增 | 105 | 0 | 105 |
| `hindsight-extensions/contextdb-service/tests/system/support/deployment.py` | 系统测试准备与支撑 | 新增 | 174 | 0 | 174 |
| `hindsight-extensions/contextdb-service/tests/system/support/knowledge.py` | 系统测试准备与支撑 | 新增 | 37 | 0 | 37 |
| `hindsight-extensions/contextdb-service/tests/system/support/mcp.py` | 系统测试准备与支撑 | 新增 | 16 | 0 | 16 |
| `hindsight-extensions/contextdb-service/tests/system/support/ui.py` | 系统测试准备与支撑 | 新增 | 85 | 0 | 85 |
| `hindsight-extensions/contextdb-service/tests/system/test_100_contextdb_service.py` | 系统测试用例 | 新增 | 125 | 0 | 125 |
| `hindsight-extensions/contextdb-service/tests/system/test_101_contextdb_knowledge.py` | 系统测试用例 | 新增 | 173 | 0 | 173 |
| `hindsight-extensions/contextdb-service/tests/system/test_102_contextdb_fixture_cleanup.py` | 系统测试用例 | 新增 | 133 | 0 | 133 |
| `hindsight-extensions/contextdb-service/tests/system/test_103_contextdb_sync_management.py` | 系统测试用例 | 新增 | 95 | 0 | 95 |
| `hindsight-extensions/contextdb-service/tests/system/test_104_contextdb_mcp_identity.py` | 系统测试用例 | 新增 | 81 | 0 | 81 |
| `hindsight-extensions/contextdb-service/tests/system/test_105_contextdb_knowledge_scope.py` | 系统测试用例 | 新增 | 97 | 0 | 97 |
| `hindsight-extensions/contextdb-service/tests/system/test_106_contextdb_default_template.py` | 系统测试用例 | 新增 | 48 | 0 | 48 |
| `hindsight-extensions/contextdb-service/tests/system/test_107_contextdb_default_compatibility.py` | 系统测试用例 | 新增 | 67 | 0 | 67 |
| `hindsight-extensions/contextdb-service/tests/system/test_109_contextdb_fault_retention.py` | 系统测试用例 | 新增 | 68 | 0 | 68 |
| `hindsight-extensions/contextdb-service/tests/system/test_110_contextdb_tenant_admin.py` | 系统测试用例 | 新增 | 262 | 0 | 262 |
| `hindsight-extensions/contextdb-service/tests/system/test_111_contextdb_business_keys.py` | 系统测试用例 | 新增 | 168 | 0 | 168 |
| `hindsight-extensions/contextdb-service/tests/system/test_112_contextdb_ui_management.py` | 系统测试用例 | 新增 | 221 | 0 | 221 |
| `hindsight-extensions/contextdb-service/tests/system/test_113_contextdb_optimized_authorization.py` | 系统测试用例 | 新增 | 157 | 0 | 157 |
| `hindsight-extensions/contextdb-service/tests/system/test_114_contextdb_diagnostic_credentials.py` | 系统测试用例 | 新增 | 124 | 0 | 124 |
| `hindsight-extensions/contextdb-service/tests/system/test_115_contextdb_workspace_recreation.py` | 系统测试用例 | 新增 | 156 | 0 | 156 |
| `hindsight-extensions/contextdb-service/tests/system/test_118_contextdb_append_contention.py` | 系统测试用例 | 新增 | 73 | 0 | 73 |
| `hindsight-extensions/contextdb-service/tests/contracts/extract-ui-key-contract.cjs` | 跨语言合同测试 | 新增 | 71 | 0 | 71 |
| `hindsight-extensions/contextdb-service/tests/contracts/test_ui_key_contract.py` | 跨语言合同测试 | 新增 | 46 | 0 | 46 |

## 其他（24文件）

新增11、修改13；新增8,705行、删除354行、净增8,351行。

| 文件路径 | 模块 | 状态 | 新增行 | 删除行 | 净增行 |
| --- | --- | --- | ---: | ---: | ---: |
| `.github/workflows/test.yml` | CI/配置/模板/构建描述 | 修改 | 113 | 3 | 110 |
| `hindsight-control-plane/eslint.config.mjs` | CI/配置/模板/构建描述 | 修改 | 1 | 1 | 0 |
| `hindsight-control-plane/knip.json` | CI/配置/模板/构建描述 | 修改 | 6 | 2 | 4 |
| `hindsight-control-plane/package.json` | CI/配置/模板/构建描述 | 修改 | 1 | 1 | 0 |
| `hindsight-control-plane/tsconfig.json` | CI/配置/模板/构建描述 | 修改 | 6 | 12 | -6 |
| `hindsight-control-plane/vitest.config.ts` | CI/配置/模板/构建描述 | 修改 | 11 | 1 | 10 |
| `hindsight-extensions/contextdb-service/deployment/Dockerfile` | CI/配置/模板/构建描述 | 新增 | 68 | 0 | 68 |
| `hindsight-extensions/contextdb-service/deployment/Dockerfile.dockerignore` | CI/配置/模板/构建描述 | 新增 | 18 | 0 | 18 |
| `hindsight-extensions/contextdb-service/deployment/compose.yaml` | CI/配置/模板/构建描述 | 新增 | 47 | 0 | 47 |
| `hindsight-extensions/contextdb-service/deployment/contextdb.env.example` | CI/配置/模板/构建描述 | 新增 | 11 | 0 | 11 |
| `hindsight-extensions/contextdb-service/deployment/intent.example.json` | CI/配置/模板/构建描述 | 新增 | 17 | 0 | 17 |
| `hindsight-extensions/contextdb-service/pyproject.toml` | CI/配置/模板/构建描述 | 新增 | 31 | 0 | 31 |
| `hindsight-extensions/contextdb-service/pytest-system.ini` | CI/配置/模板/构建描述 | 新增 | 6 | 0 | 6 |
| `hindsight-system-tests/pyproject.toml` | CI/配置/模板/构建描述 | 修改 | 16 | 0 | 16 |
| `scripts/hooks/lint.sh` | CI/配置/模板/构建描述 | 修改 | 8 | 2 | 6 |
| `hindsight-control-plane/src/i18n/contextdb-catalogs.json` | UI文案资源 | 新增 | 400 | 0 | 400 |
| `skills/hindsight-docs/references/openapi.json` | 原生OpenAPI参考副本 | 修改 | 1 | 1 | 0 |
| `CLAUDE.md` | 文档入口/测试说明/规范 | 修改 | 6 | 0 | 6 |
| `hindsight-extensions/README.md` | 文档入口/测试说明/规范 | 修改 | 1 | 0 | 1 |
| `hindsight-extensions/contextdb-service/README.md` | 文档入口/测试说明/规范 | 新增 | 51 | 0 | 51 |
| `hindsight-extensions/contextdb-service/docs/README.md` | 文档入口/测试说明/规范 | 新增 | 25 | 0 | 25 |
| `hindsight-system-tests/README.md` | 文档入口/测试说明/规范 | 修改 | 19 | 0 | 19 |
| `hindsight-extensions/contextdb-service/schemas/contextdb-control-plane.openapi.yaml` | 生成的管理OpenAPI | 新增 | 2,888 | 0 | 2,888 |
| `hindsight-system-tests/uv.lock` | 系统测试依赖锁 | 修改 | 4,954 | 331 | 4,623 |
