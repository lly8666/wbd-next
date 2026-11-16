# PLAN029 H1993｜接上H1974大尾延迟：只跑一次普通1MiB物理/Direct+Tunnel，不再盲改热路径

- 恢复点 H1992 SOURCE `ac18e797afedd1937b0aaa10f23265986d8bb6bf`；[H1991 M0原双系统Action43835248671](https://github.com/lly8666/wbd-next/actions/runs/43835248671) 已最终**success**：Normal/off真Win2025↔WSL2 Linux原TLS/Wintun/Npcap、内核TCP/UDP和双端owned Stop。H1988 DNS去空轮询、H1989 WinSock16 shard公平性、H1991 UDP空扫描退避的Windows Rust组件全通过；这三项**没有** CN Direct CPU/p99收益的真证据。
- H1974 另一源 [43808776053](https://github.com/lly8666/wbd-next/actions/runs/43808776053) 原生 **FAIL**：一条正常Direct TCP有5次61–63ms RTT和4次真实重复SEQ，SHA/FIN/owned Stop单独PASS。后来的H1978同机正常p50 Direct521μs对物理269μs，0次>8ms却未复现旧异常；不能跨VM认定修好。此轮不再追0.2μs规则或高压资源满。
- H1993 不新造业务流：重用原 H1815 **物理TCP 1MiB→FakeIP Direct TCP 1MiB** 顺序两臂、4ms/16KiB相同发送节奏，真实Linux kernel SHA/FIN，Direct期间96B Tunnel UDP至少120次持续进展、原双方Stop。签名只选 `[plan029-v3-real-p2-rebuild]`，**不选** steady-QPC 2048、4MiB bulk、ABBA、preconnect、500/700Mbps、sustain、hard pressure、CDN/IPv6；源锁GitHub Action真实SOURCE仍待跑。
- 已有 `PLAN029_H1839_P2_TCP_STAGE` 每128KiB上传和下载各八个真实Windows应用时间戳，但旧汇总只存接连/整段毫秒数。新增纯Stop前日志解析 `normal_tcp_128k_progress_gaps`，严格拒绝漏行/重复/非单调/伪造字节/错误role，计算同一正常臂最大128KiB交付空洞及桶序号，同时保留8个原测量间隔。上传明确包含原4ms pacing，下载包含kernel和OS等待，**不把八个桶说成p99、Rust CPU或纯kernel时间**；Direct相对物理为同VM顺序描述非因果。
- 新Python独立回归7个，接入旧原workflow cheap Python检测；仅对普通1MiB加字段，其余 old bulk/ABBA/10GiB、APP、Rust/Go/NPF/Wintun、TCP超时、Stop、接口完全不变。H1993 CI/原生结果未收时标 NOT_RUN。用结果决定下一个真正值得改的60ms异常阶段，不扩旧矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"H1993 measurement-only ordinary same-source physical-vs-Direct 1MiB existing 128KiB app checkpoints and concurrent Tunnel UDP; no product hot-path behavior change, no 2048 replay or extreme stress, no performance gain claim."}
```
