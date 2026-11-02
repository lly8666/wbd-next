# PLAN027 H910｜纠正 H909 混合业务 PPS 理论输入

- `scenarios/plan027-h890-normal-on-10m-25ms0-300s.json` 使用真实 packets_weight **5/10/25/60**，96/288/1060/1200B 加权平均1018.6B；10Mbps/dir ≈1227 source PPS。
- `scenarios/plan027-h892-normal-off-50m-25ms0-60s.json` 和 H897 100M 两个同类场景使用不同的 **2/3/25/70** 权重、加权平均1115.56B；50Mbps/dir ≈5603 PPS、100Mbps/dir ≈11205 PPS，取代 H909 错误复用 H890 混合值的6136/12271。只修历史理论输入，不更改真实源报告、业务首到率/CPU/Stop。
- 理论 PPS 不含原始 TCP 线头、M3 AEAD、附加 FEC、驱动传输或 packet bundling；RTT nominal=50ms 只是两个25ms netem delay和，不代表100M已实测的 RTT p99=234/249.31ms。真实高端延迟有负载依赖迹象，不能把CPU低于一个核就声明无队列。
- H908 产品原生105s在途，H903卡住的旧 Action 未重新派发；无代码产品更改。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct source-specific PPS estimate from actual declared packet weight scenario files; no product, fixture or feature behavior change."}
```
