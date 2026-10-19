# ContextDB PG 表设计（兼容入口）

更新日期：2026-10-13。表设计已并入[主设计的 PG 表设计章节](../member-apikey-bank-service-design.md#pg-表设计)，本文件保留旧链接入口，不再独立维护第二套内容。

主设计集中说明同库 schema 布局、全部 9 张元信息表、主要字段/约束/索引、事务与备份恢复边界。完整可执行 DDL 位于源码 `hindsight-extensions/contextdb-service/hindsight_ext_contextdb/schema.sql`；原生 Bank 记忆表仍由上游迁移维护。

相关记录：[实现验收](contextdb-service-verification-2026-10-13.md) · [开发问题与设计差异](contextdb-service-night-task-2026-10-13.md)。本轮没有执行数据库迁移。
