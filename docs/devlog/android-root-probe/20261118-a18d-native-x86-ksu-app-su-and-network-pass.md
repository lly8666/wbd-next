# A18d：Android16 x86 原生 App→KSU 与物理 Network 读回 PASS（2026-11-18）

实际 SOURCE `427e321dd8ea20952bc3f68d0c4749523dc7928f`：[Action44236693889](https://github.com/lly8666/wbd-next/actions/runs/44236693889) 全 workflow `SUCCESS`；`android-x86-kvm-ksu-original-native` Job `SUCCESS`，官方 Artifact 14396854925 的 `android-x86-ksu-native/receipt.json`（已核对）包含：`guest_kernel_x86_64=PASS`，`android_api36=PASS`，`ksu_shell_root=PASS`，`original_x86_go_help=PASS`，`signed_ci_apk_activity=PASS`，`app_to_ksu_root=PASS`，`physical_network_app_readback=PASS`；`original_tls_auth_lease/real_m3_m4_tcp_udp/owned_stop_route_rollback/system_dns_takeover=NOT_RUN`。

这是**普通 App UID→官方 KernelSU Manager 授权→真实 `su -c id -u`**，而非仅仅 adb shell root。CI-only `X86CiAppSuActivity` 先调用与 ARM64 正式 App **完全共用的 `NativePayload.stage`** 来验原 Go/Rust asset SHA、CN8503 许可证与来源，再向 KernelSU 请求授权。真实设备过滤日志：第一次 `APP_UID_SU_NOT_PROVEN`，经精确 `org.wbdnext.rootclient` 及 `WBD x86 CI Root` KSU Manager UI 授权，第二次 `APP_UID_SU_PASS`。同一 App 调用正式 `PhysicalNetwork.available/exact/matchesLinkProperties` 比较真实 ConnectivityManager handle、内核 ifindex/MTU/IPv4，取得 `PHYSICAL_NETWORK_EXACT_READBACK_PASS`；没有写假 Android Network、NoOp Root 或独立协议循环。

同次 `arm64-native` 同源码 ARM64/x86 原 Go/Rust/ELF ABI、`root-arm64-app` 正式 ARM64 APK 与 `linux-original-server-normal-off` 真 Linux oracle 均 `SUCCESS`。历史 x86 Guest 翻译 ARM64 ELF 的 NativeBridge139 失败**仍保留历史**，现在正常 push 中 `SKIPPED`，只在手动勾选时单独重测。这说明用户看到的那个 `arm64` 字样属于旧翻译实验，并非真正 x86 原生构建的失败。

**明确仍未完成**：正式 `RootClientService` Android 真 TLS/授权/32→原 Rust M4 双向 TCP/UDP→完整 owned Stop；ARM64 真机正式 WBD，以及系统 DNS 接管两个冷门也仍 NOT_RUN。仅实验分支 / Draft PR #36，不动 main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"登记真实同 SOURCE Android x86 内核/KSU App→su/正式 PhysicalNetwork PASS 和 ARM64 构建/Linux oracle PASS 的 Action44236693889，原 Android TLS/M4/Stop/DNS NOT_RUN 与旧 NativeBridge139 FAIL 不变。"}
```
