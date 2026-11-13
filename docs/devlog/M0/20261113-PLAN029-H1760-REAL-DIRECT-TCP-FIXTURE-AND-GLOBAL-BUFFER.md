# PLAN029 H1760｜H1759原生源码绿；签名CN Direct TCP首个物理回包和全局背压

- H1759 SOURCE `cb8dfb7a001dd9a52a5e1037fa1ed3d09e688f6f` 自动Action全部SUCCESS：Windows original-Go装配/编译+单条Defender真实CAS [43445358742](https://github.com/lly8666/wbd-next/actions/runs/43445358742)、Rust DLL+WinForms/CLI构建 [43445358922](https://github.com/lly8666/wbd-next/actions/runs/43445358922)、治理43445358655、M0-WIN-LINUX43445358745（**no-scene**）、WAL43445358730。没有产品Direct TCP双腿实网。
- 针对现代码资源/HOL：TCP每条原有每向16KiB按需；新增全actor **8MiB共享待写字节读取软预算**（与其它UDP/DNS内存共同位于64MiB共享分配上限内），满时仍写出相关流已有数据、仅暂停新增TCP读取，不停其它Direct/Tunnel；连接中30秒预算，已建TCP不再固定120秒静默强杀，FIN/RST/OS关尾才退。没有逐flow线程/全局等待。
- 复用唯一现有原始签名Windows2025↔WSL2 Normal Action [plan029-v3-real-direct-udp]：CN hostname成功FakeIP的现有两个OS物理DNS/UDP先证，然后同一个原TLS/Rust/Wintun代真实Windows TCP连接FakeIP:46112，Linux物理listen真实 TCP按宿主源IP readback 32KiB，双腿半关闭echo唯一字节，对比既有Tunnel TCP（仍独立）并在Stop断言该代Defender sidecar及WAL/routing sidecar消失。一个网络场景/测量进程，不造新workflow或二次dispatch；错误先保留物理脚本/Go日志。
- H1760实网结果仍**PENDING/NOT_RUN**；D1–D5/P1–P2 GUI生效、单DNS失败/CDN反例/Perf/Padding尚未签收。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1759 source CI and WinForms green; H1760 global TCP backpressure/healthy idle and first signed physical Direct FakeIP TCP 32KiB echo/owned Stop fixture"}
```
