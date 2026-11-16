# PLAN029 H1955｜收齐真 P1/P2；同 SOURCE 交错提前物理连接实验

## H1952 原 P1 已收（不可写成理论性能 PASS）
- [Windows/WSL2 原 Action43785063606](https://github.com/lly8666/wbd-next/actions/runs/43785063606)，SOURCE `eb5743986191a9102dda7e0aa085c7b198d0a123`，Artifact14190856869 内 `plan029-p1-ab/result.json`。原 Go/Rust 与 Linux 业务均同一 SOURCE，原 A1 all→B1 CN→B2 CN→A2 all，同 50Mbps、各实际0.6984GiB、CN 4104 IP rows/180224 domain bytes，四 arm app+双端 owned Stop 全 PASS。
- Windows Go+Rust进程 CPU/实际GiB依次20.24714/21.07503/20.67225/20.49327s；All mean20.3702、CN mean20.87364，CN **+2.471%**；CN自身1.93%漂移，All1.208%。原 H1947 +11.942% 与本差异是**不同SOURCE不同Runner实验的参考**，不能算严格“单查表导致 9.47pp 改善”的因果证明。CPU 含 Windows Go+Rust进程但不含主机全 ISR/DPC、驱动和 WSL；100/200Mbps未上探。P1 函数正确性 PASS_SCOPED、性能完整退出 OPEN。

## H1953 原 P2 六 QPC 已收
- [Windows/WSL2 原 Action43785820738](https://github.com/lly8666/wbd-next/actions/runs/43785820738)，SOURCE `acbc130775c3b1d7077b986db3a272c7d7fde738`，Artifact14190448480 内 `mode-results/normal/report.json`。**384/384** 同 Windows 应用/真实 Rust 六 QPC 严格关联；两个 Linux TCP echo 策略各192 Direct，原 4MiB SHA/FIN、Tunnel UDP120/120、持续694、Stop双端 PASS。
- FIN-first：app FIN→首次物理写 p99 **13.984ms**；listener accept→physical connect **17.266ms**，physical connected→首inner.recv **22.730ms**，inner.recv→物理写 **0.182ms**；payload-first 分别 **14.635/17.467/19.488/0.139ms**。两种策略各 **177/192** 的 listener accept 早于 app FIN；**不要把物理已连后等待 app 自身发送的9–20ms 全算成 Rust 问题，也不要加总 p99**。
- 我从 384 原 QPC 时间戳逐流筛 FIN→首物理写>8ms 的**7 条**：6条主要卡在**物理 TCP连接未完成**（accept 在/早于 FIN，connect在FIN后），第7条 physical connected早于FIN但 inner.recv晚约51.808ms，单独保留为未归因。其他大多数已在 FIN 后 <1ms 物理写。物理已收与Rust回写并非主要阶段。
- 同 SRC 4MiB 物理48.427ms/Direct120.698ms = **2.492倍**；upload19.092/57.807ms、download14.781/49.578ms。不是峰值优化 PASS。

## 本 SOURCE 实施：首次 SYN 提前物理连接，签名 A/B，而非瞎猜修复
- 物理 `connect()` 旧路径在内层 `listener.accept()` 后启动，串行两腿 TCP 握手。现在**仅** `m0_v4_probe`+GitHub Actions+原 V3/4MiB/384+原 H1945/H1948/H1953 各签名闸门+新 `WBD_PLAN029_P2_PRECONNECT_AB_SCENE=1` 时，在第一个已分类/已入有界 NAT/已入 Wintun FIFO 的 **Direct SYN**，以 owned物理IP/ifindex+真实目标启动已实现的非阻塞 `PhysicalTcpSocket::start`。
- 同 Rust TX owner 内 `pending_physical` 按 exact proxy-port 持有最先发的 socket，`DirectTcpNat` 既有 max16k 是唯一额度，不另造 worker/event/router/WFP；内层 listener accept 后从 exact port **take** socket 进入**原来的** 16-shard WinSock/POLL CONNECT、relay、逆变换路径。失败保留旧 accept-time socket fallback；未被accept的 SYN 30s 原 pending expire 同时 drop 物理 socket；owned Stop 依字段顺序 drop 在原 socket_events 之前。绝不提前 ACK/伪造接入成功，不接 Go hot-pump。
- 单 SRC 原4MiB业务+原 two-echo-policies384 Direct 交错奇偶 ordinal on/off，每策略 **96 on +96 off**；原 Stop 聚合 source_port/开关/真实 socket.start/accept QPC，Python 与六 QPC、一条真实Windows app按端口+时间双重匹配；任何 missing/ambiguity/失败回退/不一致则 FAIL。报告两臂 FIN→physical first-write 与 connect/accept 的真实分布，不跨OS混钟；p99小样本仅探索性，不宣称严格因果性能合格。
- **正常产品 preconnect 全部OFF**，只有独立原生回执完全 PASS、性能差异方向一致才考虑推广正式冷策略。当前新源码真业务 `NOT_RUN`，PLAN029 D1–D5/P1全范围/P2、GUI Connect/Stop、Game4、IPv6、padding、资源压力仍 OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect source-locked H1952 P1 CPU and H1953 genuine six-stage 384 Direct QPC; one signed-only original same-source interleaved physical preconnect A/B new native P2; keep legacy outcomes and no unproven latency/CN-CPU fix claim."}
```
