# W26 FEC source record direct arena write / CPU path optimization intent

Branch experiment/fec-network-tuning only; base PASS SOURCE ab7ea894100f245d6a510137282736781bd017ce ARM64 build 40108972702 artifact12565424535 SHA256 9bf5b07eee3e90a37a69844b23fb08834c38a9d5781f0f1635c27543bbba7067; W25 Action40109234114 B 150Mbps both scoped PASS residual0.054/0.0485%, p99 303ms, yet client/server CPU24.85/24.58 CPU-s per30s and host PSI high. New objective is to **reduce CPU allocations** without changing recovered residual, rplanned/rsent, first-send PN or DATA priority.

Existing FEC source staging calls source_owned(block,index,frame,..) for every one of ~663,665 TUN source records/side/45s: allocates a temporary 10B+frame heap Vec and copies source bytes into it, then obtains original scoped M1 arena and copies all payload bytes *again* into the final AEAD record. Replace with single source_into over precisely checked arena [14..14+10+frame_len], retaining original FEC wire, auth PN and maximum record budget. No changes to fixed/auto policy, parity math/quanta, M4, outer retransmission, M2, network host qdisc or FEC RX. Test dirty arena bytes and malformed short frame fail-closed. Only build new product once and compare frozen W25-B A versus new W26 B at exact 150Mbps/side original scenario same VM one AB measurement job. Memory, CPU, actual parity, residual, p99 and stop cleanup must remain qualified; back off if host PSI blocks certainty, no new 175+ rate.

## Completed W26 paired observation

## 2026-10-24 W26：取消每源包临时Vec及重复复制，150Mbps同机AB双腿PASS

在 W25 Fix Maximum6 150Mbps真实双向残余降到0.05%的基础上，本次只优化 FEC source 密封的CPU成本。旧 `original_fixed_stage_source` 每个源包先调用 `source_owned()` 创建新 Vec，再将同一 10B头+真实源字节复制到原 M1 arena，额外每侧约663,000次源包heap申请/45s。新精确SOURCE `564490bc7a8f61c9ab06be58add8138212306393` ([commit](https://github.com/lly8666/wbd-next/commit/564490bc7a8f61c9ab06be58add8138212306393)) 使用现有 `source_into` 对原 owned arena 精确 `[14..14+SOURCE_HEADER+len]` 写入，source/TICKET/budget校验、AEAD PN、复制确认、所有frame字节相同；不改 M3 Parity调度或外层恢复/真M2。Exact source ARM64 [构建40109847848](https://github.com/lly8666/wbd-next/actions/runs/40109847848) 全绿，zip artifact12566326717 SHA256 `a1ce0b81738a9a74ac04835546479ada398e99718fd5086775c0b765625f649c`，包括 dirty arena 源wire等价及 Fixed/Auto 内核缺源回归。

[W26 performance Action40110100061](https://github.com/lly8666/wbd-next/actions/runs/40110100061) **SUCCESS**：唯一场景、同一ARM64 runner/同一job、旧A `ab7ea894` →新B `564490bc` 顺序比较；各自warmup15s+measure30s+drain30s，双向150Mbps、真实netem IID约30%、300ms单程、固定最大6真正applied、外层DATA修复0包0B、真实首发Parity照常、原TUN fq600及owned测试静态邻居不动；Stop owned清理、TUN/source root丢包0、RX压力淘汰/codec reject0。结果artifact12565693815 SHA256 `d7127551bec2574ec38858e232cce03a65f3c76020c71856be9f389fb81e9051`。

| 同机30秒量纲 | A原双量子 | B+直接arena |
|---|---:|---:|
| C→S 实际交付/残余 |149.874Mbps / 0.1015%| **149.897Mbps / 0.0836%**|
| S→C 实际交付/残余 |149.871Mbps / 0.0954%| **149.926Mbps / 0.0623%**|
| 首次p99 C→S/S→C |304.5/304.0ms|303.7/303.8ms|
| CPU-s 客户/服务 |25.36 / 25.27 | **24.87 / 25.39**|
| CPU-s 双端合计 |50.63 | **50.26（少0.37s，-0.73%）**|
| RSS峰 客户/服务 MB |49.90 / 50.17 |49.85 / 49.71|
| native parity rplanned→rsent 客户 |830379→829009|830269→829411|
| native parity rplanned→rsent 服务 |830337→829059|830185→829614|
| 30秒outer veth TX 客户/服务 Mbps |259.71 / 259.49|259.85 / 259.81|
| Host CPU PSI峰/over20持续比 |30.58% / 100%|30.25% / 100%|

**资格**：W26 A/B两个方向、两腿各自产品级功能/业务均 PASS_SCOPED，B无Parity/首达回退；修订消除一次真实 source Vec 分配和重复copy。CPU 客户 -0.49s、服务 +0.12s，合计 -0.37s /30s，只有同机一次AB观测，**不能据此宣称有稳定0.73%硬件加速**。150Mbps比125Mbps多20%吞吐，CPU总秒不应硬压到125的绝对数而不减少真实Parity；更高175+依然 NOT_RUN，因为宿主CPU PSI持续>20%。独立 FEC Fixed 功能代表已具备150Mbps scoped资格；Auto真实损伤阶跃动态profile、真实反馈RTT age与Windows/组合资格仍未完成，merge_ready=false。现不再无限提高业务档或刷种子。
