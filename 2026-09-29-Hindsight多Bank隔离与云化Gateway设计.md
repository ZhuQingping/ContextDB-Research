# Hindsight 多 Bank 隔离与云化 Gateway 设计

## 目的

基于 Hindsight 做云场景服务化时，厘清：
- 同一 schema 下多个 bank（记忆库）之间的数据隔离性质
- 企业客户下多角色（开发/测试/运维）的记忆库隔离方案
- 客户端如何定位/切换 bank
- 自研 gateway 的定位与映射设计（**gateway 设计待后续演进思考，本文是起点**）

> 背景：Hindsight 的多租户模型是"schema 隔离租户 + bank 隔离租户内分组"两层。本文聚焦 bank 层与云化 gateway。

日期：2026-09-29

---

## 前置概念：schema 与 bank 的层级关系

理解 bank 隔离前，先明确 Hindsight 的两层隔离单元（详见《Hindsight 多 PG 实例横向扩展方案》的"前置概念"段）：

```
PG 实例（物理存储、故障域、横向扩展边界）
  └─ schema（租户级隔离单元，API key → schema，物理隔离）
       └─ bank（记忆库，租户内逻辑分组，bank_id 路由，逻辑隔离）
            └─ memory_units（实际记忆 + embedding + 图）
```

- **schema = 租户**：PG 物理隔离层，一租户一 schema（如 `user_company1`）。
- **bank = 租户内记忆库**：表里一行，靠 `bank_id` 路由（如 `dev-bank`）。URL 路径 `/v1/default/banks/{bank_id}/memories/recall`。
- **一个 schema 可含多个 bank，一个 bank 必属于一个 schema**（不是一一对应）。

---

## 一、不同 Bank 之间的数据隔离吗？——逻辑隔离（同表共存，按 bank_id 过滤）

### 结论：逻辑隔离，不是物理隔离

源码确认：同一 schema 下所有记忆表（`memory_units`/`chunks`/`documents`/`entities`/`memory_links`...）**共用同一张表**，每行带 `bank_id` 列。隔离靠 SQL `WHERE bank_id = $2` 过滤。

- 语义检索 SQL：`link_expansion_retrieval.py:97` `WHERE bank_id = $2`。
- 所有记忆表都有 `bank_id` 列 + 索引（`idx_memory_units_bank_*`、`idx_entities_bank_id` 等）。
- 实体消解带 bank_id 唯一约束：`idx_entities_bank_lower_name` on `(bank_id, LOWER(canonical_name))`——实体名只在 bank 内唯一，不会跨 bank 串。

### 这个逻辑隔离安全吗（会不会漏带 bank_id）

Hindsight 用"强制带 bank_id"机制，防止查询漏带：

1. **bank_id 也是 contextvar**（`memory_engine.py:98` `_current_bank_id`），和 schema 一样的异步隔离模式。`_bind_bank_id` 装饰器在请求边界绑定，SQL 用 `fq_table()` + contextvar bank_id。
2. **bank_id 来自 URL path**（`http.py:5839` `/v1/default/banks/{bank_id}/...`），不是请求体——每个请求必带。

所以隔离是**可靠的应用层逻辑隔离**，不是"容易漏带"的脆弱设计。

### 隔离强度对比（云化关键认知）

| 隔离边界 | 机制 | 强度 |
|---------|------|------|
| schema 间（租户间）| 不同 schema，不同表集合 | **物理隔离**（DB 层硬墙）|
| bank 间（租户内）| 同表共存，应用层按 bank_id 过滤 | **逻辑隔离**（应用层过滤）|

> **对云化的含义**：bank 间隔离靠**应用代码正确性**（都带 bank_id），不是 DB 层硬墙。日常没问题，但不像 schema 那样能防"代码 bug 导致泄露"。**企业内不同角色（开发/测试/运维）用不同 bank，是"业务隔离"级别，不是"安全隔离"级别**——若某角色数据高敏，逻辑隔离可能不够，需考虑升到 schema 级（见下文"隔离层级选择"）。

---

## 二、客户端如何定位/切换 Bank

### 两种方式

**方式 1：env 配置 `HINDSIGHT_BANK_ID`（默认 bank）**

源码（`recall.py:154` + `bank.py:125`）：静态模式下 `derive_bank_id()` 直接返回 `config["bankId"]`（即 `HINDSIGHT_BANK_ID`）。

