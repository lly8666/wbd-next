# PLAN029 H1720：H1719 同源码 Windows GUI/治理回收

- `b8c800a4e7e4473c307d991c3dd800d8d9c8c3aa` 的 [治理43384251251](https://github.com/lly8666/wbd-next/actions/runs/43384251251)、[维护43384251318](https://github.com/lly8666/wbd-next/actions/runs/43384251318)、[Windows CLI编译43384251247](https://github.com/lly8666/wbd-next/actions/runs/43384251247)、[原Go/WinForms真实配置与v2预检43384251255](https://github.com/lly8666/wbd-next/actions/runs/43384251255) 全部PASS_SCOPED。
- WinForms运行原Go CLI的v2只读预检返回 `absent`、无 owned WAL；双单DNS、默认outer1460、自动只读inner、Game4配置、保存重启和CLI effective均通过。没创建Wintun或真实联网Applied。
- [旧Windows/Linux Normal43384251240](https://github.com/lly8666/wbd-next/actions/runs/43384251240) 同SHA `legacy1400` 网络PASS但**非**029双出口。H1717真实Win32四阶段OS、H1695 A/B/C、H1709 TCP EOF、H1713 CN FakeIP UDP仍仅局部资格；H1716公网FAIL原始文件保留。
- 下一真实产品首个断点为当前原认证 Rust `stage_sources` 仍把所有Wintun帧送入Tunnel，没有接 `PacketIngress` 分流/物理UDP/内核TCP/方向DNS；故D1–D5/P1–P2、资源限额和startup-padding等**NOT_RUN OPEN**。不重复探针，不重开028矩阵，不启动030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-locked genuine WinForms original-Go v2 native preflight PASS limited to read-only GUI/config, not product 029 egress"}
```
