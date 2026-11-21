# Linux/Windows shared minimal outer DATA parser

Linux AF_PACKET RAW batch/legacy reader和Windows Npcap正式DATA接收改为单次轻量解析，不再对收到的加密DATA逐包扫描完整TCP checksum或以可变DSCP/DF/options模板提前拒绝。仍验证20B IPv4/20B TCP长度、当前tuple、未分片、DATA flags、MTU。原M3 AEAD/PN是唯一业务交付判断。纯ACK/SACK没有M3认证，保留短包checksum与范围检查。按固定头flags分类避免重复DATA/ACK解析。原strict公共解析器供测试诊断，不改Go标准TLS/AEAD/wire/owner/Stop。

## 资格与回归边界

- 施工分支：`perf/outer-rx-minimal-parse-20261121`，不直接修改main。
- 只移除无业务认证意义的前置完整性扫描/重复检查；不可越界的结构与记录长度、租约/generation、真正AEAD/PN仍执行。
- 目前仅有改动源码及静态测试；平台实际通过情况由当前source CI记录决定。不以BUILD_PASS冒称性能PASS。

```feature-impact
{"kind":"updated","ids":["linux-raw-tun","windows-native-transport"],"reason":"减少加密DATA在原M3前的外层重复校验/诊断/预解析；真实CPU、吞吐、兼容性仍需同源跑测。"}
```

## 合并候选：与 H2223 Game READY 共存及同源重测

2026-11-21：以主线 `5e2b083fc13391bf2d6ff3922d646abdc9c995f5` 为基底，将性能 PR #69 的 Rust Linux/Windows DATA 最小解析、单测和 ARM64 handover fixture 通过非强制双父 merge commit `459bba6aed013d03ef58ea63b5f1a4789e05eef6` 集成；Windows 原 H2223 Game2/4 idle READY 判定、Game original Go 汇编清单、主线 v4routekey 构建路径均保留。Windows/Linux feature-card 仍满足 16 KiB 上限。

已单独实测成功：Windows+Linux Normal [44874693298](https://github.com/lly8666/wbd-next/actions/runs/44874693298)、ARM64 原生双端 [44874254895](https://github.com/lly8666/wbd-next/actions/runs/44874254895)、ARM64 Normal/off 物理切换与 Game4 [44874980855](https://github.com/lly8666/wbd-next/actions/runs/44874980855)；主线 H2223 Game2 [44876703877](https://github.com/lly8666/wbd-next/actions/runs/44876703877) 和 Game4-FEC6 [44876705732](https://github.com/lly8666/wbd-next/actions/runs/44876705732)。这些均是**各自分支的真实独立历史成品证据**，不能替代本次集成源码测试。

本次以同一新来源重跑：Linux x86/ARM64、Windows Rust 原生编译与单测；Windows 真签名驱动+Linux WSL2 Normal 和 Game4-FEC6 双端业务，以及 ARM64 真 TLS/TUN 双端和 physical handover 的四组端到端场景。结果由实际 Actions 退出态决定，不伪报 PASS。Game2 代码路径不变，但可由合并前真机 Game2 证据补充。

## 合并前同源资格测试 —— PASS（2026-11-21）

本次整合版本 **`ade7937076bab4f0ec70c2462d4a6a25661ab180`** 在以下四组 GitHub Actions 各自完整编译、运行、Stop 均 PASS，未复用旧分支产品成品：

| 资格范围 | GitHub Actions | 实际结果 |
| --- | --- | --- |
| Windows 原始 Go + Rust 签名 Npcap/Wintun 客户端 ↔ Linux WSL2 原始 Go/Rust 服务端，Normal | [44878077613](https://github.com/lly8666/wbd-next/actions/runs/44878077613) | SUCCESS，`WBD_WL_TRUE_PUBLIC_MODE_WIN_LINUX_DUPLEX_STOP_PASS normal`；同源双向业务与 Stop |
| Windows Game4-FEC6 ↔ Linux 原始服务端 | [44878079422](https://github.com/lly8666/wbd-next/actions/runs/44878079422) | SUCCESS，`WL_PUBLIC_REAL_MODE_RESULT game4-fec PASS`；H2223 Game READY + 新 DATA RX 同源集成 |
| ARM64 Linux 原 Go/Rust 双端 TLS/TUN/UDP | [44878081170](https://github.com/lly8666/wbd-next/actions/runs/44878081170) | SUCCESS，`M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS` |
| ARM64 Linux 两代物理源切换、Normal/Auto/Game2/Game4 共存 | [44878083112](https://github.com/lly8666/wbd-next/actions/runs/44878083112) | SUCCESS，`M0_PLAN028_H1157_NATIVE_ARM64_ORIGINAL_ONE443_MIXED_COEXIST_REAL_48_UDP_SOURCE_SHA_PASS` |

[44878015084](https://github.com/lly8666/wbd-next/actions/runs/44878015084) 为紧邻的**相同 Rust 代码**整合提交 `459bba6aed013d03ef58ea63b5f1a4789e05eef6` 的原生编译/单测矩阵（Linux x86、Linux ARM64、Windows x86 均 SUCCESS）；此后到 `ade7937` 仅改测试派发 YAML 和本日志，产品 Rust/Go 未变。

**结论范围**：上述是同源产品 E2E 功能 PASS，而不是 CPU/GiB、Mbps 增益认证；Linux 采用真实 WSL2 内核但仍同一物理 Windows Actions 宿主，并非独立公网主机。此改动只精简前置密文校验，原 AEAD/PN/Stop 与纯 ACK 合法性仍由既有路径承担。Android 实验分支依旧独立，不在本次 main 合并内。
