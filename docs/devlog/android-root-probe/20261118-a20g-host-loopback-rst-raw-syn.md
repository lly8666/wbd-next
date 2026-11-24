# A20g：原 FakeTCP 首个 SYN 原生 Sendto PASS；测试宿主 scoped RST 准入与 guest RST 观测（2026-11-18）

**SOURCE `fed4dac1c6afa363f0e56324d6d0e0665288dff5` 真证据**：[GitHub Actions #44255257029](https://github.com/lly8666/wbd-next/actions/runs/44255257029) 全 workflow SUCCESS，包括正式 ARM64 APK、同源 Android ARM64/x86 Go/Rust、原 Linux server/client/Rust、原 Linux oracle、x86 KSU 普通 App Root/Network、D2-S1 同源原 Go RootService TUN/AF_PACKET 和宿主原 Linux server 真实 TUN。官方收据/Job 标记 `SYN_TX SENDTO_PASS_NOT_PEER_AUTH`，证明 **Android 原 Go `ClientAssociation.Start` 通过内核 RAW `syscall.Sendto` 成功写出首个 SYN**。但原 Go 在 SYN ACK 前退出，`real_peer_synack/tls_authenticated_32_lease/original_rust_m4_and_uid_ready=NOT_PROVEN`；本次 45s 的观测因早退未用满。不能把 Sendto 成功称为 FakeTCP/ TLS 成功，也不能证明只是 QEMU NAT 的问题。

原 Linux 已验证的 FakeTCP netns oracle `tools/m0-v4-public-real-linux-netns.sh` 在真正原 SYN 收发时阻断 Linux TCP 内核的自动 RST：`ip netns exec ... iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP`。A20 的新 x86 Android↔host-loopback server 此前没有等价条件，可能将内核的拒绝 RST 送到 QEMU 用户态 NAT。**本次只在一次性 Ubuntu Actions runner 的 `OUTPUT -o lo -p tcp --sport 443 --tcp-flags RST RST` 上加临时精确 DROP，严禁改默认路由、iptables 全局清空、DNS、安全接口或 Android Root UID 规则；trap 里仅删除同一条 CI rule，保证回滚。** 此测试路由只允许 CI Linux server 的 localhost:443；不修改原 Android/ Linux 任何报文。若宿主不允许 iptables 则 D2-S1 真实 FAIL，不伪造。

增加原 Go Android RX 已匹配真实 AF_PACKET 源/目标四元组的预 TLS `RST` 固定 marker `V4_PUBLIC_ANDROID_COLD_UNAUTH_RST_RX`（一次性 `atomic.Bool` 防刷），由正式 Java RootService anchored event `ORIGINAL_GO_COLD_UNAUTH_RST_RX` 记录，host 单测同步验证 prefix spoof 拒绝；D2-S1 无敏感原始 stderr/包/IP/密钥的收据写 `original_android_unauth_rst_observed=OBSERVED/NOT_PROVEN`。RST 是**未认证传输失败证据**，不是 Go 服务端身份或 M4 收据。现有 SYN/重传/TLS、AEAD/PN、Rust workers、Stop/UID route、正式 ARM64 APK 功能不变。

**新 SOURCE Action 尚未运行**；真实 TLS/自动 /32/应用 TCP+UDP/Stop 等仍 NOT_PROVEN/NOT_RUN。只有实验分支 PR #36 Draft，main/M0 未改，系统 DNS 接管两道安全冷门继续 false。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20g 同源 Android 真实原 Go raw Sendto SYN PASS 但握手前非零退；在一次性 GitHub runner 仅隔离 lo TCP sport443 自动 RST（退出精确撤回），原 Go AF_PACKET 只读 RST fixed marker/Java enum，用事实区分 NAT/RST 和原业务错误，不改协议/ARM64发布/DNS门。"}
```
