# PLAN029 H1890｜按 WinSock FD_READ 分腿停空读：真实内核证据驱动的第一刀

- **真实上一SOURCE已保存** H1889/H1888 [Action43673823662](https://github.com/lly8666/wbd-next/actions/runs/43673823662) Windows2025 original Go/Npcap signed Wintun Rust CN+WSL2 Linux 4MiB物理58.616/Direct111.000ms（1.894x；P2仍OPEN），Tunnel小UDP120/120、p99 3.603ms、原双owned Stop PASS。原Rust TX Stop后typed诊断外侧物理socket空read `WouldBlock=119/189` (63%)，内侧15/110，队列最大等待1ms，event wake46、relay no-progress33/207，明显先于全局ready FIFO优化。
- **H1890仅修改两腿TCP读通知状态**：一个`TcpDirectRelay`独立持有两个`read_armed` bit。原Rust TX在两内核Socket已成功注册现有`WSAEventSelect`后显式`enable_event_driven_reads()`；独立组件/其他没有事件泵的调用者仍保持原有`service_once`轮询语义。真实actor一次`WSAEnumNetworkEvents`分别检测每个socket的`FD_READ|FD_CLOSE`才调用`pair.note_read_event(inner,outer)`，不允许另一腿`FD_WRITE`或读事件错误唤醒本腿。某腿仅在真实read返回`WouldBlock`时解除该腿read权限；`FD_CLOSE`重置为可读供`recv(0)`传播FIN，另一腿读写和已有VecDeque queue清空不暂停。
- 微软官方`WSAEventSelect`文档明确FD_READ level-trigger、recv会重新使能通知；本文遵守真实Socket事件语义，且首次relay因CONNECT阶段可能已经消耗FD_READ，所以起始保守两腿可读，第一次WouldBlock之后才受新gate约束。无需每flow线程、0ms poll、多次空read试错，不改16个共享事件分片、TX owner、NAT代际、8MiB allocator预算、TCP53/UDP/纯Tunnel路由、短写、半关闭和Stop。单TX现存事件收集只是增添两个独立的bool状态，不增加新的Kernel事件注册或call。
- `RelayIoCounts`新添`event_suppressed_reads[inner,outer]`字段（按服务回合非每字节），签名P2原`PLAN029_H1888_TCP_IO_FINAL`在Stop后必需新增对应两个合法字段，保留之前原有读写WouldBlock/WSA标记验证与exact SOURCE。重要：跳过读**不是**测得用户/kernel/driver CPU降低，不把不同WinVM旧/新成绩宣称真实A/B加速。
- 新Win/Linux真实loopback单元测试：两条独立内核TCP最初各一次WouldBlock，再无FD_READ时调用服务必须为零读；收到内侧FD_READ只让内侧转送，物理外侧尚未收到事件不能空读；收到外侧FD_READ独立完成逆向回传；最后FD_CLOSE可单独解除两边read gate，两个真实FIN成功、无buffer丢包。保留此前Win2025真实128对Socket同分片两条活跃`FD_READ`与短写/背压旧单测，且签名原Win/WSL2 4MiB+持续TunnelUDP120/120+双owned Stop 必须完整SUCCESS。**H1890 SOURCE未运行**，编译和真实场景按首错修复。
- 真128条Wintun长时间idle＋少量active、同VM新旧调度CPU user/kernel和P1纯Tunnel +9.41%CPU/GiB尚未测；Game4 CN/GUI真ConnectStop/IPv6真socket/D1–D5资源满仍OPEN；PLAN029 IN_PROGRESS、PLAN030不启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1890 narrowly gates each Windows kernel TCP leg recv after true WouldBlock until that leg's actual FD_READ/FD_CLOSE, preserving FIFO/FIN and old platform callers; signed tests pending."}
```
