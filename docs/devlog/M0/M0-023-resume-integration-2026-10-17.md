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


- 反向 [BA Action39045641512](https://github.com/lly8666/wbd-next/actions/runs/39045641512) SUCCESS，M0 workflow `a4ca2fe` 的 `measure_order=BA` 只跑这一场景：同一测量 job 的 ISA-L 先行（52631块/1.24988CPU秒、p99 codec 34846ns），scalar 后行（1996块/1.25186CPU秒、p99 codec 704415ns），10/10原始窗口有效。build/result IDs+SHA在原M3 evidence JSON 的 `reverse_BA`。两个 runner 的倍率不相加、不直接比较绝对CPU。前一条 AB receipt 保留。M3角色正式交付及Go V4 FEC-on仍未因此直接通过。

## 2026-10-17 · M1/M2/M3/M4 精确组件验收与 R0-023 阶段实际接线

- 原 Normal/FEC off 基线永远固定 `fca4456313e59c0a67f4d8b98959a62d2af71b12`，历史 D10 39032995995 FAIL/INCONCLUSIVE 原样保留；新 M0 CODE `ede83b98edba1fee6f73bc99454040cc95392d4d`。
- M1 Game013 CODE `e2050aec` 已 117/117 + central scope PASS，main `7d0a1c7` 只导入 Game 两文件+mod 声明，不倒灌 worker 旧 memory/early_rx/generation；main native-functional 39047827609 PASS。
- M2 恢复010 CODE `654a3c1` 70/70 + central scope PASS，main `006cab6` 只导入 typed ingress、rx_feedback、workpack_tests+lib 声明，保留 main 原优化过的 receipt.rs；main recovery/native 39047929179 PASS。
- M3 CODE `422a261` 113 PASS/scalar、真实 native ISA-L 3 PASS、独立同机 AB39044413886/BA39045641512 PASS；`ede83b9` 只导入十个不同 codec/src blobs，原 record/wire/LINK functional 专项全 PASS，默认 native feature 仍 OFF。工位 H30 central39046275022 **FAIL verified cursor lacks reviewed PASS evidence**，之前 H29 central PASS；不能声称最终工位 H30 形式核验通过。
- M4 PACK013 CODE `b7bcde7` 94/94、原始4个平台 hot-path blobs 与 main 完全相同，不重复导入；M4 平台仅历史 scoped 单测不同。
- 原始 protected Go TLS→Rust V4→真实 raw/TUN 组合 native 39047975684 PASS：MTU 下降 fail-closed、恢复后 driver lease 按原 generation 安全重建、大1728B真实内层 IP 在现有单帧预算下拒绝、随后的小包继续 kernel copied、活跃双 worker Stop/Release+旧句柄拒绝重启。只证明 **安全拒绝** 而非 LINK 超 MTU 自动分片后交付；完整 R0-023/产品资格仍 OPEN。
- A=`fca4456` vs B=`ede83b9` 严格同机配对 P10：AB39048219356 CPU-s/GiB 104.54→109.33 (+4.58%)，BA39048219347 79.71→78.55 (−1.46%)，A/B两方向0 missing/invalid；**CPU因顺序/宿主变化结论不定**。p99 B 各leg 稍高，不宣布无回退；20pps SPARSE AB39049004790 已用于下一次限定首到验证，未得结果前不编造。
- Unified native functional `39047975666` codec 组240秒串行 timeout（其他子组PASS）；原 M3 worker suite 串行口径与 worker 多线程不一致。M0 `d8a11d` 仅把统一 codec 功能组测试设为4threads，保持性能独立跑，Action39048697568尚待实际归档；原红灯保留，不能按任何单独专项 PASS 伪造整个 workflow SUCCESS。
- 证据 `docs/evidence/M0/M0-023-modules-intake-ede83b98edba1fee6f73bc99454040cc95392d4d.json` 保存来源、产物 GitHub 提供的 SHA256/运行ID、差异清单与未验范围。当前 Go Game / repair typed 只是组件导入、尚未完成实际认证接线，整体产品功能保持 OFF。下一步仅接 live V4 owner 的 LINK fragment TX / M2 ingress，按必要结果选取组合回归，不做024微调、容量加压或 D10 重跑。