- 改 `HINDSIGHT_BANK_ID` 确实能切换 bank，插件 recall/retain 会用新 bank。
- 局限：
  1. **配置是 session/进程级**：在 `.claude/settings.json` 的 env 块，改了要重启 Claude Code 会话才生效，不能"同一会话动态切"。
  2. **粒度是"一个客户端绑一个 bank"**：不同角色（不同人/不同会话）各自配自己的 `HINDSIGHT_BANK_ID` 即可；但一个人想同时访问多个 bank 不方便。
  3. 适合"一个角色一个客户端、固定 bank"的简单场景。

**方式 2：请求 URL 里带 bank_id（云化正确姿势）**

bank_id 在 URL path（`/v1/default/banks/{bank_id}/...`），所以**gateway/客户端可以不改 env，直接每次请求在 URL 里带不同 bank_id**——这才是云化多 bank 的正确用法。env 默认值只适合单 bank 固定场景。

> 结论：云化多角色/动态切换，应走方式 2（URL 带 bank_id），不走方式 1（改 env）。

---

## 三、云化场景：企业多角色隔离设计

### 场景

一个企业客户，下面有多个员工角色：开发、测试、运维。各角色有自己的记忆库（dev-bank / test-bank / ops-bank），库之间要隔离。

### 三层隔离模型（建议）

把场景拆成三层，每层用合适的隔离机制：

```
① 企业间隔离  → Hindsight schema（物理隔离，key→schema，硬墙）
                 gateway 记录: tenant_id → schema → hindsight_tenant_key

② 企业内角色隔离 → Hindsight bank（逻辑隔离，bank_id 过滤）+ gateway ACL
                 gateway 记录: user_key → 角色权限 → 可访问 bank 列表
                 gateway 校验: 请求的 bank_id 在该用户可访问列表内

③ 记忆库内 → 无需额外隔离（bank 内数据天然在一起）
```

### 这个场景的具体映射

```
企业 company1 → schema user_company1（Hindsight 侧 key=key-zhang3）
  ├─ 开发员工 → 可访问 bank: dev-bank
  ├─ 测试员工 → 可访问 bank: test-bank
  └─ 运维员工 → 可访问 bank: ops-bank

gateway 映射表:
  user_key        tenant    role   allowed_banks
  emp-dev-001  → company1 → dev   → [dev-bank]
  emp-test-001 → company1 → test  → [test-bank]
  emp-ops-001  → company1 → ops   → [ops-bank]
  (也可能: 主管 → [dev-bank, test-bank, ops-bank] 多 bank)
```

### 隔离层级选择（bank 级 vs schema 级）

- **默认：角色用 bank 隔离**——开发/测试/运维各一个 bank，gateway 做 bank 级 ACL。够用、schema 数量不膨胀。
- **升 schema 级**：若某角色数据高敏（如运维有生产敏感数据），可考虑每个角色一个 schema——代价是 schema 数量膨胀（3 倍）、运维负担增加。一般场景 bank 级 + gateway ACL 够。

---

## 四、自研 Gateway 设计（待演进，本文是起点）

> **说明**：gateway 的完整设计（多 gateway 实例、HA、限流、计费采集、审计落盘、与华为云 IAM 集成等）待后续演进思考。本文只锁定"定位 + 三层映射 + 请求流程"这个起点，让后续演进有锚点。

### Gateway 定位

Gateway 是"企业侧鉴权 + Hindsight 侧鉴权"的翻译层：

- 对客户端：gateway 发自己的 key（emp-dev-001），客户端不接触 Hindsight 的 key。
- 对 Hindsight：gateway 用一个"Hindsight 侧的租户 key"（key-zhang3）代表整个企业租户。
- 即 gateway 把"企业内多个员工 key"收敛成"一个 Hindsight 租户 key"。

### Gateway 要记录的映射表

| 映射 | 表 | 示例 | 作用 |
|------|----|------|------|
| 企业租户 → schema | `tenant_schema_map` | company1 → user_company1 | 决定走哪个 PG schema（租户隔离）|
| 员工 key → 租户 | `user_tenant_map` | emp-dev-001 → company1 | 鉴权 + 定租户 |
| 员工 → 可访问 bank 列表 | `user_bank_acl` | emp-dev-001 → [dev-bank] | bank 级 ACL |
| bank → schema | （由 bank 所在 schema 决定）| dev-bank 在 user_company1 | bank 必在租户 schema 内 |

### Gateway 一次请求的流程

