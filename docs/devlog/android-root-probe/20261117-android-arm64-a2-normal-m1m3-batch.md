# Android A2 ARM64-only 跨层大批次（待同 SOURCE Actions 复核）

起点分支 `a672f153b010ba1a388bd2e9eb1478e86977b7c6`，main `4633f9e8c1da206401ee8952db07e2e65c83fb8d`，仅修改 Android 实验分支。用户新授权：只开发/构建 Android arm64-v8a，退出 Android x86/x86_64/32 位工作矩阵（历史证据保留）；独立 Go/Rust/Bionic/docs 并行准备后整批提交、集中运行同SOURCE ARM64 Actions。Linux/Windows x86 保护不变。

本批意图：NDK __aarch64__ ABI 闸、Rust aarch64-linux-android/Go ARM64 唯一交叉目标、16KiB ELF machine183；Go 在原认证/物理Network/租约边界绑定同一 Rust generation；Bionic RAW 通过原共享 IPv4/TCP parser 在原 M1 slab 中压缩 untrusted ciphertext，原 Rust PN/AEAD+M3 LINK 后才允许 TUN；原 FrozenRecord 共享 IPv4/TCP builder/BorrowFence 发送，拒绝伪造 ACK/重封 PN。当前连续 M4/Health/MTU/Go linker 仍是硬阻塞。

**验证**：本提交写入前不宣称 PASS；SOURCE commit 及 Actions 由下一条证据补记。Android16 ARM64 KSU ↔ 同源真Linux WBD标准TLS/认证/租约/TCP/UDP、原始完整工作线程、性能、设备装载、热点/USB全部 NOT_RUN，未操作用户真机。

**唯一下一步**：把本批原 Rust Normal/off Android IO 接线纳入真实连续 M4 worker/Health/MTU 与同步 Stop，消除 ARM64 Go M4 全链接错误；完成后 A3 才做同源实连。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户只做Android ARM64并要求较大并行跨层批次；收敛ARM64-only NDK/Go/Rust CI与原同代际Bionic M1/M3接线，M4真连接仍NOT_RUN。"}
```
