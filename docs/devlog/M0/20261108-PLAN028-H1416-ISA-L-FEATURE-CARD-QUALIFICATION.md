# PLAN028 H1416 — 按确切 SOURCE 回填原有硬件加速功能卡

2026-11-08。用户要求三平台/七档 ISA-L 默认真正启用，原 `docs/features/entries/native-crypto-backends.json` 仍记 `runtime-backend=未确认实际选择`，与已实际跑过的原生证据不符。本次只更新**既有**功能卡：Linux x86_64 原生、Linux ARM64 原生 H1409 SOURCE `337dc093` 七档 `NativeIsaL` source/prepared C 实编码与 scalar 字节一致；Windows MSVC H1410 SOURCE `0cdea544` 七档编码及**真正认证 Fixed/Auto owner** 都实际 native，官方静态库+Rust DLL hash/原 ZIP 已核。[H1411 权威分账](../evidence/M0/PLAN028-H1411-WINDOWS-LINUX-ALL-FEC-GRADES-NATIVE-ISA-L-QUALIFICATION-20261108.json)。Windows Game4FEC6 ↔ Linux 原生 server 在 H1407 SOURCE `eed0392f` 真实 TLS/签名驱动/UDP/TCP/Stop 两代 TX native quanta Windows 2/11、Linux 4/4，是真实产品资格，不能倒推其他实际 FEC 模式 per-run quanta。

实现策略精确为 `BackendChoice::default()=PreferNative` + 发行构建显式 `native_fec_acceleration` 并链接固定官方 ISA-L；只有 k≥2、符号长度≥64B 且真的需要编码/缺源解码时 native；k1、小包短尾 scalar 和 FEC Off 无调用是正常设计。旧代码缺编译 feature 的原生网络旧实验仍是其实际功能 PASS，却不是 ISA-L 证明。没有 NEON/AVX 具体指令调度、CPU 净增益或 Android/物理设备外推。保持 stage=experimental、原历史 FAIL/NOT_RUN 等各自原 SOURCE 记录。

本提交**纯功能卡及 cursor 的 SRC 限定事实校准**，不改任何二进制/协议，不触发网络。另一条 H1415 Windows 单实例＋独立 Linux 客户端同服真实业务已按独立原 SOURCE 在 Action 42494398656 运行，尚未结论。

```feature-impact
{"kind":"updated","ids":["native-crypto-backends"],"reason":"Recovered precision-scoped default native ISA-L selection and seven-grade real C/Windows authenticated owner qualification on actual x86 Linux, native ARM64 and Windows MSVC; current card previously inaccurately said runtime unknown. Does not promote unmeasured real VPN modes."}
```
