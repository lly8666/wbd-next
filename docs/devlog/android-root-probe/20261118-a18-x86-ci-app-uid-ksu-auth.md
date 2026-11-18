# A18：x86 CI 同签名原 App UID→真实 KernelSU su 门（2026-11-18）

在 [A17c Action44233506977](https://github.com/lly8666/wbd-next/actions/runs/44233506977) 新增的 `android-x86-kvm-ksu-original-native` job 中，真实 Android16 API36 x86 KVM、KSU shell UID0、同源码 CI APK/Activity、SHA比对、原 Go ELF 完整 flags `--help` 均已获官方 artifact 14396561519 的实际 PASS。D0 ARM64/x86 原 Go/Rust 同源构建、正式 ARM64 签名 APK、Linux original server oracle 继续 PASS。旧 x86 NativeBridge 执行原 ARM64 Go ELF139 FAIL 独立记录，不可混淆；同签名原 App→su 之前尚未 RUN。

本次新增的 **X86CiAppSuActivity.java 仅在 CI-only x86 APK 编译**，正式 arm64 signed APK 严格不包含。新的普通 App UID 在同一源码 Java NativePayload 完整校验原 Go/Rust SHA/CN8503 后，经 Android `ProcessBuilder("su","-c","id -u")` 发起**真正普通 App→官方 KSU Manager 授权**；KSU Manager UI 脚本在严格包名 `org.wbdnext.rootclient` 与专属 CI Label 比对下给予 root，复用历史已成功的 KSU UI 路径，不改 ksud/KernelSU allowlist，不构造假 su 或 root。唯一可验的 `APP_UID_SU_PASS` 是 root 执行真实 `id -u` 等于 0；receipt 只记录定长事件码。无新的 Java/Go packet pump、没有模拟 TLS/凭据/租约、更不会改设备全局路由、DNS/系统。

这个 APP SU test 仅代表 KSU 授权与相同 APK NativePayload 有效，**不代表正式 RootClientService 已完成 TLS→租约→原 Rust M4→App UID TCP/UDP/Stop**；`physical_network_app_readback=NOT_RUN` 和 D2/D3 均保留真实冷门。此次 commit 不宣称尚未执行的新 Actions PASS；若官方 Manager UI 改变或无法授权直接 FAIL，保留脱敏收据并明确分阶段阻断。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A18 新增 x86 CI-only 同签名 App UID 真实 KernelSU Manager 授权门，复用原 NativePayload 及 D0 同源码 Go/Rust，严格记录 su uid0；此为 App 权限测试非正式 TLS/M4/Stop。"}
```
