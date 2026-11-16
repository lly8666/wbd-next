# PLAN029 H1989｜先收H1988组件，再修普通 WinSock 跨流调度优先级

- H1988 SOURCE `22c44a70e73d8bf3ff84930b094cd39792948b6d` [Windows/Linux Rust组件Action43832554872](https://github.com/lly8666/wbd-next/actions/runs/43832554872) 全 **SUCCESS**：Win2025 job133181114319 实际 `plan029_ready_dns_drain_never_repolls_one_pending_socket_per_packet` PASS（103与105窗口各包含）；Linux job133181113859 PASS。该SOURCE [治理43832554971](https://github.com/lly8666/wbd-next/actions/runs/43832554971) SUCCESS；[M0源码预检43832554963](https://github.com/lly8666/wbd-next/actions/runs/43832554963) cheap/Windows Go/两Rust组件完成绿色，收件时最后Linux peer persona还 IN_PROGRESS，**不写成整Action成功**。无真实 CPU每GiB/p99改善数据，未启动新的两端网络场景。
- 另一条普通多连接首要调度缺口：原 TX 用 **唯一** `WaitForMultipleObjects(WAIT_ANY)` 同时看 Stop/Wintun/RX通知/16个 WinSock shard。此前只旋转三**类**组，16个 TCP shard 的内部索引 **始终升序**。两个普通 Direct TCP 内核 socket 同时 ready 时，Windows 优先返回低索引，这可能让持续活跃的低shard饥饿其他流的 FD_READ/WRITE，增加跨flow队列年龄；与 H1974 61ms 的因果关系**未确证**。
- H1989 不新建Wintun线程/读写owner、Timer或WinSock句柄，不全表扫描：保留原三类轮换和 Stop index0；在已有最多19 handle 的 wait 参数中对16个 TCP shard 作一次固定长度旋转，真正某 shard 被 WinSock 唤醒后让 **下一个 shard** 带头。仅进 `WAIT_ANY` 前做16个栈位重排（不是每packet）；纯Tunnel仍精确3个句柄、不变。原 Rust `note_tcp_socket_wake(kind-3)` 逻辑使用原索引，不错映射到 NAT。
- 新 Rust 单测对三类组 ×16起始shard，验证 Stop优先、每组恰含唯一 0..18、每个TCP shard能先于其他TCP shard，且无TCP产品仍3句柄。当前 SOURCE **CI/实网 NOT_RUN**，先收自触发的原source构建/单测；不为此重跑H1974 2048旧probe，不造压力矩阵。
- 仍严格保留 H1974真实五次61ms与4次重传、H1978原native FAIL、D1–D5/P1–P2等OPEN；这一改动只消除一个代码可证明的跨流公平偏差，不伪称尾延迟已修或性能验收。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1989 normal WinSock WAIT_ANY TCP shard fairness: rotate 16 already-owned event handles after a genuine notified shard while preserving Stop/Tunnel precedence and exact source mapping; collect H1988 Rust component PASS, no new network or claim of measured p99."}
```
