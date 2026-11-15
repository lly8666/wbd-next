# PLAN029 H1891｜收签名 H1890：FD_READ 分腿门控真实少空读，P2仍OPEN

- [H1890原生Action43676932963](https://github.com/lly8666/wbd-next/actions/runs/43676932963) exact SOURCE `6f75fc145aed1ad1e7a2e4e4ddf40f10f45067c6`，Win2025原Go／签名Npcap/Wintun／Rust V3 CN selective FakeIP + WSL2 Linux真实物理TCP及TUN，物理4MiB47.656ms、Direct131.645ms（**2.762倍，P2仍OPEN**）；双端4MiB同SHA和半关闭、Tunnel UDP双方120/120且覆盖Direct全程、Windows p99 2.269ms/最大gap19.477ms，双owned Stop、OS/驱动恢复和整个Action **SUCCESS**。
- 原Rust TX Stop后严格类型终结收据：物理外腿read调用77、WouldBlock**7**，H1888上一独立真Runner同4MiB物理外腿189次read、WouldBlock**119**；空read个数减少112/119即94.1%，`outer_read_event_suppressed=119`证实新的独立FD_READ gate在原活跃回合跳过没有对应event的read。旧新不同VM，不能将读次数变化直接换算为CPU或延迟收益。新内腿read116、WouldBlock18，外腿write98、WouldBlock2，内腿write80、WouldBlock12。ready票据213、峰值1、最长等2ms，WinSock事件49次、socket枚举92次、失败0，零进展36/207。
- 完整Windows2025 wbd-platform56/56（含真实128对loopback同分片双活事件、两腿空读disarm/FD_READ rearm/双FIN），Rust engine 89/89、probe91/91和Linux组件PASS；原Go编译及Linux原对端同SOURCE PASS。这是按WinSock语义减少空调用的功能和计数成功，**不是P1 CPU/GiB或P2 wall-clock PERFORMANCE PASS**。
- 接下来的主要风险是共享WSA分片在**真正128条来自Wintun原应用的长idle连接＋少数同分片活跃**时的丢通知、公平性与Stop，必须用签名真实OS socket场景证明，并测Windows CPU user/kernel、FIFO age和Tunnel短UDP p99；P1纯Tunnel V4/V3 +9.41%CPU/GiB独立同VM基准仍OPEN。GUI/Game4 CN/真IPv6 socket/D1-D5满退出也OPEN，PLAN029仍IN_PROGRESS，不启动030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1891 source-locked signed H1890 original Windows/WSL2 verifies real per-leg FD_READ outer empty read reduction 119 to 7 while 4MiB+Tunnel120/120+Stop PASS and P2 performance remains OPEN."}
```
