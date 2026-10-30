# PLAN027 H427｜Windows 低频 Quality 严格限定 Normal Auto

审阅 H425 的 Windows Native owner 认证控制路径发现：`m2_authenticated_kind1_entry` 已只对 `auto_low_rate_mode` 应用 Quality 摘要，但仍在 Fixed/off 的同一 M3 AEAD 控制通道接收 START/CLOSE 并维护四窗口，且处理无效 Auto TLV 之前先刷新 Health。与 PLAN027 §3 “仅 Normal Auto 采样”及 §2 控制能力隔离不一致。

在 Windows owner 原有 kind1 入口先检查 `low_rate_quality/low_rate_signal`：仅 feature7、非 Game、`auto_low_rate_mode=true` 可继续；Fixed/off、Game 或未启用的 Auto 控制返回 INVALID，**不刷新 Health、不建立窗口、不变更 ACK/交付**。沿用既有 AEAD/replay 和 capability，不添加第二控制器。现有同模块 native test 增加 Fixed/off 对认证 START 拒绝、无质量队列污染的反例，再开启 Auto 跑原 START/CLOSE、3s 成熟、唯一数与未发送不退休正例。

此为源码修复，必须回收 H427 exact-SOURCE Windows native Actions；不宣称当前源码 A1/A2/A4 或真实 Windows Npcap PASS。Linux Auto/Fixed 分界已有独立接收拒绝逻辑，仍需整体 Fixed/off M2 退役及网络验收。五项状态：①PARTIAL，②A未跑，③B OPEN，④C未跑，⑤OPEN。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Windows authenticated low-rate Quality signal/report admission is now strictly Normal Auto; Fixed/off cannot refresh Health or allocate quality windows through Auto-only control."}
```
