# PLAN027 H892｜Normal 外层重传 OFF 50 Mbps 实际容量首阶

- 接续 H891 SOURCE `ba1b8128b695bf50d1d0ba98eea8941be0fd25a2`，功能卡已记录 H884 同 VM Normal 30% OFF/ON 与 H886 原生 Game4 OFF。并行的 H889 Windows 单向 105s lifecycle 和 H890 Normal ON 300s 是不同 SOURCE/独立 Action，不与本场景共用测试结果或 OS lease。
- 新的同源码原始 Windows2025 signed Npcap/Wintun ↔ Ubuntu WSL2 Linux original Go TLS/Rust 正式 Normal OFF 容量测试：双方向业务 offered 50 Mbps，单程 delay25ms，损伤0%，60s offered、5s warmup、10s drain，TUN MTU1400；实际 UDP payload 96/288/1060/1200B，按包权重2/3/25/70，种子20261102。只使用真实 Windows 原生驱动和 Linux 内核 tc/TUN。实例化一次场景；同 runner 不并发其他性能负载。
- 模型：按包权重平均 UDP payload `1115.56B`，每方向业务 PPS≈`50e6/(8×1115.56)=5602.6` 包/s（忽略 IP/UDP/外层 framing）；单程25ms→约RTT50ms，业务 BDP≈312,500B、在途≈280 个平均 UDP payload。真外层 F/R/C、分片、调度队列、虚拟化和原生驱动负载只能由报告给出，目标不是线速。若 host/container/driver 容量不足，保留缺失和容量解释，**不得降低负载后写 50M PASS**。
- 新 Action 须按 SOURCE 构建，校验 Windows 和 Linux 两端实际 outer OFF/effective0，OS kernel `MEASURED_BOTH_OS_KERNEL`，真实 offered>=47.5Mbps/方向，首到>=0.999/方向，UDP/TCP+owned Stop、60s场景读取及二进制身份。50Mbps 若 FAIL，先查 host/driver/drop/CPU、重用当前源功能证据，不直接推进100/200M。真实 signed original 50M 完成前为 **NOT_RUN**，不代表硬件物理验证。后续同族边界再视容量处理。
```feature-impact
{"kind":"none","ids":[],"reason":"Independent source-locked 50Mbps/25ms0-loss/60s signed Windows/Linux Normal outer-repair OFF capacity scene and workflow evidence gate only; no production Go/Rust/CLI change."}
```
