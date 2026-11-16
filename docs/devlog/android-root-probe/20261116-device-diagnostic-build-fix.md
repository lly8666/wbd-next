# Android 实体 Root 诊断 APK 构建首轮 FAIL（2026-11-16）

- SOURCE `d2794f1cb4faa8a75a445506842e7a4bf16e0774`，[Android KSU Action43883692925](https://github.com/lly8666/wbd-next/actions/runs/43883692925) FAIL，证据工件14232813965；另 [Native 双ABI Action43883692972](https://github.com/lly8666/wbd-next/actions/runs/43883692972) SUCCESS，功能目录治理也 SUCCESS。
- Android target37 普通 APK Java 编译 PASS，x86_64 与 ARM64 Rust release 编译以及 `sha256sum` 原生包源锁 PASS。新设备APK构建在 `apksigner` 之后调用 `aapt2 dump xmltree` 时失败，日志 `missing required flag --file`；未启动模拟器，App→su 等均 NOT_RUN。
- 精确修复：`aapt2 dump xmltree --file AndroidManifest.xml device-diagnostic.apk`，即 CLI 版本所需参数；不修改原本 Rust 探针、特权操作范围或模拟器根策略，原失败不能改记 PASS。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Record first diagnostic APK packing CLI syntax FAIL and precise --file fixture correction; no claim of Android runtime PASS."}
```
