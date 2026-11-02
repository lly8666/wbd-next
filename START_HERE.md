# WBD Next｜main最小接续

源码、计划和进度在main。每次默认上轮可能中断，读本页、AGENTS、PROJECT_CHARTER、project/registry、M0 prompt/cursor及features入口；只核checkpoint后相关增量与在途Actions，补recovered，不重扫历史/重复派发。

当前细则：[PLAN027网络验收与低开销收口](docs/decisions/M0-PLAN027-LOW-RATE-FEEDBACK-CLOSEOUT-20261030.md)。2026-11-02用户已授权继续：收齐Game/FEC重传修复结果后，**Normal公共重传成本优化，与关闭重传的主体网络测试/优化并行；定型后各模式复用，再做ON组合回归/长测/交付**。旧cursor“只做GameFEC、其他暂停、等待新授权”不再阻止推进。

已完成接线/M2退役/Normal比例保留证据，仅补缺口；不恢复A5旧Go对照。新旧CPU仍需同VM顺序A/B。一Action一测量场景、产物复用；容量止步不免除其他任务，OFF矩阵不冒充ON全通过。完整完成条件见PLAN027§0，完成后不无限扩测。

功能：[features](docs/features/README.md)；夹具：[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)（历史限制以实际workflow及PLAN027为准）；诊断：[NETWORK_TRIAGE](docs/testing/NETWORK_TRIAGE.md)；历史：[INDEX](docs/history/INDEX.md)。按问题再追SOURCE/devlog/evidence，不将旧PASS迁到新源码或物理机。

后续顺序（2026-11-02用户指定，不打断当前在途测试）：**PLAN027收口→[PLAN027A统一MTU](docs/decisions/M0-PLAN027A-MTU-UNIFICATION-20261102.md)→[PLAN028–030](docs/decisions/M0-LEGACY-ROLLOUT-20261102.md)**。027A的[M0提示词](docs/prompts/M0-PLAN027A.md)与[唯一MTU契约](docs/architecture/MTU_CONTRACT.md)已备好；028以后复用其预算，不另算。新功能/原生资格仍以功能卡与真实证据为准，计划不代表已实现。
