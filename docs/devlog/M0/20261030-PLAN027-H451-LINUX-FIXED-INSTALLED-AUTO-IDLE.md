# PLAN027 H451｜按最新§0.1移除Linux Fixed多余质量门，修复低频空转

最新 [PLAN027§0.1](../decisions/M0-PLAN027-LOW-RATE-FEEDBACK-CLOSEOUT-20261030.md) 覆盖H444“等待两个1024PN认证质量窗后Fixed Applied”的旧做法。Linux e.quality_tx / quality_rx 现在仅 Auto 开启，`bootstrap_only` 字段与无期限遗留机会全部删除；历史名为 `wbd_m0_embedded_go_fixed_commit_mature_m2` 的C ABI仍稳定，源码判据改为同一原Go TLS epoch/feature7+当前真实 Rust `fec2_live_tx` 已安装指定revision/profile 且M4 worker在线，此时Fixed *本地配置 Installed Applied*，不依赖旧Receipt、3s窗口、伪造ACK或业务复制计数。实际两端业务/对端资格仍必须由B证据另验，禁止把本地Applied视为吞吐PASS。

同时修复 Linux `LinuxQualityTx` 真实Auto idle空转：没有新的M4 firstsend时 `due()`和 `next_signal()` 共同保持false，最后一个窗口CLOSE后记录最新已发送PN；仅新的数据才允许新的1.5s START，实际拒发CLOSE后500ms再试，不陷入0ns忙循环，缺样本保UNKNOWN，Health仍独立15s。单测断言无业务无due，先有一次首发观察才START。**H451 CI/真实场景尚待验证；不标功能完成。**

```feature-impact
{"kind":"none","ids":[],"reason":"Active PLAN027§0.1 source semantics for Linux Fixed installed config/Auto idle; feature card promotion deferred pending real CI evidence."}
```
