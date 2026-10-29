# PLAN027 H424｜Linux Auto 30字段 readback 转低频 + 旧RX bitmap停用

在 H423 修复后，将原Go TLS已授权Native mode2 Auto 接收端不再分配、填充旧每 record `RxFeedbackState`，只保留四窗口、认证v2摘要与原Health 15s/90s。Rust唯一 TX 控制worker 出 START/CLOSE、认可真实M4 firstsend F、配对发送历史以及5s slow cohort；原30字段 C ABI readback 从此低频统计读取，不再让 Auto 自证旧M2个别ACK。源窗口/质量报告可独立唤醒 TX，不让单向业务因等待TUN阻塞反馈。Fixed/off的旧M2尚待外层 ACK/SACK接替，Go Auto表现也尚待真双端测试。

Actions 完整 SOURCE 验证 **待回收**；不能把旧 native Health 或源码check成功说成新协议A2/A4通过。§0 ①PARTIAL、②A未跑、③B未完、④C未跑、⑤未完。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Linux native Auto readback now uses exact local matched low-rate F/Quality cohorts, and no longer allocates or feeds old per-record M2 RX bitmap; source pending Actions."}
```
