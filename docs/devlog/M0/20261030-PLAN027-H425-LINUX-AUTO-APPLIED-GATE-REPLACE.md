# PLAN027 H425｜Linux Auto revision APPLIED 改用真实低频 Quality 证据

回收 H424 生产接线后审核原 Linux Fixed/Auto APPLIED 读回：仍强制 M2 per-record `authenticated_reverse_reports`，Auto 停止旧位图后会永久不能 APPLIED。本批将 **仅 Auto** 的后修订版 APPLIED 条件改为 M4 真实 source + parity copied、同 epoch/lane/PN/F 成熟 v2 匹配后的新正样本/新报告；切档时冻结当前累计 baseline，旧窗口不反复充当新修订证据。Fixed 保留原旧门直到ACK/SACK替换。新增 1024 PN、START/CLOSE 驱动和 v2/慢窗去重单测。未引入另一个 Auto actor/Go包泵。

SOURCE 仍需 Actions 功能验收，新旧性能/真业务不可冒认。①部分、A 未完成、B OPEN、C NOT_RUN、最终OPEN。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Replace Linux Auto stuck per-record M2 APPLIED witness with new revision-local matched v2 authenticated quality and actual M4 source/parity, with bounded regression."}
```
