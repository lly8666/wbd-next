# PLAN029 H1857｜H1856 真P2恢复；下批独立P1同VM顺序A/B

- [H1856 Action43611621095](https://github.com/lly8666/wbd-next/actions/runs/43611621095) SOURCE `c110a982` 真签名Windows Go/Npcap/Wintun Rust Normal→WSL2 Ubuntu单场：原Go/Pinned manifest、Win Go、Win/Linux Rust编译/原build SHA全部PASS；物理TCP 1MiB 281ms，FakeIP Direct TCP 328ms、双向同SHA和半关闭PASS，差47ms（1.167倍）。
- 对照前H1849另SOURCE 37.704s，现完成328ms（约115倍改善），强支持原Go reader join后未设`pcap_setnonblock`导致Rust RX连续最多32次阻塞`pcap_next_ex`的主要延迟假设；**跨SOURCE不能冒充同VM精确AB因果或峰值吞吐**。新session已通过`pcap_setnonblock(1)`与`pcap_getnonblock()==1`的fail-closed gate；未逐次计时NPF读调用。
- 小Tunnel UDP在大TCP全程有120/120不同序号交付，最长交付空洞16ms，原Windows/WSL2内核Stop与owned Defender/WAL归还PASS。报告`p99=0.0ms`仅表示测量分辨率不足，不宣称真实0；P2此一个Normal有界节奏场景**PASS_SCOPED**。
- 原H1850/H1851真P2 38s超时/ready_full=0仍完整保留，H1852/H1855原Action首失败是旧原Go装配manifest，H1856才实际通过。无重复派发。
- 仍待`P1` 纯Tunnel同VM off/on当前SOURCE、非paced大TCP/CPU/GiB/内核/队列年龄、Game4 CN路径、GUI真实Connect/Stop、IPv6/中断恢复、D1–D5残项、DNS压力/慢FakeIP持久化和padding性能；现按既有`[plan029-v3-real-p1-tunnel-ab]`单独派**一个P1 Action**，同工作流只选择一网络场景，未与P2混测。发起时P1结果NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record signed H1856 Direct 1MiB 328ms vs same-VM physical 281ms with full Tunnel UDP overlap and both owned Stops, preserve prior FAILs; trigger a separate P1 A/B only."}
```
