# B12a｜Android 原 Rust FEC2 M3 单一认证 RX → TUN（严格关闭Fixed）

SOURCE `ebc8a6085a56493ec91f5cb727b77f404ebd946d`；本片是未授权的后续 M4 Fixed RX 实装，不是完成版产品。

- 原受保护Go TLS `handoff.negotiated_features==7` 的 `prepare_side` 只创建已存在的 `Fec2LiveRx::from_authenticated_scope` cache，方向S2C/原epoch/generation完全取原Rust owner；**没有独立ReplayProtectedLaneRx、没有第二解密器**。
- 在原 Android RAW RX worker 的同一原 M1 loan 中增加FEC分支：`owner.drain_windows_authenticated_fec2` 使用原 M3 唯一AEAD+PN后调用 `blocks.accept_authenticated`；source即时first delivery、repair RS16恢复。真实TUN写前再次查客户端/32，复用同一DNS逆映射；仅原TUN写成功累加source/recovered计数。Health仍是认证控制。
- 完整原 Stop/join 后调用 `blocks.stop()` 并清零同代fixed APPLIED，防止跨代残留。Normal/off仍走老分支。
- **关键拒绝门**：FEC RX scoped revision始终初始化0，没有设置接口；M4 RX遇未APPLIED即拒绝；`loop_start`明确只接受feature3，原Go Android FixedPending仍 `ErrAdmissionUnsupported`。必须补完原M1 FixedStream source+parity、M4 copied-prefix、双向M2/反向反馈、实际内核APPLIED再开放。
- 软件验收依赖此SOURCE同源ARM64/x86 Go/Rust、签名APK、Linux oracle、功能卡治理；Android物理设备真实数据、恢复、吞吐及固定模式仍NOT_RUN/NOT_AVAILABLE。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B12a将原M3 AEAD/PN唯一接收器的FEC2 kind2/3接进Android M4原RX/TUN、DNS逆映射与Stop，APPLIED=0/Go Fixed禁用，TX/M2待续。"}
```
