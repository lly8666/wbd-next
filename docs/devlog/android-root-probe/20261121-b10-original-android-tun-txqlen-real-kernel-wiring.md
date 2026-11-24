# B10｜原 Android owned TUN txqueuelen 真生产接线（Fixed FEC2 前置可选容量）

## 起点

SOURCE `2f76138b7fd433963a67ab2212f64e3489bb3ba6` 的原 Go `linux.go` 已提供 `--tun-txqlen-packets`（仅500/2048），在用户 owned TUN 上实际 `ip link set dev wbdv40 txqueuelen` 并通过 kernel `ip -j link` readback。Root App 的原 `OriginalGoCommandArgs` 固定500，因而该容量功能卡没接到真实 Android UI。FEC2 Fixed/Auto 尚未进入 Android 原 M4，它既不是 txqlen 的别名，也不是可通过改参数补完的功能。

## 已接入同一真实生产路径

- Activity 新增包数选择器，默认500、可选2048；START Intent `tun_txqlen` → Service（旧 Intent 默认500，限定两个有效值）→ 原 `runRoot` 的同代 `launchCommand` → 原 `OriginalGoCommandArgs.build(...,requestedTunQueue)` → 原 Go `--tun-txqlen-packets`。
- 原 Go 使用已有 `setOwnedTunTxQueue` + kernel apply/readback；失败即报告原 Go 错误，不用 Java 缓冲区/新 Rust 队列替代。旧 Java Go CLI overload 委托500，B8外层 MTU 与B9记录AEAD原路径不变。
- Host JVM 测试同一生产 argv 的500/2048及499/2049/0拒绝；源码门同时验证 App/Service/Go/TUN kernel readback，修改 B9旧源码断言以匹配合法新增参数，保留新的完整 B10调用门。
- 同一 SOURCE 的 Go/Rust 双 ABI、原签名 ARM64 APK、Linux Oracle 为软件门；真实 Android KernelSU、真实 App TCP/UDP与性能为 NOT_RUN/NOT_PROVEN，不从 Host 测试推断设备已验收。

## Fixed FEC2 下一步

已核对 `v4_fixed_stream.rs`、`v4_fec2_live_rx.rs` 是共用算法核心，但 Android `v4_android_original_m4.rs` 只做 `LinkMode::FixedOff` 的收发，Go 会在 TLS 前拒绝 Fixed/Auto；Linux `fec2_live_tx` 的 staged PN/codec parity 与 receiver 的 kernel ownership 不能只复制 flag。顺序是共同原 M1 source/parity 与单 PN/AEAD 入 Android TX→同源 RX/恢复→auth policy readback和反向 M2→真实 Game 多lane。任何一步缺失前不开放 UI 模式。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B10原App新增TUN 500/2048包队列冷配置，经过原Service/Go现成ip link kernel应用和读回；B8/B9保持兼容，Host/同源CI门和Fixed/Auto未接线边界明确。"}
```
