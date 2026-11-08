# PLAN028 H1419 — Linux B 测试的 AutoLease/手工账户映射冲突修正

2026-11-08。[H1418 原 Action42496215236](https://github.com/lly8666/wbd-next/actions/runs/42496215236) SOURCE `042afb09761dae5705e4bb056741ed14910201aa`：Windows 2025 一台签名 Npcap/Wintun 原 Go TLS/Rust M4 A Ready、共享单 443 server Alice `V4_PUBLIC_MULTI_SESSION_READY active_detached_flows=1 auto_lease=0`；Linux Bob 经真实独立 netns/veth 确实收到 SYNACK MSS1420，却有 8 次服务器 `V4_PUBLIC_MULTI_ADMISSION_REJECT stage=original_tls_or_owner`，从未 Rust READY。两客户端应用/精确 Stop **NOT_RUN**，原 Action CI FAIL 原样留存；Windows WAL 清理、原物理 bridge netns/IP/默认路由恢复 PASS。

根因是当前 **H1415 测试配置**：服务器 `--manual-client-leases-file` 为 Alice 10.66.0.2/32、Bob 10.66.0.3/32 的唯一手工身份，`originalV4ManualAccountTunnelAfterAuth` 强制拒绝 `req.AutoLease=true`，并要求账户授权的非零 TunnelID；但 Linux Bob 当时传的是 `--auto-ip`。既有 Go `manual_lease_map_linux_test.go` 已单测这个合法拒绝，因此不是放宽产品认证或调全局 persona 的理由。

H1419 **仅修原 Linux 测试调用方**：改用 `--tun-ipv4 10.66.0.3/32 --tunnel-id 102030405060708090a0b0c0d0e0f002`，仍独立 Bob 用户凭据及 AES128 record/客户端 netns、同 server；Stop marker 由 Auto shared-reader `V4_PUBLIC_SHARED_TUN_STOP generation=` 调整为本手工原生产 CLI 真正的 `V4_PUBLIC_NATIVE_STOP_DRAINED role=client`。所有 Go/TLS/Rust/Record/ISA-L/MTU/Windows WAL 产品代码保持不动。完成新原 Action 双边 UDP/TCP、Windows A Stop Linux B 存活与所有 own Stop/恢复前仍 **NOT_RUN**。

```feature-impact
{"kind":"none","ids":[],"reason":"One existing integration fixture now uses the server's authenticated manual lease contract and corresponding existing Linux manual Stop receipt; no product feature or protocol changes."}
```
