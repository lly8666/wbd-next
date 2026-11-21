# Android A2 ARM64-only 跨层大批次（待同 SOURCE Actions 复核）

起点分支 `a672f153b010ba1a388bd2e9eb1478e86977b7c6`，main `4633f9e8c1da206401ee8952db07e2e65c83fb8d`，仅修改 Android 实验分支。用户新授权：只开发/构建 Android arm64-v8a，退出 Android x86/x86_64/32 位工作矩阵（历史证据保留）；独立 Go/Rust/Bionic/docs 并行准备后整批提交、集中运行同SOURCE ARM64 Actions。Linux/Windows x86 保护不变。

本批意图：NDK __aarch64__ ABI 闸、Rust aarch64-linux-android/Go ARM64 唯一交叉目标、16KiB ELF machine183；Go 在原认证/物理Network/租约边界绑定同一 Rust generation；Bionic RAW 通过原共享 IPv4/TCP parser 在原 M1 slab 中压缩 untrusted ciphertext，原 Rust PN/AEAD+M3 LINK 后才允许 TUN；原 FrozenRecord 共享 IPv4/TCP builder/BorrowFence 发送，拒绝伪造 ACK/重封 PN。当前连续 M4/Health/MTU/Go linker 仍是硬阻塞。

**验证**：本提交写入前不宣称 PASS；SOURCE commit 及 Actions 由下一条证据补记。Android16 ARM64 KSU ↔ 同源真Linux WBD标准TLS/认证/租约/TCP/UDP、原始完整工作线程、性能、设备装载、热点/USB全部 NOT_RUN，未操作用户真机。

**唯一下一步**：把本批原 Rust Normal/off Android IO 接线纳入真实连续 M4 worker/Health/MTU 与同步 Stop，消除 ARM64 Go M4 全链接错误；完成后 A3 才做同源实连。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户只做Android ARM64并要求较大并行跨层批次；收敛ARM64-only NDK/Go/Rust CI与原同代际Bionic M1/M3接线，M4真连接仍NOT_RUN。"}
```

## 同 SOURCE ARM64 Actions 验证与封存（2026-11-17）

- **SOURCE**：`2951cda2e99150e5f0126cbd44b80f5009146d3a`；用户唯一 Android ABI `arm64-v8a`。构建 [Action44021966186](https://github.com/lly8666/wbd-next/actions/runs/44021966186) **overall FAIL**，失败位置在真实原 Go CGo → Rust 链接 `ld.lld`；`wbd_m0_embedded_go_fixed_commit_mature_m2`、`release_client_fec2_*`、`wbd_fec_network_game_*`、`game_group_*` 等原产品尚缺的 Android M4/FEC/Game native 符号，报错列表被 `too many errors` 限制截断。原 Go 完整可用产品客户端 **FAIL**，不得通过 fake stubs 或剔除必要真实能力冒充成功。
- 同一 Action 内 **Android NDK arm64-v8a Bionic C ABI、原共享 Rust 加密M1/M3 + Bionic RAW/TUN接口编译、原Go保护冷 FFI `prepare/stage/commit/stop`、`android_bind_physical/attach_raw_rx_on_interface/attach_tun` 符号、ELF AArch64机器/16KiB对齐均 BUILD_PASS**。Cross-build 不证明 Android 原生 socket 的运行权限或业务完成。
- **同源阶段证据**：[artifact14300864286](https://github.com/lly8666/wbd-next/actions/runs/44021966186/artifacts/14300864286)。已独立下载/解包并计算 ZIP SHA256 `90cfb9be158c6c30e9043e89749f2075d74e7a9129cb8dc79fe53aa11a5aa00c`，唯一 `libwbd_engine-arm64.so` SHA256 `76816bd9ffd851974563656ef2e31041e0904cec34db938fd590844e4eff3ad3`，与内置 `rust-cold-stage-manifest.json` 匹配，ELF machine=183，PT_LOAD min-align=16384。ZIP 含 `SOURCE`、`abi-arm64.o`、唯一 ARM64 `.so` 与 stage manifest，**无 Android x86/x86_64**，未生成完整 Go 客户端可执行 ELF。
- 本 SOURCE 的 [Feature/Governance44021966329](https://github.com/lly8666/wbd-next/actions/runs/44021966329) **PASS**， [governance-maintenance44021966206](https://github.com/lly8666/wbd-next/actions/runs/44021966206) **PASS**；未修改 main、M0 registry/cursor、PR Draft 状态。
- **NOT_RUN**：Android16 ARM64 KSU 实际加载/原 RAW/TUN收发，原 Go 标准TLS ClientHello/身份认证/lease，Normal/off TCP+UDP 真双向内网业务、owned worker join、MTU切网、p99/CPU/RSS/低唤醒、热点USB。未收到额外真机部署授权，不构造伪成功。

**唯一下一步**：在 ARM64 Bionic 上把已经编译通过的原 M1/M3/TUN + RAW接口连到原连续 M4 worker/Health/MTU/Stop，优先完整同源原 Go Normal/off 链接，再进入真实 Android16 ARM64 KSU ↔ Linux server 测试。不再安排 Android x86/x86_64。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"单ARM64 A2源码2951cda2/Action44021966186 Bionic共享Rust冷FFI/16KiB BUILD_PASS、原Go完整M4链接FAIL；唯一ARM64 ZIP/hash及Governance PASS留档，真WBD NOT_RUN。"}
```
