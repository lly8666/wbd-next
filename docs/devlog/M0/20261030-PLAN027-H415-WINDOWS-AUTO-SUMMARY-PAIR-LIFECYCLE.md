# PLAN027 H415｜Windows Auto 低频回报/单 Actor 配对

延续 H413/H414 的接收、发端与真实 NPF F 接线。Windows 原 M4 NativeIO mode2 设置持久 Auto 模式位，避免 Auto actor 暂时 take() 的时间窗口退回旧 per-record M2。真实 M3 验证唯一 PN 的 Normal/FEC2 数据只更新四窗口，不再向 Auto RxFeedbackState 生成 per-record bitmap；Fixed/off 暂时保留旧路径。TX START 真正成功后采样，CLOSE 成功入 16 窗发送历史。逆向认证 v2 摘要严格匹配 Window ID/PN/F/epoch，只在成熟可信时累计 fast 质量与 5s 后 slow cohort，可能修复的 PN 保守归为 ambiguous；未匹配、过期、容量不足为 UNKNOWN，重复摘要不重复增量。复用唯一 NativeAutoActor、Health kind1 与既有 30 字段只读 ABI。

本源码还缺 Linux 对端的真实 START/CLOSE/summary producer、机会式 ACK/SACK 修复，以及 Fixed/off M2 退役；新 SOURCE Actions 仍待完成，不能声称新方案业务通过。A NOT_RUN，B OPEN，C NOT_RUN，最终交付 OPEN。前两笔治理失败原因：H413 feature card 大小、H414 card 未与 impact 同步；本批修正。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Wire Windows original Rust native Auto mode to authenticated v2 matched quality fast/slow cohorts, replacing Auto per-record RX bitmap; not yet qualified end-to-end."}
```
