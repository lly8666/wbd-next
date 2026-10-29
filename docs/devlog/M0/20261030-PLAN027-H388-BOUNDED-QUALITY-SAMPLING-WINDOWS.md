# PLAN027 H388｜四接收/十六发送低频质量窗口（源码基础）
2026-10-30。在 H387 Windows WAL Stop 真实验证运行期间，继续可独立实现的 PLAN027 phase1，未重复派发旧 Actions。
- `wbd-recovery::quality_window` 新增每 lane/epoch/direction 1024 PN 位 O(1) 接收计数，不逐记录分配、全表扫描或发 WBC4 Receipt；四个接收窗口固定环，十六个已闭合发送窗口固定环；仅接受本机 M3 认证后唯一 DATA/可能重传的显式输入。
- 本机计时3秒成熟、10秒过期；缺首包前 arm、容量不足、迟到/窗口淘汰和错代次均 UNKNOWN，不伪造零损；3个必测纯源码回归覆盖边界/重复/淘汰。
- 特别说明：实际生产双方 receive/start 的接线、真实驱动首发F、双向 window ID 协议和 Auto 应用仍待完成；线上 M2 每record回执仍ACTIVE，PLAN027 A/B/C未测。本次不是产品 PASS。
- H387 WAL action 40932953430 在途，保留此前40915929426 FAIL。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Add bounded low-rate quality window accumulator and immutable completed-send history with source-locked native regression; update source-only feature limitations without asserting live product."}
```
