# PLAN029 H1942｜用两个Linux原生回显条件定位Direct TCP首回包15ms尾延迟

## H1941源锁结果已核实
[原始Action43740776215](https://github.com/lly8666/wbd-next/actions/runs/43740776215) SHA `6bbaad4b346a16c97d1b5417d03d15aa2c23d7be`、Win2025签名原Go EXE+Rust Native DLL/Wintun/Npcap/WSL2 Linux，**SUCCESS**，原始report与manifest同SOURCE，4MiB物理50.828ms、Direct70.517ms全回声SHA/FIN；384真实64B/1KiB/16KiB物理-Direct-Direct-物理小TCP均完整Linux核收件、FIN，Tunnel UDP120/120 p99 10.339ms，原两OS Stop PASS。签名Rust `PLAN029_H1888_TCP_IO_FINAL` EOF peek inner138/138 outer84/84；但Direct小TCP等首echo p99 **15.642/15.837/15.641ms**，ready-ticket服务1948次中56次>=8ms、4次>=16ms，最高25ms（队列峰值1）。**因此H1941只证明Fin peek安全性，不证明尾延迟改善**。10GiB/CPU H1941 NOT_RUN。

## H1942隔离试验
原H1926 Linux业务在收齐数据后**先等真实FIN(`recv(1)==b''`)，才echo**。首reply多等十几ms可能出自两腿TCP FIN转发、来自Linux的回声到Rust外腿、或Rust内腿/Wintun原RX回注，不能仅凭ticket age猜。H1942保留原第一批384 FIN-first不变；仅带三个精确源锁标记启动**同原客户端和Wintun owner、同TCP46112、再384条** Linux payload-first控制：Linux读满相同内容后马上sendall/SHUT_WR回声，之后仍必须recv到Windows FIN，Windows应用自己仍先shutdown(SHUT_WR)才等echo并核全部SHA/FIN。每批按原 physical-Direct-Direct-physical、三种大小各每路径64条，Linux确实同物理underlay源、双方SHA/源同、总连接数384+384、Tunnel96B UDP全程不断、Stop原有owner负责。两批按顺序而非随机化：结果只用于**区分 FIN 等待敏感性 vs 反向数据延迟**，不是旧新Rust ABBA、更不保证统计显著或消除15ms。

纯`socket.socketpair`两种应用顺序回归及负测试加入便宜治理和原生先行CI；GH工作流只有`[plan029-v3-real-p2-bulk]`、`[plan029-v3-real-p2-small-tcp-latency]`、`[plan029-v3-real-p2-echo-early-control]`同时在同源才能启用新控制，真实原Windows/WSL2报告两组SHA/FIN/Stop任何一项缺失即 FAIL。**H1942尚无原生结果**，不跑10GiB，不动任何产品Go/Rust路径/WinSock/Go热pump。P1同Rust V3 all/CN/CN/all四臂CPU ABBA仍OPEN，物理裸TCP的闲置原进程CPU不能用于归因classifier。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Signed H1941 physical/Direct TCP p99 still OPEN; new source-locked read-only test-only Linux echo-before-FIN control in same original Windows/WSL2 owner, original runtime unchanged."}
```
