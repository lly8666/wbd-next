# M0 恢复 R0-023 集成入口 · 2026-10-17

本轮不重开024：Normal/FEC-off已测基线锁定 `fca4456313e59c0a67f4d8b98959a62d2af71b12`，仍保留 D10 `39032995995` 旧A交付短缺 FAIL/INCONCLUSIVE。用户要求恢复原业务集成、Stop与超MTU，本 S 在main registry将M0转回原分配的 R0-023，不改变 M1/M2/M3/M4 权限或工位任务。

- M1 正式main registry仍分配 `R4-M1-GAME-SHARED-PIPELINE-WORKPACK-013`；worker HEAD `9d4f68aab2bb1f57bfb96dd8a472bc7eec43f556` 的 cursor 仍指历史已完成012，**不表示Game013完成，也不得由M0在worker分支替写**。M1沿现有 PACK013 自治继续。
- M2 正式main registry仍分配 `R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010`；worker HEAD `c345061c992c505c92eb19181de96a531cc39d96` cursor 仍指已交付009，**不表示010已交付**。M2继续010，不追加逐步派单。
- M3 CODE `422a26127496560c0a52e6745ecc8f354e3f4f18` 正确性已有精确 SOURCE 结果；现有 M0 专项 workflow 在同一个consume job使用已经编译/sha验证的 Release binary 顺序 scalar→ISA-L，同一 20:20/1200B 工况，只有一个性能场景，不重构 ISA-L crate 或脚手架。跑完再追加实际run/hash，不提前写 PASS。
- M1/M4冻结源码对 main 的绝大部分模块已相同；差异需逐文件判定，避免覆写主线的 original Go owner 接线帮助函数。后续 M0 原 R0-023 优先原业务真实超MTU/Stop/借用生命周期，必要组合检查才做相应 source-pin paired tests。D10、原R0-023、Game/FEC-on/物理/产线资格都不继承前项绿色。
