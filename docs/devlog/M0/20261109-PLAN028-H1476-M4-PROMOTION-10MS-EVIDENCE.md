# PLAN028 H1476｜换代真实流量不翻倍，原始10ms缺包正好落在新代交接窗口

同一SOURCE `66fb6b4454b1ce4297ab04efa20c7f931ff12383`，原始[H1473真实Action42595013191](https://github.com/lly8666/wbd-next/actions/runs/42595013191) 比较同VM真实五客户端rotating12→static12两个180秒。新的[H1475纯离线Action42598966200](https://github.com/lly8666/wbd-next/actions/runs/42598966200) SUCCESS，从不可变原始[artifact13663646307](https://github.com/lly8666/wbd-next/actions/runs/42595013191/artifacts/13663646307) 下载每10ms原始应用计数、各世代每500ms Rust M4诊断、原服务端/客户端Stop，以不同复判SHA`8162f42f...`验真。新[离线artifact13664108971](https://github.com/lly8666/wbd-next/actions/runs/42598966200/artifacts/13664108971)原ZIP SHA256 `51acd2423bcd238bf41bb977f0707830cd14c70efd3be19d2961794da7ed67d2`、CRC_PASS，所有离线单元及H1475原始收据通过。

**实际换代流量**：一个Rust共享内核TUN reader、一个生效的TUN发送路由。候选B在原Go TLS/Rust M4收到新代authenticated peer RX之后才正式接管；旧A维持10–20秒受限的RX及在途包并于精确Stop归还资源。通常不向旧A和新B双份发送所有新业务。原H1473 Alice Native M2首份线缆发送总字节rotating3代合计294,216,166，static1代294,143,551，差+0.02469%；两边outer repair=0、frozen retransmission=0。**180秒累计不等于毫秒级峰值**；不能排除双代共存瞬间的CPU/内核队列尖峰。

**换代导致低负载缺包的窗口证据更强**：真实same-clock Alice server/client每10ms共有19,001个计数桶，以累积TX−RX的所有未来最小值消去可以迟到补收的包，rotating12原Alice13个永久缺失出现在39.39/39.40(+5/+3)和132.85/132.86(+4/+1)秒，新Generation2/3 Rust M4首次500ms采样在39.905/133.367秒：分别滞后+0.515/+0.517秒。Original静态不换代5个用户十方向均零缺，rotating另Carol下行缺3，服务端所有租约队列overflow0。Gen首次500ms样本并非真正promotion瞬间，per10ms桶并非逐个网络包抓包，**此为跨原生产物相互印证的精准相关性，不等于证明第一处丢包在某行Rust代码**。

原server Alice TUN delivered-to-route offered331225、client M3 native TUN delivered总331210（含UDP与TCP），差15且server该租约queue0，与Alice独立应用UDP最终缺13方向一致但**不可直接一对一等价**。下一步只在单一原SOURCE、短可控12Mbps场记录新旧代实时间的server RAW TX/内核实际copy、client各代RAW RX/PN replay/M3 TUN写入、旧代Grace终止，再比较真正的第一差分；高压75Mbps server Full/overflow是独立故障域，不要用同一个扩大队列补丁猜两类根因。

保持SOURCE66fb真实600 75Mbps32缺/45 queue overflow严格FAIL、1800真实五用户换代+全部Stop范围PASS而零损Alice351严格FAIL、H1472 8场5PASS3FAIL、H1473 static PASS/rotating FAIL、Windows原Hosted1800 NOT_QUALIFIED、Android物理 NOT_RUN、H998旧热MTU FAIL。PLAN028仍IN_PROGRESS，无PLAN029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"Evidence reconciliation of immutable original Go/Rust 180s five-client 10ms application and 500ms M4 samples; no product or network changes."}
```
