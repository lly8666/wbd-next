# A20j：原 Linux AF_PACKET 未证实有效 SYN，独立 TAP host admission（2026-11-18）

[同源 SOURCE `6c6cfa2d` Actions #44262097315](https://github.com/lly8666/wbd-next/actions/runs/44262097315) 全 workflow SUCCESS：ARM64/x86 同源码 Go/Rust、正式 ARM64 APK、Linux 原协议 oracle、x86 Android16 KSU 普通 App→Root/PhysicalNetwork、D2-S0 原 Linux server 和 D2-S1 正式 Android RootService TUN/AF_PACKET、原 Android Go `Sendto` SYN 全部真实通过。官方 Artifact #14408871897 双侧收据：`host_loopback_syn_to_original_server=OBSERVED`，但同一宿主原 **Go server** 的 `original_linux_server_untrusted_raw_initial_syn=NOT_PROVEN`，`original_linux_server_untrusted_raw_synack_tx=NOT_PROVEN`，`real_peer_synack/tls_authenticated_32_lease/original_rust_m4_and_uid_ready=NOT_PROVEN`，TCP+UDP 和 owned Stop 仍 NOT_RUN。模拟器 Ethernet PCAP 0帧已改成 NOT_PROVEN，不能等同其 Wi-Fi 流量为零。这不是 Go/TLS/Rust 业务通过证据，也不应假定原服务端已经收到有效 FakeTCP SYN。

**方向调整**：QEMU 用户模式 NAT 将 Android 原始 TCP SYN 翻译为宿主普通 TCP socket 是可检验的环境障碍假设；其在 `lo` 生成的 SYN 并不保证保留原 FakeTCP 的 MSS/ISN/选项。原 FakeTCP 严格 MSS/认证守门不降低。根据 Android Emulator AOSP 的 `-net-tap <tap interface>` 指令，可测试把模拟器接入真实 TAP 以避免用户态地址转换，但该参数是否在当前 Actions 官方 emulator 中可用、host 是否有 KVM/TAP 权限、Android guest 是否仍能满足正式 Wi-Fi/Cellular/SELinux exact Network 条件都尚**未验证**。

新增独立、只在该文件本身变化时随实验分支 push（或显式 workflow_dispatch）运行的 `android-root-x86-tap-host-admission.yml`：只检查 `/dev/kvm`、`/dev/net/tun`、官方 `emulator -help-net-tap`，在一次性 Ubuntu runner 创建 UID-owned `wbdtapci0` TAP、配置隔离静态 `10.254.63.1/24` 并精确读回；退出 trap 无条件删除**唯一自己创建的** TAP。没有 Android guest 启动，不接触默认路由、iptables、DNS、其他用户网络或手机。单独的 source-locked `receipt.json` 将 guest、真实 Android PhysicalNetwork、TLS/M4 记为 NOT_RUN。若 TAP host 不支持，必须明确 ENV_BLOCKED/FAIL；不绕开正式 Root/netd 安全条件。后续只有 host preflight 真实 PASS 才考虑继续 TAP Android16/KSU Guest 实验。实验分支 PR #36 Draft、main/M0 不变，系统 DNS takeover 双冷许可仍 false。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20j 原 Linux host loopback 虽有 SYN，原 Go AF_PACKET合法初始 SYN及SYNACK均 NOT_PROVEN，独立新增 x86 Ubuntu/KVM/Emulator TAP 主机只读准入和一次性私有 TAP 接口精确回滚，避免继续误判 NAT 为 WBD TLS E2E。"}
```
