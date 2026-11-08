# PLAN028 H1407 — Windows Game4FEC 本机 ISA-L 实时收包与 owned Stop 资格

2026-11-08。直接收取上一轮源码 `eed0392f588053409f5dc52870d1f2d0fd55b033` 的 [真实 Action 42487098097](https://github.com/lly8666/wbd-next/actions/runs/42487098097)，原 Windows2025 signed Npcap/Wintun、原 Go TLS443、Linux WSL2 原 Go/Rust M4 server。**同 SOURCE** 35 文件原 ZIP CRC 全部 OK，原 exe/DLL/服务端 hash 和 Win64 ISA-L 官方静态档 sha256 见 `docs/evidence/M0/PLAN028-H1407-SOURCEEED-WINDOWS-GAME4FEC-ISAL-REAL-OWNED-STOP-PASS-20261108.json`；该次真实 Game4+FEC6 原版新旧两代认证、真实两端 UDP/TCP、source IPv4 .1→.9、内层 OS 1358B/用户外层默认 1460B、原服务端 B 就绪后旧代还保留 17.453s、旧代正确退休、新代服务不中断及两端 owned Stop **PASS_SCOPED**。

最重要的新增事实：原产品 Windows M4 Game4 FEC 两代 Stop 冷读回 `selected=prefer-native native_linked=1 tx_native_quanta=2/11`，Linux 原 server 两代分别 `tx_native_quanta=4/4`。因此 Windows release native 硬件加速**不只编译成功，真实 FEC 已执行**；同时允许原产品 k1/短块合法 scalar，也不把无丢包时 rx_native=0 算成未触发编码。读取位置在 owned Stop，不增稳态热轮询/头/Go热泵。

另一条 [旧 PLAN013 Windows ABI Action42487098054](https://github.com/lly8666/wbd-next/actions/runs/42487098054) CI FAIL；但原 Windows Rust 74/74 和 Health19 个测试、真实 MSVC DLL C ABI 调用均已 PASS，直到历史冻结 M4 Go assembly 检查发生**预存相同 path 的严格 source-owner 拒绝**，旧 Go TLS 复验未执行。按用户外因分账：旧 Action FAIL 原样保留、将既成 Rust ABI 标 PASS_SCOPED、冻结装配为 HARNESS_OR_CI_FAILURE、未执行后续为 NOT_RUN；与另一完整同源原签名产品的 scoped PASS 不矛盾。无因一条已知旧脚本阻断重跑 Windows 真业务。

仍缺 Windows **一台一 VPN** + 独立 Linux **客户端**同一 443 server 的多身份/租约并发及 A Stop B 继续；不能拿 Windows↔Linux server 这条证据替代，不能又启同机第二 Windows Wintun。L3 原两条 ARM64 1800 秒、独立 Linux 五人及其他已验资格维持；PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Evidence-only classification of same-source actual Windows Game4FEC native ISA-L readback, with separate historical frozen-assembly CI failure; no product code changes."}
```
