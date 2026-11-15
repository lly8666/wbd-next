# PLAN029 H1889｜签名H1888原WinSock真实I/O证据：先修外腿空读

- [H1888 exact signed Action43673823662](https://github.com/lly8666/wbd-next/actions/runs/43673823662), SOURCE `d0b6da290e8afe5a438dac511d7791b649d81cd8`, 真Windows2025原Go/Npcap签名Wintun/Rust V3 Normal CN＋WSL2 Linux真实物理TCP，4MiB无pause两端SHA和FIN、Tunnel UDP双端各120/120，Win p99 3.603ms，最长回包空洞25.164ms，原Windows/Linux owned Stop均PASS，整个Action SUCCESS。对照物理58.616ms、Direct111.000ms，额外52.384ms/1.894倍，P2性能**仍OPEN**。
- 原始 Rust TX 终结`PLAN029_H1888_TCP_IO_FINAL`从原Go client.log在Stop以后严格类型解析，固定有效Source；物理外侧TCP读**189次，WouldBlock119次（63.0%）**，Windows内侧读110次、WouldBlock15次（13.6%）。外腿写95次、WouldBlock2，内腿写88次、WouldBlock20；短写双方0，global capacity gate：inner2/outer18。全量直送7616448B，复制到原有队列837696B，不等于实际内核发送字节。
- 就绪分片：46次共享WinSock事件唤醒，86次socket事件枚举，失败0，FD_READ30、FD_WRITE14、FD_CONNECT2、FD_CLOSE3；ready FIFO峰值1、有效票据213，最大等待**1ms**、累计51ms。真实relay回合207，零进展33。**不能以此归因用户/内核CPU**，但足以将首要空转假设收敛到事件到达后仍对另一条不就绪TCP kernel腿调用read，而不是等待列表拥堵。
- 下一SOURCE只做**按腿 FD_READ/FD_CLOSE 唤醒控制**：在现存TcpDirectRelay两个kernel TCP腿上，起始保守可读，某腿recv确实WouldBlock后该腿不可读，直到该腿现有WSAEventSelect/Enum真正报告FD_READ或FD_CLOSE才恢复，另一腿及缓冲发送/FIN仍进展；既不改原byte FIFO也不拆线程。微软文档`WSAEventSelect`的recv会重新使能FD_READ，FD_READ是level-trigger，因此此规则可不丢剩余数据。必须用Windows128 socket同分片事件和双向FIN/实际签名4MiB＋Tunnel UDP/Stop验证；任何真实返回异常先回滚或首错修复。
- 不将不同VM的1.894/2.453/2.787当旧新代码因果趋势，H1886同VM ABBA旧队列均值78.137、直送82.636也尚不能提供端到端收益。P1纯Tunnel CPU/GiB+9.41%、真正128 Wintun idle少活跃、GUI/Game4 CN/IPv6及D1-D5资源满未测，029持续IN_PROGRESS，028/030不扩。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1889 collects exact signed H1888 true Rust kernel TCP final I/O attribution: outer read WouldBlock 119/189 and max FIFO ticket age 1ms; downstream per-leg event design justified, P2 still OPEN."}
```
