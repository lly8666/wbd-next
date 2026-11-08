# PLAN028 H1383｜并行双 ISA 原始 TLS 假冒凭据拒绝、A/B 仍真实通信

2026-11-08。与 Windows 真双产品 H1382 同时并行：源锁定的原 x86_64 和 ARM64 Go TLS443/Rust M4 同一服务器接收原 Alice、Bob 两个独立账号/手动 /32，并已产生真实双方内核 UDP 后，在第三原 netns 创建相同 Alice tunnel ID 与 /32、密码错误的原 Go TLS 客户端，要求原服务端实际保护认证阶段拒绝、没有第三个原 server Rust Ready，Alice 与 Bob 各自再真实 UDP echo 5 次。然后原 A Stop、B继续、A 新 TLS 和各个 exact Stop，服务器 routed>=69、unrouted=0、backpressure=0。

没有更改原 Go/Rust TCP/TLS/wire 或业务源，仅增加原生 Linux test-owned 独立用例。Windows 两已认证签名产品 H1382 与旧 Windows H998 同连接热 MTU FAIL 仍单独判定。

```feature-impact
{"kind":"none","ids":[],"reason":"H1383 independent native x86+ARM real wrong-password same-lease original protected Go TLS candidate rejection, test only; no feature/product code change."}
```
