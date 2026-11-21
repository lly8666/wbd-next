# A20k：x86 TAP 主机准入首次 KVM 权限失败与复核（2026-11-18）

[Commit bf651660 TAP host Action #44263906843](https://github.com/lly8666/wbd-next/actions/runs/44263906843)：新的**独立**实验任务 FAIL；官方 Artifact #14410010676 的 source-locked receipt 明确 `exit_code=11`，`phase=ENV_BLOCKED_KVM`，`emulator_net_tap_help_advertised/kernel_tap_interface_create_readback/isolated_host_tap_ipv4_readback=NOT_PROVEN`。其失败发生在**普通 runner 用户未获 /dev/kvm 读写权限**的预检中，不等于 TAP 或模拟器本身不支持。同源正式 D0-D2-S1 原生 Actions 仍有此前独立成功证据（SOURCE 6c6cfa2d Action #44262097315）。

本次只让该宿主实验脚本**复用历史 KSU3.3.1 正式 CI 的既定 KVM admission 方式**：先检查 `/dev/kvm` 为字符设备，再用一次性 GitHub runner 的 `sudo -n chmod a+rw /dev/kvm`，随后精确 `test -r/-w`，失败继续独立 ENV_BLOCKED 不伪造。正式 Android App、原 Go/Rust 协议、PhysicalNetwork、Root UID、DN​S、安全许可、ARM64 APK 和系统服务全未改。TAP 主机其他门只有下一次独立 Actions 真实通过才记 PASS；更不意味着 Android TAP guest/TLS/M4/Stop 已执行。实验分支 PR #36 Draft，main/M0 不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20k 独立 x86 TAP host 首次在 /dev/kvm 用户权限预检处 ENV_BLOCKED，并非 TAP 不支持；复用同分支已 PASS 的 Android16 KSU Runner sudo chmod KVM 准入，再真检 TAP 参数/内核接口，不改任何产品行为。"}
```
