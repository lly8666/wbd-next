# Android16 UIAutomator 第二次进程 OOM 137 历史失败及黑盒触摸替代（2026-11-16）

Source `dcf3ceec5277ca7217536a362f2a4d535f68356d` [KSU Action43898866446](https://github.com/lly8666/wbd-next/actions/runs/43898866446) 仍 **FAIL**，但该 SOURCE 的 target37 APK、双ABI Android Rust、APNIC5500条 CN 前缀、`APP_UID_TUN_ROUNDTRIP_PASS`、`MAINSTREAM_DNS_TLS_PASS`、`SIGKILL_WATCHDOG_CLEANUP_PASS`、Tether+恢复、Root内置APK真实原生自检的 `android_split_policy=PASS`、`android_split_uid_kernel=PASS` 与独立netns `ip route get` 10/10 全部通过。UI失败仅在**新增**第二次UIAutomator时 `adb shell uiautomator dump` 五次空stdout rc137（环境中内存触发SIGKILL）且无XML；App设置输入和native回读 NOT_RUN。失败包 artifact14240682277，SHA256 `f89e6da328f8dfeed4a04fd7bd9db97cd96594117805dc72fd7907680ba07dfe`，不把 FAIL 篡改成 PASS。

同一A VD **先前的** `device-diagnostic-ui.py` 在这个SOURCE早已取得真实UIAutomator `device-diag/ui.xml`，里面含真实可点击「Android 分流/全局设置」按钮 bounds `[24,170][296,230]`。因此无需重复启动会被杀掉的UIAutomator：使用这份**同一启动周期、相同安装包**的真实快照以 `adb shell input tap` 打开设置，检查 Android resumed activity，随后 Android `SplitSettingsActivity` 通过 debug-only App 私有文件 `wbd-split-ui-bounds.json` 输出**实际View `getGlobalVisibleRect`**（label只包含package输入、add/save按钮坐标，不含输入字符或任何网络机密），CI对可见控件实际坐标执行 Android 输入动作。仍必须真实 tap 包名输入 `uid:10502`、点击「添加」、点击「保存并Root校验」，最后通过 `run-as` 读取 App真实原子保存配置及 Root 原生 JSON 验证 `uid 10502=global`、默认split、CN CIDR数量、双DNS和 `installed=false`，无假按钮、无虚构 PASS。

这是**UI测试底层的稳健性修复**，不是新权限/路由策略：App依旧不改主namespace、不接真实 WBD、无FakeIP，主网络的Apply与精确日志回滚尚不可用。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Avoid second API36 UIAutomator OOM by using already authenticated screen bounds and real Android View geometry for actual touch + rooted config persistence checks, retaining historical failure evidence."}
```
