# PLAN029 H1915｜Rust TX 原生分腿TCP：仅有未完成工作才再次调度，不因成功字节而自旋

- **已复现成本**：H1909原签名Win/WSL2 10GiB二进制 `64f6819460f7f950f13bc7d10659a6f4552b28b6`，另一次H1913重用**完全相同的原Windows EXE/Rust DLL/Linux binary**，两次均各自4段原真实TCP/Tunnel96B UDP/双owned Stop SUCCESS。H1909 Rust relay 231,572回合中零进展87,237(37.67%)；H1913 274,595回合中零进展93,796(34.16%)，有效ready队列峰均为1、最长等待2ms。原Windows进程Direct增量CPU/GiB首次单向+11.210938、双向+9.317708；复测+9.062500/+7.630209。CPU额外开销长期存在，但跨VM不同数字**不能**作为严格代码因果A/B。
- H1890之前已实现两个内核TCP腿各自`FD_READ/FD_CLOSE`使能、`WouldBlock`解除读取资格；本SOURCE再删一个确认的无工作调度环：`NativeTcpActor`之前仅因为`tick.bytes_read>0||tick.bytes_written>0`就自我`to_requeue.push(port)`，即使该服务已把所有新读数据直接写到物理Socket、`tick.buffered==0`且每条腿单次read小于64KiB，仍立刻做一次无事件的下一轮读写，再次排队无新工作。H1915只在`tick.buffered!=0`（仍有待发旧数据）**或**任一腿读取达到64KiB最大量子（可能仍有更多内核待读数据）时保留有界立即self-ticket；其它短读+已全部交付时仅由原16固定WinSock分片上的实际`FD_READ|FD_WRITE|FD_CLOSE`再唤醒。任何错误/Stop/EOF退场和global allocated 8MiB背压、两个内核腿一致的顺序、有限MAX_QUANTUM=8、公平性、TCP NAT generation与FakeIP返回都不变。
- 新增原Rust冷聚合`relay_progress_no_self_ticket`/`relay_progress_self_ticket`在同一`PLAN029_H1888_TCP_IO_FINAL`源锁定严格收据中输出。签名Python parse必须两值均为非负整数，且总数不超过真实`relay_turns`；不通过则Action fail-closed，不以静态单测代替生产。新增Windows Rust predicate用例覆盖无进展/小量直送/64KiB两向整读/有界缓冲尾部，原真实WinSock 128对loopback共享事件、双腿FD_READ独立通知、FIN/半关闭、短写/WouldBlock等原平台测试仍运行。
- H1915 **新SOURCE未运行**，commit marker将触发实际Win2025/WSL2签名原产品**长10GiB**：每路径2GiB单向和每向1.5GiB双向（物理及Direct先后）、Windows原Go+Rust user/kernel CPU秒/GiB、96B Tunnel UDP全覆盖与p99、原双方真实SHA/FIN/Stop以及Rust Drop计数；这次由于生产Rust已改动**严禁H1909二进制复用**，按新源码重新构建。新旧WindowsVM不同，不得因零进展回合减少直接宣称CPU/GiB或p99因果提升；后续再作同VM编译策略A/B，重点driver CPU独立计量。PLAN029 P1/P2性能仍OPEN、GUI/Game4/IPv6/D1–D5仍OPEN、PLAN030不启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1915 changes actual Windows Rust NativeTcpActor progress requeue policy: only pending tail or full64KiB read self-enqueues, otherwise existing FD_READ/FD_WRITE/FD_CLOSE event; cold signed counters added; performance NOT_RUN."}
```
