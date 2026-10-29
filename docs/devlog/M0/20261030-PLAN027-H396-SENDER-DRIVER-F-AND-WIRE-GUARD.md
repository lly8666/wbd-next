# PLAN027 H396｜低频发送窗口真实驱动 F 与远端匹配防护
2026-10-30。恢复 main dca376af1123e9d7b94f7e5382a2ae4a16d2affe、M0 cursor H395、PLAN027 和最近 Actions：40936343251 native 全组 PASS、40936824758 governance PASS；没有仍在途的已登记测试，未重复启动旧矩阵。

- 新增固定 1024-PN/128B 位图的发送端窗口计数器。仅预先宣布 start 且驱动确认后才可能完整覆盖；真实首发 Accepted 才加 F，NotSent/Uncertain、晚到 start、容量缺失均将整个区间标 UNKNOWN，不把本机失败算 WAN loss。重复 PN 不重计，关闭窗口与接收端 3s 成熟分开。
- `SendHistory::assess_wire` 要求远端 v2 摘要的 id/range 和 **first_sent** 与本机已闭合驱动 F 精确匹配，远端不能通过不一致 F 改写 Auto 损失率。此入口必须由原 M3 AEAD/unique-PN/代次认证后调用，不能直接解析未认证数据。
- 将两项新回归加入 recovery required 清单，main push 自动触发 native-functional 和治理 Actions。**此批仅源码基础，尚无新 SOURCE 的 Actions 结果；不冒充产品通过。**
- PLAN027 §0 五项仍开放：线上逐record M2 未退役，双端 start/close/报告/Auto/ACK/Health 未接线，A/B/C 与长测未跑。下一步回收 Actions 后继续双方生产接线，不重复旧 M2 矩阵。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Add source-only driver-accepted low-rate send-window F and authenticated matched-report guard; live Windows/Linux production Auto remains NOT_RUN."}
```
