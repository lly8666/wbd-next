# A25｜把原 Android WLAN0 接入真实 Wi-Fi TAP，仅重跑一次预认证

**阻塞已由同源事实缩小**：[A24 Action #44282946884](https://github.com/lly8666/wbd-next/actions/runs/44282946884)，SOURCE `84aa66ee04d003da59656c41f8cc8fd1bd8fe1f8`，官方 [Artifact #14417488088](https://github.com/lly8666/wbd-next/actions/runs/44282946884/artifacts/14417488088)：`android_original_selected_interface=WLAN0`、`guest_to_host_tap_l2_during_boot=NOT_OBSERVED`、`guest_to_host_tap_l2_during_d2_session=NOT_OBSERVED`；原 Go TUN/RAW/SYN sendto PASS、未认证 RST OBSERVED，原 Linux RAW SYN RX/SYNACK TX、TLS租约/M4/Stop 仍 NOT_PROVEN。A24 所有必要构建/oracle PASS，两个冗余 SLIRP guest Jobs 按约定 SKIPPED。

**网络根因证据**：上游 [AOSP Emulator 源码](https://android.googlesource.com/platform/external/qemu/+/refs/heads/emu-32-release/android-qemu2-glue/main.cpp) 中 `-net-tap` 连接 `mynet` 普通虚拟网卡，而 `-wifi-tap` 独立连接 `virtio-wifi`；无 `-wifi-tap` 时 Wi-Fi 仍可走用户态 SLIRP。此前 TAP 宿主 RX=0 而原 Android `wlan0` 收未认证 RST，与此拓扑相符，但此前不曾证明最终身份或 TLS 错误。

**唯一 CI 修复和短测**：保留普通 App→真实 KernelSU `su`、原 Go/Rust/RootService、Android 实际 `ConnectivityManager.Network` 和 `android_setsocknetwork`+原 RAW ifindex，只把第二次实验 guest 的 `-net-tap` 更换为官方 `-wifi-tap`。先检查 Emulator 真支持该选项；在隔离且精确归属的 `wbdtapci0` 上启动单进程 dnsmasq DHCP，仅给 10.0.2.16–19/24 的短本地租约，`--port=0` 不提供 DNS 服务，DHCP Option 3/6 明确为空、不下发默认网关和 DNS，也不改 host 主路由/防火墙全局/DNS/SELinux。只有真实 Android 网络读回与原 socket 继续成立才到 original D2 双端 RAW。所有受控 DNS/DHCP 进程、TAP、443 RST 规则和 Linux TUN 都精确回收；不上传 lease/MAC/PCAP/凭据，收据仅固定状态。任一 wifi-tap/DHCP/netd 门失败按 `ENV_BLOCKED` 终止，不回退 SLIRP 伪造 PASS。

同 SOURCE 一条 TAP guest 纵切面，普通 SLIRP D1/D2-S1 SKIPPED；发布 ARM64 构建及 Linux 真 oracle 单独回归。该提交本身不包含新设备运行结果，原 SYN/SYNACK/TLS/租约/M4/Stop 仍按上一 Action 状态，不提前判 PASS。PR #36 继续 Draft，main/M0 不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A24证据确认Android原Network为WLAN0而-net-tap宿主无guest流量；针对AOSP Virtio-WiFi独立后端只在一次性CI采用-wifi-tap及真正隔离无默认路由/DNS的短DHCP，继续按原Linux RAW双端事实门验证。"}
```
