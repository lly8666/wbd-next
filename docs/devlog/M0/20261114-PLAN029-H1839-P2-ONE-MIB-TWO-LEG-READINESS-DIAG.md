# PLAN029 H1839｜先收真P2失败，用应用层+内核两腿双向收据定位停滞

- SOURCE `33e2f79352469d62e3025176670fd03d450e554a` [签名P2 Action43593094309](https://github.com/lly8666/wbd-next/actions/runs/43593094309) 真实Windows2025原Go TLS/Rust signed Wintun、UbuntuWSL2：原Go/Win+Linux Rust构建组件success，Windows真实客户端OS Applied；真实 CN DNS Direct UDP、32KiB TCP half-close先成功（454ms）；**同VM普通物理TCP 1MiB=281ms**。Linux物理内核TCP服务端第二次确实收到了1MiB、匹配SHA、读到EOF并且`sendall+shutdown`成功。但Windows FakeIP Direct 1MiB子进程超过38s上限，`plan029-h1815-direct-windows.log`为空（原夹具仅终态写JSON），全部分段时序**NOT_MEASURED**；故P2 FAIL。保存失败归档ID14113213130、stdout trace和`docs/evidence/M0/PLAN029-H1839-H1837-P2-SIGNED-ONE-MIB-DOWNLINK-TIMEOUT-20261114.json`，绝不把旧6.36s结果冒充新SOURCE的真实时长。
- 连续Tunnel小UDP在该失败Action只看到两端READY，最终数量/唯一回包/p99/最大空洞**NOT_PROVEN**。客户端原Rust stop日志证实真实Join及原生WAL清理成功，但P2报告`stop=NOT_RUN`，因为业务未完成；不报P2 Stop PASS。
- **修正一个错误假设**：`NativeSplitWorker.has_udp_flows`已经把`tcp.has_work()`算进10ms活跃I/O等待；所以不存在“忘记对活跃TCP加10ms”的可证明修复，不重复这种代码，也不粗暴改1ms。风险集中在两腿socket实际read/write、缓冲/逆向交付或FIN，必须凭精确阶段收据归因。
- **H1839唯一诊断新SOURCE**：保留原应用16KiB每块+4ms pacing、相同kernel TCP/IPv4/Tunnel并发、同源Linux guest和Stop，不调量子、Nagle、AEAD或路由。应用在connected、每128KiB上传、half-close、首回包、每128KiB下载都flush有限JSON；Linux接收完成/echo sendall分别flush；Tunnel UDP每128条flush一次。Controller失败保留最后1800字节的确切应用阶段，不再空日志。Rust物理Direct TCP两腿在冷启动仅`WBD_PLAN029_P2_RELAY_DIAG=1`时按现有1s tick打印累计`inner_read/outer_read/inner_write/outer_write`＋queued/resident/active；默认产品不格式化/写记录，不读socket地址、内容或敏感配置，不增加worker/每flow thread/轮询时钟。目的是判断首停滞边界而非伪造高速PASS。
- 此提交标记**恰好一次**`[plan029-v3-real-p2-rebuild]`，触发真实原Windows+Linux SIGNED P2。H1839当前网络结果**NOT_RUN**直到Action终态；不重派其他P2，H1838 GUI Action43593580875 compiled WinForms→Go配置全PASS_SCOPED但仍非网络。后续按阶段确证在kernel socket readiness/FIN/反向Wintun交付第一异常后修机制，优先于CPU或Game4盲改。
- PLAN029仍有产品真实非Actions Normal split、Game4 CN、GUI实体Connect/Stop、IPv6 D4、异步FakeIP慢盘并发/日志压缩崩溃/Stop、P1 CPU归因等OPEN，028限定范围不扩矩阵。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record H1837 true signed P2 failure and add source-locked cold-only kernel relay leg diagnostic plus bounded application phase receipts; no runtime routing or protocol behavior change."}
```
