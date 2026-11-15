# PLAN029 H1893｜签名真实Wintun 128并发：同分片双活、全程UDP和Windows原进程CPU

- [H1892 exact SOURCE签名Action43680192237](https://github.com/lly8666/wbd-next/actions/runs/43680192237) job132710158218，真正Win2025原Go/TLS+Npcap签名Wintun+Rust TX及WSL2 Linux eth0 TCP/TUN，全部job及Action SUCCESS。原客户端固定Wintun源42500–42627和FakeIP目标46112，实际Rust源锁定日志**128个独立Wintun NAT→kernel accept**、`active_peak=128`、每proxyport的shard准确；原Linux内核TCP监听真实accept128；全程保持**126空闲8秒**，第15/31条各64KiB真实回显SHA和FIN，Rust记录两条确属**同一WSA分片1**（最大分片8flow）。Go/Rust产品无每flow线程，测试应用单select loop。
- 1Hz原Windows Go+Rust**进程**在实际128 TCP全部已建立、开始活跃数据之前的静默段有8次Win32实采样，覆盖7.156秒：`GetProcessTimes` kernel0.203125 CPU-s、user0.093750 CPU-s、total0.296875 CPU-s，占单个逻辑核**4.149%**；线程采样数量19、峰值私有40,124,416B与工作集45,887,488B。这不是Rust独占、不是NPF/Wintun驱动ISR/DPC CPU，也不是"128条造成额外4.149%"（缺少同VM 0条TCP空闲基线）。不是0CPU、更不能声称64MiB业务CPU/GiB。
- Tunnel UDP始终与P2+128并行：Windows/Linux各**679**个真实内核UDP小包完成（120最低门槛、序号一一对应），Windows RTT **p99=7.133ms**、最大interreply gap**53.641ms**。对应P2物理4MiB64.953ms、Direct121.689ms（1.873x，仍P2性能OPEN）；跨VM的历史比值**不可当提高速度的A/B**。在128真TCP高载场景，Rust真实16-shard事件唤醒432次、WSA枚举3478个Socket事件、`event_take_errors=0`，ready票据峰8、最大等待2ms、总77ms/778票。注意这些是整个SOURCE试验生命周期计数，**不等于8秒静默窗口独有**。
- 原Windows/Linux双owned Stop与WAL、signed Wintun/NPF/HyperV精确原规则恢复均PASS；Win/Linux Rust组件与Go编译PASS，Win platform原128loopback和双FIN仍PASS；本次**是真128 Wintun而非只有Loopback组件**。P1纯Tunnel V3/V4 CPU/GiB历史+9.41%仍OPEN，P2 Direct仍1.873x，Game4 CN/GUI真ConnectStop/IPv6 socket/D1–D5资源满仍OPEN，PLAN029 IN_PROGRESS，不启动030。
- 下一因果关口：**同一原Windows进程、同一TLS/UDP背景、同VM先有8秒0 TCP idle基线，再128 TCP idle8秒窗口**，比较各自GetProcessTimes kernel/user CPU-s/秒、短UDP p99、原Rust实际分片wake，并确保两个窗口至少3个采样。只有这个对照可以近似分离"维持128静默连接的增量进程CPU"（仍非驱动CPU）；随后P1 all-Tunnel同VM V3/V4 CPU/GiB单独解决。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1893 archive exact signed real original Wintun 128 TCP NAT/physical accept, 126 idle 8s and two same shared shard active SHA/FIN, 679/679 Tunnel UDP plus both owned Stop, scoped Windows kernel/user process CPU and explicit P1/P2 limitations."}
```
