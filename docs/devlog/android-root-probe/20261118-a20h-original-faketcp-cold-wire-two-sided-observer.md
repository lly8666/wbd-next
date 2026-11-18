# A20h：原 Android FakeTCP SYN 已发送但未收到 SYNACK——双侧只读网络取证（2026-11-18）

## 最新已验证结论

[Commit `650542f7` Actions #44256957613](https://github.com/lly8666/wbd-next/actions/runs/44256957613) 全工作流 SUCCESS。官方 D2-S1 Artifact 14407570235 的 receipt 与 App Root 日志确认：x86 Android16 KernelSU 普通 App UID→su、正式 RootService、原 Go TUN/AF_PACKET 和同源 Linux 原 server 均真实通过；`original_android_cold_syn_send=SENDTO_PASS_NOT_PEER_AUTH`，即原 Go `ClientAssociation.Start` 真实从 RAW 发送 SYN，**不是**收到 peer SYNACK。原 Go 在 SYN 发出约 6s 后以非零退出；既未记录 SYNACK，也未记录原 AF_PACKET 收到不可信 RST，故 `real_peer_synack/tls_authenticated_32_lease/original_rust_m4_and_uid_ready=NOT_PROVEN`，真实应用 TCP+UDP/Stop 也尚未运行。宿主仅针对一次性 lo 443 RST 曾作临时精确 DROP，仍未打通连接；不得猜成 TLS、凭据或 Go 业务实现出错。

## 本批施工

新增 **只读网络取证脚本** `android/root-app/ci/x86-d2-cold-wire-observer.py`：Android Emulator **官方 `-tcpdump`** 只在 D2 的第二次启动捕获其虚拟以太网（PCAP 留在临时 runner，不进入工件），同一 runner 的真实 Linux `lo` 开始时通过一次性 root `AF_PACKET` 监听真实 TCP flags（立即降到 runner 普通 UID、不写 PCAP），两侧只计数 TCP port443 的 SYN/SYNACK/RST 及固定链路格式。两条独立 `guest-wire-summary.json`、`host-wire-summary.json` 严格区分 OBSERVED / NOT_OBSERVED / NOT_PROVEN，并注入 D2-S1 收据；不收集/上传任何包、IP、UID、SNI、证书、账户、密码或密文。退出前清理 PCAP、临时 socket 和原 RST rule。静态单元测试只产生无载荷合成 Ethernet flag，**不表示原业务 E2E**。

接下来的真正 Actions D2-S1 一次运行将回答：原 Android Go Sendto SYN 是否真到虚拟 guest NIC、SLIRP 是否把 SYN 映射到宿主 loopback，以及宿主是否实际回复 SYNACK/RST。结果若仅 guest 观测、host 未观测，则归为用户态 NAT 可能阻断而非“原 Go 失败”，后续应评估可验证的 TAP/桥接物理 Network 或真实 KSU phone 接口，不降低 Android PhysicalNetwork 精确约束。**新 SOURCE 尚未运行**；DNS takeover 两道冷安全许可仍 false，正式 ARM64 APK 和 Linux/Windows WBD 原协议未改，main/M0 不动，只有实验分支 PR #36 Draft。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20h D2-S1 收据证实原 Go SYN Sendto 成功但仍无有效 SYNACK/RST，新增 Android Emulator 虚拟 LAN 与原 Linux host lo 同时只读 TCP 旗标取证；只上传固定无敏感字段收据，不动正式 Go/Rust协议/ARM64发行/DNS冷门。"}
```
