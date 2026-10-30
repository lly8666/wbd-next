# PLAN027 H428｜两端稀疏窗口的真实 M4 firstsend 与定时唤醒

H427 core允许在认证START预告的1024PN上限内安全缩短CLOSE。原始 Linux TX owner只用M4 copied/uncertain/unsent已结清的最后PN，Windows原 Rust NPF owner要求区间内没有pending driver结果；超过2s且见首次真实DATA时执行 close_prefix，不虚构F或烧未来PN；满窗旧条件仍有效。Windows原TX在2s CLOSE、1.5s新窗、RX3s Quality成熟、原Health独立到期时唤醒；Linux TX在2s CLOSE时唤醒。无Go逐包热路径、无跨流HOL、无另一密钥/PN分配。新的source native Actions必须验证；历史Auto稀疏Smoke失败不删除，Fixed/off旧M2及ACK/A/B/C尚开放。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Wire 2s sparse bounded Quality CLOSE to original two-OS M4 driver and native Health/receive-maturity scheduling; native verification pending."}
```
