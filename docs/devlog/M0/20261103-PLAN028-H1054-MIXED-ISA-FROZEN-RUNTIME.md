# PLAN028 H1054 — 同构建双 ISA 真实 netns 夹具修复

H1053 Action [41667172847](https://github.com/lly8666/wbd-next/actions/runs/41667172847) 的一次 AMD64 + ARM64 原 Go/Rust **BUILD PASS**，工件 ID `13246003010`，确切二进制 SOURCE `140a06622a97251863c6959c1290a0dd11b7a38b`。原两方向 Action 在 TLS 之前 QEMU 动态加载失败：缺 ARM64 `libgcc_s.so.1`，不是已证明的产品 Bug。修复 runner 包 `libgcc-s1-arm64-cross`，并修仅用于证据读回的 IPv4 regex 与错误 `tail` 参数。

**不重新编译** Go/Rust，两个独立 job 从 H1053 同一工件下载，复核 ELF machine/SHA256 和原 binary SOURCE，另记本轮 harness commit。分别验证 ARM client ↔ AMD server 与反向，真实 kernel netns、AF_PACKET、TUN、证书验证/账号密码、一个443/自动 /32、真实 UDP echo、OS MTU 读回及双方 owned Stop。新 Action 前为 SOURCE_FROZEN_FIXTURE_NOT_RUN。

ARM64 为 QEMU-user，不得称 ARM64 物理性能/CPU/p99 或 Android PASS；H998 在线收窄 FAIL、旧 ARM64 Game4FEC FAIL 和公网 ICMP 未测原样保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1054 exact H1053 mixed binary artifact reused, QEMU guest libgcc_s dependency and lease matcher fixed without second compile; two reciprocal real netns scenarios awaiting outcome."}
```

## H1055 同二进制两个角色完整结果

[Action 41668311813](https://github.com/lly8666/wbd-next/actions/runs/41668311813) **FAIL_SCOPED_UDP**。两个 role 的 ZIP artifact `13246379680` (ARM client)、`13245988762` (ARM server) 已单独核原始 client/server/udp 日志；独立下载原工件 `13246003010` 并逐项校验 SHA256/ELF。两个真实 Linux kernel netns 的原 Go TLS、自动 X25519 pre-CH、真实证书、用户名密码、自动分配 /32、双端TUN MTU=1389、Stop 全过；但真实 TUN 应用 UDP echo 均 12 秒超时：ARM client Rust TX staged UDP=1 且 first-wire=0；ARM server 场景 AMD client first-wire=114 而 ARM guest 内层 UDP 未递交。QEMU-user 原 ARM side 的 Rust packet path 不合格，不能推出 ARM64 native physical hardware FAIL 或 PASS，更不能拿模拟器 CPU/p99 做因果。

`docs/evidence/M0/PLAN028-H1055-SOURCE140A-MIXED-ISA-REAL-NETNS-FAIL-20261103.json` 为已核证的限定失败原始 SOURCE `140a066`；本次不重启同一 QEMU scene、不为模拟器重写FEC/重传/record。下一目标转真 ARM64 native host + peer 真实网络和 Windows 实际网卡/IP event。
