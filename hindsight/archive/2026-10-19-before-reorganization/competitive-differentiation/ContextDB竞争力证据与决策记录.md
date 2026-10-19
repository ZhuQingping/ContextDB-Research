# ContextDB 竞争力证据与决策记录

版本：1.0｜日期：2026-10-08｜机器入口：解析下方唯一 JSON 代码块。

当前结论见 [阅读文档](ContextDB差异化竞争力.md)。本文件保存稳定编号、来源定位、验证边界、能力状态、历史纠错和未关闭问题。历史中的“已确认”“唯一”等措辞不能覆盖当前状态。

- EV 连接证据，source_ids 定位来源，capability_ids 连接功能，DEC 记录决策，Q 记录未关闭问题。
- official_doc_previous_review 是上一轮核验；imported_report 是继承调研；search_index_only 不是正文快照。
- snapshot_path 为 null 表示无可寻址原网页快照；源报告不是原网页。SHA-256 证明内容完整，不证明外部事实。
- 更新追加同 ID 的 revision/supersedes 与日志，保留旧断言，再更新阅读稿。
- 原六稿全文归档，原报告保留；本轮未重新验证报价、产品或性能。
- 未知负责人、交期、快照写 null，不把建议测试量写成已验证容量。
- historical_tables 保留原表文字和原链接；链接按 original_path 所在目录解释，搬迁文件通过 coverage 映射到 archive。代码块内原表不作为本文件的可点击链接。

索引：coverage → sources → evidence → assertion_history → capabilities → decision_history → open_questions → historical_tables → journal。

