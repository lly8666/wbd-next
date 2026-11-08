# PLAN028 H1415｜一 Windows 签名客户端＋独立 Linux netns 原客户端，同一标准 TLS443 server

2026-11-08。H1414 [原生 bridge Action42493577906](https://github.com/lly8666/wbd-next/actions/runs/42493577906) 已证 Windows host→WSL2 guest vSwitch 与另一个 Linux namespace→同一 bridge 的真实 UDP 内核往返，严格恢复 eth0 原 IPV4/default gateway/MAC 以及自有 bridge/netns/HyperV firewall；该资格只是 underlay 可行性。旧 H1412/H1413 cleanup CI FAIL 原样保留，反映脚本错误，不改变产品业务资格。

基于成熟 [H1382 双Windows多账户 server](https://github.com/lly8666/wbd-next/blob/main/tools/m0_plan028_h1382_windows_two_original_tls_product.py) 的共享 server users/manual lease 原接口、[H1407 签名 Win↔Linux server Go TLS/Rust Game4](https://github.com/lly8666/wbd-next/actions/runs/42487098097) 的 Windows 单原客户端以及 [H1414 WSL2 bridge](https://github.com/lly8666/wbd-next/actions/runs/42493577906)，本次新增**一个**完整真实产品 L1 场景：original Go TLS443 + Rust shared TUN server 绑定 guest 原真实以太桥；Windows 单原 Npcap/Wintun、account Alice/10.66.0.2；隔离 Linux namespace 的原 Go/Rust raw/veth/TUN client account Bob/10.66.0.3（独立安装 ID、AES128）。Go 原有 client/server/record/owner 参数、原密文/MTU 默认1460、安全 PN/Stop 全不改变。两客户端真实 UDP/TCP 各自业务并存，Windows A Stop 后 Linux B 原 TUN 仍发收 UDP/TCP，最后 Bob/server owner Stop、bridge/route/Win WAL 全恢复。禁止另起第二 Windows Wintun。

已知待验：Linux Client FakeTCP legacy persona 与 shared server 为 Windows 端实际需要的 `--peer-persona windows11` 并存可能是冷路径真实接线缺口，不能预判；实际 A 标准认证和 B TLS 回执决定是否修。不得改公共流协议和外层所有权以盲兼容。Windows job/日志/源 hash 完整后再把本场 `PASS/FAIL/NOT_RUN` 写 Evidence；这次提交只是完整候选，**NOT_RUN**，原签名旧资格和 ARM64 2×1800 PASS_SCOPED保留。

```feature-impact
{"kind":"none","ids":[],"reason":"One native original product integration test topology and single-scenario workflow only; no product wire, FEC/Auto/Game algorithm, hot path or user-facing feature change."}
```
