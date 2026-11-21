# A19：同源 Android x86 D2-S0 原 Linux WBD 服务端主机装配（2026-11-18）

真实已成功前提：[SOURCE `427e321dd8ea20952bc3f68d0c4749523dc7928f` Action44236693889](https://github.com/lly8666/wbd-next/actions/runs/44236693889) 整体 SUCCESS，包括同源码 ARM64/x86 Android Bionic 原 Go/Rust D0、ARM64 正式签名 APK、原 Linux ARM64 server oracle、真实 x86 Android16 KernelSU 普通 App UID→su、相同 Java `PhysicalNetwork.available/exact/matchesLinkProperties` 的 ifindex/MTU/源 IPv4 读回。x86 客户端业务 WBD TLS/租约/M4/Stop 仍 NOT_RUN。

**本批 A19 开始 D2 的主机侧准入，不制造假数据链**。新增 `android/root-app/ci/x86-original-linux-server-prep.sh` 和独立 Actions `linux-x86-original-server-d2-s0`，在真正 x86_64 Ubuntu runner 上使用同一 run 的原 Android x86 Go/Rust SOURCE/SHA artifact、完全固定的原 donor `wobuzhidao@a7a82db`、与已验证 ARM64 Linux oracle 相同的 FakTCP/RealityFront/Go overlay，以及 Rust 同一 `wbd-engine` 特征，编译真正 Linux x86_64 原 `wbd-v4-server`/ `wbd-v4-client` 和 `libwbd_engine.so`。静态检查三份 ELF machine62、Rust DT_NEEDED 真实链接、原 Go CLIs `--help` 真实执行/flag.ErrHelp 严格预期、哈希与 SOURCE 匹配；生成 **独立不含凭据** 的 D2-S0 工件清单，供后续同一 GitHub Actions KSU 主机连接真实 Linux server。

**重要界限**：D2-S0 只证明原服务端在 x86 主机同源码编译+CLI 实启动，不启动真实认证服务、不会出现客户端 TLS、自动 /32、Rust Android M4 的真实 TCP/UDP，不声明 D2 已通过。新 Job 实际 Actions 若 FAIL 不改为 PASS；只有实际构建和 --help 全 PASS 才能记 D2-S0 PASS。用户账户/密钥不会进入仓库或工件；将来要用 job 内独立临时凭据，不能用开发者真实账户。原 Android 系统 DNS takeover 两道冷许可继续 false；正式 ARM64 产品不变，旧 NativeBridge ARM64-on-x86 139 历史 FAIL 继续保留，用户 CI 持续只运行真实 x86 native。实验分支/PR #36 Draft；main/M0 不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A19 在已实测 x86 Android KSU App su/Network D1 PASS 基础上，加入同 SHA 原 Linux Go/Rust x86_64 服务端构建及 CLI 实执行 D2-S0 准入，不伪称 Android TLS/M4/E2E；原 ARM64 release、DNS 冷门及 M0 不变。"}
```
