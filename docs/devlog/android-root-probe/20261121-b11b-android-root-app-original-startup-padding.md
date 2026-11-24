# B11b｜Android Root App 原 startup-padding 三模式至 Native M4

B11a 原生 SOURCE `7d40a607df829e234980a02c079824e50859ee1c` 的 [Action #44919634690](https://github.com/lly8666/wbd-next/actions/runs/44919634690) 保留实际状态 **9 SUCCESS、1 FAIL、5 SKIPPED**：ARM64/x86原生编译、Host/源码门、签名APK构建成功；失败是 `test-apk-native-wiring.py` 旧断言要求 Android startup-padding 为unsupported。本次B11b精确修正为真实Go冷协商、Android Bridge与Rust M4代码验证，且要求 ARM64/x86 Rust ELF 实际导出 `normal_startup_padding_set/counters`。旧失败不改写；本次以自己的完整CI验收。

继 B11a Rust Bionic/原Go M4 真实接线 SOURCE `7d40a607df829e234980a02c079824e50859ee1c`。App原来没有 `startup-padding` 入口；现在严格从已有原协议三项 off（默认）、tls、flows 中选，作为冷配置传递至原 Go。

生产传递：Activity Spinner→START Intent `startup_padding`→Root Service原同代参数→真实`OriginalGoCommandArgs.build(...,paddingMode)`→Go `--startup-padding`→原TLS受保护Admission/ColdSnapshot→B11a Rust唯一M4 M1 slab/AEAD LINK padding。旧Intent缺值和旧Java overload均off；拒绝非白名单，且原 Fixed/Auto/Game仍不可选。

Host JVM在原生产参数生成器测三项与无效字符串/null；CI源码检查包括真正Rust B11a数据面入口、原Go受保护模式与App/Service argv的一整条接线。签名ARM64 APK、双ABI、原Linux Oracle依赖同一SOURCE；实际手机FakeTCP/M4/APP吞吐和填充bytes仍NOT_RUN/NOT_PROVEN，不用软件PASS冒充手机通过。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B11b把原Android App的off/tls/flows启动padding选项经同代Root Service/原Go受保护TLS冷模式连至B11a Rust唯一M4 TX；默认off向后兼容，设备性能待验。"}
```
