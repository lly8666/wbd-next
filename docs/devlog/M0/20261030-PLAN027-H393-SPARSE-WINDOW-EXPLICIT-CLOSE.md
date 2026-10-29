# PLAN027 H393｜稀疏 1024PN 窗口不能从首包起算成熟
2026-10-30。按 PLAN027 §3 审核 H388 的 4RX/16TX 低频窗口：接收端原来 `opened_at+3s` 即可成熟，但 1024PN 窗口在低 PPS 下可能持续超过3s，尚未发出的未来 PN 会被错误计为 WAN 损失。现在要求**显式的、未来由现有认证控制承载的 close 事件**；本机收到 close 后再等待3s成熟、10s过期。无 close 保持 `NotMature`/UNKNOWN，不跨机比较时钟；迟到/容量/代次仍有界。

新增 `r2_plan027_receiver_requires_closed_window_for_maturity` mandatory native 反例：9s 未关闭窗口仍未知、重复 close 拒绝、close 前本机时间拒绝、3s/10s 边界；原有三个 RX 回归同步显式 close。此时只有 Rust source primitive，真实双方加密 announce/close 和生产 Auto 仍未接通，不能宣称 phase1 或 A PASS。H392 的 native/治理 Actions 如在途先收，不重复派同源。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Correct source-only low-rate receiver maturity to require explicit close for sparse windows and pin a required negative regression; live sender/receiver product integration remains NOT_RUN."}
```
