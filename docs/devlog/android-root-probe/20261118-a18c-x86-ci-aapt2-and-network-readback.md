# A18c：Android x86 新标签资源覆盖准入 + CI App 物理网络读回（2026-11-18）

[A18b Action44235862762](https://github.com/lly8666/wbd-next/actions/runs/44235862762) 的同源 D0 ARM64/x86 Android Bionic 原 Go/Rust、正式 ARM64 APK 与 Linux 原服务器 oracle 均成功；旧 ARM64 NativeBridge 作业按 A15 最新方案手动化、正常推送里 `SKIPPED`，并未伪造其先前的 ELF139 失败。但 x86 CI-only APK 打包时报 Android SDK `aapt2` 明确错误 `resource string/wbd_x86_ci_label does not override an existing resource; define an <add-resource> tag or use --auto-add-overlay`。这个报错发生在 KSU 模拟器启动前，不是 x86 原客户端或 SELinux 失败。新增唯一 CI-only `aapt2 link --auto-add-overlay`，继续硬要求由 `aapt dump badging` 返回确切 `WBD x86 CI Root` 应用标签。原 ARM64 build/manifest 不改。

并行增加 x86 **CI-only** App 的真实 `PhysicalNetwork.available`、`PhysicalNetwork.exact` 和 `matchesLinkProperties` 内核接口/Network handle/ifindex/MTU/IPv4 读回（和正式 ARM64 一模一样的 Java 类，不复制原协议）。只输出定长 `PHYSICAL_NETWORK_EXACT_READBACK_PASS` / `PHYSICAL_NETWORK_ENV_BLOCKED` 事件，后台读回被 AVD 条件阻断则记录 `ENV_BLOCKED`，不会绕过正式 Wi-Fi/蜂窝 Network 条件，也不通过 adb-root 伪装选网。App→KSU 仍需真实官方 Manager UI 授权；这一批尚未取得最新 Action PASS，x86 D1 完整业务仍 NOT_RUN。

原 Linux auth/M4/TCP+UDP 和完整 owned Stop 在 Android 仍不宣称通过；DNS 两道系统接管冷安全门继续 false。仅实验分支 PR #36 Draft，main/M0 没动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A18b x86 CI APK aapt2 新 string 资源缺失 auto-add-overlay 导致失败；按 SDK 明确报错仅加 CI-only overlay，保留 App 标签红门。增加 CI-only 调用同一 PhysicalNetwork 实体 exact 网络读回并分离 ENV_BLOCKED，正式 ARM64 不变。"}
```