```
员工客户端（带自己的 key + 指定 bank_id）
   │  Authorization: Bearer emp-dev-001
   │  请求: POST /v1/default/banks/dev-bank/memories/recall
   ▼
Gateway（自研）
   ① 验 emp-dev-001 → 查 user_tenant_map → company1
   ② 查 tenant_schema_map → user_company1
   ③ 查 user_bank_acl：dev-bank 是否在 emp-dev-001 的 allowed_banks 内
       （防越权：开发不能访问运维的 bank）
   ④ 改写请求：用 Hindsight 侧的租户 key（key-zhang3）+ 透传 bank_id=dev-bank
       POST http://hindsight/v1/default/banks/dev-bank/memories/recall
       Authorization: Bearer key-zhang3
   ▼
Hindsight（StaticKeysTenantExtension）
   key-zhang3 → user_company1 schema → 在该 schema 里按 bank_id=dev-bank 过滤
```

### 关键设计点

1. **bank 级 ACL 在 gateway 校验，不在 Hindsight 内**：Hindsight 的 bank 是逻辑隔离，不防"同一 schema 内跨 bank 访问"（同一个 key 能访问该 schema 下所有 bank）。所以"开发不能读运维 bank"这个约束，**必须在 gateway 层校验**——Hindsight 本身不提供 bank 级 ACL。
   - 为什么不在 Hindsight 内做 bank ACL：bank 设计是"租户内逻辑分组"，不是"权限边界"。强行在 Hindsight 加 bank ACL = 改核心。Gateway 层做 = 正交外挂，不动 Hindsight。

2. **schema 级隔离交给 Hindsight**：不同企业的隔离靠 Hindsight 的 schema（key→schema），这是硬隔离，gateway 透传即可。

3. **gateway 的"租户→schema"映射表，与 Cognee 上用 Agent 开发的 `tenant_pg_routing` 同构**——都是"路由表 + 鉴权翻译"层。那套设计经验可复用到 Hindsight gateway。

4. **Hindsight 的 `StaticKeysTenantExtension` 本身就是"env 配置版 gateway"**（key→user→schema 映射在 env）。自研 gateway 本质上是把它升级成"DB-backed + 多层 ACL"版——映射逻辑不变，数据源从 env 改 DB，加 bank 级 ACL。这是对多租户调研里"自写 DB-backed `TenantExtension`"的具体化。

### 待后续演进思考的点（占位，不在本文展开）

- gateway 多实例与 HA（多副本 + 共享映射表 DB）
- 限流 / 配额（per-tenant / per-bank）
- 计费采集（按 recall 次数、按 memory_units 条数、按 embedding 存储）
- 审计落盘（谁在何时访问了哪个 bank）
- 与华为云 IAM 的集成（企业身份 → gateway key 的发放）
- bank 的生命周期管理（创建/归档/删除/迁移）
- gateway → Hindsight 的连接池管理
- 是否把 gateway 做成 TenantExtension 插件（in-process）而非独立进程

---

## 五、一句话总结

> **同 schema 不同 bank 是逻辑隔离（同表按 bank_id 过滤，靠 contextvar 强制带 bank_id，可靠但非 DB 硬墙）。云化正确姿势是自研 gateway，管三层映射：员工 key→企业租户（定 schema，Hindsight 硬隔离）、租户→schema、员工→可访问 bank 列表（bank 级 ACL 在 gateway 校验，Hindsight 不提供）。客户端通过 URL 带 bank_id 切换库（不只是改 `HINDSIGHT_BANK_ID` env）。企业间隔离靠 Hindsight schema，企业内角色隔离靠 gateway + bank ACL。gateway 完整设计待后续演进。**

---

## 六、源码证据索引

| 结论 | 证据 |
|------|------|
| bank 逻辑隔离（按 bank_id 过滤）| `engine/search/link_expansion_retrieval.py:97` `WHERE bank_id = $2`；`alembic/.../5a366d414dce_initial_schema.py` 各表 `bank_id` 列 + 索引 |
| bank_id 强制带（contextvar）| `engine/memory_engine.py:98` `_current_bank_id` ContextVar + `_bind_bank_id` 装饰器 |
| bank_id 来自 URL path | `api/http.py:5839` `/v1/default/banks/{bank_id}/memories/recall` |
| 实体名 bank 内唯一 | `idx_entities_bank_lower_name` on `(bank_id, LOWER(canonical_name))` |
| 客户端默认 bank 来自 env | `recall.py:154` + `bank.py:125` 静态模式 `config["bankId"]` |
| Hindsight 侧 key→schema 映射 | `hindsight-extensions/static-keys-tenant/extension.py:209` `schema_name = f"{prefix}_{user_id}"` |
