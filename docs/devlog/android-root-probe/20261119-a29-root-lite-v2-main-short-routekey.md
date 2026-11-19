# A29 · WBD Android Root Lite v2 源锁测试 APK（main H2208 offline short RouteKey）

源点：实验 `6de1d62aecd31c1c78f23577819cc9549754fe00` 已双父同步 main `46a756df1114aecda8dc2d5d259a5cbb4c9a909f`；历史 Action #44466332473 是 11 SUCCESS/4 SKIPPED，仅Host原Go/Rust/签名APK，不是实体Android WBD连接PASS。

用户请求“根据同步来的这些新功能，做一版新的android简版测试版”。此包**只把真正适用于 Android 冷入口的 main H2208 8..32 ASCII RouteKey v2** 接入原 ARM64 Root 客户端，保留64hex兼容：生产 Java `RootRouteKeyV2` 使用 main Go `v4routekey/short.go` 完全相同的PBKDF2-HMAC-SHA256 4096与域盐、3 个主线 golden vectors、cache check HMAC domain；`RootRouteKeyCache` 在 noBackupFilesDir 使用 0600 AtomicFile 保存派生32B key+HMAC、缓存验证复用/坏缓存 fail-closed/合法换Key再派生。没有明文短口令存储、在线密钥协商或 TLS 前私有字段。Activity 仍只把32B hex写入原 `wbd-route.secret`，原Go `--route-key-hex-file`、标准TLS证书/账号、原Rust M4/MTU/安全路由/ownedStop完全不改。短 Key 并非密码强度256位；建议随机24..32位。服务器必须已经手工配置 v2/派生hex，未经用户授权不碰服务器。

Lite UI 主页面按实体Network/服务器SNI/用户/短Key或64hex/START-STOP/脱敏TXT组织，高级自检默认折叠。既有“默认全部普通App IPv4”政策仍保留（建议首次手动取消，选单个App），保护服务器/32 private FIB THROW和Root self/manager排除。未开放 Linux服务端 Decoy、Linux padding、Fixed/Auto/Game、系统DNS/IPv6、VpnService、新UID协议。APK同包名并由CI随机调试证书签名：旧版应完成原生Stop及检查无残留UID route再自行卸载安装，不能in-place替换。用户真实手机与原Linux服务器均未测试，不运行 KSU/TAP emulator。

本次自动门：纯Host JVM用真实生产 Java 类与main Go三个黄金向量及错误缓存/换Key/非法字符测试；Production RootService Go argv/文件安全合同；真实签名 APK DEX 主线 KDF/缓存 class，Bionic ARM64 原 Go+Rust 及原 Linux oracle 同SOURCE，源锁APK SHA & UI；历史 FAIL/NOT_RUN保留，产品实机 SYNACK/TLS/auth/lease/M4/应用 TCP UDP/Stop 不凭静态 PASS 宣称成功。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户指定新的 Android Root Lite v2 签名测试 APK；将同步main的离线短RouteKey v2和安全缓存接上真实Go hex-file，Host/JVM验证且不扩展未授权Android功能与网络测试。"}
```

## A29 完整新 SOURCE 的最终收据（2026-11-19）

- 真正包含 Lite v2 Java KDF/缓存、原 Go/Rust ARM64、原 Linux server 的 SOURCE：`6bcdbc6c7c27b71a8ea47c25f8385cd177daa985`。
- [Actions #44469615589](https://github.com/lly8666/wbd-next/actions/runs/44469615589) **completed SUCCESS：11 SUCCESS + 4 SKIPPED**。arm64-native、root-arm64-app、linux-x86-original-server-d2-s0、linux-original-server-normal-off、arm64-cuttlefish-host-admission 与六项 Host M3/DNS Job 都成功；Android x86/KSU、NativeBridge、D2-S1、TAP guest 均 SKIPPED（手工 opt-in 未授权）。
- 原 Root APK 生产 Java 实现的 PBKDF2 v2 三个主线原 Go 黄金向量/非法输入/错Key/损坏缓存/64hex兼容 **`ANDROID_ROOT_LITE_V2_SHORT_ROUTEKEY_MAIN_GO_VECTORS_HOST_PASS`**；原 Go 参数合同 `ANDROID_ORIGINAL_APK_GO_CLI_ARGV_HOST_CONTRACT_PASS`、正式 `ANDROID_ROOT_ARM64_APP_AND_NATIVE_ASSETS_SOURCE_LOCKED_BUILD_PASS`、签名资产 Go/Rust DEX `ANDROID_SIGNED_ARM64_APK_ORIGINAL_GO_RUST_WIRING_HOST_PASS`。
- [同 SOURCE GitHub APK 工件 #14503003885](https://github.com/lly8666/wbd-next/actions/runs/44469615589/artifacts/14503003885) 含 `wbd-root-lite-arm64-debug.apk` 与完全相同的原 `wbd-root-arm64-debug.apk`。仅临时 debug 证书，原包名不改；旧版本 Stop 后需卸载再安装。
- 不能凭 Host 算法验证或 ARM64 APK 生成推断实体 Android original FakeTCP SYNACK、TLS/认证/32租约、Rust M4 应用 TCP/UDP、UID kernel 内核 egress 或 exact Stop 已通过，以上继续 `NOT_RUN`。
- [本 SOURCE 首次治理 #44469615699](https://github.com/lly8666/wbd-next/actions/runs/44469615699) **FAIL**：devlog Markdown 代码围栏被多余转义导致找不到 `feature-impact`。本次只修正本历史笔记围栏并更新同 SOURCE 真实验证行；不改既有旧收据，后续治理只评价其新 SHA，不重跑原生产品。
