# B2b：固定CN8503规则与MIT许可进入正式签名APK → 原Go Root冷核验（2026-11-17）

**开发分支** `experiment/android-temp-root-probe`，基线HEAD `e2d408c7f227064d186675bd1cd7c6c0fec01819`。Draft PR #36、main/M0不动、实体KSU不动、无额外云资源。本批只把上一批B2a真实8503规则送进**原产品签名APK和原Go Bionic冷控制**，不伪造Android DNS E2E。

## B2b源码工作

- `.github/workflows/android-root-product-a1.yml` 正式`root-arm64-app`需同时依赖`arm64-native`和`b2-authentic-cn-geosite-host`两Job均SUCCESS，按同一次`GITHUB_RUN_ID/GITHUB_SHA`精确下载B2产物，拒绝缺失、过时SHA或其他版本/假规则替换，保证最终APK/原Go Native/上游Geosite同SOURCE。
- `android/root-app/ci/build-source-locked.sh`先验B2 receipt的`source`与SHA、v2fly固定commit`41504eae2a11f305fe88cfc605cf6c105a80bf5a`、TXT完整SHA`45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6`、8503条、8431 domain/69 full/3 regexp、MIT许可证存在；把真实`wbd-cn-geosite.txt`、`wbd-cn-geosite-license.txt`、`cn-geosite-provenance.json`放进签名APK的`assets/native-arm64/`，签完重开APK Zip逐项验证原始字节且无VpnService；不得默默回退为小样例规则。
- `NativePayload.stage`在Android启动冷路径再次验来源SHA、许可证、规则数量、完整TXT SHA，并把TXT以0600复制/同步到App私有`wbd-arm64-verified`目录。Root Service把该私有文件路径作为独立参数`--android-cn-geosite-file`送入**原Go**，不在Java承接任何DNS/业务包。
- 原Go `linux.go`共享命令行新增**Android-only、client-only**参数。真正原Root Go在任何TLS/auth/路由之前，通过`dnsnative.ReadPinnedCNFile`对同一fd执行`O_NOFOLLOW|O_NONBLOCK`打开、检查普通文件+0600、长度上限、完整SHA、8,503条类型语义；失败立即拒绝启动。成功仅记`V4_PUBLIC_ANDROID_CN8503_COLD_FILE_VERIFIED count=8503 sha256=... dns_capture=NOT_CONNECTED`，没有创建DNS socket，不能把这个收据叫系统DNS PASS。
- B2独立Actions Host Go测试加入完整源规则的0600安全文件加载、0644拒绝、symlink拒绝、篡改SHA拒绝、目录拒绝；App Host CI核对Service/NativePayload/Go flag调用链。Root签名APK与原M3/Go Rust ARM64/Linux原server oracle同SOURCE回归。

## 禁止扩大结论

本SOURCE尚待Actions，不能从实现就宣称APP打包或Root cold P3 PASS。Host Go是真规则加载逻辑，Android原生Go ELF与APK是**交叉编译/签名/静态运行链路**；实际 Android16 ARM64 APK打开私有文件权限、Root `su`、netd系统DNS、WBD TUN UDP/TCP53、物理Network的DNS socket出站和真实CN业务仍NOT_RUN/NOT_CONNECTED。ARM64托管runner缺可访问KVM，P2/P3仍ENV_BLOCKED，P5实体最终另授权。不动原Linux/Windows协议或Route journal。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2b固定真8503 TXT+MIT/来源锁从同SOURCE B2 Actions打进签名APK，由Android App 0600私有暂存并交原Go Android-only Root冷校验；数据包DNS及KSU运行仍未接。"}
```
