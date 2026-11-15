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
