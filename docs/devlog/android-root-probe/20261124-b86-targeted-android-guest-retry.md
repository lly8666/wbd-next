# B86｜集中测试定向续跑，不重复已通过的场景

B85 SOURCE `3cd25ceba4fff1a2f322534c4a828b97f9d1e8d6` [Action 45376451064](https://github.com/lly8666/wbd-next/actions/runs/45376451064)：25 SUCCESS / 3 FAILURE / 3 SKIPPED，全部结束。9个原生/Host/原Linux jobs、API35/36 stock真实正式APK UI+独立普通UID TCP/UDP（不经WBD）、14个双架构七模式原Linux场景 SUCCESS。ARM64正式APK已签名并上传（[artifact 14911876866](https://github.com/lly8666/wbd-next/actions/runs/45376451064/artifacts/14911876866)）；root-arm64-app 在旧UI文案源码断言FAIL。两个KSU job均在CI-only Java Activity调用已移除的 InstalledAppCatalog.launchable 编译FAIL，未启动guest。治理/维护成功；独立旧NativeBridge/Cuttlefish/TAP SKIPPED。

B86仅改CI测试：使用真实生产 discoverable 接口；旧UI文案断言改为实际 ServerAddress.valid 调用；[android-cold-suite] [android-guest-retry] 触发同一新SOURCE标准构建及两项未完成的KSU并行（ART/Root/原x86及ARM64转译MTU/Go c-shared；D2仅真实preauth），不重开已通过的14场景和stock guest，不重跑TAP/SLIRP握手/旧ELF139，不改任何正式产品Java/Go/Rust代码、不增安全门。历史B85通过只属于B85，B86新结果待本SOURCE；ARM64真机完整业务及性能未验。A48历史真机Normal/off原SYN/SYNACK/TLS/认证/租约/M4双向/owned Stop已观察，不回退到早期SYN阻塞。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record actual B85 parallel results; fix obsolete CI-only catalog method and UI text assertion, then retry only unfinished KSU cold/preauth scenarios with original production binaries."}
```

## B86a｜实际 CI 入场修正

B86 `960b181a7b114aeb537c69da3138e5bd30102630` [产品 Action 45381072996](https://github.com/lly8666/wbd-next/actions/runs/45381072996) workflow 表达式多余右括号，未启动任何产品 Job；[功能目录 45381076198](https://github.com/lly8666/wbd-next/actions/runs/45381076198) 卡片超过既有 16KiB 上限。仅修表达式括号和恢复紧凑JSON/缩短已在B80 devlog完整记录的历史说明，不改变任何产品或测试判据，保留前次FAIL。
