# A28b：修复 main 新增 v4routekey 包在实验分支的真实同源装配遗漏

A28 真实双父合并 `c93adca4d0688fc7936ba5161b20e64babf6a6be` 已纳入冻结主线 `46a756df1114aecda8dc2d5d259a5cbb4c9a909f` 的所有源码、归档和历史。第一次原生 [Action #44464990631](https://github.com/lly8666/wbd-next/actions/runs/44464990631) 有六个独立 Host Job SUCCESS，但原 `arm64-native` **FAIL**：`internal/v4productcli/linux.go:43:5: no required module provides package .../internal/v4routekey`。说明新合入的 main 短 RouteKey v2 本地 KDF 源文件本身存在，但 Android source-locked 脚本只向固定 `legacy` donor 装配 `v4productcli`/DNS/RootJournal，没有装配新间接包。原生 Rust 编译已完成，此处 Go 路径缺包阻塞 APK 和独立 Linux oracle，不能把 A28 称为全构建通过。

修复三个**同源**原 Go 安装入口：`android/root-native/build-source-locked.sh`、`android/root-native/ci/linux-original-oracle.sh`、`android/root-app/ci/x86-original-linux-server-prep.sh`，统一先碰撞检查，再把 `r0/go_overlay/internal/v4routekey/*.go` 原文件装入 `legacy/internal/v4routekey`，使 Android + Linux 同源码、同注册表、相同本地 short-key v2 源实现，不手写另一套KDF。正式 ARM64 APK UI 仍只能输入原64位 route-key-hex，不能因为源存在即宣称 Android 短Key UI 已接线。保留所有 RST/SYNACK/TLS/真实M4资格门和用户不运行 KSU/TAP/真机要求。

第一次合并治理 [#44464990589](https://github.com/lly8666/wbd-next/actions/runs/44464990589) 的历史 `invalid feature-impact IDs` 也保留为 **FAIL**，这是新旧两边大量 M0 归档被本轮合并增量检查所解析。旧 devlog/evidence **不改写、不删除**。本小提交只含本次包装配与相关 Android 功能卡/说明，单独重新验证治理；不能把新 Action 绿灯追溯改写历史 FAIL。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A28两分支全量合并后原Go缺main新增v4routekey包；补三条源锁编译装配链并保留真实历史治理FAIL与Android未测试边界。"}
```
