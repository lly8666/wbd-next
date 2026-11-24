# A21b：首轮全应用 CI 编译 PASS、rootjournal Host PASS、静态测试变量先后顺序修复

[SOURCE 4c7a4091 Actions #44269101861](https://github.com/lly8666/wbd-next/actions/runs/44269101861) 的 arm64-native Job SUCCESS（同源码 Android ARM64/x86_64 原 Go+Rust Bionic）；linux-x86-original-server-d2-s0 Job SUCCESS，其中新增真实 Go rootjournal/allapps_test.go Host 单测报告 ANDROID_ALL_APP_ROOTJOURNAL_EXACT_ROLLBACK_HOST_PASS，证明范围生成、系统 UID 排除、事务失败回滚、owner flock、重启与 Stop 的 host 假 ip runner 回归。ARM64 APK 与 x86 KSU 作业在同一 test-network-scope-gate.sh 静态 Python 中因变量 cold 在定义前引用而 NameError，实际还没有进入 APK/Android 模拟器测试，绝不冒充成功。

本次仅修复 Host Python 检查，先读取 linux.go 给 cold 变量再检查 --android-route-all-apps/Go source lock，保留原来所有安全断言。顺带修正 ARM64 产品 UI 的边界用语：当前全应用默认只处理 App IPv4，IPv6/系统 DNS/system_server/netd/root 等**未经过验证且未被接管**。新 SOURCE CI 成功前不宣布发布验证；真实 Android 全应用规则由于 D2 TLS/租约/M4 未打通依旧 NOT_RUN。仅实验分支 Draft PR #36，main/M0 不动，系统 DNS 双冷安全门继续 false。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A21 首轮双 Bionic 编译与 Go rootjournal 全 UID Host 事务回滚 PASS，但 APK 静态测试因 cold 变量未先赋值 FAIL；修测试读取顺序不删断言，UI 明确全应用仅 IPv4、IPv6/system DNS 仍未接管。"}
```
