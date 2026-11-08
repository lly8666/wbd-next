# PLAN028 H1409｜每挡 ISA-L 默认实际编码资格（Linux x86/ARM64、Windows MSVC）

2026-11-08 用户要求并行核对 Linux↔Linux、Windows↔Linux **各 FEC 挡位**是否默认真实启用 ISA-L。SRC checkpoint 6efde5b9fe9c6a3608a7008f697eb09bcdd4ca42；H1409 为诊断/测试变更、原产品 FEC/Auto/Game/协议均不改，028 继续 **IN_PROGRESS**。

当前代码前提：`wbd-codec::fec_v2::BackendChoice::default()==PreferNative`；Linux original Fixed/Auto 经 `v4_fixed_stream.rs::next_quantum_reuse`，Game2/4 Fixed 复用 `GameFecTx`，Win 正式 Fixed/Auto 用 `v4_windows_fec2_owner.rs::encode_repair_entry` 并通过相同 `Rs16`，Win Game4 亦复用相同 codec。且只有编译 `native_fec_acceleration`→`wbd-codec/native-isal` 且 k≥2、symbol_len≥64B 的 parity/真正缺源解码才会硬件执行。k=1/短尾无损 scalar 是可接受后备；FEC Off 无 ISA-L 工作，不能为 Off 强造非零 quanta。七 profile grades 0..6 分别 Light/Mild/Medium/Balanced/High/Strong/Maximum；Auto 使用相同强度，实际等级随原 M2 调整。

历史边界：H1392 ARM64 五客户端 L3 2×1800s 的 Game4 FEC 真实正 native quanta；H1407 Windows2025 signed Npcap/Wintun Game4 FEC6 ↔ Linux 原服务端两代 Stop 的 Windows native quanta=2/11、Linux=4/4，有真实 TLS/UDP/TCP/Stop、源码/HASH 同源。旧 Linux 某些 Fixed/Auto 短验 build **缺 native feature**，只能证明 FEC 功能，不能臆写硬件加速；H1393 确认发行构建链接，但不是产品运行。

补精确而廉价的断言：`r1_f2_default_native_all_seven_profiles_real_encode_prepared` 在 Linux x86 和原生 ARM64、Windows MSVC 都对实际 pinned ISA-L C encoder 运行 0..6 全强度、k4/160B，检验 `BackendChoice::default()` 原生、普通 source 编码、M4 prepared batch 原生和 scalar 记录逐字节一致。Windows 另在 **原认证 Fixed/Auto owner** 真实编码入口逐档 k2/160B 要求 `NativeIsaL` 并与 scalar 原密文字节结构完全一致，最终真正的 quiesce/Stop/release 不豁免。按三个原生宿主独立构建和测试，官方 SHA `c387163fcbca62701d646149564c550c78a4f985`、Rust 1.85.1、产物 SHA/manifest 同源，一次 SOURCE 多平台。同一资格工程 **不跑任何网络业务**，因此新结果不能代替每一个模式真实数据面 quanta / 交接资格；不为每一 profile 重新刷 1800s。

验收标记在新 Action 收回前全部 H1409 **NOT_RUN**。如果编译或测试夹具失败，最小修复；真实原业务已证资格保持。跨设备 Windows 单客户端 + 独立 Linux 客户端同服仍 NOT_RUN，不能用 Windows↔Linux **服务端**现有通过替代。

```feature-impact
{"kind":"none","ids":[],"reason":"Native platform FEC profile tests and release qualification only; no product protocol or user configuration change."}
```

## H1409 首轮原始结果与 H1410 夹具定向修正

[H1409 Action 42490258856](https://github.com/lly8666/wbd-next/actions/runs/42490258856)：**Linux x86_64、原生 ARM64 两 job PASS_SCOPED**。每个 grade 0..6 有真实 `owned=native prepared=native scalar_match=1` 七行；每原生平台的实际 ISA-L 静态 lib 和 release engine hash/官方 pin 均由原始 ZIP 校核，见 `docs/evidence/M0/PLAN028-H1409-SOURCE337-LINUX-X86-ARM64-SEVEN-REAL-ISAL-PROFILES-PASS-20261108.json`。两平台分别提供真实能力等级原生证据，不能把测试用的 160B/k4 解释为所有真实应用块皆 native。

Windows job 原 CI FAIL 发生于 **测试前**：Chocolatey `nasm` 正常安装，`$GITHUB_PATH` 只影响下一 Action step，`cmd /c nmake` 在同一 PowerShell step 内未继承 `nasm.exe`，出现 `NMAKE fatal U1077: nasm not recognized`。H1410 在同一步写 `$env:PATH="$bin;$env:PATH"`，先 `where nasm`，再真正 `vcvars64 && where nmake && where nasm && nmake`。这一源提交的 Linux x86/ARM64 资格原始凭据直接复用，新 push 用明确 `[plan028-win-nasm-only]` 仅跳过 Linux 这两项重复原生 job；下次普通 push 仍正常对 Linux 三平台共用测试。

另外原 [main FEC2 native Action 42490258886](https://github.com/lly8666/wbd-next/actions/runs/42490258886) 执行真实 Rust 17/17 全 PASS，随后历史 checker 强制 `16 passed` 导致 CI 假失败；H1410 修改仅审计器计数为实际 `test result: ok N passed; 0 failed` 和精确必需测试集合，新七挡 marker 7/7，依旧不放宽 C/GF 字节比对。修它不重跑任何网络，原失败证据保留。
