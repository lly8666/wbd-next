# B9｜Android 原 V4/M3 记录层 AEAD 三算法 App→Go→Rust 真实接线

## 依赖审查与功能

B8 源码 `32b553ec798641e8055d15ece19bd558cb11b812` 已将外层IPv4 MTU传入原Rust预算；其真实 Actions 结果以各 Job 为准。本片复查原 Go `linux.go` 已有客户端 `--record-cipher`、`PolicyForClientWithInitialAndCipher`，原 TLS Admission 按所选 cipher 从真实 exporter/HKDF 派生方向密钥，原 Rust owner `v4_owner_crypto.rs` 用 `RecordSuite::try_from(identity.cipher)` 创建收发 AEAD/PN。Android 原 M4 使用这个共同 owner；**不另造任何算法或放宽密码学检查**。

此前 Android 签名 App 既无 cipher 下拉选项，也不传 `--record-cipher`，总用默认 ChaCha20。现在在原 Activity 增加 ChaCha20-Poly1305/AES-128-GCM/AES-256-GCM 三选一（默认第一项），沿 `START.record_cipher` → Root Service 本代参数（旧 Intent 默认为ChaCha）→ 同一原 Root launch → `OriginalGoCommandArgs` → 原 Go `--record-cipher` → 已受保护的标准 TLS Admission policy/原Rust M3 owner。原 B8 MTU 与旧 Go argv overload 完全保留。

生产不增加 JNI/Java 逐包操作、Linux/Windows 协议变更、防篡改框架、额外私钥管理。Host JVM 测三种真实 argv 参数和非法选择，静态门核对 Go policy→Rust suite，共用同一 SOURCE 签名 ARM64 APK、原 Go/Rust 双 ABI 和 Linux Oracle。**CI 只能证明编译/Host/源码门；Android实体 AES 性能、应用字节交付和Stop仍 NOT_RUN/NOT_PROVEN**。AES 在某些 ARM64 设备或许更快，仅实际同设备对照测试才可下结论。

后续真正缺口：Android Fixed/Auto/FEC2/Games 的原 Rust owner 及多 lane 生命周期，Android resolver/netd、物理 TCP53、CN IP direct、IPv6、热点与切网重建。B9 不能替它们开假开关。

## B9a｜旧 B8 源码门失配的精确修复

SOURCE `f7e926d59d54eb2cf7b18ec63e102e2f434fc367` [Action #44917505827](https://github.com/lly8666/wbd-next/actions/runs/44917505827) 的 `root-arm64-app` 在 JVM 的 B9 三种真实 argv 用例已 PASS 后，脚本中 B8 遗留的 `cnSplitDNS,requestedOuterMTU);` 文本断言失败：B9 原生产 Service 正确追加了 `recordCipher`。仅将旧 B8 检查改为确认 MTU 参数存在，紧邻的 B9 检查仍精确固定完整新调用签名；不改任何 Go/Rust/Android 生产代码、协议、默认值或证据。旧 Action FAIL 保留，后续同 SOURCE Actions 需独立验证签名 APK 和 Linux Oracle。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B9把原Go已经支持的三种V4记录AEAD通过Android原App/Service/Go真实参数选取，沿现有受保护Admission/Rust M3原算法，默认ChaCha和B8旧参数兼容；同源Host/源码门及设备待验边界明确。"}
```
