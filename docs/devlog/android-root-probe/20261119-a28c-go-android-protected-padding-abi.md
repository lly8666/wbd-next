# A28c｜第二个真实 main→Android 冲突：共享 Go 的 Linux Padding API

在 `5c741a77e974ce27093689f465acce432b1105a7` 的真实 [Action #44465728503](https://github.com/lly8666/wbd-next/actions/runs/44465728503)，main `v4routekey` 缺包已解决，Rust+六条Host Job通过，但原 ARM64 Go 在以下4处失败：
`bridge_v4_linux_client_product.go:205/230` 和 `bridge_v4_linux_server_product.go:302/385` 调用 `configureNormalStartupPadding`/ `normalStartupPaddingCounters`，Android 专用 `v4EmbeddedNativeBridge` 未定义。Go 的 Android target 也满足通用的 `linux` 条件，Linux shared product file 在 Android 构建时也会被编译；不可仅依据文件名判断 Android 代码不受影响。

**最小安全修复**：在共享客户端冷参数阶段直接拒绝 Android 非off `StartupPaddingMode`；在原 Rust worker start 前，仅 Linux 才实际调用保护态 Padding 配置接口。Android bridge 上同签名方法明确返回 `ErrAdmissionUnsupported`，只为 Go 编译提供不可用的合法接口，不做无效果 `PASS` 回执、不影响 Android Normal/off 真实 Go TLS/Rust M4 与 Root 路由。Linux bridge 原本成熟的 authenticated protected padding 实现原样保留，仍按 main scope 运行。Android 服务端早于 TLS 即拒绝；新接口的 unsupported 也不会被伪作服务端 ready。构建后检查 Go/ARM64、原 Linux server 与签名 APK。

治理与旧 CI FAILED 证据不改写；此次是跨平台兼容性修复，不引入新 GUI 参数、DNS、模式、测试性 FakeTCP 或模拟网卡试验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修复main Linux受保护Padding共享Go接口在Android编译时缺失：Android仅off且专用bridge返回UNSUPPORTED，保留Linux真Padding与标准TLS。"}
```
