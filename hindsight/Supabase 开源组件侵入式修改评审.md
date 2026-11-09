# Supabase 开源组件侵入式修改评审

> 本文档由 `议题（侵入式）材料：Supabase开源组件侵入式修改评审.pptx` 整理而来，共 9 页幻灯片。

| 项目     | 内容                            |
| -------- | ------------------------------- |
| 汇报人   | 李丰瑞                          |
| 部门     | RDS for Postgres                |
| 评审主题 | Supabase 开源组件侵入式修改评审 |

---

## 一、Supabase 侵入式修改基本信息

### 1. 基本信息

| 条目             | 描述                                                         | 介绍                                                         |
| ---------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 开源软件介绍     | 如功能介绍、社区常见用法、是否涉及标准协议接口实现、社区代码量介绍等。 | 1、基本功能：Supabase 是开源的 Firebase 替代方案，基于 PostgreSQL 构建的一站式开发平台，可用于开发网页、移动端及 AI 类应用，核心提供专属 Postgres 数据库服务，依托多语言技术栈与开源组件，覆盖全场景开发需求。<br>2、社区主导力量：Supabase<br>3、活跃程度：Stars 100k，Issues 267 / PRs 728，贡献者众多<br>4、质量情况：截止 2026-03-05，存在 Issues 267 / PRs 728，质量状况尚可，且社区活跃度高，对于严重 issue 会及时修复<br>5、语言：ts<br>6、官方代码仓：<https://github.com/supabase/supabase>、<https://github.com/supabase/storage><br>7、License：Apache-2.0 License<br>8、版本：v1.26.03<br>9、发布时间：2026-03-05 |
| 产品定制需求描述 | 如业务场景（涉及产品软硬件集成方案）、产品立项/交付客户形态（可能会高频收集需求、发布等）、个性功能增强等。 | Supabase 网络配置适配华为云安全要求及可信构建要求，storage 组件需要适配华为云的存储模式。 |
| 需求解决什么问题 | 介绍业务和开源的 gap，介绍社区是否有类似功能和用法。         | 1、网络配置适配华为云安全要求<br>2、存在因 License 问题无法引入的依赖，需要移除<br>3、存储功能适配 |
| 定制是否可以消减 | 能否通过在业务自研代码中适配/规避、或优化架构等方法解决。    | 否                                                           |

### 2. 前期评审结论

| 组织/角色        | 评审结论 | 附件 |
| ---------------- | -------- | ---- |
| 产品部 CMC 或 PC | 同意     |      |
| 研发部开源 COE   | 同意     |      |

### 3. 定制修改需求和信息

