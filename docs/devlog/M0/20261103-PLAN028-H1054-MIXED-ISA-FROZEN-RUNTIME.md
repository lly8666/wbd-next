# PLAN028 H1054 — 同构建双 ISA 真实 netns 夹具修复

H1053 Action [41667172847](https://github.com/lly8666/wbd-next/actions/runs/41667172847) 的一次 AMD64 + ARM64 原 Go/Rust **BUILD PASS**，工件 ID `13246003010`，确切二进制 SOURCE `140a06622a97251863c6959c1290a0dd11b7a38b`。原两方向 Action 在 TLS 之前 QEMU 动态加载失败：缺 ARM64 `libgcc_s.so.1`，不是已证明的产品 Bug。修复 runner 包 `libgcc-s1-arm64-cross`，并修仅用于证据读回的 IPv4 regex 与错误 `tail` 参数。

**不重新编译** Go/Rust，两个独立 job 从 H1053 同一工件下载，复核 ELF machine/SHA256 和原 binary SOURCE，另记本轮 harness commit。分别验证 ARM client ↔ AMD server 与反向，真实 kernel netns、AF_PACKET、TUN、证书验证/账号密码、一个443/自动 /32、真实 UDP echo、OS MTU 读回及双方 owned Stop。新 Action 前为 SOURCE_FROZEN_FIXTURE_NOT_RUN。

ARM64 为 QEMU-user，不得称 ARM64 物理性能/CPU/p99 或 Android PASS；H998 在线收窄 FAIL、旧 ARM64 Game4FEC FAIL 和公网 ICMP 未测原样保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1054 exact H1053 mixed binary artifact reused, QEMU guest libgcc_s dependency and lease matcher fixed without second compile; two reciprocal real netns scenarios awaiting outcome."}
```
