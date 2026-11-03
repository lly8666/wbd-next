# PLAN028 H1056 — 精确 H1053 二进制移到真实 ARM64 runner

H1053 生成一次原 Go TLS/Rust 双 ISA SOURCE `140a06622a97251863c6959c1290a0dd11b7a38b`（[Action 41667172847](https://github.com/lly8666/wbd-next/actions/runs/41667172847)，工件 `13246003010`），H1054 QEMU-user ARM64 虽已认证、租约/MTU和Stop成功，实际内层 UDP 双向均 FAIL。该结果不能直接推论 ARM64 真机；不该为用户态仿真器改 Rust 热路径或刷 seed。

H1056 不构建 Go/Rust、不拿其它 SOURCE ARM64 工件。直接把 H1053 ARM64 **原始二进制字节**复制到真正 `ubuntu-24.04-arm` runner，复核每个 ELF e_machine=183、SHA256 与原 `mixed-isa-build/manifest.json`。原 `arm64_linux_netns_smoke.sh` 的单个 Normal 真内核两端口夹具仅增加可选 `WBD_ARM64_USE_AUTO_ROUTE=1`：省去手工route-key、client导入本次自签TLS根证书，并检查双方原 pre-ClientHello X25519 log；其它原 Go TLS / Rust、真实 AF_PACKET/TUN、双向 ICMP/Stop、外层默认1460均不改。

这一步回答**同一 H1053 ARM64 bytes 在 native ARM64 内核能否业务收发**；是两台真 netns，但运行在**一台 ARM64 主机**，严格不算 ARM64↔x86 双物理机、Windows真切网、CPU/p99 或 Android PASS。结果须由新原生 Action 和工件核验。H998 在线缩窄 FAIL、旧 ARM64 Game4FEC FAIL、远端 ICMP 未测照旧。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1056 run exact H1053 ARM64 original Go/Rust binary bytes on physical native ARM64 runner, compare with prior QEMU-user UDP failure; X25519 password/cert and existing TUN/Stop fixture, Action pending."}
```

## H1057 原生 ARM64 资格结果

[Action 41670216313](https://github.com/lly8666/wbd-next/actions/runs/41670216313) **SUCCESS**；原生工件 `13249110172` 已独立解包并检查全部 12 个证据文件（原 `manifest.json`、SHA256SUMS、双方日志、两方向 ICMP、`receipt.json`）。原二进制 SOURCE `140a06622a97251863c6959c1290a0dd11b7a38b`、测试 harness SOURCE `b7630173b5f868a3d2a534ba5dd5338a0a4af7b0`、真实原 Go/Rust ARM64 sha256 未变。真实 ARM64 native runner（不是 QEMU）上一个 Linux kernel 的两 netns，原 X25519→TLS 证书/密码、双方 Rust M1 数据面、外层1460/内层OS1389、双向各3个 ICMP 均0% loss、双方 Stop/namespace 清理 **限定 PASS**。证据 `docs/evidence/M0/PLAN028-H1057-SOURCE140A-NATIVE-ARM64-TLS-ICMP-20261103.json`。

这只将“相同 ARM64 产品字节在 native ISA 收发成功”与 QEMU 的 UDP FAIL 分开，不是不同实体 ARM64↔x86 主机间真通信，也不是 CPU/p99 或 Game4FEC 性能、热缩 MTU、Windows 物理切网资格。
