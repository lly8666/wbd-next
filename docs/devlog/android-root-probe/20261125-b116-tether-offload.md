# B116｜真机共享两种独立 offload：可归还硬件设置与 BPF 准入

B115 SOURCE `18c618aa49e82ecf5c70913e675b1e9903ef7224` [Action 45583719117](https://github.com/lly8666/wbd-next/actions/runs/45583719117) 14 SUCCESS / 0 FAIL / 7 SKIP；ARM64签名APK、API35/36真实UI参数及十槽、Normal实际远端回归均通过。用户B115/API36脱敏报告先 HARDWARE_OFFLOAD，手工关闭后 BPF_OFFLOAD，均在原RAW/TUN前失败；不再误归因服务器、TLS或FEC。旧BPF_OFFLOAD枚举同时覆盖真实启用和dump无法确认，尚不能从报告断言具体BPF运行状态。

用户授权研究并自动关闭/断开恢复共享硬件加速。AOSP OffloadController.start读取 Settings.Global.tether_offload_disabled，但已started会提前返回；dump在设置为disabled时可隐藏真实HAL状态，因此写入1不等于实时HAL停止。BpfCoordinator.mIsBpfEnabled构造时读取独立配置，AOSP文档指出默认启用、OEM RRO可改变。参考 https://source.android.com/docs/core/ota/modular-system/tethering 和 AOSP OffloadController/BpfCoordinator。不能假设硬件开关同时关闭BPF，也不直接重启系统服务、改BPF maps/程序、SELinux、netd、全局DeviceConfig或用户其他网络。

B116仅明确选中共享且实际下游、forwarding、BPF=false、HAL明确未启动时，原Root Go将原硬件偏好0或缺省null写入fsync+0600独占journal，临时settings put 1并读回；原值1时不改。正常Stop/冷启动失败在TUN/RAW/owned route等清理后恢复原0或删除键（原null），不覆盖已改为其他值的设置；转发journal未清理保留恢复记录，用户原“恢复网络”入口精确清理后归还。进程异常退出需该Restore；无实时HAL停止/恢复运行承诺，已启动或状态不明的HAL不自动关闭，避免只改设置便宣称停止。BPF_ENABLED/BPF_UNKNOWN分别固定收据，BPF未获准不修改硬件设置，不静默放行。该设备热点功能仍未通过，不能称已修复。

Host实际生产设置owner逻辑用可控Runner验证0/null/1归还、运行中HAL拒绝、未清理时保留journal及显式恢复、BPF与硬件配置独立；Java固定收据分类和原Normal真实远端回归、ARM64签名构建。真实手机Settings/HAL/tether业务未验证。main未改，PR36 Draft，历史治理失败保留。新SOURCE待CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Separate hardware tether offload preference ownership/restore from independent BPF eligibility; preserve user original setting and accurately report unresolved device compatibility."}
```
