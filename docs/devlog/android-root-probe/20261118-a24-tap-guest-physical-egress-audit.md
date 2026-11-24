# A24｜TAP guest 真实网络出口分辨：先固定 L2/Network 证据

**同源原证据**：[Action #44279861569](https://github.com/lly8666/wbd-next/actions/runs/44279861569)，SOURCE `1ab281f5a38b39f4fc6d92f4c38463aafe264962`：14 个 SUCCESS + 1 NativeBridge SKIPPED，其中 TAP guest Job SUCCESS 仅代表 guest boot、真实 Android PhysicalNetwork exact、KSU App→su、原 TUN/RAW、原 Go SYN `sendto` 及 TAP owned cleanup；**不等于原 SYN 在 TAP 出口**。官方 [TAP artifact #14417081933](https://github.com/lly8666/wbd-next/actions/runs/44279861569/artifacts/14417081933)：`original_android_unauth_rst_observed=OBSERVED`，原服务端 RAW SYN RX/SYNACK TX 均 NOT_PROVEN，host TAP 观察器 `tcp_frames_examined=0`。普通 SLIRP [artifact #14416508266](https://github.com/lly8666/wbd-next/actions/runs/44279861569/artifacts/14416508266) host lo SYN OBSERVED，但原 server RAW RX 仍 NOT_PROVEN。TLS/认证/32租约、M4 双向 App TCP/UDP、认证后 UID 路由和 owned Stop 无新证据。

**必须纠正**：Emulator [官方 `help_net_tap`](https://android.googlesource.com/platform/external/qemu/+/emu-master-qemu/android/android-emu/android/help.c) 说明 TAP 网络依赖真实 DHCP，并且 `-net-tap` 禁用 `-tcpdump`；上一轮 TAP 端仍传 `-tcpdump`、`slirp_bypassed_not_fake_network=true` 是**超范围收据表达**，不表示 Android SYN 真到 TAP。本次删除无证依据的布尔通过宣称；TAP 模式不再传 `-tcpdump`，把 guest pcap 三值写为 `NOT_RUN`。

**仅做一轮带源锁的网络事实复查**：在独立 TAP Job 的第二次真实 Android16 KSU guest 启动前读取本 Job 自己创建的 `wbdtapci0` Linux 内核 RX 计数，guest 启动后及整段 D2 运行结束、但尚未终止 guest 前分别按增量写 `OBSERVED/NOT_OBSERVED/NOT_PROVEN`，明确只能证明 L2 不是 SYN。x86 CI-only Activity 对其真正 `PhysicalNetwork.available/exact` 所选接口写固定 `WLAN0/ETH0/OTHER` 枚举、不写 handle/IP/UID、无伪 Network 或修改系统路由。仅 host TAP SYN OBSERVED + 原 Linux RAW 初始 SYN RX OBSERVED 才能将 `slirp_bypass_for_original_syn` 判 OBSERVED；guest boot 另列。原 Go/Rust、FakeTCP、TLS、证书、认证、/32、M4、Android `android_setsocknetwork`、ARM64 发布、Linux/Windows 逻辑全部不动。

这是新 SOURCE **尚未运行的代码改动**，即使新的 L2 OBSERVED 也不等同 D2a SYNACK 或 D2b/D2c 完成。若 TAP 无实际 egress 或被真实 Network 选中路径绕开，记明 `ENV_BLOCKED/NOT_PROVEN`，不得禁用 SELinux/降级TLS/假造Network。新单次 TAP push 源锁任务只执行一次原 KSU guest/D2 纵向场景；普通 SLIRP 的 D1 与 D2-S1 Job 对此标记显式 `SKIPPED`，不为相同 SOURCE 重复启动几套重型 Android guest。保持 Draft PR #36，main/M0 不改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A23真实TAP guest已启动但原SYN未达Linux RAW且Android收未认证RST；纠正TAP禁用tcpdump和未经证实的SLIRP绕过字段，加入Linux TAP内核L2计数与Android原PhysicalNetwork选中接口固定枚举，原TLS/M4不动。"}
```
