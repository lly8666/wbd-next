# A53｜Android 安全 Normal/off 复验前的默认 TLS 与 B3 DNS 冷门

## 已核验起点与边界

实验前序 SOURCE `a173939c41c183fa8df6048541037254323badba`：Android A48 旧 SOURCE `4a19f20456e74f3e7700e3a2876eda40536bb8d9` 的 API36 安全 TXT 证明原 Go SYN/SYNACK/TLS/受保护 Admission、/32、Rust M4 收到并认证回程 `auth=1227`、反向 TUN `rtun=1218`、有界 Stop；当时证书身份校验 **DISABLED**。A52/B3 新源码只有双 ABI/签名 APK/Go/Rust Host/Linux Oracle CI 资格，不能因此声称可信 TLS 或当前 Android TCP/UDP E2E PASS。

## 最小生产变更

- Android Root Activity TLS 证书链/SNI 验证默认 ON，实验性 Tunnel UDP53 默认 OFF；自签服务器须导入受信任的专属 CA，错误证书拒绝而不是静默降级。
- Java RootService 缺省严格 TLS；旧 Java argv 重载默认严格 TLS、DNS 关闭。显式 B3 DNS 只有同时开启 TLS 证书验证才可从 UI、Service、argv 进入原 Go；原 Go Android CLI 独立拒绝 `--android-tunnel-dns` 与未开启 `--tls-verify-server` 的组合。明确选择关闭验证时 DNS 仍可保持 OFF，但这只适合诊断，不能称完整安全 E2E。
- 保留同一原 Go/Rust TLS/认证/租约/AEAD/PN/重放、Normal/off M4、物理 Network/UID/owned Stop；Linux/Windows 共享 Go CLI 旧默认、main H2229 ACK 及其源代码不变。
- Host JVM 原生产 argv 用例覆盖两种旧重载默认、selected/all App、显式 DNS/CA 及未验证 TLS+DNS 拒绝；源码门覆盖 UI→Service→原 Go 三门。推送后按实际 Actions 同 SOURCE Job 结果登记，不把 Host/BUILD 宣称设备 PASS。

## 下一条唯一资格

在用户单独授权的 ARM64 真机+原 Linux 服务端上，单测试 App UID、已验证 TLS 证书、DNS OFF 验真实 TCP/UDP、A52 ACK、owned Stop，再单独进行 B3 DNS query/认证 reply/逆映射/Stop。未获授权不操作设备/服务器，不重启 KSU/TAP，不改 main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A53 将 Android Root App TLS 身份验证默认开启、实验性 B3 DNS 默认关闭，Java/Go 入口拒绝不验证TLS而启用DNS；Host 与源码门覆盖。"}
```
