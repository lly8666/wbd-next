# PLAN029 H1943｜H1942原生证实FIN不是首回包高尾延迟的必要条件，追踪Rust TX反向ready票据

[H1942原始Action43751965403](https://github.com/lly8666/wbd-next/actions/runs/43751965403) SOURCE `cbf01fae158e47b3ef967f5351f978f7cc083768` **SUCCESS**。同一原始Win2025 Go EXE/Rust DLL、Npcap/Wintun及WSL2原Linux内核，真实4MiB物理23.403ms/Direct59.086ms全量SHA/FIN；同owner一次先384 Linux FIN-first，后384 Linux payload-first，每组真物理/Direct A-B-B-A各大小64B/1024B/16384B每路径64条，总768个真实kernel TCP、两端完整聚合SHA `0425643d53f93dc3d3e43049f4934b321b18c14d655400e07a93767db4b17f8a`与Linux真实FIN，Tunnel96B UDP240/240 p99 **14.401ms**，原OS双owner Stop **PASS**。原报告与manifest中SOURCE完全一致。**新组不等recv(0)直接sendall/SHUT_WR，仍照样高尾延迟**：64B Direct首echo p95/p99 FIN-first **15.044/15.568ms** vs payload-first **15.152/15.729ms**，同VM物理0.208/.261 vs0.206/.221ms；1KiB Direct21.088 vs15.174ms p99，16KiB1.627 vs22.479ms，64个经验p99接近最大、不随机化不得拿两个p99之差宣称改善或回退。结论: Linux应用等待FIN不是造成约15ms慢回包的必要条件，H1941 EOF-peek方向不能继续当唯一优化重点。

## 进一步缩小反向路径
- Rust Direct TX `TcpLegDiagnosis`原先`ready_wait_max_ms`汇总所有方向、所有服务，无从知道那些长等待是否发生在**真实服务器→客户端回复数据**。H1943在已有generation-scoped ready入队时间`now_ms-queued_at`基础上，**仅P2原有冷诊断**聚合外腿`outer_read>0`服务次数及票据等待max、>=8ms/16ms次数；同时拆分`outer_read>0且inner_write>0`同轮写内核、`outer_read>0但inner_write==0`需排队、`outer_read==0且inner_write>0`延迟队列冲刷。没有新计时调用、锁/每flow日志、IP或原文、定时轮询、线程、额外socket操作；不触碰`TcpDirectRelay`状态机、H1920任意读写真实进展续票和Stop。
- 单元Rust真计数正/负回归与廉价原生源码测试；原`PLAN029_H1888_TCP_IO_FINAL`只向末尾追加七个十进制整数，旧字段、原历史签名报告兼容。解析器仅在出现新字段时要求七个全部合法、外读服务必须被同轮写/未写精确划分、>=16<= >=8<=总外读；workflow源锁标记`[plan029-v3-real-p2-reply-ticket-diag]`同时需原P2 short markers，严格查真实`p2.tcp_kernel_io_diagnostic.values`及Stop。
- **观察范围**: ready时间只计Rust原队列入队→服务，不能捕捉WinSock内核事件在harvest前的滞留，也不能直接计Wintun RX回注和应用调度；只有外读服务同轮内写与否可证明**Rust软件转发回合是否追加等待**。H1943新源实机4MiB+768小TCP/TunnelUDP/Stop尚NOT_RUN；没有声称真正降低p99/CPU。P1同Rust all/CN/CN/all 4臂CPU仍独立OPEN，绝不能用裸物理0.3s/GiB代表分流规则成本。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Archive signed H1942 768 TCP FIN-vs-echo-first result and add low-overhead opt-in Rust TX reverse-reply ticket/same-turn kernel write diagnostic; native performance exit still OPEN."}
```
