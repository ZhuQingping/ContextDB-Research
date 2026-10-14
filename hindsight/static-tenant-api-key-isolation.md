# Hindsight 静态租户、API Key 与隔离

**可以按“组织”理解：组织之间数据隔离，一个组织可以有多个 Key，各 Key 都能访问该组织的所有 bank。**

本文适用于仓库提供的可选 `StaticKeysTenantExtension`，需先让运行环境能够导入该扩展。当前 ContextDB 使用自己的租户扩展，不能直接套用下面的配置。

## 配置方式

```bash
HINDSIGHT_API_TENANT_EXTENSION=hindsight_ext_static_keys_tenant:StaticKeysTenantExtension
HINDSIGHT_API_TENANT_USERS="MySQL:key1,MySQL:key2,PG:key3"
```

- `HINDSIGHT_API_TENANT_EXTENSION`：选择租户认证扩展，负责验证 Key 并确定访问的 schema。
- `HINDSIGHT_API_TENANT_USERS`：配置逗号分隔的 `组织标识:API Key` 映射，同一组织可出现多次。

**不要将此映射写入 `HINDSIGHT_API_TENANT_API_KEY`。** 内置单 Key 扩展会把整串当作一个 Key，不会拆分组织。

API 和 Worker 需使用相同的租户配置。这里的组织是静态身份，不包含注册、成员或组织管理功能。

## 组织、schema 和 bank

| 组织标识 | API Key | 默认 PG schema | bank 示例 |
| --- | --- | --- | --- |
| MySQL | key1、key2 | user_mysql | bank1、bank2 |
| PG | key3 | user_pg | bank1、bank3 |

`MySQL`、`PG` 只是组织名称；两者的数据都保存在 PostgreSQL。默认 schema 名称使用 `user_` 前缀，并将组织标识转为小写。

每个 schema 有自己的业务表，可以创建多个 bank。bank 是用 `bank_id` 区分的业务容器，不是子 schema；不同 bank 的记忆分别存储和查询，不会自动合并。

**不同组织可以使用相同的 bank_id。** 两个组织的 bank1 相互独立；同一组织内的 bank_id 必须唯一。

## 相同 URL 如何访问不同组织

Recall 的 URL 可以完全相同：

```text
POST /v1/default/banks/bank1/memories/recall
```

客户端通过 `Authorization: Bearer <Key>` 传入凭据：

- 使用 key1 或 key2：访问 user_mysql 中的 bank1。
- 使用 key3：访问 user_pg 中的 bank1。

**Key 决定组织/schema，URL 中的 bank_id 决定该组织内的 bank。** Key 无法通过修改 bank_id 切换组织。

隔离范围如下：

- **跨组织**：业务 API 无法访问另一组织的数据。
- **组织内部**：多个 Key 的访问范围相同，都可访问该组织下的所有 bank；没有按 Key 限制 bank 或设置只读角色的能力。
- **计算资源**：共享 Hindsight 服务和 PG 实例，没有独立的 CPU、内存、连接或磁盘配额。这里是逻辑数据隔离。

## 原生 UI 的两个 Key

| 变量 | 用途 |
| --- | --- |
| `HINDSIGHT_CP_DATAPLANE_API_KEY` | UI 调用后端 API 的 Key，决定访问哪个组织 |
| `HINDSIGHT_CP_ACCESS_KEY` | UI 登录口令，不决定访问哪个组织 |

例如：

```bash
HINDSIGHT_CP_DATAPLANE_API_KEY=key1
HINDSIGHT_CP_ACCESS_KEY=ui-login-secret
```

登录这个 UI 后，访问的是 MySQL 组织。**一个 UI 实例使用一个固定的后端 Key，登录口令不会切换组织。** 登录口令可单独生成。

## 核验依据

核验日期：2026-10-14；Hindsight 本地源码提交：`cdfc199e5`。本次核对源码和已有测试定义，未重新运行服务或隔离测试。

- [静态扩展说明](https://github.com/ZhuQingping/hindsight/blob/cdfc199e5f48b1d9cc9a99119b3efb761f656ef6/hindsight-extensions/static-keys-tenant/README.md)、[认证实现](https://github.com/ZhuQingping/hindsight/blob/cdfc199e5f48b1d9cc9a99119b3efb761f656ef6/hindsight-extensions/static-keys-tenant/hindsight_ext_static_keys_tenant/extension.py)：配置、Key 映射及 schema 隔离。
- [内置单 Key 扩展](https://github.com/ZhuQingping/hindsight/blob/cdfc199e5f48b1d9cc9a99119b3efb761f656ef6/hindsight-api-slim/hindsight_api/extensions/builtin/tenant.py)、[同名 bank 隔离测试](https://github.com/ZhuQingping/hindsight/blob/cdfc199e5f48b1d9cc9a99119b3efb761f656ef6/hindsight-api-slim/tests/test_schema_isolation.py)。
- [UI 后端 Key](https://github.com/ZhuQingping/hindsight/blob/cdfc199e5f48b1d9cc9a99119b3efb761f656ef6/hindsight-control-plane/src/lib/hindsight-client.ts)、[UI 登录口令](https://github.com/ZhuQingping/hindsight/blob/cdfc199e5f48b1d9cc9a99119b3efb761f656ef6/hindsight-control-plane/src/app/api/auth/login/route.ts)。
