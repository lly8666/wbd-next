# A17b：x86 CI 原 Java 签名资产校验 Host gate 更新（2026-11-18）

[A17 首次 Action44231882991](https://github.com/lly8666/wbd-next/actions/runs/44231882991) 的 `android-x86-kvm-ksu-original-native` 在 host JVM/Python 静态测试失败：`test-network-scope-gate.sh` 仍硬断言旧四参数 `new NativePayload(go,rust,cn,source)`，但本次 Java 加入经过签名 manifest 严格验证的 exact ABI executableName（五参数）用于 ARM64/x86 原 Go 子进程与 owned Stop。真正 JVM Stop 测试、A11/12 selftest 的所有既有门已 PASS；**当时根本未执行 x86 CI APK 和 Android guest**。本次同步加强静态门，必须校验单一 ABI、CI-only x86 release=false、OS ABI、原 Go/Rust 资产及精确 Stop ownerExecutable。不绕过真实性、不取消旧 Host 测试；待新 SOURCE 重跑。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A17 x86 原客户端 Actions host 静态检查还硬编码旧 NativePayload 四参数构造，更新为严格检查签名双架构单一 ABI/CI-only x86 及 Go 子进程精确 Stop；原安全验证仍在。"}
```
