# PLAN028 H1411｜三原生平台七强度 ISA-L 实际启用资格

2026-11-08。先收完全部 H1409/H1410 同系 Action，无在途任务。原 H1409 Linux x86_64/原生 ARM64 相同 SOURCE `337dc093` 各 7/7 强度真实 `NativeIsaL` C Encode 且 Prepared M4 量子回传确实为 Native，7/7 都与 scalar 原记录逐字节一致；两原 ZIP CRC 合格。原 Windows H1409 Action 虽 CI FAIL，但 NASM 已由 Chocolatey 安装、没有更新**本步骤** CMD PATH 导致 NMAKE 尚未建库，Win 七档属于 NOT_RUN，非产品失败。

后续 H1410 `0cdea544` 仅修相同步骤 PATH、审计原硬编码 16 测试数（实际新增测试后 17 个）；[Windows 原 Action42490713541](https://github.com/lly8666/wbd-next/actions/runs/42490713541) MSVC pinned ISA-L `c387163f...` 静态库 / release DLL 构建、C 编码七强度以及**原认证 Windows Fixed/Auto FEC2 owner 入口**七档各 `NativeIsaL`、scalar 字节完全一致且原 Stop/Release，全部 PASS。另 [FEC2 native 17/17 原 Action42490713558](https://github.com/lly8666/wbd-next/actions/runs/42490713558) PASS。三份原 ZIP 的 SHA、原 Rust Release hash 和原 ISA-L 静态库 hash、精确 SOURCE 和适用边界详见 `docs/evidence/M0/PLAN028-H1411-WINDOWS-LINUX-ALL-FEC-GRADES-NATIVE-ISA-L-QUALIFICATION-20261108.json`。

代码：`BackendChoice::default()` 是 `PreferNative`；Normal Fixed/Auto Rust 原 owner 调度、Win C ABI 修复符号和 Game2/4 Fixed 的相同 `Rs16` 均由此 backend 选项获益。编译须显式 `native_fec_acceleration` 并链接固定官方 ISA-L；源 k≥2、符号≥64B 且实际进行 parity 才原生，其他合法 scalar。FEC Off 三档无 ISA-L 工作，不应判退化。现有 **Game4 Fixed6** Windows2025↔Linux server 原 Wintun/Npcap/TLS/UDP/TCP+owned Stop 两代 Windows native TX 2/11、Linux server 4/4 真实功能 PASS_SCOPED；ARM64 native 2×1800s Game4 亦原生。**Normal Fixed/Auto/Game2 的每个真正网络模式非零 native 计数**目前只证明了建链与代码接线/原生 owner，不能把未测写成全部已触发。

下一最值得做的是一台 Windows 一个 VPN 客户端，与独立 Linux 客户端同时连同一真实服务器且 B Stop A 继续（原用户 scope）。原 Win+WSL2 server 单客户端不是此项多客户端资格，不能拿同机双 Windows 代替。保留 Android/物理/H998 原有限资格，PLAN028 仍 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Authoritative raw native ISA-L grade, original Windows owner and build-source evidence; no product or protocol change."}
```
