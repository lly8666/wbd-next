# WBD Next｜main最小接续

M0源码、方案和进度均在main。**每次提示都先恢复可能中断的上一轮，不把提示词视为新任务。**读本页、AGENTS、PROJECT_CHARTER、.governance/project.json、.governance/registry.json、docs/prompts/M0.md、M0 cursor和docs/features/README.md。只核checkpoint后的提交/devlog与在途Actions，补recovered，不全仓翻历史。

当前唯一施工细则：[PLAN027低频反馈收尾](docs/decisions/M0-PLAN027-LOW-RATE-FEEDBACK-CLOSEOUT-20261030.md)。顺序：**去M2 Receipt/接替代逻辑→简化A→剩余接线B→代表矩阵C→结果修复优化→交付即停**。新registry/PLAN027优先于cursor旧next_action；PLAN026只保留不冲突的实现背景。已运行测试收结果，不重复启动。

Normal/off既有源码级功能/Stop、240s N0和150Mbps证据保留，SOURCE009d七模式等最新证据按功能卡/devlog核对；不迁移成新源码/物理全绿，也不为这些旧门阻止当前批次。最新Game/驱动/序号/MTU修复继续保留。

新计划矩阵10–200Mbps、0–30%损伤、单程≤250ms，Game4最高FEC≤20Mbps；一个Action一个测试控制进程、统一编译复用、容量止步。完成条件已满足则简短报告“本轮基本完成，待用户验收”，重复定时提示不得再派新矩阵。功能唯一入口[features](docs/features/README.md)，夹具[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)，历史[INDEX](docs/history/INDEX.md)。
