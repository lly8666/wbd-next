# PLAN029 H2005｜修复 H2002 WinSock FD_READ ACK 后置的丢唤醒竞态

- 已查历史 H1989/H1991 TCP shard rotation/UDP empty-sweep只省CPU，并未直接唤醒物理UDP；H2000原签名真正UDP/物理socket 3包长 p99=21–26ms vs<0.35ms，优先处理显著延迟。
- H2002 `67e4cda32a30c678629ba855d0719ab1427b2791` 先接16个普通 UDP WinSock事件进入原Rust TX WAIT_ANY，保留原16 TCP shards/Stop优先/剩余UDP10ms兜底；Windows+Linux原纯Rust组件 [Action43870817212](https://github.com/lly8666/wbd-next/actions/runs/43870817212) SUCCESS，原签名网络[Action43870817399](https://github.com/lly8666/wbd-next/actions/runs/43870817399)正在收件，暂不套用H2005修正结论。
- 复核Microsoft WinSock `WSAEventSelect` 官方语义：`FD_READ` **level-triggered**、`recv` 是重新启用记录的例程、`WSAEnumNetworkEvents` 原子取出+清事件。因此H2002若**recv后再Enum**，多包到达可能把仍待接收的二次FD_READ清掉，尤其高吞吐UDP；H2005将精确单socket `WSAEnum`确认移至 **recv之前**。如果收到原事件但同一次 `WSAPoll(0)` 空，也完成一次非阻塞recv，WouldBlock会重新武装下个到达，避免旧event永久signaled/或回包竞态漏唤醒；其他事件/无数据绕过。
- 新 `plan029_windows_udp_wake_two_queued_datagrams_rearm_after_each_recv` 真Windows本地内核 socket 单个WSAevent、预先连续排两包、逐包`WSAEnum->recv`，第二轮必须真实WSA event可见且不空转；不是单测伪事件或模拟payload。
- 不动其他内容：原 UDP16事件句柄上限、16k flows hard、单 Rust TX/Wintun RX/Stop/Tunnel、TCP、DNS和None fallback、计时器全保留。独立SOURCE只跑原签名 `[plan029-v3-real-direct-udp] [plan029-h1999-direct-udp-rtt]`：96/512/1200B × 物理/Direct各120、准确SHA/720唯一、双端Stop，原通过为准；本 SOURCE 真实p99/产品回归**NOT_RUN**直到 Action 成功。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2005 narrow WinSock FD_READ event acknowledgement ordering correction and real queued-two-datagram Windows event regression for bounded Direct UDP wake; no extra workers, timer changes, or unrelated optimizations."}
```
