# PLAN029 H1867｜单项P1纯Tunnel空回程轮转小修

- 当前H1866真Windows IPv6原OS Action [43647750349](https://github.com/lly8666/wbd-next/actions/runs/43647750349) 已过装配/Win Go/Win/Linux Rust原build，但real D4 IPv6路由仍在途；**不dispatch第二次IPv6，不混改其SOURCE**。
- H1863同VM一场V4/off→V3/all-Tunnel 50Mbps真业务都PASS、Stop都PASS，Go+Rust进程CPU/GiB A21.0525、B22.5293（+7.01%，绝对约0.0172核），Win小UDP p99 47→62ms；不同V4/V3后端，不能把差额当已证明某个热点。现有`PacketIngress::plain_all_tunnel`已免DATA FlowPin，重复优化它没意义。
- 定向源码检查：`v4_windows_native_runtime::tx_loop`在每个V3 Tunnel packet的forward turn仍调用`NativeSplitWorker::poll_udp_reverse`，即使本generation没有任何Direct socket、DNS pending/queued replies和TCP ready，每轮最多检查三空子队列。H1867只在已有`owner.has_udp_flows()`（覆盖Direct UDP、DNS pending/本地SERVFAIL及TCP active/ready）为真时才进入既有32项回程轮转；原`owner.tick()`（包括1s到期、DNS durable fsync completion、Stop）无条件仍执行，原Wintun事件/原密文/MTU/32量子/公正lane不改。
- 新Rust纯测试：All Tunnel普通UDP不凭空产生回程任务；收到强制Tunnel DNS ticket并本地SERVFAIL时，`has_udp_flows`为真，仍通过原Wintun回程生成回复，随后清空。Windows/Linux纯测试在提交时**NOT_RUN**。
- 唯一`[plan029-v3-real-p1-tunnel-ab]`标记：一Action一个同VM顺序50Mbps A(off旧V4)→B(on V3/all Tunnel)，同SOURCE编译/源码hash复用，真实CPU/GiB、RSS、p99/最长交付空洞及双端owned Stop测后方能宣称改善。若无明显新信息，不连续刷P1或调TCP buffer。H1866 IPv6/GUI真Connect/Stop/Game4 CN/D1–D5残项继续OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Skip proven empty V3 all-Tunnel reverse queues while preserving real DNS SERVFAIL/TCP/UDP work, then run one scoped same-VM P1 A/B; no P2 or D4 duplicate dispatch."}
```
