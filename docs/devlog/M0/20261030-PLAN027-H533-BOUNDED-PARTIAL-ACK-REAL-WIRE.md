# PLAN027 H533 — 最新用户表演式机会重传授权、原ACK旧洞放弃

**不复活旧门**：外层只是可选、低CPU的 TCP-like 机会重传。撤销6–10%下限、追完整丢包/业务恢复比例、每条缺口精确证明和额外 M2 反馈。保留R≤0.10F上限、稀疏绝对资源和8MTU突发、每record最多一次同原PN/Seq/密文、真实驱动、认证隔离、MTU、Stop，以及独立业务不等旧洞。

**已恢复旧SOURCE确切证据**：H520 [Action41060763175](https://github.com/lly8666/wbd-next/actions/runs/41060763175) 原Go TLS+Windows签名NPF/Wintun↔Linux WSL2 Rust Normal 10M/25ms/0%，首到双向100%/Stop PASS，Windows F=86402246 R=0 C=227836。H528 [Action41064438830](https://github.com/lly8666/wbd-next/actions/runs/41064438830) 同SOURCE7a每向50M/150ms、真实30%损伤60秒，首到约70%/方向，Windows F=421680421 R=1638 C=2422 六个实际原密文重发、Linux F=415891317 R=328 两个实际重发，双Stop PASS；但累计ACK退休为0、约206k可选影子过期。低R不直接代表失败，更不能为比例强行重传；不过最早外观洞一直不推进，会使后续候选长期被前四组旧SACK挡住。

**最小源代码修复**：Windows `PresentationAck` 与 Linux `OriginalPresentationAck` 在已有真实认证RX处理循环里，仅对同一旧外观ACK洞停滞≥600ms且有后续认证区间时放弃旧洞，推进只用于表演的ACK到最多256项有界真实区间最后端，清空旧SACK积压，之后持续认证数据可重新发现新缺口。现有ACK/SACK发送函数继续用，Linux复用可发送普通ACK的同一个SACK构建器；不新增数据包类型、额外加密、定时重传、Go逐包路径或全局队列扫描。旧内层M3首次交付/PN/replay/Health/Auto质量绝不从该ACK取得证明。加Windows/Linux各一条256错序+新缺口重新启动的core单测。其他现有一次影子、缓存、预算、真实驱动和Stop代码不变。

H532最新测试结论按SOURCE7a保留：Auto240真实下降一步/Stop PASS；Normal50/100零损PASS；Normal50M/300s Action41067316465已结束SUCCESS待记录完整指标；Linux B idle100/dead106/reconnect三个Actions PASS范围待聚合。C200 Action41069012141真实Action失败，Fixed50和weak100 Actions41069016503/20380 workflow SUCCESS但需提取报告；同源码CPU比较A5 Go首次退出失败，不做速度提升声明。H532治理 Action41068984192 FAIL：fec-auto卡超过16KiB、M0 cursor超过8KiB；H533仅压缩历史卡文字和cursor，所有验收SOURCE/状态/失败/evidence引用保留，治理门不放宽。

**本批冻结仅为候选，绝不宣称PASS**：H533先Action中真正构建新SOURCE原Go+两端Rust，用现成A2 10M/250ms/0%/60s双向正常流量测真实性能/Stop；成功后同一run产物原样复用，单独测真实30%/60s及F/R/C、CPU/RSS/新业务首到/候选接续，无比例下限、不刷seed。之后自动继续Windows B生命周期/GameFEC、A5失败处理、C未覆盖矩阵/长测及整体交付，五项均仍是OPEN。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","normal-off","fec-auto","linux-raw-tun","windows-native-transport"],"reason":"Linux和Windows真实Rust接收端根据认证新数据有界放弃旧表演ACK缺口，开启后续ACK/SACK机会；功能目录归档历史说明压缩不改变任何source/evidence/FAIL。"}
```
