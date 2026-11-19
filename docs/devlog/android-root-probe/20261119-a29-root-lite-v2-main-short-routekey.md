# A29 · WBD Android Root Lite v2 源锁测试 APK（main H2208 offline short RouteKey）

源点：实验 \`6de1d62aecd31c1c78f23577819cc9549754fe00\` 已双父同步 main \`46a756df1114aecda8dc2d5d259a5cbb4c9a909f\`；历史 Action #44466332473 是 11 SUCCESS/4 SKIPPED，仅Host原Go/Rust/签名APK，不是实体Android WBD连接PASS。

用户请求“根据同步来的这些新功能，做一版新的android简版测试版”。此包**只把真正适用于 Android 冷入口的 main H2208 8..32 ASCII RouteKey v2** 接入原 ARM64 Root 客户端，保留64hex兼容：生产 Java \`RootRouteKeyV2\` 使用 main Go \`v4routekey/short.go\` 完全相同的PBKDF2-HMAC-SHA256 4096与域盐、3 个主线 golden vectors、cache check HMAC domain；\`RootRouteKeyCache\` 在 noBackupFilesDir 使用 0600 AtomicFile 保存派生32B key+HMAC、缓存验证复用/坏缓存 fail-closed/合法换Key再派生。没有明文短口令存储、在线密钥协商或 TLS 前私有字段。Activity 仍只把32B hex写入原 \`wbd-route.secret\`，原Go \`--route-key-hex-file\`、标准TLS证书/账号、原Rust M4/MTU/安全路由/ownedStop完全不改。短 Key 并非密码强度256位；建议随机24..32位。服务器必须已经手工配置 v2/派生hex，未经用户授权不碰服务器。

Lite UI 主页面按实体Network/服务器SNI/用户/短Key或64hex/START-STOP/脱敏TXT组织，高级自检默认折叠。既有“默认全部普通App IPv4”政策仍保留（建议首次手动取消，选单个App），保护服务器/32 private FIB THROW和Root self/manager排除。未开放 Linux服务端 Decoy、Linux padding、Fixed/Auto/Game、系统DNS/IPv6、VpnService、新UID协议。APK同包名并由CI随机调试证书签名：旧版应完成原生Stop及检查无残留UID route再自行卸载安装，不能in-place替换。用户真实手机与原Linux服务器均未测试，不运行 KSU/TAP emulator。

本次自动门：纯Host JVM用真实生产 Java 类与main Go三个黄金向量及错误缓存/换Key/非法字符测试；Production RootService Go argv/文件安全合同；真实签名 APK DEX 主线 KDF/缓存 class，Bionic ARM64 原 Go+Rust 及原 Linux oracle 同SOURCE，源锁APK SHA & UI；历史 FAIL/NOT_RUN保留，产品实机 SYNACK/TLS/auth/lease/M4/应用 TCP UDP/Stop 不凭静态 PASS 宣称成功。

\`\`\`feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"用户指定新的 Android Root Lite v2 签名测试 APK；将同步main的离线短RouteKey v2和安全缓存接上真实Go hex-file，Host/JVM验证且不扩展未授权Android功能与网络测试。"}
\`\`\`