```json
{
  "schema_version": "1.0",
  "document_id": "contextdb-competitive-evidence",
  "updated_at": "2026-10-08",
  "human_document": "ContextDB差异化竞争力.md",
  "authority_order": [
    "evidence最新修订及adopted决策",
    "capabilities实现状态",
    "历史归档/source报告仅作输入"
  ],
  "consolidation_scope": "已有资料重组，无本轮联网验证/运行/性能测试；目录外设计只引用",
  "verification_policy": {
    "versioning": "稳定ID，追加revision/supersedes保留旧记录，同日用sequence不伪造时间",
    "checked_at": "已有记录日期，不表示本轮重新访问",
    "snapshots": "null表示无可寻址原网页快照，源报告不等于网页存档",
    "unknowns": "负责人/交期/快照未知写null",
    "hashes": "SHA-256验证文件完整性，不证明外部事实",
    "refresh": "价格/版本/star/产品状态发布前复核；未找到不等于不存在",
    "release": "底座支持不是已商用，没有验收不标verified_commercial"
  },
  "coverage": [
    {
      "archive_source_id": "SRC-001",
      "original": "00-executive-summary.md",
      "archive": "archive/2026-10-08/00-executive-summary.md",
      "preserved": "full_text_except_relocated_relative_links",
      "human_sections": [
        "1",
        "2",
        "7"
      ],
      "machine_sections": [
        "sources",
        "evidence",
        "capabilities",
        "decision_history",
        "historical_tables"
      ]
    },
    {
      "archive_source_id": "SRC-002",
      "original": "01-weknora-analysis.md",
      "archive": "archive/2026-10-08/01-weknora-analysis.md",
      "preserved": "full_text_except_relocated_relative_links",
      "human_sections": [
        "3",
        "5",
        "6"
      ],
      "machine_sections": [
        "sources",
        "evidence",
        "capabilities",
        "decision_history",
        "historical_tables"
      ]
    },
    {
      "archive_source_id": "SRC-003",
      "original": "02-competitor-landscape.md",
      "archive": "archive/2026-10-08/02-competitor-landscape.md",
      "preserved": "full_text_except_relocated_relative_links",
      "human_sections": [
        "3",
        "6"
      ],
      "machine_sections": [
        "sources",
        "evidence",
        "capabilities",
        "decision_history",
        "historical_tables"
      ]
    },
    {
      "archive_source_id": "SRC-004",
      "original": "03-academic-evidence.md",
      "archive": "archive/2026-10-08/03-academic-evidence.md",
      "preserved": "full_text_except_relocated_relative_links",
      "human_sections": [
        "4.3",
        "6"
      ],
      "machine_sections": [
        "sources",
        "evidence",
        "capabilities",
        "decision_history",
        "historical_tables"
      ]
    },
    {
      "archive_source_id": "SRC-005",
      "original": "04-differentiation-strategy.md",
      "archive": "archive/2026-10-08/04-differentiation-strategy.md",
      "preserved": "full_text_except_relocated_relative_links",
      "human_sections": [
        "1",
        "5",
        "7"
      ],
      "machine_sections": [
        "sources",
        "evidence",
        "capabilities",
        "decision_history",
        "historical_tables"
      ]
    },
    {
      "archive_source_id": "SRC-006",
      "original": "05-concrete-selling-points.md",
      "archive": "archive/2026-10-08/05-concrete-selling-points.md",
      "preserved": "full_text_except_relocated_relative_links",
      "human_sections": [
        "2",
        "4",
        "5",
        "6"
      ],
      "machine_sections": [
        "sources",
        "evidence",
        "capabilities",
        "decision_history",
        "historical_tables"
      ]
    }
  ],
  "sources": [
    {
      "id": "SRC-001",
      "kind": "archived_analysis",
      "path": "archive/2026-10-08/00-executive-summary.md",
      "original_path": "00-executive-summary.md",
      "original_sha256": "9169d16c81ac20865e7343a28ef48d9bbe29b3f97fd713ff19e25886a02c17fc",
      "sha256": "9a6bc162bb7bdf165d7f9d65cd7353b3b0124028215b5b9206bd5f673701434d",
      "original_bytes": 3394,
      "original_lines": 37,
      "archived_at": "2026-10-08",
      "status": "historical_not_current_authority",
      "sections": [
        {
          "heading": "华为云 ContextDB 差异化竞争力：执行摘要",
          "line": 1
        }
      ],
      "link_rewrites": [
        {
          "from": "evidence/review-concrete-capabilities.md",
          "to": "../../evidence/review-concrete-capabilities.md"
        },
        {
          "from": "evidence/sources-index.md",
          "to": "../../evidence/sources-index.md"
        }
      ]
    },
    {
      "id": "SRC-002",
      "kind": "archived_analysis",
      "path": "archive/2026-10-08/01-weknora-analysis.md",
      "original_path": "01-weknora-analysis.md",
      "original_sha256": "0bea39d91a33d52a7a4c01821ff20b437541d0d4865519a6841e2986d70b542c",
      "sha256": "0010f618b251fc40435b1bbe99ec0cdceb48ca69dea6fd34b9e2a0253e15f75b",
      "original_bytes": 12780,
      "original_lines": 146,
      "archived_at": "2026-10-08",
      "status": "historical_not_current_authority",
      "sections": [
        {
          "heading": "WeKnora 深度剖析：对华为云 ContextDB 的可借鉴点",
          "line": 1
        },
        {
          "heading": "1. 结论速览",
          "line": 8
        },
        {
          "heading": "2. 项目基本面【已确认】",
          "line": 14
        },
        {
          "heading": "3. 架构与核心能力【已确认】",
          "line": 29
        },
        {
          "heading": "3.1 存储与检索架构",
          "line": 31
        },
        {
          "heading": "3.2 文档解析管线",
          "line": 39
        },
        {
          "heading": "3.3 多租户与安全【已确认】",
          "line": 43
        },
        {
          "heading": "3.4 Agent 与 MCP",
          "line": 49
        },
        {
          "heading": "4. 产品化思路：从 RAG 问答到知识运营【已确认】",
          "line": 53
        },
        {
          "heading": "5. 商业化形态",
          "line": 68
        },
        {
          "heading": "6. 关键判断：WeKnora 与 ContextDB 的竞争交汇【已确认】",
          "line": 76
        },
        {
          "heading": "7. 可借鉴点清单（按优先级）",
          "line": 94
        },
        {
          "heading": "7.1 P0 —— 记忆治理闭环（确认制 + 来源血缘）",
          "line": 98
        },
        {
          "heading": "7.2 P0 —— 记忆参与检索（MemoryAffinity 思路）",
          "line": 104
        },
        {
          "heading": "7.3 P1 —— 知识/记忆即 MCP 服务",
          "line": 110
        },
        {
          "heading": "7.4 P1 —— 知识运营功能包",
          "line": 116
        },
        {
          "heading": "7.5 P2 —— PG 同库混合检索 + 引擎抽象",
          "line": 122
        },
        {
          "heading": "8. 明确不借鉴的部分",
          "line": 128
        },
        {
          "heading": "9. 证据来源",
          "line": 137
        }
      ],
      "link_rewrites": [
        {
          "from": "evidence/source-weknora-deep-dive.md",
          "to": "../../evidence/source-weknora-deep-dive.md"
        },
        {
          "from": "evidence/source-weknora-deep-dive.md",
          "to": "../../evidence/source-weknora-deep-dive.md"
        }
      ]
    },
    {
      "id": "SRC-003",
      "kind": "archived_analysis",
      "path": "archive/2026-10-08/02-competitor-landscape.md",
      "original_path": "02-competitor-landscape.md",
      "original_sha256": "5dece52cf84e3280c921094b2f2310fd95db7722ba6a227d9ea3658867764daf",
      "sha256": "94930df070384019f8749d09aba90d0c955a6fcff333e33d1848f758d76598a9",
      "original_bytes": 15323,
      "original_lines": 134,
      "archived_at": "2026-10-08",
      "status": "historical_not_current_authority",
      "sections": [
        {
          "heading": "友商全景：Agent 记忆/上下文服务竞争格局",
          "line": 1
        },
        {
          "heading": "1. 结论速览",
          "line": 9
        },
        {
          "heading": "2. 六方全景总表【已确认，除注明外】",
          "line": 17
        },
        {
          "heading": "3. 国内三强详析",
          "line": 31
        },
        {
          "heading": "3.1 阿里云：需重点对照的国内产品",
          "line": 33
        },
        {
          "heading": "3.2 火山引擎：商业模式最完整的对手，打法可复制",
          "line": 45
        },
        {
          "heading": "3.3 腾讯：生态玩家，暂无托管记忆收入",
          "line": 56
        },
        {
          "heading": "4. 国际云三范式",
          "line": 66
        },
        {
          "heading": "5. 国际开源光谱与行业分界线",
          "line": 78
        },
        {
          "heading": "6. 定价模式对比表",
          "line": 94
        },
        {
          "heading": "7. 威胁矩阵与空白矩阵",
          "line": 109
        },
        {
          "heading": "7.1 威胁矩阵（对我方既有差异化假设的冲击）",
          "line": 111
        },
        {
          "heading": "7.2 具体能力比较与验证缺口",
          "line": 120
        },
        {
          "heading": "8. 来源",
          "line": 131
        }
      ],
      "link_rewrites": [
        {
          "from": "evidence/",
          "to": "../../evidence/"
        },
        {
          "from": "evidence/review-concrete-capabilities.md",
          "to": "../../evidence/review-concrete-capabilities.md"
        },
        {
          "from": "evidence/",
          "to": "../../evidence/"
        },
        {
          "from": "evidence/source-aliyun-contextdb.md",
          "to": "../../evidence/source-aliyun-contextdb.md"
        },
        {
          "from": "evidence/source-tencent-volc.md",
          "to": "../../evidence/source-tencent-volc.md"
        },
        {
          "from": "evidence/source-aws-google.md",
          "to": "../../evidence/source-aws-google.md"
        },
        {
          "from": "evidence/source-opensource-landscape.md",
          "to": "../../evidence/source-opensource-landscape.md"
        },
        {
          "from": "evidence/source-weknora-deep-dive.md",
          "to": "../../evidence/source-weknora-deep-dive.md"
        },
        {
          "from": "evidence/source-papers-survey.md",
          "to": "../../evidence/source-papers-survey.md"
        }
      ]
    },
    {
      "id": "SRC-004",
      "kind": "archived_analysis",
      "path": "archive/2026-10-08/03-academic-evidence.md",
      "original_path": "03-academic-evidence.md",
      "original_sha256": "ec8c8ddf8aa68ceb41dcb665eb1e3bbc28e655926351445a2b54761ddf961222",
      "sha256": "909263fc3f9dc4c5eb0d9251c7e1a1076375ca0cb38b56dd31d46f3c36b5cb8a",
      "original_bytes": 8675,
      "original_lines": 83,
      "archived_at": "2026-10-08",
      "status": "historical_not_current_authority",
      "sections": [
        {
          "heading": "学术证据：记忆机制论文与评测基准",
          "line": 1
        },
        {
          "heading": "1. 对 ContextDB 战略最重要的三个发现",
          "line": 9
        },
        {
          "heading": "1.1 Hindsight 有论文与作者评测；独立复现待核验",
          "line": 11
        },
        {
          "heading": "1.2 记忆巩固（consolidation）是论文证据最密集的方向",
          "line": 23
        },
        {
          "heading": "1.3 评测基准本身是差异化战场",
          "line": 35
        },
        {
          "heading": "2. 记忆系统论文速览",
          "line": 43
        },
        {
          "heading": "3. Top 8 可产品化记忆机制（按论文证据强度排序）",
          "line": 59
        },
        {
          "heading": "4. 评测方法论警告（写给所有引用 benchmark 的人）",
          "line": 74
        },
        {
          "heading": "5. 证据来源",
          "line": 81
        }
      ],
      "link_rewrites": [
        {
          "from": "evidence/source-papers-survey.md",
          "to": "../../evidence/source-papers-survey.md"
        },
        {
          "from": "evidence/review-concrete-capabilities.md",
          "to": "../../evidence/review-concrete-capabilities.md"
        },
        {
          "from": "evidence/source-papers-survey.md",
          "to": "../../evidence/source-papers-survey.md"
        }
      ]
    },
    {
      "id": "SRC-005",
      "kind": "archived_analysis",
      "path": "archive/2026-10-08/04-differentiation-strategy.md",
      "original_path": "04-differentiation-strategy.md",
      "original_sha256": "67fde464d8c8de2452095dccb2d70a94c2a8ecc8c680fde70c9737fd6c5d53c4",
      "sha256": "3a8e64cee032f83e104c086743bbe0f0ca88ce510bb588f1aa56e00ba0a49a35",
      "original_bytes": 5276,
      "original_lines": 74,
      "archived_at": "2026-10-08",
      "status": "historical_not_current_authority",
      "sections": [
        {
          "heading": "ContextDB 差异化交付策略",
          "line": 1
        },
        {
          "heading": "1. 判断竞争力的标准",
          "line": 7
        },
        {
          "heading": "2. 三个主打点的交付物",
          "line": 20
        },
        {
          "heading": "3. 工程边界",
          "line": 30
        },
        {
          "heading": "4. 顺序与阶段出口",
          "line": 42
        },
        {
          "heading": "5. 衔接既有设计",
          "line": 53
        },
        {
          "heading": "6. 发布证据",
          "line": 66
        }
      ],
      "link_rewrites": [
        {
          "from": "evidence/review-concrete-capabilities.md",
          "to": "../../evidence/review-concrete-capabilities.md"
        },
        {
          "from": "evidence/sources-index.md",
          "to": "../../evidence/sources-index.md"
        }
      ]
    },
    {
      "id": "SRC-006",
      "kind": "archived_analysis",
      "path": "archive/2026-10-08/05-concrete-selling-points.md",
      "original_path": "05-concrete-selling-points.md",
      "original_sha256": "0e8a06e4d7e064eeb59143a0b85c9a2a6d8111f9b8712609e779c0f92797cbed",
      "sha256": "0373455461f1f74b0dc2de94d481e9e21ad363f62710807d0e2db82d00c56d32",
      "original_bytes": 13232,
      "original_lines": 115,
      "archived_at": "2026-10-08",
      "status": "historical_not_current_authority",
      "sections": [
        {
          "heading": "ContextDB 具体竞争力：功能、客户价值与验收标准",
          "line": 1
        },
        {
          "heading": "1. 优先交付的 12 项能力",
          "line": 9
        },
        {
          "heading": "2. 数据加密存储：交付覆盖清单",
          "line": 28
        },
        {
          "heading": "3. 记忆与知识导出：定义什么算全量",
          "line": 50
        },
        {
          "heading": "4. 中文优化：分词、理解和回答分别验收",
          "line": 72
        },
        {
          "heading": "5. 其他能力的最小演示与边界",
          "line": 93
        },
        {
          "heading": "6. 扩展候选",
          "line": 104
        }
      ],
      "link_rewrites": [
        {
          "from": "evidence/review-concrete-capabilities.md",
          "to": "../../evidence/review-concrete-capabilities.md"
        },
        {
          "from": "../hindsight-cloud-open-source-comparison.md",
          "to": "../../../hindsight-cloud-open-source-comparison.md"
        },
        {
          "from": "../backend-storage.md",
          "to": "../../../backend-storage.md"
        }
      ]
    },
    {
      "id": "SRC-101",
      "kind": "research_report",
      "path": "evidence/source-weknora-deep-dive.md",
      "sha256_at_merge": "54e19b4bb604479e1f769448dcda9d127de7f90a57e91781821b161fa6296d85",
      "bytes_at_merge": 7641,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "调研源报告：WeKnora 深度调研",
          "line": 1
        },
        {
          "heading": "WeKnora 竞争调研报告（所有来源均于 2026-10-08 实际抓取验证）",
          "line": 9
        },
        {
          "heading": "1. 项目基本面【已确认】",
          "line": 11
        },
        {
          "heading": "2. 架构与核心能力【已确认】",
          "line": 15
        },
        {
          "heading": "3. 产品化思路【已确认】",
          "line": 23
        },
        {
          "heading": "4. 商业化形态【已确认】",
          "line": 26
        },
        {
          "heading": "5. 与 Agent 记忆的差异与融合【已确认】",
          "line": 30
        },
        {
          "heading": "6. 可借鉴点 Top 5",
          "line": 33
        }
      ],
      "explicit_urls_as_authored": [],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-102",
      "kind": "research_report",
      "path": "evidence/source-aliyun-contextdb.md",
      "sha256_at_merge": "d7843caa1ecc5e787068a8391a36dcdd90c8e30b5683ec8da7e64ebc60b924cc",
      "bytes_at_merge": 6314,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "调研源报告：阿里云 Agent 记忆/上下文管理产品布局",
          "line": 1
        },
        {
          "heading": "阿里云 Agent 记忆/上下文管理产品布局调研（2026-10-08，均于当日访问实测抓取）",
          "line": 9
        },
        {
          "heading": "一、RDS ContextDB 现状【已确认，官方文档】",
          "line": 11
        },
        {
          "heading": "二、百炼记忆能力【已确认，官方文档】",
          "line": 20
        },
        {
          "heading": "三、开源布局【已确认，GitHub 实测】",
          "line": 25
        },
        {
          "heading": "四、商业化打法",
          "line": 32
        },
        {
          "heading": "五、对华为云 ContextDB 的威胁点",
          "line": 36
        },
        {
          "heading": "最值得学习的 3 点",
          "line": 43
        }
      ],
      "explicit_urls_as_authored": [
        "https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start",
        "https://www.aliyun.com/activity/database/contextdb",
        "https://www.alibabacloud.com/help/en/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start",
        "https://docs.bailian.console.aliyun.com/zh/model-studio/memory/billing.md",
        "https://www.aliyun.com/activity/database/rdsclaw"
      ],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-103",
      "kind": "research_report",
      "path": "evidence/source-tencent-volc.md",
      "sha256_at_merge": "e738cca31b83bb043f77d10f8ecbe27773ab92b4db4a4a7f93161b8e88a5fac2",
      "bytes_at_merge": 6587,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "调研源报告：腾讯云与火山引擎 Agent 记忆/上下文管理产品布局",
          "line": 1
        },
        {
          "heading": "腾讯云 vs 火山引擎：Agent 记忆/上下文管理产品布局调研（2026 下半年）",
          "line": 9
        },
        {
          "heading": "一、火山引擎：OpenViking Context 已正式商用",
          "line": 13
        },
        {
          "heading": "二、腾讯云：双开源 + 平台内嵌，尚无托管记忆服务",
          "line": 23
        },
        {
          "heading": "三、华为云防御点与总结",
          "line": 30
        }
      ],
      "explicit_urls_as_authored": [
        "https://www.volcengine.com/product/openviking-service（页面标题\"火山引擎",
        "https://docs.volcengine.com/docs/84313/2374478（更新于",
        "https://docs.volcengine.com/docs/vector_database_vikingdb/Releasenotes-14",
        "https://www.volcengine.com/docs/84313/billing-instructions"
      ],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-104",
      "kind": "research_report",
      "path": "evidence/source-aws-google.md",
      "sha256_at_merge": "7bc1faf97868664a6c9b599ff624143e4aebe2b18d0dff6fcb7bfa83f7d2dc97",
      "bytes_at_merge": 9522,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "调研源报告：国际云厂商 Agent 记忆托管服务（AWS/Google/Anthropic/OpenAI）",
          "line": 1
        },
        {
          "heading": "国际云厂商 Agent 记忆托管服务竞品调研（2026-10-08）",
          "line": 9
        },
        {
          "heading": "一、AWS Bedrock AgentCore Memory",
          "line": 13
        },
        {
          "heading": "二、Google：Gemini Enterprise Agent Platform Memory Bank",
          "line": 25
        },
        {
          "heading": "三、Anthropic：不做托管服务，给 client-side 工具",
          "line": 37
        },
        {
          "heading": "四、OpenAI：记忆是产品功能，不是 API",
          "line": 45
        },
        {
          "heading": "五、对比与对 ContextDB 的 5 条启示",
          "line": 49
        }
      ],
      "explicit_urls_as_authored": [
        "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html",
        "https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_Operations.html",
        "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html",
        "https://aws.amazon.com/bedrock/agentcore/pricing/",
        "https://docs.cloud.google.com/gemini-enterprise-agent-platform/vertex-ai-name-changes",
        "https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank",
        "https://cloud.google.com/products/gemini-enterprise-agent-platform/pricing",
        "https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool",
        "https://code.claude.com/docs/en/memory",
        "https://claude.com/blog/memory",
        "https://openai.com/index/memory-and-new-controls-for-chatgpt/",
        "https://developers.openai.com/api/docs/llms.txt",
        "https://developers.openai.com/api/docs/guides/conversation-state"
      ],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-105",
      "kind": "research_report",
      "path": "evidence/source-opensource-landscape.md",
      "sha256_at_merge": "544ec8c2d4a696e332a8d3bebc37c6c71c77b0c5fdf5f7aaab0c74fcd7693696",
      "bytes_at_merge": 8306,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "调研源报告：开源 Agent 记忆产品全景（Mem0/Zep/Letta/Cognee/MemOS/A-MEM/Hindsight）",
          "line": 1
        },
        {
          "heading": "开源 Agent 记忆产品格局调研（截至 2026-10-08，所有数据当日实抓）",
          "line": 9
        },
        {
          "heading": "一、数据刷新【已确认】（GitHub API，2026-10-08）",
          "line": 11
        },
        {
          "heading": "二、2026 下半年关键动作【已确认=官方博客/仓库；官方宣传单独标注】",
          "line": 25
        },
        {
          "heading": "三、商业模型对比【已确认】（定价页实抓）",
          "line": 33
        },
        {
          "heading": "四、Hindsight 其他动态【已确认】",
          "line": 42
        },
        {
          "heading": "五、云厂商自研 vs 采用开源【已确认】",
          "line": 46
        },
        {
          "heading": "(a) 商业模式光谱表",
          "line": 53
        },
        {
          "heading": "(b) 对华为云\"核心开源+商业增值\"的 4 条启示【推断，基于上述证据】",
          "line": 65
        }
      ],
      "explicit_urls_as_authored": [],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-106",
      "kind": "research_report",
      "path": "evidence/source-papers-survey.md",
      "sha256_at_merge": "49b90b9bac2c8eabb4855fb9639b67c431145b651f5d58928de50f2aca40ffb8",
      "bytes_at_merge": 9455,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "调研源报告：Agent 记忆机制论文证据",
          "line": 1
        },
        {
          "heading": "Agent 记忆机制：论文证据与产品化依据（2023-2026）",
          "line": 9
        },
        {
          "heading": "一、记忆系统论文（均经 arxiv.org/abs 页面核验）",
          "line": 11
        },
        {
          "heading": "二、检索增强记忆",
          "line": 23
        },
        {
          "heading": "三、评测基准",
          "line": 29
        },
        {
          "heading": "四、记忆巩固与\"睡眠\"机制",
          "line": 35
        },
        {
          "heading": "五、上下文工程共识",
          "line": 39
        },
        {
          "heading": "六、Top 8 可产品化记忆机制（按论文证据强度排序）",
          "line": 43
        }
      ],
      "explicit_urls_as_authored": [
        "https://arxiv.org/abs/2310.08560",
        "https://arxiv.org/abs/2504.19413",
        "https://arxiv.org/abs/2502.12110",
        "https://arxiv.org/abs/2507.03724",
        "https://arxiv.org/abs/2501.13956",
        "https://arxiv.org/abs/2405.14831",
        "https://arxiv.org/abs/2502.14802",
        "https://arxiv.org/abs/2401.18059",
        "https://arxiv.org/abs/2402.17753",
        "https://arxiv.org/abs/2410.10813",
        "https://arxiv.org/abs/2304.03442",
        "https://arxiv.org/abs/2504.13171",
        "https://arxiv.org/abs/2512.12818",
        "https://arxiv.org/abs/2507.13334"
      ],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-107",
      "kind": "previous_review",
      "path": "evidence/review-concrete-capabilities.md",
      "sha256_at_merge": "d0caaeef0f705b63d7545709c7def0f591a235fef565bb42d1e675c06832d473",
      "bytes_at_merge": 5100,
      "recorded_at": "2026-10-08",
      "verification": "previous_turn_review",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "本轮检视：具体能力与证据纠错",
          "line": 1
        },
        {
          "heading": "1. 本轮外部核验",
          "line": 7
        },
        {
          "heading": "2. 本地交叉检视与推理纠错",
          "line": 29
        },
        {
          "heading": "3. 实施及发布前待关闭",
          "line": 47
        }
      ],
      "explicit_urls_as_authored": [
        "https://support.huaweicloud.com/usermanual-rds-pg/rds_09_0065.html",
        "https://support.huaweicloud.com/intl/en-us/usermanual-rds-pg/rds_pg_05_0025.html",
        "https://support.huaweicloud.com/rds_faq/rds-faq.pdf",
        "https://support.huaweicloud.com/usermanual-rds-mysql/rds_08_0050.html",
        "https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start",
        "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-types.html",
        "https://www.huaweicloud.com/product/pg.html"
      ],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-108",
      "kind": "research_report",
      "path": "evidence/sources-index.md",
      "sha256_at_merge": "8fa032b234db88b70a7b894b41f261d609f845da860bb5abea84fba01de972a4",
      "bytes_at_merge": 3961,
      "recorded_at": "2026-10-08",
      "verification": "imported_report_not_reverified",
      "snapshot_type": "local_analysis_or_report_not_original_web_capture",
      "sections": [
        {
          "heading": "来源索引",
          "line": 1
        },
        {
          "heading": "原始源报告（本目录）",
          "line": 5
        },
        {
          "heading": "按主题的关键来源",
          "line": 18
        }
      ],
      "explicit_urls_as_authored": [],
      "limitations": "来源报告中的已确认标签不是本轮复核；正文快照缺失时不得视为原网页存档。"
    },
    {
      "id": "SRC-109",
      "kind": "local_baseline",
      "path": "../backend-storage.md",
      "scope": "当前本地 english/bge-m3/search_vector 存储记录",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-110",
      "kind": "local_baseline",
      "path": "../hindsight-cloud-open-source-comparison.md",
      "scope": "2026-10-07 Cloud/开源接口实测对比；0.10.2，源码 f7dd3f4fd7420f7beec60c32c965e5e5cf7be066",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-111",
      "kind": "local_baseline",
      "path": "../Hindsight Architecture.md",
      "scope": "Cell/扩展点/PG 队列架构",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-112",
      "kind": "local_baseline",
      "path": "../scheme3-prototype-design.md",
      "scope": "多 Cell 原型设计与证据纪律",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-113",
      "kind": "local_baseline",
      "path": "../cloud-service-architecture.md",
      "scope": "云产品设计、知识晋升/撤回",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-114",
      "kind": "local_baseline",
      "path": "../contextdb-high-level-design.md",
      "scope": "context/query 与计量设计",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-115",
      "kind": "local_baseline",
      "path": "../contextdb-design-expert-review.md",
      "scope": "既有交期/设计评审输入",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-116",
      "kind": "local_baseline",
      "path": "../cloud-service-priorities.md",
      "scope": "原产品差异化假设",
      "version": "见各原文",
      "verification": "referenced_local_record",
      "sha256_at_merge": null,
      "limitations": "未在本次合并重新验证部署或接口；不是商用验收。"
    },
    {
      "id": "SRC-201",
      "kind": "official_web_reference",
      "url": "https://support.huaweicloud.com/intl/en-us/usermanual-rds-pg/rds_pg_05_0025.html",
      "title": "RDS PG 磁盘加密",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_full_text",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-202",
      "kind": "official_web_reference",
      "url": "https://support.huaweicloud.com/usermanual-rds-pg/rds_09_0065.html",
      "title": "RDS zhparser",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_search_text",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-203",
      "kind": "official_web_reference",
      "url": "https://support.huaweicloud.com/rds_faq/rds-faq.pdf",
      "title": "历史 RDS FAQ",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_search_index",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-204",
      "kind": "official_web_reference",
      "url": "https://support.huaweicloud.com/usermanual-rds-mysql/rds_08_0050.html",
      "title": "MySQL 备份加密，仅辨别引擎范围",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_search_text",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-205",
      "kind": "official_web_reference",
      "url": "https://help.aliyun.com/zh/rds/apsaradb-rds-for-mysql/rds-contextdb-quick-start",
      "title": "阿里 ContextDB",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_search_index_body_mismatch",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-206",
      "kind": "official_web_reference",
      "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-types.html",
      "title": "AWS 短/长期记忆和 metadata",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_page_and_pdf_index",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-207",
      "kind": "official_web_reference",
      "url": "https://www.huaweicloud.com/product/pg.html",
      "title": "RDS HA/副本",
      "recorded_access_date": "2026-10-08",
      "verification": "previous_review_product_page",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-208",
      "kind": "official_web_reference",
      "url": "https://docs.volcengine.com/docs/84313/billing-instructions",
      "title": "火山计费",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report_latest_fetch_failed",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-209",
      "kind": "official_web_reference",
      "url": "https://aws.amazon.com/bedrock/agentcore/pricing/",
      "title": "AWS 价格",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-210",
      "kind": "official_web_reference",
      "url": "https://cloud.google.com/products/gemini-enterprise-agent-platform/pricing",
      "title": "Google 价格",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-211",
      "kind": "official_web_reference",
      "url": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool",
      "title": "Claude memory tool",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-212",
      "kind": "official_web_reference",
      "url": "https://vectorize.io/pricing",
      "title": "Hindsight 价格",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-213",
      "kind": "official_web_reference",
      "url": "https://benchmarks.hindsight.vectorize.io",
      "title": "Hindsight 作者榜单",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-214",
      "kind": "official_web_reference",
      "url": "https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale/memory-bank",
      "title": "Google Memory Bank",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-215",
      "kind": "official_web_reference",
      "url": "https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_Operations.html",
      "title": "AWS API",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-216",
      "kind": "official_web_reference",
      "url": "https://github.com/Tencent/WeKnora",
      "title": "WeKnora 仓库",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-217",
      "kind": "official_web_reference",
      "url": "https://github.com/volcengine/OpenViking",
      "title": "OpenViking 仓库",
      "recorded_access_date": "2026-10-08",
      "verification": "imported_report",
      "snapshot_path": null,
      "limitations": "合并时未重新访问；URL 不是原文快照。确认范围按 evidence 记录，变化风险在发布前复核。"
    },
    {
      "id": "SRC-301",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2310.08560",
      "title": "MemGPT",
      "mechanism": "虚拟上下文/分层管理",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-302",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2504.19413",
      "title": "Mem0",
      "mechanism": "抽取/巩固/检索，图记忆",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-303",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2502.12110",
      "title": "A-MEM",
      "mechanism": "动态笔记与演化",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-304",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2507.03724",
      "title": "MemOS",
      "mechanism": "MemCube 与统一资产",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-305",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2501.13956",
      "title": "Zep/Graphiti",
      "mechanism": "双时间与事实演化",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-306",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2405.14831",
      "title": "HippoRAG",
      "mechanism": "图与 Personalized PageRank",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-307",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2502.14802",
      "title": "HippoRAG 2",
      "mechanism": "关联记忆与检索",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-308",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2401.18059",
      "title": "RAPTOR",
      "mechanism": "分层摘要树",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-309",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2402.17753",
      "title": "LoCoMo",
      "mechanism": "长对话评测，有标注争议",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-310",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2410.10813",
      "title": "LongMemEval",
      "mechanism": "抽取/多轮/时序/更新/拒答五维",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-311",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2304.03442",
      "title": "Generative Agents",
      "mechanism": "reflection 消融",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-312",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2504.13171",
      "title": "Sleep-time Compute",
      "mechanism": "离线预计算",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-313",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2512.12818",
      "title": "Hindsight",
      "mechanism": "retain/recall/reflect 与巩固",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    },
    {
      "id": "SRC-314",
      "kind": "paper",
      "url": "https://arxiv.org/abs/2507.13334",
      "title": "Context Engineering survey",
      "mechanism": "上下文工程综述",
      "verification": "imported_author_report",
      "snapshot_path": null,
      "report_source_id": "SRC-106",
      "limitations": "原材料中的作者实验，未在本轮核对论文全文/复跑；不作华为性能承诺。"
    }
  ],
  "evidence": [
    {
      "id": "EV-001",
      "revision": 1,
      "kind": "fact_record",
      "claim": "RDS PG 官方列出 DEW 管理的磁盘加密、AES_256/SM4 及操作约束",
      "current_status": "official_doc_previous_review",
      "scope": "RDS PG 底座，不是产品全链路",
      "source_ids": [
        "SRC-201",
        "SRC-107"
      ],
      "locator": "检视记录§1：PG 磁盘加密",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "未做实际 Cell 配置或密钥/恢复实验",
      "capability_ids": [
        "A1",
        "A2"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-002",
      "revision": 1,
      "kind": "inference",
      "claim": "磁盘加密不能直接证明 MetaPG、OBS、日志、缓存和模型链路保护，也不等于密评通过",
      "current_status": "derived_boundary",
      "scope": "保护覆盖与认证分别验收",
      "source_ids": [
        "SRC-201",
        "SRC-107",
        "SRC-006"
      ],
      "locator": "具体竞争力原稿§2",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "保护范围按各对象配置；不能推导端到端加密",
      "capability_ids": [
        "A1"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-003",
      "revision": 1,
      "kind": "fact_record",
      "claim": "PG 备份默认行为存在历史文档/版本口径差异；密钥失效警示不能解释为加密备份一律不可恢复",
      "current_status": "conflicting_docs",
      "scope": "目标 PG 区域与版本",
      "source_ids": [
        "SRC-201",
        "SRC-203",
        "SRC-204",
        "SRC-107"
      ],
      "locator": "检视记录§1：PG 备份加密/备份恢复警示",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "需目标实例/官方确认及恢复演练；MySQL 限制不能套 PG",
      "capability_ids": [
        "A1",
        "A2",
        "C1"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-004",
      "revision": 1,
      "kind": "fact_record",
      "claim": "阿里快速入门官方搜索索引列记忆与知识库导出限制，打开正文未取得同段",
      "current_status": "search_index_only",
      "scope": "阿里 RDS ContextDB 的导出，不涉及删除/审计",
      "source_ids": [
        "SRC-205",
        "SRC-102",
        "SRC-107"
      ],
      "locator": "检视记录§1：阿里导出；源报告§一",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "发布前保存正文快照；不能称永久限制",
      "capability_ids": [
        "D1"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-005",
      "revision": 1,
      "kind": "fact_record",
      "claim": "华为 RDS 已有 zhparser 官方说明，可查询目标实例扩展版本",
      "current_status": "official_doc_previous_review",
      "scope": "RDS 插件支持",
      "source_ids": [
        "SRC-202",
        "SRC-107"
      ],
      "locator": "检视记录§1：zhparser",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "目标区域/版本及应用接口仍待验",
      "capability_ids": [
        "B1"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-006",
      "revision": 1,
      "kind": "fact_record",
      "claim": "当前本地 PG 查询使用 english，search_vector 由应用写入计算",
      "current_status": "local_inspection_record",
      "scope": "当前本地配置/所核源码路径",
      "source_ids": [
        "SRC-109",
        "SRC-107"
      ],
      "locator": "backend-storage.md §3.3",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "不可推断所有 Hindsight 后端；写入/查询统一配置并重建",
      "capability_ids": [
        "B1"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-007",
      "revision": 1,
      "kind": "inference",
      "claim": "CMK 与导入密钥材料 BYOK 不同；卷密钥按实例，禁用不等于即时删除所有副本",
      "current_status": "derived_boundary",
      "scope": "当前共享/独享 Cell 方案",
      "source_ids": [
        "SRC-201",
        "SRC-111",
        "SRC-107"
      ],
      "locator": "检视记录§2：BYOK/禁用即删除、OBS 三隔离",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "跨账号/材料导入/缓存与备份处理待验",
      "capability_ids": [
        "A2",
        "A3",
        "D4"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-008",
      "revision": 1,
      "kind": "fact_record",
      "claim": "本地 Cloud/开源接口比较记录部分文档导入导出、Cloud 主体导出/删除/回执；未证明 Workspace 全资产合同",
      "current_status": "local_inspection_record",
      "scope": "0.10.2 的接口记录",
      "source_ids": [
        "SRC-110",
        "SRC-107"
      ],
      "locator": "Cloud 对比§3.1–3.2/3.5",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "接口存在不等于所有功能可用；全量/快照/恢复需验",
      "capability_ids": [
        "D1",
        "D4"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-009",
      "revision": 1,
      "kind": "fact_record",
      "claim": "bge-m3/1024 维是本地部署选择，不是所有部署的通用默认",
      "current_status": "local_inspection_record",
      "scope": "当前本地 embedding",
      "source_ids": [
        "SRC-109",
        "SRC-107"
      ],
      "locator": "backend-storage.md §3.2/配置表",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "中文检索与抽取/回答需分别实测",
      "capability_ids": [
        "B1",
        "B3"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-010",
      "revision": 1,
      "kind": "fact_record",
      "claim": "阿里原报告记录记忆晋升、审批、知识评审与同步、CLI/MCP 接入",
      "current_status": "imported_report",
      "scope": "阿里各产品线分别比较",
      "source_ids": [
        "SRC-102",
        "SRC-003",
        "SRC-205"
      ],
      "locator": "阿里源报告§一–三",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "合并未全面刷新；治理对象不是全产品统一",
      "capability_ids": [
        "D2",
        "D3",
        "X-MCP"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-011",
      "revision": 1,
      "kind": "fact_record",
      "claim": "WeKnora 原报告记录推断确认、拒绝抑制、JSON 导出与记忆参与检索",
      "current_status": "imported_report",
      "scope": "WeKnora 开源侧",
      "source_ids": [
        "SRC-101",
        "SRC-002",
        "SRC-216"
      ],
      "locator": "WeKnora 原报告§5；原主稿§6–7",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "不能自动证明所有托管服务缺此能力",
      "capability_ids": [
        "D1",
        "D3",
        "X-MEMORY-RETRIEVAL"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-012",
      "revision": 1,
      "kind": "fact_record",
      "claim": "WeKnora 原报告有来源区分、人工版本保护、FAQ/评估/解析运营与数据源同步",
      "current_status": "imported_report",
      "scope": "知识/Wiki/运营侧",
      "source_ids": [
        "SRC-101",
        "SRC-002"
      ],
      "locator": "WeKnora 原报告§3",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "不能直接变成 ContextDB 已有记忆血缘",
      "capability_ids": [
        "D2",
        "X-KNOWLEDGE-OPS"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-013",
      "revision": 1,
      "kind": "fact_record",
      "claim": "Hindsight 有租户/操作/HTTP/MCP 扩展点，Cell 接固定 PG；PG 队列无需先引入另一任务引擎",
      "current_status": "local_inspection_record",
      "scope": "本地架构与原型设计",
      "source_ids": [
        "SRC-111",
        "SRC-112",
        "SRC-110"
      ],
      "locator": "Hindsight Architecture 的扩展点和任务队列段落",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "请求级 hook 不足以证明治理候选过滤，必要适配待查",
      "capability_ids": [
        "A3",
        "A4",
        "D3",
        "X-HA"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-014",
      "revision": 1,
      "kind": "inference",
      "claim": "SQL 账号和 CTS 不能自动还原记忆业务操作者；PITR 实例恢复不等于 Workspace 回滚",
      "current_status": "derived_boundary",
      "scope": "业务审计/租户恢复",
      "source_ids": [
        "SRC-107",
        "SRC-005",
        "SRC-006"
      ],
      "locator": "检视记录§2：SQL/CTS、PITR",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "需业务 request_id 与隔离提取、附件/删除清单处理",
      "capability_ids": [
        "A4",
        "C1"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-015",
      "revision": 1,
      "kind": "fact_record",
      "claim": "Cloud 原型接口有主体删除/隐私回执先例，逐条删除不证明派生数据和备份已全清",
      "current_status": "local_inspection_record",
      "scope": "主体删除范围",
      "source_ids": [
        "SRC-110",
        "SRC-107"
      ],
      "locator": "Cloud 对比§3.2；检视记录§3",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "开源范围、任务重生成及备份期限待验",
      "capability_ids": [
        "D4"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-016",
      "revision": 1,
      "kind": "fact_record",
      "claim": "火山原报告包含同内核托管、分层文件、生态计费及企业版独占实例",
      "current_status": "imported_report",
      "scope": "OpenViking/OpenViking Context 分开",
      "source_ids": [
        "SRC-103",
        "SRC-208",
        "SRC-217"
      ],
      "locator": "腾讯/火山源报告§一",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "最新外部正文读取失败，SKU/区域/许可需复核；撤回全共享",
      "capability_ids": [
        "X-HA",
        "X-ECOSYSTEM"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-017",
      "revision": 1,
      "kind": "fact_record",
      "claim": "腾讯原报告描述 WeKnora/Agent Memory/ADP 多线，L0–L3 与微信生态；未见独立托管记忆计划",
      "current_status": "imported_report",
      "scope": "报告搜索范围内未发现，不是不存在",
      "source_ids": [
        "SRC-103",
        "SRC-101"
      ],
      "locator": "腾讯/火山源报告§二",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "不能推断全集团无相关产品或永久免费",
      "capability_ids": [
        "X-ECOSYSTEM"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-018",
      "revision": 1,
      "kind": "fact_record",
      "claim": "AWS 原报告记录双平面、事件/记忆记录、多种策略、客户密钥、TTL 与三档抽取模式",
      "current_status": "imported_report",
      "scope": "AgentCore Memory",
      "source_ids": [
        "SRC-104",
        "SRC-215",
        "SRC-209"
      ],
      "locator": "AWS/Google 源报告§一",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "定价和 API 本轮未重新抓取；metadata 覆盖另见 EV-019",
      "capability_ids": [
        "A2",
        "X-COST"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-019",
      "revision": 1,
      "kind": "fact_record",
      "claim": "AWS 文档索引/页面提示短期事件 metadata 不在客户管理密钥保护范围",
      "current_status": "official_doc_previous_review",
      "scope": "短期事件 CMK 覆盖，不是无加密",
      "source_ids": [
        "SRC-206",
        "SRC-107"
      ],
      "locator": "检视记录§1：AWS metadata",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "不能推广到所有元数据或服务安全优劣",
      "capability_ids": [
        "A1",
        "A2"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-020",
      "revision": 1,
      "kind": "fact_record",
      "claim": "各家榜单与自报分数条件不同，Hindsight 作者成绩不代表华为服务成绩",
      "current_status": "research_author_report",
      "scope": "版本/模型/预算/数据集固定才可比",
      "source_ids": [
        "SRC-004",
        "SRC-106",
        "SRC-213"
      ],
      "locator": "学术主稿§1/§4",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "原独立复现没有报告/脚本，不作背书；见 DEC-004/DEC-014",
      "capability_ids": [
        "B3",
        "X-EVAL"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-021",
      "revision": 1,
      "kind": "fact_record",
      "claim": "LongMemEval 五维和 LoCoMo 的争议可作为质量评测设计输入",
      "current_status": "research_author_report",
      "scope": "研究方法而非中文标准",
      "source_ids": [
        "SRC-310",
        "SRC-309",
        "SRC-106"
      ],
      "locator": "学术原稿§1.3/§4",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "英文指标不能代替中文验证，自建集要声明采样",
      "capability_ids": [
        "B3",
        "X-EVAL"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-022",
      "revision": 1,
      "kind": "fact_record",
      "claim": "Hindsight 论文/原材料描述 retain/recall/reflect、四逻辑网络和后台 observations 巩固",
      "current_status": "research_author_report",
      "scope": "上游研究与内核",
      "source_ids": [
        "SRC-313",
        "SRC-106",
        "SRC-111"
      ],
      "locator": "学术原稿§1.1",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "产品观测/权限/治理需新增，不是独有创新",
      "capability_ids": [
        "D2",
        "X-CONSOLIDATION"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-023",
      "revision": 1,
      "kind": "fact_record",
      "claim": "Generative Agents/Sleep-time Compute 提供反思和离线预计算研究依据",
      "current_status": "research_author_report",
      "scope": "研究机制",
      "source_ids": [
        "SRC-311",
        "SRC-312",
        "SRC-106"
      ],
      "locator": "学术原稿§1.2",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "作者数字不作成本降幅承诺",
      "capability_ids": [
        "X-CONSOLIDATION"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-024",
      "revision": 1,
      "kind": "fact_record",
      "claim": "HippoRAG/2 与 Zep 提供 PPR 关联检索、时序演化的研究依据",
      "current_status": "research_author_report",
      "scope": "候选研究优化",
      "source_ids": [
        "SRC-306",
        "SRC-307",
        "SRC-305",
        "SRC-106"
      ],
      "locator": "学术原稿§2–3",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "PG 有实体图不证明新增 PPR 已实现",
      "capability_ids": [
        "X-TEMPORAL-GRAPH"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-025",
      "revision": 1,
      "kind": "fact_record",
      "claim": "MemGPT/RAPTOR/Mem0/MemOS/A-MEM 提供分层管理、摘要、记忆包、笔记演化输入",
      "current_status": "research_author_report",
      "scope": "候选机制",
      "source_ids": [
        "SRC-301",
        "SRC-308",
        "SRC-302",
        "SRC-304",
        "SRC-303",
        "SRC-106"
      ],
      "locator": "学术原稿§2–3",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "不合并不同论文成绩为统一产品指标",
      "capability_ids": [
        "X-RESEARCH"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-026",
      "revision": 1,
      "kind": "fact_record",
      "claim": "Google 原报告记录 scope、fact、consolidation、revision/TTL、IAM/CMEK 与投毒提示",
      "current_status": "imported_report",
      "scope": "Memory Bank",
      "source_ids": [
        "SRC-104",
        "SRC-214",
        "SRC-210"
      ],
      "locator": "AWS/Google 源报告§二",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "产品名称/模型/端点限制未在合并时刷新",
      "capability_ids": [
        "D2",
        "D3",
        "X-COST",
        "X-REGION"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-027",
      "revision": 1,
      "kind": "fact_record",
      "claim": "Anthropic memory tool 是客户端存储协议，六命令适配是候选接入方向",
      "current_status": "imported_report",
      "scope": "文件语义与客户端责任",
      "source_ids": [
        "SRC-104",
        "SRC-211"
      ],
      "locator": "AWS/Google 源报告§三",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "路径安全、版本、权限、rename/编辑语义需验，不保证简单映射",
      "capability_ids": [
        "X-MCP"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-028",
      "revision": 1,
      "kind": "fact_record",
      "claim": "开源商业样本包含 Mem0/Zep/Cognee/Hindsight 的托管增值，Letta 转型等历史动态",
      "current_status": "imported_report",
      "scope": "原报告所列项目，非全行业",
      "source_ids": [
        "SRC-105",
        "SRC-003",
        "SRC-212"
      ],
      "locator": "开源源报告§二–五",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "许可不等于性能优势；转型不证明独立记忆商业化必失败",
      "capability_ids": [
        "X-ECOSYSTEM",
        "X-COST"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-029",
      "revision": 1,
      "kind": "fact_record",
      "claim": "RDS 官方产品页有 HA、同步提交、只读扩展；不能直接套 ContextDB SLA",
      "current_status": "official_doc_previous_review",
      "scope": "数据库底座",
      "source_ids": [
        "SRC-207",
        "SRC-107"
      ],
      "locator": "检视记录§1：RDS HA",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "需 API/Worker/网关/模型全链路演练",
      "capability_ids": [
        "C1",
        "X-HA",
        "X-REPLICA"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    },
    {
      "id": "EV-030",
      "revision": 1,
      "kind": "fact_record",
      "claim": "原报告保留价格、版本、star、OpenAI/Claude 产品说明及云厂采用开源观察",
      "current_status": "imported_report",
      "scope": "2026-10-08 原材料历史快照",
      "source_ids": [
        "SRC-103",
        "SRC-104",
        "SRC-105",
        "SRC-106"
      ],
      "locator": "各报告全文及 historical_tables",
      "verification": {
        "recorded_at": "2026-10-08",
        "performed_in": "previous_review_or_imported_research",
        "reverified_during_merge": false
      },
      "limitations": "本轮未全面复核；索引缺项不能证明产品不存在，行业结论需谨慎",
      "capability_ids": [
        "X-ECOSYSTEM",
        "X-COST"
      ],
      "checked_at": "2026-10-08",
      "snapshot_path": null
    }
  ],
  "assertion_history": [
    {
      "id": "EV-H01",
      "revision": 1,
      "claim": "PG备份默认不加密",
      "status": "superseded",
      "recorded_at": "2026-10-08",
      "source_ids": [
        "SRC-107"
      ],
      "origin": "prior_session_claim_preserved_in_review",
      "snapshot_path": null,
      "limitations": "旧整稿未另存，只保存已记录的旧断言"
    },
    {
      "id": "EV-H01",
      "revision": 2,
      "claim": "目标版本待验，撤回确定判断",
      "status": "conflicting_docs",
      "recorded_at": "2026-10-08",
      "supersedes": {
        "id": "EV-H01",
        "revision": 1
      },
      "evidence_ids": [
        "EV-003"
      ],
      "source_ids": [
        "SRC-107"
      ]
    },
    {
      "id": "EV-H02",
      "revision": 1,
      "claim": "火山个人和企业全共享",
      "status": "superseded",
      "recorded_at": "2026-10-08",
      "source_ids": [
        "SRC-107"
      ],
      "origin": "prior_session_claim_preserved_in_review",
      "snapshot_path": null,
      "limitations": "旧整稿未另存，只保存已记录的旧断言"
    },
    {
      "id": "EV-H02",
      "revision": 2,
      "claim": "原报告企业独占，现行SKU待核验",
      "status": "imported_report",
      "recorded_at": "2026-10-08",
      "supersedes": {
        "id": "EV-H02",
        "revision": 1
      },
      "evidence_ids": [
        "EV-016"
      ],
      "source_ids": [
        "SRC-107"
      ]
    },
    {
      "id": "EV-H03",
      "revision": 1,
      "claim": "VT/媒体独立复现已确认",
      "status": "superseded",
      "recorded_at": "2026-10-08",
      "source_ids": [
        "SRC-107"
      ],
      "origin": "prior_session_claim_preserved_in_review",
      "snapshot_path": null,
      "limitations": "旧整稿未另存，只保存已记录的旧断言"
    },
    {
      "id": "EV-H03",
      "revision": 2,
      "claim": "缺实验报告/脚本，不作背书",
      "status": "unverified",
      "recorded_at": "2026-10-08",
      "supersedes": {
        "id": "EV-H03",
        "revision": 1
      },
      "evidence_ids": [
        "EV-020"
      ],
      "source_ids": [
        "SRC-107"
      ]
    },
    {
      "id": "EV-H04",
      "revision": 1,
      "claim": "六方全闭源无评测",
      "status": "superseded",
      "recorded_at": "2026-10-08",
      "source_ids": [
        "SRC-107"
      ],
      "origin": "prior_session_claim_preserved_in_review",
      "snapshot_path": null,
      "limitations": "旧整稿未另存，只保存已记录的旧断言"
    },
    {
      "id": "EV-H04",
      "revision": 2,
      "claim": "所列样本有反例，撤回全集判断",
      "status": "retracted",
      "recorded_at": "2026-10-08",
      "supersedes": {
        "id": "EV-H04",
        "revision": 1
      },
      "evidence_ids": [
        "EV-028"
      ],
      "source_ids": [
        "SRC-107"
      ]
    },
    {
      "id": "EV-H05",
      "revision": 1,
      "claim": "不可导出所以不可审计删除",
      "status": "superseded",
      "recorded_at": "2026-10-08",
      "source_ids": [
        "SRC-107"
      ],
      "origin": "prior_session_claim_preserved_in_review",
      "snapshot_path": null,
      "limitations": "旧整稿未另存，只保存已记录的旧断言"
    },
    {
      "id": "EV-H05",
      "revision": 2,
      "claim": "独立核验三类能力",
      "status": "retracted",
      "recorded_at": "2026-10-08",
      "supersedes": {
        "id": "EV-H05",
        "revision": 1
      },
      "evidence_ids": [
        "EV-015"
      ],
      "source_ids": [
        "SRC-107"
      ]
    },
    {
      "id": "EV-H06",
      "revision": 1,
      "claim": "bge-m3是统一默认",
      "status": "superseded",
      "recorded_at": "2026-10-08",
      "source_ids": [
        "SRC-107"
      ],
      "origin": "prior_session_claim_preserved_in_review",
      "snapshot_path": null,
      "limitations": "旧整稿未另存，只保存已记录的旧断言"
    },
    {
      "id": "EV-H06",
      "revision": 2,
      "claim": "只确认本地模型选择",
      "status": "local_inspection_record",
      "recorded_at": "2026-10-08",
      "supersedes": {
        "id": "EV-H06",
        "revision": 1
      },
      "evidence_ids": [
        "EV-009"
      ],
      "source_ids": [
        "SRC-107"
      ]
    }
  ],
  "capabilities": [
    {
      "id": "A1",
      "legacy_id": "A1",
      "description": "数据库磁盘加密；附件、备份和导出包分别管理加密策略",
      "customer_value": "保护会话和组织知识",
      "implementation": {
        "record": "RDS 底座支持；自动开通与覆盖检查拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "基础能力，完整覆盖是交付优势",
      "priority": "P0",
      "evidence_ids": [
        "EV-001",
        "EV-002",
        "EV-003",
        "EV-019"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.1",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "A2",
      "legacy_id": "A2",
      "description": "独享版绑定客户管理密钥，显示密钥标识与授权状态",
      "customer_value": "客户控制密钥权限",
      "implementation": {
        "record": "RDS 支持自定义密钥；跨账号授权与恢复流程待验证",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "基础能力，政企选配",
      "priority": "P1",
      "evidence_ids": [
        "EV-001",
        "EV-003",
        "EV-007",
        "EV-018"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.1",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "D1",
      "legacy_id": "D1",
      "description": "按 Bank/知识库导出，Workspace 批量包采用公开格式",
      "customer_value": "保存资产、离云交接、迁移与审计",
      "implementation": {
        "record": "上游有部分文档导出接口；完整资产、快照及恢复拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "直接差异：阿里当前导出限制",
      "priority": "P0",
      "evidence_ids": [
        "EV-004",
        "EV-008",
        "EV-011"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.2",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "B1",
      "legacy_id": "B1",
      "description": "中文分词与向量混合召回",
      "customer_value": "找准连续中文中的专名与术语",
      "implementation": {
        "record": "RDS 已支持 zhparser；应用读写适配和历史重建拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "相对当前部署的候选差异；竞品效果待测",
      "priority": "P0",
      "evidence_ids": [
        "EV-005",
        "EV-006",
        "EV-009"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.3",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "B2",
      "legacy_id": "B2",
      "description": "企业术语/别名映射，如 PG/PostgreSQL",
      "customer_value": "减少同义表达漏检与错配",
      "implementation": {
        "record": "企业词表及查询扩展拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "候选差异",
      "priority": "P1",
      "evidence_ids": [
        "EV-005",
        "EV-009",
        "EV-021"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.3",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "B3",
      "legacy_id": "B3",
      "description": "中文抽取与更新质量门禁，覆盖否定、时间、身份、金额",
      "customer_value": "正确记住变化的中文事实",
      "implementation": {
        "record": "当前部署用 bge-m3；抽取/巩固/回答仍需分别评测",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "候选差异",
      "priority": "P0",
      "evidence_ids": [
        "EV-009",
        "EV-020",
        "EV-021"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.3",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "A3",
      "legacy_id": "A3",
      "description": "按 Workspace/Bank/知识库授权；导出单独授权",
      "customer_value": "控制 Agent 共享范围",
      "implementation": {
        "record": "上游有扩展点；云产品 ACL 和越权验证需完善",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "基础能力",
      "priority": "P0",
      "evidence_ids": [
        "EV-007",
        "EV-013"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §5",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "A4",
      "legacy_id": "A4",
      "description": "写入、检索、修改、删除、导出审计到成员/API Key",
      "customer_value": "追查谁修改、谁下载",
      "implementation": {
        "record": "底层 SQL/CTS 不够；业务审计拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "基础能力，业务可追溯是重点",
      "priority": "P0",
      "evidence_ids": [
        "EV-013",
        "EV-014"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §5",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "C1",
      "legacy_id": "C1",
      "description": "在保留窗口内恢复误删，按 Workspace 提取恢复",
      "customer_value": "数据资产可找回",
      "implementation": {
        "record": "RDS 备份/PITR 底座；隔离恢复与附件对齐拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "基础能力，租户级恢复是候选差异",
      "priority": "P0 演练 / P1 自助",
      "evidence_ids": [
        "EV-003",
        "EV-014",
        "EV-029"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §5",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "D2",
      "legacy_id": "D2",
      "description": "展示记忆来源，人工纠正保留历史",
      "customer_value": "判断依据、修正错误",
      "implementation": {
        "record": "上游有来源引用；完整血缘及人工版本保护拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "候选差异，竞品知识侧有先例",
      "priority": "P1",
      "evidence_ids": [
        "EV-012",
        "EV-022"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §5",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "D3",
      "legacy_id": "D3",
      "description": "可选“推断确认后可检索”，拒绝条目留抑制记录",
      "customer_value": "防止 AI 推断未经确认影响回答",
      "implementation": {
        "record": "WeKnora 有先例；状态及检索/后台链路过滤拟开发",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "对齐实践，云上差异待核验",
      "priority": "P1",
      "evidence_ids": [
        "EV-011",
        "EV-013",
        "EV-026"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §5",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "D4",
      "legacy_id": "D4",
      "description": "按主体删除并返回范围、执行回执及备份期限",
      "customer_value": "离职、撤回授权、清理敏感记录",
      "implementation": {
        "record": "Hindsight Cloud 有先例；开源覆盖及派生清理待验证",
        "status": "planned_or_pending_validation",
        "verified_commercial": false
      },
      "positioning": "对齐实践，可审计流程有价值",
      "priority": "P1",
      "evidence_ids": [
        "EV-008",
        "EV-015"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §5",
      "spec_source_ids": [
        "SRC-006",
        "SRC-005"
      ],
      "release_gate": "验收通过后才可宣称支持"
    },
    {
      "id": "X-EVAL",
      "title": "可复现评测",
      "scope": "中文质量门禁与固定版本/模型/预算评测，发布采样/标注/脚本和分维结果",
      "status": "candidate_not_verified",
      "priority": "initial_quality_gate_then_public_reproduction",
      "evidence_ids": ["EV-020", "EV-021"],
      "acceptance_locator": "ContextDB差异化竞争力.md §4.3"
    },
    {
      "id": "X-MEMORY-RETRIEVAL",
      "title": "记忆参与检索",
      "scope": "有权限记忆改写查询/排序，不扩大权限",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-011"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-KNOWLEDGE-OPS",
      "title": "知识运营",
      "scope": "人工保护/FAQ反例/解析观测/评估/数据源",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-012"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-CONSOLIDATION",
      "title": "巩固可观测",
      "scope": "产出/消耗/调度，收益实测",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-022"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-TEMPORAL-GRAPH",
      "title": "事实演化与PPR",
      "scope": "时序历史与多跳候选，未新增实现",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-024"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-RESEARCH",
      "title": "摘要/记忆包/笔记",
      "scope": "分层管理、MemCube、动态关联研究",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-025"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-REGION",
      "title": "地域/私网",
      "scope": "PG/OBS/备份/模型全链路验证",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-026"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-HA",
      "title": "HA与多Cell",
      "scope": "路由/扩容/重连/Worker幂等，SLA另测",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-029"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-REPLICA",
      "title": "副本检索",
      "scope": "验证写副作用/复制延迟/读后写",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-029"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-COST",
      "title": "成本/配额",
      "scope": "三操作/后台token/存储，超额与计量闭环",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-018"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-MCP",
      "title": "MCP/SDK/协议",
      "scope": "租户只读/scoped token/六命令，版本和语义测试",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-027"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-ECOSYSTEM",
      "title": "开源/生态",
      "scope": "差异表、客户端、华为产品与上游贡献",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-028"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    },
    {
      "id": "X-ARCHIVE",
      "title": "冷归档",
      "scope": "附件先行，测回源费/延迟/召回",
      "status": "candidate_not_verified",
      "priority": "after_initial_or_dependency_driven",
      "evidence_ids": [
        "EV-013"
      ],
      "acceptance_locator": "ContextDB差异化竞争力.md §6"
    }
  ],
  "decision_history": [
    {
      "id": "DEC-001",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 1,
      "title": "能力分层",
      "previous_statement": "底座支持等于产品实现/零开发",
      "current_statement": "底座/原型/产品/效果分开",
      "reason": "组件不是完整服务",
      "evidence_ids": [
        "EV-001"
      ],
      "capability_ids": [
        "A1"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-002",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 2,
      "title": "中文前置",
      "previous_statement": "等待zhparser白名单",
      "current_statement": "官方支持，实例/读写/重建待验",
      "reason": "前置已改变",
      "evidence_ids": [
        "EV-005"
      ],
      "capability_ids": [
        "B1"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-003",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 3,
      "title": "导出与迁移",
      "previous_statement": "部分导出=全量低成本迁移",
      "current_statement": "定义资产/快照；导入验收后称迁移",
      "reason": "接口不是资产合同",
      "evidence_ids": [
        "EV-008"
      ],
      "capability_ids": [
        "D1"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-004",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 4,
      "title": "效果与背书",
      "previous_statement": "上游分数/独立复现直接继承",
      "current_statement": "作者口径，华为另测，复现待证",
      "reason": "配置不同且缺报告",
      "evidence_ids": [
        "EV-020"
      ],
      "capability_ids": [
        "B3"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-005",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 5,
      "title": "密钥语义",
      "previous_statement": "BYOK=CMK；禁用即删除",
      "current_statement": "材料导入/管理/不可访问/删除分开",
      "reason": "副本缓存备份未证明",
      "evidence_ids": [
        "EV-007"
      ],
      "capability_ids": [
        "A2"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-006",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 6,
      "title": "业务审计",
      "previous_statement": "SQL/CTS即到Key的业务审计",
      "current_statement": "应用记录操作者/request_id/范围/结果",
      "reason": "账号不是最终用户",
      "evidence_ids": [
        "EV-014"
      ],
      "capability_ids": [
        "A4"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-007",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 7,
      "title": "恢复粒度",
      "previous_statement": "PITR即单租户任意恢复",
      "current_statement": "窗口内隔离恢复提取，对齐附件/删除清单",
      "reason": "粒度不同",
      "evidence_ids": [
        "EV-014"
      ],
      "capability_ids": [
        "C1"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-008",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 8,
      "title": "删除范围",
      "previous_statement": "不可导出=不可审计删除；API删除=全部擦除",
      "current_statement": "独立调查，回执列范围/备份期限",
      "reason": "无必然关系且派生待验",
      "evidence_ids": [
        "EV-015"
      ],
      "capability_ids": [
        "D4"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-009",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 9,
      "title": "治理接入",
      "previous_statement": "OperationValidator即可不改内核确认制",
      "current_statement": "验证候选/reflect/组合/后台，必要适配",
      "reason": "请求校验不覆盖全链路",
      "evidence_ids": [
        "EV-013"
      ],
      "capability_ids": [
        "D3"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-010",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 10,
      "title": "产品边界",
      "previous_statement": "治理/知识闭环唯一",
      "current_statement": "承认先例，保留运营，不重做IM/运行时/Wiki",
      "reason": "范围与证据约束",
      "evidence_ids": [
        "EV-011"
      ],
      "capability_ids": [
        "X-KNOWLEDGE-OPS"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-011",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 11,
      "title": "交期与SLA",
      "previous_statement": "8周全交付，无实测规模/成本，套底座SLA",
      "current_statement": "依赖验收，规模/恢复/成本/SLA另测",
      "reason": "证据不足",
      "evidence_ids": [
        "EV-029"
      ],
      "capability_ids": [
        "X-HA"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-012",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 12,
      "title": "商业判断",
      "previous_statement": "Letta转型证明不能独立商业化，许可天然胜出",
      "current_statement": "作为风险假设，价格/许可/性能分别比较",
      "reason": "单案例非普遍规律",
      "evidence_ids": [
        "EV-028"
      ],
      "capability_ids": [
        "X-COST"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-013",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 13,
      "title": "基础边界",
      "previous_statement": "算法/信创/渠道/PG前缀自动构成优势",
      "current_statement": "认证/适配/地域/网络/计算/对象各验",
      "reason": "不能由组件推导",
      "evidence_ids": [
        "EV-002"
      ],
      "capability_ids": [
        "A1"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-014",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 14,
      "title": "竞品全集",
      "previous_statement": "全部闭源无评测，火山全共享，PG备份默认不加密",
      "current_statement": "收紧或撤回，保留冲突与待验",
      "reason": "内部反例与版本冲突",
      "evidence_ids": [
        "EV-003"
      ],
      "capability_ids": [
        "A1"
      ],
      "status": "adopted",
      "origin": "previous_review_and_merge",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    },
    {
      "id": "DEC-015",
      "revision": 1,
      "recorded_at": "2026-10-08",
      "sequence": 15,
      "title": "文档整合",
      "previous_statement": "六稿入口分散重复",
      "current_statement": "两个入口，六稿完整归档，原报告保留",
      "reason": "用户授权且要求保留关键内容",
      "evidence_ids": [],
      "capability_ids": [],
      "status": "adopted",
      "origin": "current_user_authorization",
      "limitations": "保存已知纠错，不声称已归档所有更早整稿版本"
    }
  ],
  "open_questions": [
    {
      "id": "Q-001",
      "status": "open",
      "question": "PG备份加密/轮换/恢复",
      "capability_ids": [
        "A1"
      ],
      "evidence_ids": [
        "EV-003"
      ],
      "close_condition": "目标实例配置与恢复报告",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-002",
      "status": "open",
      "question": "插件版本/全文入口",
      "capability_ids": [
        "B1"
      ],
      "evidence_ids": [
        "EV-005"
      ],
      "close_condition": "读写一致/历史重建验证",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-003",
      "status": "open",
      "question": "全量遍历/快照/导入/引用",
      "capability_ids": [
        "D1"
      ],
      "evidence_ids": [
        "EV-008"
      ],
      "close_condition": "对象合同/校验/迁移报告",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-004",
      "status": "open",
      "question": "主体删除派生/附件/任务/备份",
      "capability_ids": [
        "D4"
      ],
      "evidence_ids": [
        "EV-015"
      ],
      "close_condition": "范围图/回执/防重生成",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-005",
      "status": "open",
      "question": "治理候选过滤/人工保护",
      "capability_ids": [
        "D3"
      ],
      "evidence_ids": [
        "EV-013"
      ],
      "close_condition": "检索与后台测试",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-006",
      "status": "open",
      "question": "阿里导出正文快照",
      "capability_ids": [
        "D1"
      ],
      "evidence_ids": [
        "EV-004"
      ],
      "close_condition": "官方原文/日期",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-007",
      "status": "open",
      "question": "火山SKU/区域/隔离",
      "capability_ids": [
        "X-HA"
      ],
      "evidence_ids": [
        "EV-016"
      ],
      "close_condition": "官方产品/价格快照",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-008",
      "status": "open",
      "question": "中文正确率/成本/延迟",
      "capability_ids": [
        "B3"
      ],
      "evidence_ids": [
        "EV-021"
      ],
      "close_condition": "固定配置分层报告",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-009",
      "status": "open",
      "question": "负载/端到端恢复/SLA/副本",
      "capability_ids": [
        "X-HA"
      ],
      "evidence_ids": [
        "EV-029"
      ],
      "close_condition": "负载/故障报告",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-010",
      "status": "open",
      "question": "CMK跨账号/BYOK导入",
      "capability_ids": [
        "A2"
      ],
      "evidence_ids": [
        "EV-007"
      ],
      "close_condition": "授权/轮换/恢复验证",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    },
    {
      "id": "Q-011",
      "status": "open",
      "question": "协议/客户端版本兼容",
      "capability_ids": [
        "X-MCP"
      ],
      "evidence_ids": [
        "EV-027"
      ],
      "close_condition": "六命令与权限测试",
      "owner": null,
      "due_at": null,
      "blocks": "产品实现或发布声明，不阻止本次文档合并"
    }
  ],
  "historical_tables": [
    {
      "original_path": "01-weknora-analysis.md",
      "heading": "## 2. 项目基本面【已确认】",
      "start_line": 16,
      "raw_markdown": [
        "| 维度 | 数据（2026-10-08） |",
        "|---|---|",
        "| Stars / Forks | 32,413 / 4,315，582 open issues |",
        "| 建仓时间 | 2025-07-22（15 个月） |",
        "| 最后推送 | 2026-10-07（前一天，极度活跃） |",
        "| 近 90 天提交 | ≥1000 |",
        "| 贡献者 | >100 人；首位 lyingbug 独占 2111 commits（企业全职团队驱动） |",
        "| 许可证 | MIT |",
        "| 技术栈 | Go（gin+gorm+asynq）+ Vue3/TS + Python 解析服务 |",
        "| 发版 | v0.1.2（2025-09）→ v0.8.2（2026-09-24），40 个 release，约 2-6 周一版 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "01-weknora-analysis.md",
      "heading": "## 4. 产品化思路：从 RAG 问答到知识运营【已确认】",
      "start_line": 57,
      "raw_markdown": [
        "| 动作 | 具体做法 |",
        "|---|---|",
        "| Wiki 模式 | Agent 把文档提炼为互链页面 + 知识图谱；**版本历史区分 pipeline/agent/user/revert 四种来源**；软上限 50 优先清理机器版本、硬上限 200 保人工记录；回滚本身可回滚 |",
        "| 分块级编辑 | 分块 + 版本历史，改错字不必重传文档 |",
        "| FAQ 库 | 标准问 / 相似问 / **反例问**（negative examples） |",
        "| 运营可观测 | 解析时间线、卡住检测、活动流、自动打标签、批量重解析 |",
        "| 评估 API | BEIR 式数据集，输出 Precision/Recall/NDCG/MRR/MAP/BLEU/ROUGE |",
        "| 数据源同步 | 飞书/Confluence/Notion/语雀/钉钉/GitLab/RSS 等 10 个数据源定时同步 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "01-weknora-analysis.md",
      "heading": "## 8. 明确不借鉴的部分",
      "start_line": 130,
      "raw_markdown": [
        "| WeKnora 能力 | 不借鉴理由 |",
        "|---|---|",
        "| 10 个 IM 渠道、Chrome 插件、桌面版 | C 端分发打法，与 ContextDB 政企 B 端定位不符 |",
        "| 技能沙箱（Docker/E2B） | 这是 Agent 运行时能力，ContextDB 不做执行层 |",
        "| Neo4j GraphRAG | Hindsight 已有 PG 内实体图（entities/memory_links）；引入第二图引擎增加运维面，PG 内路径更符合数据库团队基因 |",
        "| Wiki 页面形态 | ContextDB 的知识形态是 KB 条目 + 记忆，不重做 Wiki 产品 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "02-competitor-landscape.md",
      "heading": "## 2. 六方全景总表【已确认，除注明外】",
      "start_line": 19,
      "raw_markdown": [
        "| 维度 | 阿里云 RDS ContextDB | 火山引擎 OpenViking Context | 腾讯云 | AWS AgentCore Memory | Google Memory Bank | Hindsight（开源内核） |",
        "|---|---|---|---|---|---|---|",
        "| 状态 | 中国站正式商用；国际站 invitational preview | GA 约 5 个月（2026-05-26 计费上线），仅 cn-beijing | **无托管记忆服务**；双开源引流 | 全托管在售 | 全托管在售（平台更名 Gemini Enterprise Agent Platform） | MIT 开源 46,695★，Cloud 按量在售 |",
        "| 归属 | RDS（AI 能力中心） | VikingDB 文档树（数据库线） | WeKnora=微信事业群；Agent Memory=数据库团队 | Bedrock | Gemini Enterprise Agent Platform（Scale 板块） | Vectorize（$3.6M seed 独立公司） |",
        "| 记忆模型 | 事实/实体 Entity Card/记忆规则/自动遗忘 + 记忆晋升为知识 | viking:// 统一文件、L0/L1/L2 分层 | 开源侧：L0 对话→L1 原子→L2 场景→L3 人格 | 事件流 + MemoryRecord + 5 类策略（semantic/preference/summary/episodic/custom） | fact 对象 + scope 隔离 + topic 枚举 + consolidation + revision | 四网络（事实/经历/实体/信念）+ retain/recall/reflect + 后台 consolidation |",
        "| 知识侧 | 知识库+知识图谱+ContextDB Sync（钉钉/飞书）+知识评审 | Resource/Skill 与 Memory 同为 viking:// 文件 | WeKnora（32,413★，知识管理+记忆+Wiki） | 无（纯记忆） | 无（纯记忆，RAG 在别处） | Knowledge Page 原生 |",
        "| 开源策略 | 闭源（开源侧为 AgentScope/ReMe 引流） | AGPLv3 开源同内核+商业差异表 | 双 MIT 开源（WeKnora 32,413★、Agent Memory 27,762★） | 闭源 | 闭源 | MIT 全功能开源 |",
        "| 计费 | Credit（1 元/Credit）+ 存储 GB/时；新客送 834 元 | 0.01 元/时起 + 按文件量；AgentPlan 订阅 AFP 抵扣；前 50 文件免费 | 免费（引流） | 摄入 $1.00/GB + 存储 $0.10/GB-月 + 检索 + 记录 $0.75/千/月 | 存储 $0.30/GiB-月 + 读写折算 vCPU-h + 抽取 token 单列 | Cloud 按量（token/调用+存储），无席位费 |",
        "| 导出 | 原调研及本轮官方搜索索引列限制，正文快照待复核 | 全量包未核验 | 自托管可访问数据，正式导出覆盖另验 | 有列表读取 API，全量包未核验 | 有读取/revision，全量包未核验 | 有部分文档导出，Workspace 全量待验证 |",
        "| 中文优化 | 专项效果未核验 | 专项效果未核验，原评测用 Doubao | 面向中文，专项效果待核验 | 专项效果未核验 | 专项效果未核验 | 当前本地 PG 路径 english；中文向量已配置，全文适配待做 |",
        "| 公开评测 | 本轮未核验 | 原材料有开源内核评测，托管服务待核验 | 原材料有 Agent Memory 自报评测 | 本轮未核验 | 本轮未核验 | 原材料有作者榜单；独立复现未验证，不作华为成绩 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "02-competitor-landscape.md",
      "heading": "## 4. 国际云三范式",
      "start_line": 70,
      "raw_markdown": [
        "| 范式 | 代表 | 机制 | 对 ContextDB 的含义 |",
        "|---|---|---|---|",
        "| 记录式 | AWS AgentCore Memory | 事件流→MemoryStrategy 抽取→MemoryRecord；三档执行（built-in 贵/override 中/self-managed 便宜） | 策略分档定价是毛利保护机制：托管抽取成本内化（built-in 记录费 3 倍）；ContextDB 定价应把抽取/巩固 token 单列或分档 |",
        "| 生成式 | Google Memory Bank | 会话事件→LLM 生成合并 fact 对象；scope≤5KV 隔离；topic 枚举+few-shot 自定义；revision 历史+TTL | 治理细节最全：scope 级 IAM、区域驻留、记忆投毒（memory poisoning）官方警示+Model Armor 建议——\"记忆投毒防御\"已进入国际厂官方文档，可作为 ContextDB 安全叙事的对齐点 |",
        "| 协议式 | Anthropic memory tool / OpenAI 产品内嵌 | Anthropic 不做托管，六命令文件协议、存储归客户端；OpenAI 记忆仅是 ChatGPT 产品功能，API 无记忆服务 | **memory tool 协议正在成为事实标准**：ContextDB 应可直接充当 Claude memory tool 的 `/memories` 托管后端——\"协议优先+托管后端\"双形态进入存量生态 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "02-competitor-landscape.md",
      "heading": "## 5. 国际开源光谱与行业分界线",
      "start_line": 82,
      "raw_markdown": [
        "| 模式 | 代表 | 变现 |",
        "|---|---|---|",
        "| 引擎开源+云独占功能 | Mem0（66,768★）、Cognee | 订阅/用量；图谱、整合、治理云独占 |",
        "| 引擎开源+闭源数据面 | Zep（31,525★，Graphiti+闭源 Konig） | 云订阅+BYOC |",
        "| MIT 全开源+纯托管 | **Hindsight（46,695★，仅次于 Mem0）** | 按量托管+企业版（BYOC/SLA 99.95%/SSO） |",
        "| 开源+产品化转型 | Letta（25,068★，主仓 5 月后无 release） | 转型 agent 产品——**记忆 infra 单独变现困难的信号** |",
        "| 论文代码 | A-mem（1,192★，停更） | 无——**无维护即死** |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "02-competitor-landscape.md",
      "heading": "## 6. 定价模式对比表",
      "start_line": 98,
      "raw_markdown": [
        "| 厂商 | 计费单位 | 入门门槛 | 特点 |",
        "|---|---|---|---|",
        "| 阿里 ContextDB | Credit（1 元/Credit）+ 存储 0.00017~0.0021 元/GB/时 | 新客送 834 元 | 调用含模型成本，Pro/Lite 价差 50 倍 |",
        "| 火山 OpenViking | 0.01 元/时起+按文件量（1 万文件 0.003 元/时） | 前 50 文件免费；AgentPlan AFP 抵扣 | 全场最低入门价+订阅捆绑 |",
        "| AWS AgentCore | 摄入 $1.00/GB（10-06 新政）+存储 $0.10/GB-月+记录 $0.75/千/月+built-in 3 倍溢价 | 按量 | 策略分档定价的毛利设计范本 |",
        "| Google Memory Bank | 存储 $0.30/GiB-月+读写折算 vCPU-h+抽取 token 单列 | 首 1GiB 免费 | 成本结构最透明（Compute/Memory/Storage 三资源） |",
        "| Hindsight Cloud | 按 token/调用+存储，无席位费 | 按量 | 与 Vectorize 自家 Cloud 互为镜像——华为云托管 Hindsight 的定价可参照其上限（企业版 BYOC+SLA 99.95%） |",
        "| 腾讯 | 记忆零收费（ADP 套餐+PU 包间接变现） | 免费 | 引流逻辑 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "02-competitor-landscape.md",
      "heading": "### 7.1 威胁矩阵（对我方既有差异化假设的冲击）",
      "start_line": 113,
      "raw_markdown": [
        "| 我方原假设 | 现状 | 冲击评级 | 应对方向 |",
        "|---|---|---|---|",
        "| 团队知识闭环（个人记忆→人审→团队 KB） | 阿里\"记忆晋升+知识评审\"已上线 | **高** | 下沉到记忆层治理（确认制/血缘/抑制记录），知识闭环保留但不再作为主差异点 |",
        "| 数据库级运维与正确性 | 阿里挂 RDS 树、火山挂 VikingDB 树，均已在讲数据库故事 | 中 | 比拼深度：多 Cell/多区域/SLA/国产化替代（华为 GaussDB 基因强于两者） |",
        "| 成本可解释性 | Google 已做\"三资源透明计费\"；AWS 分档定价 | 中 | 对齐+超越：抽取/巩固/检索成本在控制台可见可归因 |",
        "| 开放核心 | 火山 AGPL 同内核+差异表已跑通；行业分界线已收敛 | 中 | MIT 优于 AGPL+可导出承诺+上游贡献换生态主导权 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "02-competitor-landscape.md",
      "heading": "### 7.2 具体能力比较与验证缺口",
      "start_line": 122,
      "raw_markdown": [
        "| 能力 | 比较依据与边界 | 我方验证 |",
        "|---|---|---|",
        "| 导出 | 阿里索引列限制，其他完整资产包未全面核验 | 格式/快照/权限/校验与导入 |",
        "| 中文 | 当前本地 Hindsight PG 用 english，竞品效果待测 | 分词读写适配、历史重建、同条件评测 |",
        "| 治理 | WeKnora 有确认/抑制，Google 有 revision，不能称唯一 | 检索与后台全链路过滤、人工保护 |",
        "| 加密 | AWS/Google 已有客户密钥 | 各落点覆盖、密钥依赖及恢复 |",
        "| 质量报告 | 多方有自报研究分数，服务效果仍须同条件测试 | 固定版本/模型/预算，不继承上游分数 |",
        "| 防投毒/协议 | 原材料已有多个先例，托管支持待核验 | 攻击样本和客户端版本测试 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "03-academic-evidence.md",
      "heading": "### 1.2 记忆巩固（consolidation）是论文证据最密集的方向",
      "start_line": 27,
      "raw_markdown": [
        "| 论文 | 证据 | 要点 |",
        "|---|---|---|",
        "| Generative Agents（2304.03442，2023，Stanford） | 消融实验 | reflection（定期把记忆合成为更高阶反思）是 believable 行为的关键因子 |",
        "| Sleep-time Compute（2504.13171，2025，Letta/MemGPT 原班） | 定量 | 查询到来前离线\"预思考\"：同等准确率下测试时计算省 5 倍；扩展睡眠时计算再 +13%/+18% 准确率 |",
        "| Hindsight（2512.12818，2025，Vectorize+VT） | 论文作者实验 | 后台 consolidation 是一等公民机制 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "03-academic-evidence.md",
      "heading": "## 2. 记忆系统论文速览",
      "start_line": 45,
      "raw_markdown": [
        "| 论文 | arXiv | 日期 | 核心机制 | 关键数字（自报） |",
        "|---|---|---|---|---|",
        "| MemGPT | 2310.08560 | 2023-10 | OS 虚拟内存式分层上下文管理，主上下文与外部存储间分页换入换出 | — |",
        "| Mem0 | 2504.19413 | 2025-04 | 抽取-巩固-检索三段式 + 图记忆变体 | LoCoMo 较 OpenAI 相对 +26%；较全文上下文 p95 延迟 -91%、token -90%；有争议（Zep 指实现配置有误） |",
        "| A-MEM | 2502.12110 | 2025-02 | Zettelkasten 式动态笔记网络 + 记忆演化 | Multi-Hop ROUGE-L 27.23 vs 基线 4.68；token 1.2-2.5K vs 16.9K |",
        "| MemOS | 2507.03724 | 2025-07 | 记忆操作系统，MemCube 统一内容+溯源+版本，明文/激活/参数三级记忆 | LoCoMo 88.83、LongMemEval 89.20 |",
        "| Zep/Graphiti | 2501.13956 | 2025-01 | 时序知识图谱（bi-temporal），动态维护历史关系 | LongMemEval-S 71.2% vs 全文基线 60.2%；延迟 2.58s vs 28.9s；上下文 1.6K vs 115K token |",
        "| HippoRAG | 2405.14831 | 2024-05 | 海马体索引理论：LLM+KG 索引+Personalized PageRank | 多跳 QA 超 SOTA 至多 20%；比 IRCoT 便宜 10-30 倍 |",
        "| HippoRAG 2 | 2502.14802 | 2025-02 | PPR+深度段落整合，修复\"加图后事实检索退化\" | 联想记忆超 SOTA embedding +7% |",
        "| RAPTOR | 2401.18059 | 2024-01 | 递归嵌入-聚类-摘要构建分层摘要树 | QuALITY 绝对准确率 +20% |",
        "| Context Engineering 综述 | 2507.13334 | 2025-07 | 上下文工程正式学科化，记忆系统为系统级实现之一 | 覆盖 1400+ 论文 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "03-academic-evidence.md",
      "heading": "## 3. Top 8 可产品化记忆机制（按论文证据强度排序）",
      "start_line": 61,
      "raw_markdown": [
        "| # | 机制 | 论文依据 | ContextDB 产品化方向 | 难度 |",
        "|---|---|---|---|---|",
        "| 1 | 睡眠时后台巩固（facts→observations/beliefs，证据可溯） | 2304.03442 消融 + 2504.13171 定量 + 2512.12818 作者实验，三篇研究支持 | **已内置于 Hindsight**：后台 consolidation 生成带引用与证明计数的信念层，refine 不覆盖。华为云的增量是把它做成可观测、可治理的产品能力 | 内核已有，产品化中 |",
        "| 2 | 虚拟上下文/分层记忆管理 | MemGPT 2310.08560 + Anthropic | 上下文预算 API、多级换入换出 | 中 |",
        "| 3 | 海马体式图索引 + PPR 关联检索 | HippoRAG 2405.14831/2502.14802 | PG 内实体图（entities/memory_links）已存在；增量是 PPR 多跳检索，与数据库团队 PG 优化能力匹配 | 中 |",
        "| 4 | 分层摘要树 | RAPTOR 2401.18059 | 知识库侧后台递归聚类摘要，跨抽象层检索 | 低-中 |",
        "| 5 | 时序知识图谱与知识更新/事实失效 | Zep 2501.13956 + LongMemEval 知识更新维 | bi-temporal 事实演化追踪；对应\"记忆会过时\"这一企业痛点（与阿里\"自动遗忘\"对位） | 高 |",
        "| 6 | 抽取-巩固-检索三段流水线 | Mem0 2504.19413（数字有争议，宜独立复测） | Hindsight 已内置同类机制；主打 token 成本优势时须自测 | 中 |",
        "| 7 | 统一记忆资源抽象（MemCube） | MemOS 2507.03724 | 记忆包生命周期管理与跨场景迁移（如 Workspace 迁移、导出） | 高 |",
        "| 8 | Zettelkasten 记忆演化 | A-MEM 2502.12110 | 动态笔记网络、记忆自动演化 | 中 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/source-weknora-deep-dive.md",
      "heading": "## 6. 可借鉴点 Top 5",
      "start_line": 35,
      "raw_markdown": [
        "| # | WeKnora 做法 | 对 ContextDB 的启示 | 成本 |",
        "|---|---|---|---|",
        "| 1 | **知识即 MCP 服务**：每空间独立端点+作用域令牌+工具组默认只读+限流；CLI/插件把知识送进任意 AI 工具 | Hindsight 内核的记忆 API 直接包装为租户级 MCP 端点（读写分离、默认只读），这是\"被 Agent 生态消费\"的分发面，WeKnora 已验证需求 | 低 |",
        "| 2 | **记忆参与检索排序**：MemoryAffinity 插件挂在重排链最内层，retrieval_conditioning 用记忆改写问题理解与文档排序 | 差异化核心：让 Agent 记忆成为混合检索的一等输入（记忆→检索条件化），而非独立 recall API；注意 WeKnora 同样强调\"记忆不扩权限\" | 中 |",
        "| 3 | **记忆治理闭环**：确认制、抑制记录、显式/自动双模式、上限与整理 | 给 Hindsight 自动 consolidation 加企业级治理：推断须确认、来源可溯、可导出清空——这是企业采购的记忆合规底线 | 中 |",
        "| 4 | **双向沉淀带版本血缘**：wiki/chunk 编辑版本区分 pipeline/agent/user/revert，清理策略优先保护人工编辑 | \"会话经验晋升知识条目\"必须带同样纪律：晋升条目标注 agent 来源、可回滚、人工优先；对应 Hindsight 的知识晋升链 | 中 |",
        "| 5 | **PG 同库混合检索+引擎抽象**：默认 ParadeDB（pgvector+BM25）与业务同库，RRF 上移，10 后端可按库绑定、懒重建 | 印证 ContextDB 的 Cell/DataPG 多 PG 方向：单 PG 同库混合作为默认档，专用引擎按租户/库选配；WeKnora 的注册表懒重建/singleflight 设计可直接抄 | 低-中 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/source-opensource-landscape.md",
      "heading": "## 一、数据刷新【已确认】（GitHub API，2026-10-08）",
      "start_line": 13,
      "raw_markdown": [
        "| 项目 | Stars | 许可证 | 最近 push | 最新 release |",
        "|---|---|---|---|---|",
        "| Mem0 | 66,768 | Apache-2.0 | 10-07 | v2.2.1（09-25） |",
        "| **Hindsight** | **46,695** | MIT | 10-07 | v0.10.2（09-29） |",
        "| Cognee | 31,545 | Apache-2.0 | 10-07 | v1.6.3（10-07） |",
        "| Zep/Graphiti | 31,525 | Apache-2.0 | 10-07 | v0.30.2（09-08） |",
        "| Letta | 25,068 | Apache-2.0 | 09-10 | v0.16.8（2026-05-14） |",
        "| MemOS | 11,745 | Apache-2.0 | 09-29 | v2.0.34（09-23） |",
        "| A-mem | 1,192 | MIT | 2025-12-12 | 无（停更） |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/source-opensource-landscape.md",
      "heading": "## (a) 商业模式光谱表",
      "start_line": 55,
      "raw_markdown": [
        "| 模式 | 代表 | 开源 | 变现 |",
        "|---|---|---|---|",
        "| 论文代码 | A-mem | 全部 | 无，已停更 |",
        "| 引擎开源+云独占功能 | Mem0、Cognee | Apache-2.0 | 订阅/用量；整合、图谱、治理云独占 |",
        "| 引擎开源+闭源数据面 | Zep（Graphiti+闭源 Konig） | Apache-2.0 | 云订阅+BYOC |",
        "| MIT 全开源+纯托管 | Hindsight | MIT 全功能 | 按量托管+企业版 |",
        "| 开源+产品化转型 | Letta | server+code | 订阅+算力 |",
        "| 中国生态开源+私有化 | MemOS | Apache-2.0 | Cloud+企业版+行业方案 |",
        "| 云厂自研闭源 | AWS/Google/Azure | 无 | 绑定自家 agent 栈 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/source-papers-survey.md",
      "heading": "## 六、Top 8 可产品化记忆机制（按论文证据强度排序）",
      "start_line": 45,
      "raw_markdown": [
        "| # | 机制 | 论文依据 | 产品化方向（ContextDB/Hindsight） | 难度 |",
        "|---|------|---------|--------------------------------|------|",
        "| 1 | 睡眠时后台巩固（facts→observations/beliefs，证据可溯） | 2304.03442 消融 + 2504.13171 定量 + 2512.12818 独立复现，三重证据 | 后台 consolidation 生成带引用与证明计数的信念层，refine 不覆盖 | 高 |",
        "| 2 | 虚拟上下文/分层记忆管理（分页、compaction） | MemGPT 2310.08560 + Anthropic 2025-09 | 多级存储与换入换出、上下文预算 API | 中 |",
        "| 3 | 海马体式图索引 + Personalized PageRank 关联检索 | HippoRAG 2405.14831 / 2502.14802 | PG 系存储上实现 KG+PPR 多跳关联检索 | 中 |",
        "| 4 | 分层摘要树（多粒度后台索引） | RAPTOR 2401.18059（+20% 绝对） | 后台递归聚类摘要，跨抽象层检索 | 低-中 |",
        "| 5 | 时序知识图谱与知识更新/事实失效 | Zep 2501.13956 + LongMemEval 知识更新维 | bi-temporal 事实演化追踪，对标五维评测 | 高 |",
        "| 6 | 抽取-巩固-检索三段流水线 + 图/向量双存储 | Mem0 2504.19413（数字有争议，宜独立复测） | 增量事实抽取、双索引，主打 token 成本优势 | 中 |",
        "| 7 | 统一记忆资源抽象（MemCube：内容+溯源+版本，可迁移融合） | MemOS 2507.03724 | 记忆包生命周期管理与跨场景迁移 | 高 |",
        "| 8 | Zettelkasten 记忆演化（新记忆触发旧记忆更新与链接） | A-MEM 2502.12110 | 动态笔记网络、记忆自动演化 | 中 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/review-concrete-capabilities.md",
      "heading": "## 1. 本轮外部核验",
      "start_line": 9,
      "raw_markdown": [
        "| 项目 | 证据与限制 | 修订结果 |",
        "|---|---|---|",
        "| RDS PG zhparser | 官方专页搜索返回完整说明，更新于 2026-01-08，包含实例查询方法 | 产品已公开支持；待验证目标实例、读写适配及历史重建 |",
        "| PG 磁盘加密 | 国际站英文正文可读，更新于 2026-09-08，含 DEW、算法与操作约束 | 仅陈述存储层能力，不推导端到端或即时删除 |",
        "| PG 备份加密 | 2024 FAQ PDF 索引说明 PG 加密备份；2026 磁盘页讨论有/无备份加密；MySQL 专页限制不能直接套用 PG | 撤回默认不加密判断，目标版本行为待官方/控制台确认及恢复演练 |",
        "| 备份恢复警示 | 加密页警示处于密钥禁用/删除/冻结语境 | 不说加密备份一律无法恢复；明确密钥依赖 |",
        "| 阿里导出 | 官方快速入门搜索索引仍返回记忆与知识库限制；本轮打开页未提取同段正文 | 有条件保留对照，发布前保存原文快照；不推导删除或审计缺失 |",
        "| AWS metadata | 官方 Memory types/PDF 索引列出短期事件客户密钥覆盖限制 | 只比较 CMK 覆盖，不说完全无静态加密 |",
        "| RDS HA/副本 | 官方产品页列主备、同步及只读扩展 | 只作底座输入，不直接套 SLA，也未证明 recall 无写副作用 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/review-concrete-capabilities.md",
      "heading": "## 2. 本地交叉检视与推理纠错",
      "start_line": 31,
      "raw_markdown": [
        "| 旧稿问题 | 依据/缺口 | 修订口径 |",
        "|---|---|---|",
        "| 火山企业/个人都是共享 | [原报告](source-tencent-volc.md) 写有企业版独占；本轮外部正文读取未成功 | 撤回共享判断，现行 SKU/隔离细节待核验 |",
        "| 不可导出所以不可审计删除 | 两类能力无必然关系 | 各自调查 |",
        "| 六方全部闭源/无评测 | 同目录记录了 OpenViking/WeKnora 开源及多方论文/评测 | 比较具体托管产品与范围，不说行业全集 |",
        "| 治理都停在 IAM | 原报告已有知识审批、确认、revision、防投毒 | 比较对象与链路，不说唯一 |",
        "| 上游导出=Workspace 全量导出 | [接口对比](../../hindsight-cloud-open-source-comparison.md) 仅证明部分接口，未证明完整资产语义 | 定义对象覆盖、分页、快照、权限、附件、关系与恢复 |",
        "| 中文只改查询端即可 | [存储核验](../../backend-storage.md) 记录 search_vector 由应用计算 | 写入/查询同步适配，重建历史数据 |",
        "| bge-m3 是通用默认 | 来源是本地 1024 维部署 | 标明部署范围，效果待测 |",
        "| BYOK=自定义密钥；禁用即删除 | 无密钥材料导入及缓存/备份全覆盖证据 | CMK/BYOK 分开；不可访问和删除分开 |",
        "| OBS 前缀=三隔离 | 前缀是命名范围 | 各种隔离分别验证 |",
        "| SQL/CTS 即业务审计 | 底层账号不等于最终用户 | 应用层记录操作者、request_id、范围、结果 |",
        "| PITR 直接租户回滚 | 实例与 Workspace 粒度不同 | 隔离恢复后提取，对齐附件，重放删除清单 |",
        "| OperationValidator 即确认制 | 请求检查无法证明候选/后台过滤 | 验证 recall/reflect/组合查询/巩固链路 |",
        "| 独立复现已确认，可继承成绩 | 原报告无复现报告/配置/脚本，还把 VT 列为合作研究方 | 原“独立复现”降为未验证，不作背书；作者成绩另标 |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    },
    {
      "original_path": "evidence/sources-index.md",
      "heading": "## 原始源报告（本目录）",
      "start_line": 9,
      "raw_markdown": [
        "| 文件 | 覆盖范围 | 调研方式 |",
        "|---|---|---|",
        "| [source-weknora-deep-dive.md](source-weknora-deep-dive.md) | WeKnora 架构/记忆/治理/MCP/商业化 | GitHub API + 官方文档站 11 页实抓 |",
        "| [source-aliyun-contextdb.md](source-aliyun-contextdb.md) | 阿里 RDS ContextDB/百炼记忆/开源布局 | 官方帮助文档/活动页/GitHub API，69 次调用 |",
        "| [source-tencent-volc.md](source-tencent-volc.md) | 腾讯 WeKnora+Agent Memory+ADP；火山 OpenViking Context | curl+jina 渲染+搜狗搜索兜底 |",
        "| [source-aws-google.md](source-aws-google.md) | AWS AgentCore Memory/Google Memory Bank/Anthropic memory tool/OpenAI | 官方文档+定价页；OpenAI 经 Wayback 验证 |",
        "| [source-opensource-landscape.md](source-opensource-landscape.md) | Mem0/Hindsight/Cognee/Zep/Letta/MemOS/A-mem 数据刷新与商业模式 | GitHub API+定价页实抓 |",
        "| [source-papers-survey.md](source-papers-survey.md) | 14 篇论文 + 评测基准 + 上下文工程共识 | arxiv.org/abs 页面逐篇核验（13 来源） |"
      ],
      "status": "historical_verbatim_not_reverified",
      "limitations": "历史数字与已确认等措辞不是当前事实保证"
    }
  ],
  "retained_detail_index": {
    "research": {
      "paper_source_ids": [
        "SRC-301",
        "SRC-302",
        "SRC-303",
        "SRC-304",
        "SRC-305",
        "SRC-306",
        "SRC-307",
        "SRC-308",
        "SRC-309",
        "SRC-310",
        "SRC-311",
        "SRC-312",
        "SRC-313",
        "SRC-314"
      ],
      "author_numbers": "SRC-004/SRC-106全文与historical_tables",
      "independent_replication": "未验证EV-020/EV-H03",
      "rules": "固定版本/模型/prompt/预算/judge/数据集，区分绝对与相对"
    },
    "pricing": {
      "source_ids": [
        "SRC-003",
        "SRC-102",
        "SRC-103",
        "SRC-104",
        "SRC-105"
      ],
      "status": "historical_not_quote",
      "details": "币种/调用/存储/策略/免费与活动门槛全文保留",
      "suggestion": "存储/调用/token解释费用，策略分档/订阅/独享SKU"
    },
    "ecosystem": {
      "source_ids": [
        "SRC-101",
        "SRC-103",
        "SRC-104",
        "SRC-105"
      ],
      "details": "客户端、CLI/MCP、Claude文件六命令、IM/数据源/解析/引擎细节完整保留",
      "boundary": "未声明所有版本当前兼容；不首期重做IM/运行时/Wiki"
    },
    "architecture": {
      "source_ids": [
        "SRC-109",
        "SRC-110",
        "SRC-111",
        "SRC-112",
        "SRC-113",
        "SRC-114",
        "SRC-115",
        "SRC-116"
      ],
      "details": "Cell/placement、PG队列/图/索引、知识晋升/三操作、扩展/模型网关/D01-D12衔接",
      "boundary": "未改目录外设计/任务板"
    },
    "risks": {
      "items": [
        "竞品跟进导出/治理",
        "上游升级",
        "评测/自建集争议",
        "模型费用/后台归因",
        "区域/密钥/备份完整性",
        "许可/国产化/认证",
        "客户端版本/权限"
      ],
      "treatment": "配置固定、合同与验收、成本和区域覆盖，不称不可复制"
    }
  },
  "journal": [
    {
      "id": "LOG-001",
      "date": "2026-10-08",
      "sequence": 1,
      "event": "原始分主题调研",
      "source_ids": [
        "SRC-101",
        "SRC-102",
        "SRC-103",
        "SRC-104",
        "SRC-105",
        "SRC-106"
      ],
      "verification": "历史报告自述，未重演"
    },
    {
      "id": "LOG-002",
      "date": "2026-10-08",
      "sequence": 2,
      "event": "具体能力检视与证据纠错",
      "source_ids": [
        "SRC-107"
      ],
      "decision_ids": [
        "DEC-001",
        "DEC-002",
        "DEC-003",
        "DEC-004",
        "DEC-005",
        "DEC-006",
        "DEC-007",
        "DEC-008",
        "DEC-009",
        "DEC-010",
        "DEC-011",
        "DEC-012",
        "DEC-013",
        "DEC-014"
      ]
    },
    {
      "id": "LOG-003",
      "date": "2026-10-08",
      "sequence": 3,
      "event": "用户授权两份合并并要求保留信息",
      "decision_ids": [
        "DEC-015"
      ]
    },
    {
      "id": "LOG-004",
      "date": "2026-10-08",
      "sequence": 4,
      "event": "阅读稿/机器记录/六稿归档/源报告保留",
      "policy": "完整保留正文，仅相对链接迁移；不伪造早期整稿快照"
    }
  ]
}
```
