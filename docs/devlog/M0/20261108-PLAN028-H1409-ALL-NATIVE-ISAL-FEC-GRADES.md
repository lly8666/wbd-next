# PLAN028 H1409｜每挡 ISA-L 默认实际编码资格（Linux x86/ARM64、Windows MSVC）

2026-11-08 用户要求并行核对 Linux↔Linux、Windows↔Linux **各 FEC 挡位**是否默认真实启用 ISA-L。SRC checkpoint 6efde5b9fe9c6a3608a7008f697eb09bcdd4ca42；H1409 为诊断/测试变更、原产品 FEC/Auto/Game/协议均不改，028 继续 **IN_PROGRESS**。

当前代码前提：`wbd-codec::fec_v2::BackendChoice::default()==PreferNative`；Linux original Fixed/Auto 经 `v4_fixed_stream.rs::next_quantum_reuse`，Game2/4 Fixed 复用 `GameFecTx`，Win 正式 Fixed/Auto 用 `v4_windows_fec2_owner.rs::encode_repair_entry` 并通过相同 `Rs16`，Win Game4 亦复用相同 codec。且只有编译 `native_fec_acceleration`→`wbd-codec/native-isal` 且 k≥2、symbol_len≥64B 的 parity/真正缺源解码才会硬件执行。k=1/短尾无损 scalar 是可接受后备；FEC Off 无 ISA-L 工作，不能为 Off 强造非零 quanta。七 profile grades 0..6 分别 Light/Mild/Medium/Balanced/High/Strong/Maximum；Auto 使用相同强度，实际等级随原 M2 调整。

历史边界：H1392 ARM64 五客户端 L3 2×1800s 的 Game4 FEC 真实正 native quanta；H1407 Windows2025 signed Npcap/Wintun Game4 FEC6 ↔ Linux 原服务端两代 Stop 的 Windows native quanta=2/11、Linux=4/4，有真实 TLS/UDP/TCP/Stop、源码/HASH 同源。旧 Linux 某些 Fixed/Auto 短验 build **缺 native feature**，只能证明 FEC 功能，不能臆写硬件加速；H1393 确认发行构建链接，但不是产品运行。

补精确而廉价的断言：`r1_f2_default_native_all_seven_profiles_real_encode_prepared` 在 Linux x86 和原生 ARM64、Windows MSVC 都对实际 pinned ISA-L C encoder 运行 0..6 全强度、k4/160B，检验 `BackendChoice::default()` 原生、普通 source 编码、M4 prepared batch 原生和 scalar 记录逐字节一致。Windows 另在 **原认证 Fixed/Auto owner** 真实编码入口逐档 k2/160B 要求 `NativeIsaL` 并与 scalar 原密文字节结构完全一致，最终真正的 quiesce/Stop/release 不豁免。按三个原生宿主独立构建和测试，官方 SHA `c387163fcbca62701d646149564c550c78a4f985`、Rust 1.85.1、产物 SHA/manifest 同源，一次 SOURCE 多平台。同一资格工程 **不跑任何网络业务**，因此新结果不能代替每一个模式真实数据面 quanta / 交接资格；不为每一 profile 重新刷 1800s。

验收标记在新 Action 收回前全部 H1409 **NOT_RUN**。如果编译或测试夹具失败，最小修复；真实原业务已证资格保持。跨设备 Windows 单客户端 + 独立 Linux 客户端同服仍 NOT_RUN，不能用 Windows↔Linux **服务端**现有通过替代。

```feature-impact
{"kind":"none","ids":[],"reason":"Native platform FEC profile tests and release qualification only; no product protocol or user configuration change."}
```
