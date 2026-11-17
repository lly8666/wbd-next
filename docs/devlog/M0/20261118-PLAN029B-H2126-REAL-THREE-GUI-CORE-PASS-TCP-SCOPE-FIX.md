# PLAN029B H2126｜三代真实 GUI 主验收全程达成，旧028双向TCP验收混入使 Action FAIL

[Action44147461765](https://github.com/lly8666/wbd-next/actions/runs/44147461765) SOURCE `cb40f28ea70789baaab6549ea3cf084f22f2decc` **整体 FAIL**，不是“完成”。原 ZIP `14357279016` SHA256 `f0ed08fd8a862b2030722881d2712703bb330a51304e8263d380c934aee91c6a`，28文件CRC全PASS、Go/Rust/夹具 SOURCE 同锁；Cheap、WinGo、WinRust、LinuxRust、Linux与Windows原始构建均SUCCESS。

**真实B4核心限域达成：** 原 WinForms `SetEditor/SaveEditor/Connect/Disconnect` 三代各自原始TLS源端口41031/41032/41033及原Linux Rust M4；原Win2025 Wintun OS Applied三次、外层MTU1460和实际inner1389三次、原始 SYN/SYNACK MSS1420三组；高级CN真FakeIP+物理DNS/物理业务，普通CN真A CNAME TTL2+物理DNS/Tunnel业务，all无业务分流+Tunnel DNS/业务。Linux原本机UDP53上游三个DNS与真实业务均识别；Windows APP三次真内核UDP echo，旧FakeIP app无回复，Linux物理与TUN AF_PACKET旧FakeIP目标发包0；原WinForms owned Stop/WAL清理三次，原Linux共有TUN最后Stop。独立两端普通UDP窗口Windows 64发67收，Linux315发63收（只证明正向交付，不代表rate/p99）。

**整体FAIL的首错为 B4 实际三代验证之后默认执行的历史 PLAN028 Linux→Windows 双向TCP对照**：Windows client_echo=true、Linux server_received=40，证明 Windows→Linux TCP 到达；反向 Linux→Windows Windows server_received=0，Linux client_echo=false，该方向在原夹具注释明确为“previously failing PLAN028 ... inbound comparator”。B4没有授权重开028，也不能为了绿灯取消真TCP。故 [H2127新SOURCE](https://github.com/lly8666/wbd-next/commit/534b7ba84af901492f571334a76ed510dad093da)只让 B4 复用已有真实原 Win→Linux Tunnel TCP（原 H1762 真正独立收发），保留原严格两端回执和Stop；旧028双向分支未动。唯一新 Action [44150334492](https://github.com/lly8666/wbd-next/actions/runs/44150334492) 收集时尚未最终完成，B4不可提前升整体 PASS。

B0–B3既有SOURCE历史限域保持；Game2/Game4、B5同VM10Mbps CPU/实际GiB/RSS/p99仍 NOT_RUN，029/029B OPEN，030 未开始。

```feature-impact
{"kind":"none","ids":[],"reason":"H2127 only test runner chooses preexisting true Windows->Linux kernel TCP comparator after original three-generation B4; no Go/Rust/TCP/FEC/wire/product runtime change or feature readiness promotion."}
```
