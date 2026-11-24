# H2279 · 同六台原生机器双组三Runner Windows→ARM 直接/中继干净TCP容量判别

## 现有判据
- H2276 [44925523352](https://github.com/lly8666/wbd-next/actions/runs/44925523352) 使用x86 Linux内核relay，Win→relay经Tailscale DERP，双组无损分别10.00/16.23Mbps，CPU未满：**INFRA_INVALID**，不准拿来优化产品队列。
- H2277 [44926156989](https://github.com/lly8666/wbd-next/actions/runs/44926156989) 把relay改为**不同的ARM64 VM**，保持每组真Windows2025 client＋ARM64 relay＋另一ARM64 Linux server（总六台不同VM）。两组全部real OS TCP及StopSUCCESS，Win→relay和Win→server均direct candidate，无损0ms吞吐48.577/78.444Mbps，但仍远低于800Mbps，CPU未满，弱网请求的200ms RTT有小流P99小于400ms，说明之前`tc`损伤施加/双向有效性尚未验证，不能因业务Script PASS声称丢包产品性能资格。
- H2278单机真实Win original TCP反向第二代目录WinError183已修，仅归档单测PASS；**不自动重跑昂贵Windows WSL场景**。独立主线仍应优先解决跨机网络容量。

## 本次独立最小有辨别力对照
同两个独立a/b三机组，每组使用同一 Windows 原生 Winsock端、同一ARM64服务端、同一四条真实内核TCP bulk＋160稀疏TCP样本、同一SOURCE和同一owner启动/Stop；先跑 **Windows 直接 Tailscale→ARM server TCP18727**（不经过relay和tc，干净0ms），再跑 **Windows→独立 ARM Linux relay 内核 DNAT/SNAT→同一 ARM server**（relay netem`-1`，无额外时延/无丢包）。两档分开记录真实ARM接收字节、Win本机单调时钟P99、两端allcore CPU、两个实际peer IP及Tailscale direct/DERP。相邻顺序在同一Runner保留先后顺序影响，不推断随机事件为可重复性能；两个独立组均完整保留，绝不挑好结果归因。
- 如果直连goodput数倍高于relay，优先核查二次Tailscale加解密、内核NAT/TUN转发以及内部路由吞吐，而不改Rust/FEC/Shadow队列。若直连也只有几十Mbps，说明当前GitHub runner tailnet/云平台容量本身不足，不再浪费完整1/5%六机矩阵；改用能真正直接互通并具有较高TCP裸容量的网络载体，或者在经验证的Linux原生高容量同机作有因果关系的优化。
- 新环境 `WBD_H2279_CAPACITY_AB=1` 只由当前双三机工作流发出，使同源Python工具临时把阶段缩到 `direct→relay0ms`（仍经过真实Windows/ARM OS TCP，而非synthetic TCP）；工作流三个昂贵原生角色均由提交显式标记 `[m0-029-h2279-clean-path]` 或人工dispatch开启，廉价静态总先行，以免 unrelated Python fix 在相同脚本路径误触发6台Runner；原H2276/2277全部冻结Source与ZIP不擦除。此提交产品Go/Rust、默认、Stop**完全不改**。成功只能是两组三机**网络容量对照**，非WBD性能晋级。

```feature-impact
{"kind":"none","reason":"H2279 test-only exact Windows ARM OS TCP clean direct-vs-relay source-locked comparison and expensive dual-triple workflow explicit marker gating, not Go/Rust product or defaults."}
```
