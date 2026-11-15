## H1937 P1 实测回执（补录，原始Action完整结论为FAIL）

[Action43734219846](https://github.com/lly8666/wbd-next/actions/runs/43734219846) exact SOURCE 16742c8：A1 `all` 真实Win2025/WSL2 Rust/Go 50Mbps双向60s、真实TCP/UDP、双端Stop **PASS**，原Windows进程15.1406 CPU秒/0.69839实际收件GiB即21.6792s/GiB，Rust TX6.296875s/RX7.296875s（抽样下界）。B1 `bypass-lan-cn` 真实网络/Stop同样PASS，**但冷启动回执 `cn_rows=8 domain_bytes=180224`，与预期4096非相邻/32不符**，故旧严格 P1 测量门判FAIL；B2/A2未执行，**无全量有效ABBA CPU增量**。这是真实规则规模不匹配，不是Actions假红。后续先查Go `--china-ip-file` 到Rust cold所载规则源，不能放宽4096规模门来凑出CPU赢。

# PLAN029 H1938｜Direct TCP首回包 >10ms：物理连接建立后一次有界首读机会

真实H1931原始Win2025/WSL2 384小TCP(64/1024/16384B，同VM物理/Direct/Direct/物理，每大小64连接)SHA/FIN全PASS但Direct`first_echo_after_half_close`p99为10.696/14.957/6.389ms，同机物理1.225/0.554/2.477ms。H1931原Rust ready ticket wait max16ms（跨整个10GiB采样，不可当小TCP p99精确归因）。**高延迟仍OPEN，不能因为大流量达500/700Mbps关闭。**

源码审查发现原`NativeTcpActor::tick`在`TcpPhase::Connecting`时会从WinSock shard消费`FD_READ`，但在非阻塞外层`PhysicalTcpSocket::poll_connected`成功切换为`TcpDirectRelay`后，只有先前`FD_CLOSE`被观察到才追加续票。可能出现连接期间早到小请求字节、ready事件已被消费、后继无新边沿，初次`recv`晚到的交接窗口。H1938将**每条实际Connected的连接恰好追加一次**到原`RelayFollowups`固定8项FIFO，跟在本轮service之后公平处理。不改变原WSAEventSelect登记/连接失败处置/其他socket不持有新线程；第一次真实非阻塞读如WouldBlock，原`read_armed`会关，直到下一FD_READ，**不做定时自轮询**。原H1920 any-read OR any-write positive progress continuation和零进展停止不动，避免H1916/H1917真4MiB卡死。

原有仅P2手动冷期开启的`TcpLegDiagnosis`增`connected_first_probe_tickets`和ready ticket age≥8ms/≥16ms计数，不增加新时间系统调用，不记录包/地址/TID/凭证。原`PLAN029_H1888_TCP_IO_FINAL`仍保留所有旧字段，额外三个可选整数，旧解析器忽略额外字段；新测试/原报告可比两阶段有无调度尾部。不改普通Tunnel和DNS/UDP。

验证计划：等H1937同Rust P1 ABBA跑完，**独立**一次原生Normal [plan029-v3-real-p2-bulk] + [plan029-v3-real-p2-small-tcp-latency]，现有H1815 4MiB硬门+H1926 384小TCP physical/direct A-B-B-A、与Tunnel 96B UDP和两端Owned Stop；无需10GiB。短场如失败不假绿；若未证实p99改善还需同Windows VM旧新二进制ABBA，不能拿不同Runner p99声称因果性能收益。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Rust Direct TCP safe one-shot initial relay-read after actual physical connect to address missed early FD_READ and first-reply tail; signed real 384-small-TCP proof pending."}
```
