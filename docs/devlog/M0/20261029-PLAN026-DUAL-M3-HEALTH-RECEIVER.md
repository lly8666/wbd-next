# M0 PLAN026 — 真实 Linux/Windows M3 Health 接收及同包 Receipt（代码候选）

2026-10-29，main 同任务 epoch1。原 Rust TX/RX、Go TLS 与 OS/WAL、现行 FEC2/Normal 的加密、PN 与重放门保持不变。本批将原 M3 接收 kind1 唯一 Receipt 限制扩展为严格WBC4 v1 Health（10B version/flags/idleNs）、既有Receipt及长度受限非可信Quality可共存，同一认证记录不制造ACK-of-ACK；不新开 wire type、密钥或 goroutine。

- Rust v4_native_health: 添加 canonical Health/WBC4 encoder/parser 和恶意长度/重复版本回放单元测试，必须在M3 unique AEAD+PN之后调用。Quality只是 opaque hint，不能替代真实成熟M2损失证据。
- Rust v4_owner_crypto: Linux real original background RX 与 Windows Normal/Fixed FEC 原始 M3 opener 使用相同解析；Linux standalone Health 记为认证控制，不被判未送达的业务或新的Receipt。Windows M2每lane HealthClock记录认证活性、对端 idle 和真实业务，无线程或新定时器。
- Rust v4_windows_owner / _fec2_owner: 真正验证的 M2 Receipt 仍是唯一可释放 frozen DATA 的渠道；Health-only不能假造反馈或数据交付。
- 当前不是完整 Keepalive：Windows/Linux定时 Heartbeat TX及真实驱动 copied/unknown 结算、服务端90s超时和 FIN Dormant/Wake 的参数/读回、Game2/4 Rust-native I/O 仍 UNWIRED/NOT_RUN。主矩阵继续遵循全代码完成后 Fixed→Game→Auto最后（Health一起测）；不以此提交宣称双端连接正常。

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive","windows-native-transport","linux-raw-tun"],"reason":"Windows/Linux真实M3解密后kind1接收扩展到版本化Health/合并Receipt，Windows M2认证时钟更新；暂无Heartbeat TX、参数或产品验收。"}
```
