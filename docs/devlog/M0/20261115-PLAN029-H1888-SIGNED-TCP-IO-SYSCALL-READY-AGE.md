# PLAN029 H1888｜真实内核TCP就绪通知、系统调用与票据等待：只冷态计数

- **改动动机**：H1886 [签名ABBA同VM Action43670529264](https://github.com/lly8666/wbd-next/actions/runs/43670529264) 原Windows Go+Npcap签名Wintun+Rust与WSL2 Linux五次TCP会话、四次FakeIP 4MiB各SHA/FIN、Tunnel120/120、Stop全PASS，但A旧队列复制平均78.137ms，B直送平均82.636ms（单组B反慢5.76%），不支持已加速声称。历史H1877/H1882跨VM ratio也不能证明直送受益。优先定位何处真正发生无工作syscall和等待。
- 本SOURCE保留**原16个WinSock共享事件分片、单Rust TX、一个Wintun RX/Wintun回注owner、8个ready flow量子、全部Nat/FakeIP/DNS/Stop**，不改read/write/FD_WRITE/FIFO/半关闭/吞吐/背压决策，不新增线程/定时器/轮询时钟/核心数据拷贝。原`service_once_with_scratch`返回纯整数`RelayIoCounts`（数组下标0=Windows内核listener方向inner，1=物理绑定outer），计数该回合内实读/写调用、具体WouldBlock、短写、**因8MiB allocated/64KiB per leg gate而不读**。不再将“没有写成功”等同于内核WouldBlock。
- `NativeTcpActor`仅在已有`WBD_PLAN029_P2_RELAY_DIAG=1`（单一签名CI P2由原Go主程序传给Rust）时累计16分片真实WSA事件数、WSAEnum socket扫描次数、FD_READ/WRITE/CONNECT/CLOSE、失败保守入队、有效`(port,generation,monotonic-enqueue-ms)` FIFO票据的**实际就绪队列等待最大/总和/样本数**、读取/写入与零进展回合。旧代token依然拒绝，已经入队的port只能保留一票；没有可运行flow就不计伪等待，饱和相同老容量保留。原日志每1秒不加新per-packet输出；Actor Drop只打一条不含IP/密钥/原始包/地址的`PLAN029_H1888_TCP_IO_FINAL`，socket全部保持原先owned drop顺序。
- 签名Normal P2在**原双方owned Stop之后**从原Go client.log解析最终Rust marker：必须恰好一条，有固定27个非负整数键、真实kernel two-leg标签、计数合法与双方向read>=1，否则显式FAIL，不能仅因4MiB业务完就宣布有可用诊断。该typed record随P2结果JSON落盘，CPU用户态/内核态/driver没有归因的仍是`NOT_MEASURED`；不解释为内核CPU总耗时。静态Python测试防缺字段/重复/负值/假source，Windows Rust实际relay组件测试保留FIFO、FIN。
- H1888所有新SOURCE实网与组件**NOT_RUN**；只按 [main单一M0 writer](../../../.governance/registry.json) 使用`[plan029-v3-real-p2-bulk]`准确源码触发一场签名4MiB+持续Tunnel小UDP+Stop，先收编译/测试首错。若诊断显示大量非活动腿的WouldBlock，再在一个新SOURCE限制性地基于真实FD_READ/FD_WRITE切换单腿service；绝不能用1ms忙轮询或复制小分支继续猜。真实128条Wintun idle+少量active、P1 V4/V3纯Tunnel CPU/GiB、GUI/Game4 CN/真IPv6 socket仍OPEN，029IN_PROGRESS、030不施工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1888 one cold source-locked actual Rust TCP kernel read/write/WSA event/wouldblock/ready FIFO age diagnosis and post-owned Stop typed signed receipt; no performance promotion before signed verification."}
```
