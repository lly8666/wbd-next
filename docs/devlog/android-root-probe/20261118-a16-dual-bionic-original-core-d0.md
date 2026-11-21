# A16：原 Go/Rust Android 双 Bionic ISA 构建施工（2026-11-18）

根据 A15 新施工合同，实际修改原 Rust Android M4 模块及 Bionic TUN/RAW 驱动的编译架构门，从 Android ARM64-only 扩展到 **同一模块源码的 ARM64 + x86_64**，并将源锁 NDK C ABI、Go/Rust ELF 双目标编译、同一导出 FFI 列表及 ELF machine 核验纳入现有原 ARM64 Action。ARM64 仍为唯一正式发行 ABI，x86_64 仅 CI 同源产物，另写 manifest-ci-x86_64.json；原签名 APK 始终只装 ARM64。原 Go TLS/授权租约、Rust 原 M1/M3/M4/AEAD、owned Stop 未替换或分叉。原旧 NativeBridge ARM64 ELF139 红门和 Linux server oracle 仍独立。

**本提交建立 D0 的可执行 CI 代码，不表示 D0 已通过**。在新 SOURCE Actions 真正成功之前记 D0=NOT_RUN；D1 原生 x86 Android APK→KernelSU su、D2 原客户端 TLS/租约/真实 TCP+UDP、D3 原 Stop 均 NOT_RUN；ARM64 真原 TLS/M4 仍 NOT_RUN。用户此前手机 UID→临时 TUN 包 PASS 不能推导业务 PASS。系统 DNS 双安全门保持 false，main/M0 未碰；后续编译问题不得通过假 native ABI、第二 data plane 或规避证据修复。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A16 实装原 Go/Rust 同源码 ARM64/x86_64 Android Bionic 构建/FFI/ABI/ELF 检查，ARM64 正式 APK 不加 x86；Actions D0 尚未确认通过、D1-D3 及 ARM64 真业务 NOT_RUN。"}
```
