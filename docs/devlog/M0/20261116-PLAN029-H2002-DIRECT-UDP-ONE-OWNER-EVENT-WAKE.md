# PLAN029 H2002｜先验历史，直指原 Windows Direct UDP 10ms 被动探测瓶颈

- 用户要求：先检索前任 agent 方法，再定位后动手，只优化突出问题。H1988/H1991 原 TX 取消重复空WSAPoll，减少无意义CPU；H1989/H1990原WinSock TCP 16 shard WAIT_ANY轮转防优先级饿死，均**未**给Direct UDP实际物理回包加入事件；H1974/H1978源码锁QPC+原业务RTT/ACK/Stop提供真实观测方法；H1995分段上传/下载、同机物理对照、防伪PASS。
- H2000原 Win2025/WSL2 [Action43858907438](https://github.com/lly8666/wbd-next/actions/runs/43858907438) 真UDP 96/512/1200B 各120物理+120 Direct：物理p99 **0.347/0.282/0.350ms**、Direct **21.725/25.684/24.974ms**，Direct全部360条>=8ms，零丢/零错、两端Stop PASS；这不是Tunnel UDP。H1997真已建连TCP p99 0.699ms尚可；H1998 4MiB unpaced物理51.970/Direct97.260ms，次优先。禁止把普通TCP绝对+0.29ms先改掉。
- 首个物理UDP回包（WinSock UDP UdpSocket.recv）在 `v4_client_direct_udp_actor::poll_reverse_ready` 中只用 `WSAPoll(...,0)`，原Rust TX在无Tunnel/Wintun/TCP工作时 `needs_10ms_poll()` 允许原WAIT_ANY睡到10ms，Direct UDP socket根本不在19个等待句柄集合。三个大小近似相同的14–16ms p50/22–26ms p99与无事件轮询高度一致，但**不算因果已经证实**。
- 最小定向修复：只对**同时最早16条真实Direct UDP物理socket**冷建原WinSock `WSACreateEvent + WSAEventSelect(FD_READ|FD_CLOSE)`，每socket一个有界事件，永不超过16句柄，不造socket对应线程、不改Go/Rust协议、FakeIP、DNS分类、业务重试或Wintun writer；同一个原Rust TX WAIT_ANY从3+16延至最多3+16+16=35（Windows<=64），Stop始终索引0且跨TCP/UDP队列轮换。UDP信号传递原flow key优先检查，仍不阻塞WSAPoll、仍限RX量子；收到原物理回包后原Wintun mailbox/notify机制保持。 `WSAEnumNetworkEvents`在recv后清原socket事件；若信号来时WSAPoll空，也准确复位，防止空转。超过16条Direct UDP（或event无法注册）继续旧10ms有界扫，未测高规模性能不宣称优化。
- 只触发原签名 Normal CN Direct UDP三包长场景 `[plan029-v3-real-direct-udp] [plan029-h1999-direct-udp-rtt]`，核验Windows/Linux compile、720个真实UDP收发、三包长物理/Direct p50/p95/p99/max、原TCP/Tunnel基础双端业务与owned Stop；绝不自动开4MiB/higher-rate/128、P200、极限16k。这轮源码和真实网络**NOT_RUN until CI**，先验收收益后才谈下一个问题。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2002 narrow event-driven wake for the first 16 ordinary Direct UDP physical sockets, preserving prior bounded fallback, existing single Rust owner/Tunnel/Stop; original signed p99 A/B not yet run."}
```
