# A20e：原 Linux server ↔ Android x86 KSU 正式 RootService TUN/RAW D2-S1 真 PASS（2026-11-18）

**实际 SOURCE `70b3a8223f27e6895f6f40f033c370bec5068883`**：[GitHub Actions #44251978166](https://github.com/lly8666/wbd-next/actions/runs/44251978166) **全工作流 SUCCESS**；独立 `android-x86-kvm-ksu-original-d2-s1` Job 真成功，官方 Artifact #14405085187 的 `receipt.json`、`app-diagnostic-enums.txt`、`secret-stage-enum.txt` 已核对。收据明确：`linux_real_original_server=PASS`（宿主真正原 Go server 创建 `wbdvs4` TUN）；`ephemeral_app_private_secrets=PASS`（Android KSU root 仅将 CI 内一次性证书/随机口令/路由 key 放 App 私有目录，readback UID/0600）、`signed_app_requested_original_root_service=PASS`、`original_go_root_process_launched=PASS`、`original_android_tun_configured=PASS`（原 Go 真建 Android TUN）、`original_android_raw_af_packet=PASS`（原 Go 真开 AF_PACKET RAW）。后两项是**正式 Java RootClientService 解析原 Go 内核实际输出才写的固定 enum**，不是旧 standalone 探针，也不是 ELF `--help`。

这次另有 D0 双 ABI Go/Rust Bionic ELF+ARM64 16KiB、正式 ARM64 APK、D1 x86 Android16 原生 KSU App→su/正式 `PhysicalNetwork` 读回、D2-S0 原 Linux x86 server client ELF、原 Linux oracle 均 SUCCESS；旧 Android x86 模拟器上翻译 ARM64 ELF 的 NativeBridge139 手动诊断仍 SKIPPED/保留历史失败。**未取得**：`real_peer_synack=NOT_PROVEN`、`tls_authenticated_32_lease=NOT_PROVEN`、`original_rust_m4_and_uid_ready=NOT_PROVEN`、`owned_stop_verified=NOT_PROVEN`、`tcp_udp_bidirectional_application_data=NOT_RUN`、`route_rollback_kernel_proved=NOT_RUN`、`system_dns_takeover=NOT_RUN`。App 原 Go 进程曾退出非零；不可声称 Android 生产流量或 Stop 通过。

**后续验收优化**：A20e 新 SOURCE 仅扩充 D2-S1 原 Native TUN/RAW 就绪后的**有界 45 秒真实 FakeTCP/Go TLS/Lease 观测**（上次到 RAW 就立即停止，无法判断服务器/模拟器网络）。增加明确 SYNACK/租约 fixed enum，若无仍 `NOT_PROVEN`，不会为了让总 CI 绿跳过真正 D2 业务。Android Emulator 的 10.0.2.2 是 QEMU user-mode NAT host-loopback alias，不能假设保留 AF_PACKET 的真实 TCP 控制面；若 45s 后无 SYNACK 应进一步查 TAP/真实 guest-link，而不是篡改原 Go/Rust 协议或改宽 Wi-Fi/蜂窝网络/UID route。原双安全 DNS takeover false，ARM64 发布只 arm64-v8a，实验分支 PR #36 Draft，main/M0 不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"记录 A20 SOURCE70b3a822 Action44251978166 真实同源 x86 Android 正式 RootService 原 Go KSU TUN+AF_PACKET 与原 Linux server TUN 双侧 PASS；仅延长 45s 真 SYNACK/TLS/租约观测，保留 D2 M4数据与Stop NOT_PROVEN，不修改 ARM64发布或 DNS 安全门。"}
```
