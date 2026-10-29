# PLAN027 H421｜Linux 原 M4 首发、RX report 和窗口结果

H420 Linux 低频 TX 状态接真实已验证 M3 RX 报告与 M4 sendmmsg 首发结果。入站只有 AEAD+replay unique 的 v2 report 才进有界 RX inbox；原生 Auto 在创建原 TX/RX worker 时建自己方向的发送窗；每轮真实 copied/uncertain/not-sent 驱动结果更新窗口 F，控制 START/CLOSE 真实 copied 才承认，无新计时线程或 Go 逐包调用。Fixed/off Auto 参数仍隔离。

后续继续接原 TX kind1 发出及纯Auto readback、退休旧 Rx bitmap；SOURCE 编译/原生资格尚待 Actions，不宣称 A/B/C 通过。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Feed Linux Auto sender and receiver quality state from actual M3 replay and M4 kernel copied/uncertain outcomes."}
```
