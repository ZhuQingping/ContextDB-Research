# 模型切换交接

用户于2026-10-04要求停止高额度消耗，切换至GPT-5.6 Sol、Medium后继续原调研任务。主代理无法通过现有工具更改当前会话模型；不再启动新代理或扩展研究。

已完成：主开发文档、HLD/LLD/12任务包与8周计划、差异化修订；参数/模型/权限/DDL/幂等/发布/UI探针；四客户端真实自动记忆验证。原Hindsight源码未改，8888/9999主服务健康。

待收尾：test_pipeline当前全API local-ml suite结果；保留完整失败与独立24通过结果，不能合称全绿。该代理正保存checkpoint，详见reports/tests.md、tests-ci-runbook.md及evidence/tests-api-localml-offline。全跑完成后脱敏日志（已有scripts中工具）、停止仅本轮PG15499/15500/15591，保留8888/9999/55432。更新主文档§4最终计数，运行scripts/delivery_verify.py，更新清单，交付结果。不要重新做已完成研究/测试。

重要边界：pg0 fsync=off；无真实华为MaaS/RDS/OBS验收；本轮不是8小时负载测试。DML-only可健康启动但不能建Bank，需特权预建；原生UI共享口令不等于客户权限。研究goal仍active，未宣称产品上线验收完成。

收尾更新：完整suite已完成（10477通过/2失败/185跳过/5预期失败），结果已写报告；测试PG已停，日志已脱敏。运行时按用户新要求切换gpt-5.6-luna/low，并发1，关闭自动整合；启动模型验证成功，API/UI健康。
