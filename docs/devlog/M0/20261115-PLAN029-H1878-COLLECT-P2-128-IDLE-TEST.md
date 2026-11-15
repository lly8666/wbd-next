# PLAN029 H1878｜收H1877签名P2，128空闲socket共享事件双活并发回归

- [H1877 real signed Action43663127990](https://github.com/lly8666/wbd-next/actions/runs/43663127990), source `9fa1724a9c4802bed3889cd2480b6e64595f5566`, original Windows Go/Npcap/Wintun/Rust Normal CN 与 WSL2 Linux 同SOURCE，4MiB无pace、客户端真实FakeIP Direct TCP / physical sequential same-VM: 物理50.606ms vs Direct141.030ms，**2.787倍、额外90.424ms，P2性能仍OPEN**。上传物理19.485/Direct48.403 (+28.918ms)；回传物理16.117/Direct77.939 (+61.822ms，主要新增阶段)；建连11.681/10.350ms。两端4194304字节和同SHA，半关闭/原应用完整。
- Tunnel UDP同时覆盖Direct整个生命周期：Windows与Linux唯一交付各120/120，Windows p99 4.283ms、最大回包空洞29.606ms；真实双owned Stop，NpCap和HyperV等精确恢复及原CLI退出PASS。这证明H1877事件分片没有使此单flow真业务停顿，但不证明高并发、CPU收益、零漏事件；不能把源H1875 2.792倍与本次2.787倍(不同VM)当真实A/B。
- 为直接攻击 WinSock 多socket共用manual事件的最危险语义，新加 **Windows loopback 128对真实内核TCP socket** 单测：128张已注册FD_READ/FD_CLOSE、空闲时不应唤醒；两条选同一事件分片同时写各1字节，原子复位第一条并枚举其余socket后**两条均必须读出**，126条完全空闲。只有这一真实WinSocket局部单测可以校验组事件不丢第二条FD_READ；仍不是128路Wintun全业务、多代NAT压力测量。
- 本批修改仅wbd-platform的测试，无生产算法改动。H1878新SOURCE Windows tests尚**NOT_RUN**；通过后继续源锁定的同一VM调度前后P2和高连接数场景（用户+内核CPU、就绪队列年龄、空系统调用/唤醒、小包p99）。P1纯Tunnel另一工作项，D1–D5/GUI/Game4/IPv6未闭环。029仍IN_PROGRESS。老H1876编译E0502 FAIL保留，H1877修复记录保留，不启动030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1878 source-locked signed H1877 real P2 collection and Windows 128-idle two-active same-WinSock-event safety regression candidate without claiming P1/P2 performance."}
```
