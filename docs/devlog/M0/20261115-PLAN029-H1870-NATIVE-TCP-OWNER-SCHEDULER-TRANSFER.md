# PLAN029 H1870｜Windows native TX调度、搬运和唤醒优化候选

- 先收H1867 [Action43648334316](https://github.com/lly8666/wbd-next/actions/runs/43648334316) SOURCE `45ae468f`：同VM真实V4/off→V3/all各50Mbps/60s、owned Stop PASS；Windows CPU/GiB 18.5469→20.2921（+9.41%；总CPU 12.9531→14.1719秒）、小UDP p99均47ms。后端不同、驱动CPU及最老队列年龄NOT_MEASURED，P1性能OPEN。
- H1868 [Action43648756279](https://github.com/lly8666/wbd-next/actions/runs/43648756279) SOURCE `11a1daaf` hard8签名压力：16新Direct/5回声/11未回复（未typed不可全归因硬满），旧Direct心跳11、新Tunnel进展、到期后新Direct和双owned Stop PASS_SCOPED。TCP buffer、DNS三表满及队列年龄仍NOT_RUN。
- 只改Rust Windows：无pending Direct或DNS NAT时跳过`listener.accept`与TCP服务函数；实际pending/active继续有界处理，closing NAT按deadline恢复，TCP53不被关闭。回程TCP和DNS已拥有Vec直接送原有256有界TX→RX channel，只有物理UDP需要从scratch复制一次；满channel时TCP保序回退到actor队首、UDP允许局部丢，RX消费后继续唤醒TX。
- 成功入队的1–32条回程现在该轮只唤醒RX一次，**不等待凑满**，RX满批非阻塞重检/Stop事件仍照旧。原relay每次新建64KiB零数组改为每generation actor首次有实际relay才分配一份、跨至多8条服务复用，计入局部8MiB保留容量。
- 新纯测试：无NAT不做accept，DNS TCP映射仍可accept；Owned返回Vec指针不变；scratch尺寸不够拒绝、无输入不清零。未把10ms调成1ms，未完成IOCP/WSA readiness；大量空闲flow中少量活跃flow的真实性能仍待独立工序，不称本提交消除了该架构缺口。
- 本批仅新SOURCE候选，Windows/Linux CI编译和签名P1/P2均NOT_RUN；由提交自动Action收事实，不引用旧绿灯当本SOURCE通过。不改TLS/FEC/旧WFP/MTU/028矩阵或030。H1866真实IPv6 socket NOT_RUN、Game4 CN、GUI实连及DNS/资源满其他出口继续OPEN。旧governance-maintenance H1869三项冻结SHA错配不当成新native联网失败。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect in-flight H1867/H1868 and stage bounded native Windows TCP idle service, move-only reverse queue, batched notify and shared scratch candidate; no performance promotion."}
```

### H1871｜治理长度回收（不改 H1870 原生代码或实测 SOURCE）

- H1870 push 的 Governance 首个失败为 `SCOPE_AUDIT_FAILED: unbounded context_refs`（cursor 9条超过限额）；功能目录 `feature card must be bounded regular JSON`（16KiB）。收敛 cursor 到8条、删除本批重复新增的两个 verification 行，**不删除任何历史已登记的验证**；两项H1867/H1868真实信息仍在本页和H1870 evidence，功能卡summary保留索引。
- H1870 Rust/Windows/P2 Actions 在途，本H1871仅元数据，不再次dispatch标记，不把旧Source结果推为当前代码真实PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1871 fix only H1870 metadata bounds after actual first Governance failure, retaining historical evidence and source-locked Windows test."}
```

### H1872｜Windows Rust 编译首错（真实P2尚未运行）

- [H1870 Rust component Action43660216474](https://github.com/lly8666/wbd-next/actions/runs/43660216474) Windows失败在 `v4_windows_native_split.rs:687`：旧 DNS SERVFAIL 单测把改成 `NativeReverse` 的返回值与整数做 `>=40`，Rust `E0369`，业务/Stop **NOT_RUN**；Ubuntu组件成功、native-functional分组通过。非Windows网络失败，亦非内核/Rust relay实测PASS。
- 本SOURCE仅修测试：从新返回类型拆出既有 `Owned(Vec)` DNS reply，按原IP/UDP/DNS字段断言；生产算法、队列/唤醒、Go/OS/WAL完全不变。按同一个P2 SOURCE marker构建/验证一场，保留前一编译FAIL。

```feature-impact
{"kind":"none","ids":[],"reason":"H1872 fix original Windows-only Rust test signature after H1870 move-only DNS reverse; actual network still NOT_RUN."}
```
