# PLAN029 H1700｜收Rust双平台纯单测；修cursor SOURCE；为真实Direct UDP准备物理socket与逆向IP封装

- 收 [SOURCE 889c1e74 M0-WIN-LINUX Action43344252063](https://github.com/lly8666/wbd-next/actions/runs/43344252063)：Linux Rust eligible library job 131619935035 和 Windows Rust eligible library job 131619935079 **SUCCESS**，11个 PLAN029 v4_client_split/wire 纯测试全 PASS（各自总279/304 passed）。整体Action仍 **FAIL** 于旧 public two-OS，不能把子job的绿色冒充真实Direct/Tunnel。
- 收 [Governance43344253726](https://github.com/lly8666/wbd-next/actions/runs/43344253726)：失败首因 `evidence is for a different SOURCE`，H1699 cursor上次SOURCE写4de00f，而证据引用H1698真实Win32OS源adb0ae。此提交将 last_tested_source 对齐到已实际测试的889c，并且 evidence_refs 改成 SOURCE889c 的纯单测受限证据；H1698老正例保存在历史 evidence、card和devlog，不伪造新版本重跑。
- 新 `crates/wbd-platform/src/windows_direct_udp.rs`：Windows-only独立冷路径真实 `UdpSocket::bind(physical_ipv4:0)` + WinSock `IP_UNICAST_IF`（ifindex网络字节序）设置/读取一致性 + 单真实remote connect + nonblocking `send`/`recv`，不依赖Go逐包pump，不设全局路由/WFP，也不套超时重试。Rust源解析的Direct UDP原应用包要验证当前租约、目标原展示IP、UDP长度/端口，已解封payload直接进入物理socket；逆回包组正确 IPv4/UDP checksum，源地址仍为应用所见的 `presented` IPv4（可为已宣布Fake），在完成封包之后才由未来原Wintun TX Allocate/Send，不延用借用ring/slot。此模块**未连入稳态Rust IO worker**，不能声称物理网络交付。没有引入 per-flow 线程或第二个 Wintun reader。
- `v4_client_split_wire.rs` 改造 fragmented IP：先检查完整TCP/UDP首部、IPv4 MF 8字节对齐、可用fragment关联、quota/冲突/有效期，**再**占 Direct pin；旧 first fragment quota full 后遗留Direct flow的缺陷已定向修复。到期片即使粗tick未清也不允许沿旧决策转发；不同方向复用同ID拒绝覆盖。新增单测针对满额无幽灵Direct、晚到片、异议/恶意包。
- 本SOURCE含Rust平台新Windows FFI（原crate unsafe仅模块局部allow）及纯包组装/回程。**H1700尚未测试**，接下来在原有Linux/Windows Rust单测里验证编译和包checksum，再接唯一Native Wintun/物理socket worker。真实H1694 Defender A/B/C 与H1697四阶段OS资格既有PASS维持原source范围；不重跑028，030不动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Collect exact H1699 two-platform pure Rust tests and correct M0 governance SOURCE; add physical-bound Windows UDP socket and reverse IPv4/UDP builder plus atomic fragment admission."}
```
