# PLAN027 H422｜Linux original TX 加密低频控制接线

继 H420/H421 新增发送16历史与原 M4 F/RX report 之后，实际 Rust 原 TLS Native TX worker 使用同一 M3 AEAD/PN 发送低频 START/CLOSE 与3s成熟v2 Quality，通过原 M4 kind1 并携带真实 idle；失败 START 不后置认可，CLOSE 失败保留。Auto分支不生成旧每-record bitmap草案。RX摘要最多16条在TX低频轮配对，不给TCP外观ACK验证权。后续继续 mode2 rx旧bitmap完全退休、控制真实结果/调度、Auto readback和受影响Action；本 SOURCE 不提前标PASS。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Wire Linux Auto low-rate encrypted START/CLOSE and matured Quality TX in existing Rust M3/M4 owner."}
```
