# PLAN029 H1903 | 签名长窗口物理与Direct TCP同VM CPU对照

- H1902 源锁定签名 Action 43688959038 成功：Windows2025 original Go/Rust、签名Npcap/Wintun、WSL2实际TCP。512MiB单向目标500Mb/s实测499.965Mb/s；256MiB双向各发目标聚合700Mb/s实测699.760Mb/s。严格都略低于目标，未宣称达标；SHA、双方半关闭、Tunnel UDP96B全覆盖、双侧owned Stop PASS。
- H1902 原Go+Rust进程单向CPU 13.6875秒/GiB（用户态3.28125、进程内核态3.5625 CPU秒/0.5GiB）；双向12.125 CPU秒/GiB（用户态2.1875、进程内核态3.875 CPU秒/0.5GiB）；Tunnel小包p99单向1.495ms、双向3.066ms。原测试仅8.59s、6.14s，且没有同体量物理基线。
- H1903 新SOURCE明确仅签名私有Normal CN、原产品一代Wintun及同一Go+Rust PID。一个WSL2物理Linux监听端口46118依次接受物理源绑定Windows TCP与真实FakeIP Direct。每路径先2GiB单向500Mb/s目标（理论34.36秒），再双向各1.5GiB同时700Mb/s聚合目标（理论36.81秒），两路径总约142秒、10GiB流式网络字节。每次64KiB固定缓冲，真实两端SHA、FIN。只用同VM物理控制同源结果，非跨VM。
- 每阶段同时运行96-byte真实Tunnel UDP、按Windows高分辨率单调时钟划六段：pre/physical500/physical700/Direct500/Direct700/post。每个负载阶段至少750个有序小UDP回包，独立p99与间隔。按阶段读取原Go+Rust PID进程用户/内核CPU秒/GiB、另测Python generator PID和全Windows机器忙碌率；Direct减物理差值保持有符号，不伪造driver ISR/DPC归因。
- 不变更生产Rust/Go/Npcap/Wintun/UDP算法、不增加Rust每flow线程或空轮询；长流量每阶段最多180秒、单真实负载子进程400秒、Tunnel最多60000个独立96B包，超出保留首错。原H1898 512/256MiB路径及老证据保留；长量需要显式 [plan029-v3-real-p2-long-ab]、bulk、500-700三锁协同且WSL必须额外收到p2long argv。完整Windows/WSL2 signed Action、SHA、FIN、每段UDP及双方Stop是验收条件，新SOURCE目前NOT_RUN。
- 下一阶段依原进程用户/内核CPU的同VM增加量、物理与Direct吞吐差、整机忙碌率选择优先优化的TX/Wintun调度位置。P1纯Tunnel CPU/GiB、Driver CPU、Game4 CN、GUI真实Connect/Stop、IPv6原生socket和D1-D5剩余任务仍OPEN，PLAN029 IN_PROGRESS，PLAN030未启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1903 archives short signed 500/700 original process CPU and adds source-locked long sameVM physical versus Direct 2GiB/1.5GiB full-duplex CPU, SHA/UDP and owned Stop control; no production hotpath change."}
```
