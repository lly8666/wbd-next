# PLAN029 H1814｜已接线的原生纯Tunnel同VM P1 A/B（结果待真实Action）
- 不重新运行旧028完整七模式。采用原现成 Windows Go/Rust DLL / Linux Rust server 和 signed Wintun/NPF＋WSL2/TUN，源为本提交。唯一 Action、唯一 VM，依次 A（原V4纯Tunnel）→owned Stop→B（V3 Rust split route=all，仍纯Tunnel）→owned Stop，严格同程序SHA256。当前50Mbps双向、25ms/0%真内核tc、60s，96B/1200B两类，不搞极端负载。
- 原`m0_wl_public_modes_e2e.py`已处理真实双方UDP/TCP/Stop与OS恢复。新协调器复用既有编译产物、1Hz Windows原进程Go＋Rust CPU/RSS和每OS UDP RTT探针，判定真交付字节、实测 CPU/交付GiB、往返p99、最长包间隔。无跨OS时钟校准，单向延迟/驱动CPU和用户排队最老年龄记NOT_MEASURED。
- A是V4、B是V3/all，可能含不同后端成本：**不隔离分流算法因果**；只做同VM总代价及下一步风险评估。各腿失败立即停止，绝不借后一腿冒充绿色。Driver/WAL均沿旧finally精确owned恢复。
- 本H1814只写测试流程、场景、工作流、cursor，无新产品行为；先收Action源锁/真实CPU后再评估P2。Game4实际新分流、真实GUI点击起网和IPv6生命周期仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Add one moderate-source-locked signed native P1 same-VM A/B harness using existing binaries and owned Stop; no product data-plane or configuration change."}
```
