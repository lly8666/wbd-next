# PLAN028 H1387–H1391｜真实 Windows MTU、双账号路线争用及两条 1800秒长测分账

2026-11-08。并行的 Windows 独立源测试、两场 ARM64 真 1800 秒原始长测、原工件离线审计和签名 Npcap 供应核验全部保留各自原始 PASS/FAIL/NOT_RUN。

## 原始 ARM64 2×1800秒 L3

- [H1389 原始两场 Action 42466954711](https://github.com/lly8666/wbd-next/actions/runs/42466954711) build/baseline/heterogeneous 都 SUCCESS；各场 **1800 秒**、五名原始 Go TLS443/Rust M4 客户、原生 ARM64 Go/Rust 同 source `096a2d55...`。五用户真实轮换 PASS，原精确 Stop，服务端 baseline routed **9,709,868**/heterogeneous **14,610,542**，unrouted0/backpressure0、共享 Rust TUN reader joined。
- **基线产品与性能 PASS_SCOPED**：原始 raw 34文件 ZIP SHA256 `7c4cf6005ea025bf77455f5d1982b554bd3455e049fee29c6af119f24002ba7c`、CRC全过，0 app alert。Alice/Bob/Carol 各 old Stop 27/25/22，Dave Game4 独立 lane hot 19，Erin fixed6 old Stop16。
- **异构弱网业务/所有权轮换 PASS_SCOPED，但性能 FAIL**：原始 raw 34文件 ZIP SHA256 `58fae41aa929fe9b8234f52fab070b9fe0beabad00869ff4a0a94a23fc28c851`、CRC全过。五客户端 A/B/C/D/E 原 owner turn 23/20/17/16 Game4 hot/15、Stop 全通过，但 Erin 在原配置 kernel netem 30%/125ms 上行真应用无收件 **3.31秒**、下行 **3.32秒**，超过原 750ms 告警门槛；原告警2不能由 Action SUCCESS 抹除。
- [H1390 原 34 文件严格离线复核 Action 42472269266](https://github.com/lly8666/wbd-next/actions/runs/42472269266) 双场作业均 SUCCESS，**没有重跑网络**；原始 app 181001 个10ms bin/方向、所有原 owner 轮换/stop、实际共享 TUN/overflow0、两个原 Erin alerts均核实。离线 2文件 baseline ZIP `b8dc44f0825c1dc985064aac93952c41defac3892e5fd92157a391f585705bcb`、heterogeneous ZIP `0761fe45c1025ef04be8368fd0167cb51d5bc93f29cf4bd6b129d30d1cf70f22`，CRC 全过。证据：docs/evidence/M0/PLAN028-H1390-H1389-SOURCE096A-ARM64-TWO-1800S-L3-BASELINE-PASS-HETERO-ERIN-PERFORMANCE-FAIL-20261108.json

## Windows 真 NIC MTU1500→1280 原始双端 App 成功（但不是 hot 同socket）

- [H1388 Action 42466674474 attempt2](https://github.com/lly8666/wbd-next/actions/runs/42466674474) 六个作业 SUCCESS；真实签名 Npcap/Wintun、Windows2025+WSL2 的同源码9a21 Go TLS443/Rust M4，同ifindex25、同 `198.19.254.1` 真 OS MTU **1500→1280**，Windows SYN MSS **1420→1240**，原 Wintun 真实 OS TUN **1389→1209**。Windows 原 UDP sent107/rx108，Linux sent234/rx103，两端 TCP37 echo、A 原代 Stop→B 新代 Ready、所有原 OS/WAL/alias/默认路由最终恢复；原 raw **28文件 CRC全PASS** ZIP SHA256 `0c5d1ea08d4be46b5e5668f190bf51f295460837783486fca6fcb6a93639ae3b`。
- H1388 attempt1 只因签名驱动 CDN 504 **NOT_RUN**；attempt2 真产品已经 PASS。旧 H998 **不重建同socket hot物理 MTU**原失败仍保持，不能偷换。证据：docs/evidence/M0/PLAN028-H1388-SOURCE9A21-WINDOWS-SAME-IP-MTU1500-1280-REAL-TLS-UDP-TCP-STOP-PASS-20261108.json

## Windows 双真实原产品仍 FAIL：B 第二个 Wintun /32 路由所有权

- [H1387 Action 42466552995 attempt4](https://github.com/lly8666/wbd-next/actions/runs/42466552995) 真签名驱动下载终于成功；原 WSL2 Go TLS443/Rust M4 服务端确实认证 **Alice、Bob 两个账号**，两个原 server session READY。Windows A 真 Wintun ifindex30、原 `WBD_WINDOWS_CLIENT_READY`、TCP echo 原始通过，原 Rust RX 1,562且 WAL Stop PASS；B 真 Windows 原 Go TLS SYN/服务器认证成功，Rust线程实际创建，但 **B `WBD_WINDOWS_CLIENT_READY` 未出现**。
- B Win32 app 源IP绑定实际 `WinError 10049`，原 B Stop/WAL 提示 `windowsclient: route is not owned; refuse to replace`；因此 B 原 Windows Wintun OS 路由激活失败、同服A+B双 Win32 UDP/TCP 及 A Stop 后 B继续都是 **NOT_QUALIFIED**。这次是**真实产品未达到目标的 FAIL**，不能称 CDN 或报告误报。原21文件 ZIP CRC全过 SHA256 `c97acdaf4b90685da0ca64aecc2649258ec2b177f06adeecd59703d20d6634c6`，证据：docs/evidence/M0/PLAN028-H1387-SOURCED9B4-WINDOWS-DUAL-A-READY-B-ROUTE-OWNERSHIP-FAIL-20261108.json

## 已确认的签名驱动源码不能乱换

- [H1391 Windows 签名源核验 Action 42472578878](https://github.com/lly8666/wbd-next/actions/runs/42472578878) 原官方 `npcap-1.88.exe` SHA256 `a2f4ec...`、Authenticode Nmap Valid、两个 userland DLL 原 hash 匹配，但NSIS提取的 `NPFInstall.exe`/`npcap.sys`/`npcap.cat` 3个签名驱动文件与项目旧批准 test driver package 的**硬固定 SHA 不同**。据此新源 **NOT_REPLACEMENT**，不禁用硬pin，不上传驱动二进制或假称原产品启动。证据：docs/evidence/M0/PLAN028-H1391-SOURCEC42C-NPCAP-OFFICIAL-1-88-INSTALLER-DIFFERENT-DRIVER-HASH-NOT-REPLACEMENT-20261108.json

## 后续硬门

Windows 真双认证 B 所有权/路由作用域仍需修正并真实两设备 A→A+B→B/TCP/UDP/WFP/WAL 验收；H998 同一socket hot PMTU仍开放。异构 Erin 30%/125ms 原3.31/3.32秒真实性能 FAIL 不能用双1800s Actions绿灯视为全过。PLAN028 **IN_PROGRESS**。

```feature-impact
{"kind":"none","ids":[],"reason":"Evidence-only accounting: original source096a two 1800s L3 baseline true PASS vs hetero two genuine Erin performance gaps; source9a21 Windows original cold MTU true PASS; sourced9b4 Windows A authentic Ready/B route ownership true FAIL; sourcec42c signed-driver provenance not a verified replacement. No feature card or production code changed."}
```
