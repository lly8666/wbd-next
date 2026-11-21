# A20l：TAP host runner 缺 Android emulator 包而非 TAP 不可用（2026-11-18）

[修正 SOURCE `8c3535d9` 的独立 Actions #44264420412](https://github.com/lly8666/wbd-next/actions/runs/44264420412)：官方工件 14409761429 标记 `exit_code=15 / phase=ENV_BLOCKED_EMULATOR_BINARY`；本轮已按成功的 KSU job 的 `sudo chmod a+rw /dev/kvm` 方法跨过上一次 KVM 权限早退，但全新 `ubuntu-24.04` 托管 runner 上**只有 Android cmdline tools、尚未装 emulator 二进制**。因此此前两个失败都未执行 `-net-tap` 和真实 TAP 接口准入，不得把它们解读成平台 TAP 功能不支持。

为让小型独立 host-only Job 真正达到关键测试，若 `$ANDROID_HOME/emulator/emulator` 缺失，直接使用与已成功 Android16 KSU 准入一致的 `cmdline-tools/latest/bin/sdkmanager emulator` 安装且检查可执行，不安装 Android Guest/system image、不引入 Root、用户 APK、Linux 原协议或绕过 PhysicalNetwork，命令输出保留在 runner 私有临时文件，收据只报告固定 enum。安装后才执行官方 `-help-net-tap`、隔离 `wbdtapci0` 创建及回滚。新 SOURCE 尚待 Actions 真验；实体 x86 TAP Guest/正式 Android Root/TLS/M4/Stop 依然 NOT_RUN。仅实验分支 PR #36，DNS 双冷许可 false，main/M0 不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20l TAP host 第2轮已跨 KVM 权限，但独立 Ubuntu runner 还未安装 Android emulator，按原 KSU CI SDK 管理工具仅安装 emulator 后才检查官方 TAP flag/内核接口；不修改产品/ARM64或宣称 TLS。"}
```
