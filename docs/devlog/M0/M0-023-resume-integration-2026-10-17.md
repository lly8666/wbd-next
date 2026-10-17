# M0 恢复 R0-023 集成入口 · 2026-10-17

本轮不重开024：Normal/FEC-off已测基线锁定 `fca4456313e59c0a67f4d8b98959a62d2af71b12`，仍保留 D10 `39032995995` 旧A交付短缺 FAIL/INCONCLUSIVE。用户要求恢复原业务集成、Stop与超MTU，本 S 在main registry将M0转回原分配的 R0-023，不改变 M1/M2/M3/M4 权限或工位任务。

- M1 正式main registry仍分配 `R4-M1-GAME-SHARED-PIPELINE-WORKPACK-013`；worker HEAD `9d4f68aab2bb1f57bfb96dd8a472bc7eec43f556` 的 cursor 仍指历史已完成012，**不表示Game013完成，也不得由M0在worker分支替写**。M1沿现有 PACK013 自治继续。
- M2 正式main registry仍分配 `R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010`；worker HEAD `c345061c992c505c92eb19181de96a531cc39d96` cursor 仍指已交付009，**不表示010已交付**。M2继续010，不追加逐步派单。
- M3 CODE `422a26127496560c0a52e6745ecc8f354e3f4f18` 正确性已有精确 SOURCE 结果；现有 M0 专项 workflow 在同一个consume job使用已经编译/sha验证的 Release binary 顺序 scalar→ISA-L，同一 20:20/1200B 工况，只有一个性能场景，不重构 ISA-L crate 或脚手架。跑完再追加实际run/hash，不提前写 PASS。
- M1/M4冻结源码对 main 的绝大部分模块已相同；差异需逐文件判定，避免覆写主线的 original Go owner 接线帮助函数。后续 M0 原 R0-023 优先原业务真实超MTU/Stop/借用生命周期，必要组合检查才做相应 source-pin paired tests。D10、原R0-023、Game/FEC-on/物理/产线资格都不继承前项绿色。

## 2026-10-17 · M3 同机标量/ISA-L CPU Action 收据

- 原完整 worker CODE `422a26127496560c0a52e6745ecc8f354e3f4f18`。M0 workflow `d361f7563c770b30f6e684dcadededf4961f1d53` 的原 build+consume 编译一次 Rust Release test 二进制并核 sha，然后在 **同一 consume job/VM** 用固定 20:20×1200B、同一 deterministic 源，`WBD_FEC_ORDER=AB` 顺序 scalar→真实 Intel ISA-L，共两条连续 leg。
- [Actions 39044413886](https://github.com/lly8666/wbd-next/actions/runs/39044413886) SUCCESS：真实 Go矩阵/ISA-L 正确性3/3，标量 2712 blocks/1.25096s CPU，ISA-L 123331 blocks/1.25022s CPU，两个 leg 各5个 >=250ms有效窗口、0坏窗口，编码20 systematic+20 parity并恢复4/块。观测的codec块每单位CPU处理能力约45.5倍，**不是原隧道吞吐、业务RTT、具体 AVX dispatch、完整FEC-on/500Mbps**。p99纯codec操作 wall: 标量507789ns、native13242ns，同样不是packet p99。
- 初次 [39044344082](https://github.com/lly8666/wbd-next/actions/runs/39044344082) Rust AB 测量原始完成，M0 自增 Python regex 转义错误导致结果解析FAIL，完整失败保留；修正后的 d361 Action 为独立实际 PASS。所有 build/result artifact IDs、hash和源码详见此独立 JSON。
- 工位登记不变：M1主线任务 Game013，M2主线任务恢复010。M3码 `422a` 已冻结但worker cursor仍 PARTIAL；M0 不抢改M3分支，不在未交付前将其真实产品集成冒充通过。Normal/FEC off已测SOURCE `fca4456` 原样冻结，D10失败原样保留。