> 原幻灯片此处为内嵌的 OLE 对象（附件），为一封 `.msg` 邮件：**《【请阅】2026年6月10日数据库云服务领域 TMG 例会简报》**，来自 `D:\workspace\supabase\`。正文文字内容未内嵌于幻灯片文本层，故此处仅作附件说明。

---

## 二、Supabase 需求介绍

### 1. 服务简介

Supabase 是开源的 Firebase 替代方案，基于 PostgreSQL 构建的一站式开发平台，可用于开发网页、移动端及 AI 类应用，核心提供专属 Postgres 数据库服务，依托多语言技术栈与开源组件，覆盖全场景开发需求。

### 2. 开源软件对应的功能模块在产品的位置

- **studio 组件**：Supabase 的前端页面，集成数据库访问、修改、存储、认证、日志查看等功能。
- **storage 组件**：Supabase 的存储模块，用于对接对象存储。

> 原幻灯片此页包含一张架构图片（`图片 7`），未在文本层中。

---

## 三、Supabase 开源软件侵入式修改详细方案

### 开源软件侵入式修改原因及方案

| 序号 | 修改模块        | 修改原因                                                     | 侵入式修改点                                                 | 预计修改工作量 | 是否返回社区                   |
| ---- | --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | -------------- | ------------------------------ |
| 1    | Supabase studio | 依赖的软件包 `@sentry/nextjs` 和 `stripe-experiment-sync` 因无 License 及 License 不可商用问题，需要移除 | Supabase studio 中涉及的源码删除调用点                       | 1 人/天        | 否，主要为符合公司可信构建规范 |
| 2    | Supabase studio | Supabase studio 使用环境变量 `SUPABASE_PUBLIC_URL` 配置的地址拼接 URL，无法适用于公网 / 私网均需访问的情况 | 将 Supabase studio 中从 `SUPABASE_PUBLIC_URL` 环境变量获取地址，替换成从浏览器请求动态获取 URL | 1 人/天        | 否，主要为符合公司安全规范     |
| 3    | storage         | storage 上传文件默认使用的访问模式为 `x-amz-content-sha256`。华为云 OBS 不支持该模式。<br>华为云支持的 V4 签名模式说明见：<https://support.huaweicloud.com/obs_faq/obs_faq_0274.html> | 侵入式修改 storage 源码适配华为云 OBS                        | 1 人/天        | 否，主要为适配公司 OBS         |

> 原幻灯片此页包含一张图片（`图片 3`），未在文本层中。

---

## 四、开源软件安全分析（安全检查项 14 条）

> ⚠️ **整理说明**：本页在原 PPT 中标题为「Prometheus 开源软件安全分析」，且表格表头第一行残留 `KubeRay / 1.5.1` 的模板标识。结合整份材料主题为 Supabase、以及评估结论列中出现“Supabase”，判断本页系沿用 Prometheus 评审模板、未完成标题与表头替换。以下内容按原表如实转录。

| 检查项（14 条）                                       | 检查内容                                                     | 检查方法说明                                                 | 是否必填项 | 评估结论 |
| ----------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ---------- | -------- |
| 1.1 业界已知公开的安全漏洞                            | 软件版本不含业界已经公开的危害级别为高的安全漏洞。           | 可在 CVE 官方网站查看 <http://web.nvd.nist.gov/view/vuln/search> / <https://cve.mitre.org/> 描述当前版本是否有 CVE 漏洞；如果有漏洞，记录漏洞号、漏洞级别、是否已有补丁。 | 必选       | 无       |
| 1.2 安全问题求助渠道                                  | 社区有安全处理机制及安全修复记录，无不良记录。               | 检查官网或平台社区网站是否提供了安全问题的解决渠道。         | 必选       | 有       |
| 1.3 官网披露漏洞的地址                                | 填写官网或者 NVD 网站承载该软件漏洞信息的 URL 地址；例如 Openssl 的官网漏洞披露地址为 <https://www.openssl.org/news/vulnerabilities.html>。 |                                                              | 可选       |          |
| 1.4 官网软件名称                                      | 填写官网的软件名称；Openssl 的漏洞披露网址为 <https://www.openssl.org/>，披露的软件名称为：OpenSSL，多个名称使用英文分号 `;` 分隔。 |                                                              | 可选       | Supabase |
| 1.5 NVD 漏洞库对应的软件名称                          | 填写官网漏洞地址披露的软件名称；Openssl 的漏洞披露网址为 <https://www.openssl.org/news/vulnerabilities.html>，披露的软件名称为：OpenSSL，多个名称使用英文分号 `;` 分隔。 |                                                              | 可选       |          |
| 1.6 其他漏洞收集来源的地址                            | 填写除官网以外的漏洞披露地址，例如 NVD 漏洞披露地址 <https://nvd.nist.gov/vuln/search/results?form_type=Basic&results_type=overview&query=openssl&search_type=all>，多个名称使用英文分号 `;` 分隔。 |                                                              | 可选       |          |
| 1.7 整理开源软件包含的账号口令清单                    | 检查开源软件资料（开源软件官网描述、用户手册、readme），从资料文档中搜索查找类似“account、password”这样的“账号”、“口令”关键字，整理该软件包含的账号口令清单。 | 检查开源软件资料（开源软件官网描述、用户手册、readme）       | 可选       | 未涉及   |
| 1.8 是否存在第三方的网络嗅探、调试工具、开发/编译工具 | 该项使用 secbinarycheck 工具扫描。<br>根据扫描出来的结果，分析开源软件中是否涉及网络嗅探、调试工具、开发/编译等易被客户质疑的工具。产品在集成该开源软件时，需要从产品软件包中删除这些可能被质疑的工具。<br>工具链接：<https://secguard-szv.clouddragon.huawei.com/secguard/tool/engine/secbincheck><br>工具帮助文档：<http://wiki.inhuawei.com/pages/viewpage.action?pageId=79844637><br>工具链接：<https://secbinarycheck.rnd.huawei.com/><br>工具帮助文档：<http://3ms.huawei.com/hi/group/1007713/file_13374589.html> | 工具部分支持扫描（secbinarycheck）                           | 可选       | 无       |
| 1.9 是否存在未公开的公网地址                          | 该项使用 secbinarycheck 工具扫描。<br>分析公网地址用途（包括公网 IP 地址、公网 URL 地址/域名、邮箱地址），产品在集成该开源软件时，需要在产品资料、或软件界面中公开这些公网地址，避免产品存在恶意向公网发送信息引起客户质疑。<br>工具链接：<https://secguard-szv.clouddragon.huawei.com/secguard/tool/engine/secbincheck><br>工具帮助文档：<http://wiki.inhuawei.com/pages/viewpage.action?pageId=79844637> | 工具支持扫描（secbinarycheck）                               | 可选       | 无       |
| 1.10 是否存在发送恶意连接等行为                       | 该项使用 sechunter、secdroid 2 个工具扫描。<br>1、恶意消耗用户数据流量，当前 sechunter 工具支持该项扫描。根据扫描出来的结果，查看开源软件中是否存在恶意消耗用户数据流量。<br>工具链接：<https://sechunter-szv.clouddragon.huawei.com/sechunter/android/detection/task><br>工具帮助文档：<http://wiki.inhuawei.com/pages/viewpage.action?pageId=110558995><br>2、吸费陷阱，当前 secdroid 工具支持该项扫描。根据扫描出来的结果，查看开源软件中是否存在恶意吸费陷阱。<br>工具链接：<http://rnd-secdroid.huawei.com/workspace#><br>工具帮助文档：<http://3ms.huawei.com/hi/group/2034125/file_12348839.html> | 工具支持扫描（sechunter、secdroid）                          | 可选       | 不涉及   |

---

## 五、开源软件中心仓定制分支现状

> ⚠️ **整理说明**：原 PPT 本页标题为「Prometheus 开源软件中心仓定制分支现状」，表格内容（使用产品 CloudMonitorCenter/UCS/CAE/AOM、旧版本 Prometheus 版本超期问题）亦为 Prometheus 评审内容，与 Supabase 主题不符。以下按原表如实转录。

| 范围   | 使用版本                    | 使用产品                             | 归一策略                                                     |
| ------ | --------------------------- | ------------------------------------ | ------------------------------------------------------------ |
| 云软件 | V2.53.2 / V2.28.0 / V2.43.1 | CloudMonitorCenter / UCS / CAE / AOM | 不可归一，旧版本 Prometheus 存在大量版本超期问题，需使用最新 LTS 版本修复 |

查询云软件定制修改的软件信息：<https://fuxi.huawei.com/mine/public-services/centralHomePage/centralWarehouse/sourceCentralRepository/editIntrusive>

---

## 六、开源软件演进策略

> ⚠️ **整理说明**：原 PPT 本页标题为「Prometheus 开源软件演进策略」，同样为模板未替换内容。以下按原文如实转录。

### 1. 维护策略、投入情况

计划 1 人实现开发与维护。

### 2. 社区同步情况

暂不同步。

---

## 七、决策点

**同意 Supabase studio / storage 组件引入中心仓，并定制修改。**