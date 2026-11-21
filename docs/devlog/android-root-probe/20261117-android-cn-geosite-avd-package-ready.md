# Android16 AVD PackageManager 服务未就绪假失败（2026-11-17）

- SOURCE `ff1b01d38444383e5880e7153a09a898125f8139` [KSU Action43946662076](https://github.com/lly8666/wbd-next/actions/runs/43946662076) overall FAIL，但双 ABI Rust、固定 APNIC 与 8,503 条CN完整geosite、target37自包含APK签名全部PASS。Android16 KSU AVD第一次冷启动虽然返回 `sys.boot_completed=1`，第一次 `adb install out/apk/app-su.apk` 报 `cmd: Can't find service: package`，所有Root/新增UI/DNS测试均 **NOT_RUN**，该历史FAIL不可改写为策略失败。
- 精确基础设施修复：在 `start_avd(first|second)` 的 `sys.boot_completed` 之后增加 bounded（最多95s） `adb shell pm path android` PackageManager Binder 注册检查，输出每phase独立 `out/ksu/package-ready-*.txt`。必须真实看到 `package:` 才继续安装；超时明确 `ENV_BLOCKED` 附 emulator log/service check，不进入Root结果统计。只改变KSU模拟器启动验收门，不动正式Android、Root/网络路由/域名匹配。原CLI App输入焦点验证仍按前述提交执行。

```feature-impact
{"kind":"none","ids":[],"reason":"Bounded PackageManager readiness after AVD boot_completed to avoid bogus pre-test install failure, maintaining true source-locked KSU and UI/DNS acceptance."}
```
