# B2c3 Android Root服务器FQDN物理DNS bootstrap→原Go FakeTCP/TLS（2026-11-17）

本批起点分支 `e59551ec0023da133beae3b230548decfb9c797b`，main `0956c04ca4ba87201e2229bb701fa24bca734385`；只改 `experiment/android-temp-root-probe`，PR #36 保持Draft。已核远端已提交变更/Action与最近方案功能卡；无远端worktree，未声称检查未提交本地代码。上一批原Rust B2c2b2 [Android 10/10 Action44098023555](https://github.com/lly8666/wbd-next/actions/runs/44098023555) 及 [治理Action44099495195](https://github.com/lly8666/wbd-next/actions/runs/44099495195) 均通过。

## 本批产品实现

- 正式Android Root App服务器underlay输入可选IPv4或ASCII FQDN（预转换的punycode可用），Service二次校验并按类型启动原Go `--peer-ip` 或 Android专属 `--peer-host`；用户App/UID真实选择和SNI证书验证保持原样。没有合成探针按钮。
- 原Go在实际物理Network/ifindex/MTU/源IPv4读回后，复用已存在 `dnsnative.NewAndroidPhysicalDNSDialer` 的Android Bionic `android_setsocknetwork`、`SO_BINDTODEVICE`、同FD读回，只对服务器FQDN进行至多5秒**真实物理DNS控制面bootstrap**：原B1标准UDP53 query/ID/QNAME，TC仅原物理223.5.5.5:53同一出口TCP53重试；有界A/CNAME名字压缩解析，拒绝不可用/恶意回复和缺A；域名实际解析IPv4交给原FakeTCP SYN及合法TLS ClientHello/原认证租约。无默认系统DNS/其它上游/Tunnel fallback，无稳态逐包Go、JNI或第二TUN reader。
- 纯Go真实UDP+TCP loopback增加3项bootstrap/回答/失败Host，Java App校验与Go cold入口源锁夹具同批更新；ARM64 Bionic原Go+Rust ELF、签名Root APK和Linux原服务端协议oracle由完整同源Actions裁决。

**新的SOURCE提交之前测试NOT_RUN**；Host socket和Android ELF构建均不代表 Android16 KVM模拟器中已实际解析或TLS连上。原Rust M4普通App DNS仍 `hijack_enabled=0`，CN→物理普通DNS/Tunnel1.1.1.1、TCP53全局流/系统Resolver接管未接通。实体KSU仍需单独授权。

**唯一下一步**：普通App双DNS真实物理+隧道后端与Android Resolver owned准入，优先真实Android16 ARM64 KVM同源Linux服务器Normal/off业务；不增加独立探针或极端工况。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2c3原Root App+原Go cold增加物理Network精确绑定服务器域名DNS bootstrap后再发真实FakeTCP/TLS；新增原DNS真实UDP/TCP与Java源夹具，普通App DNS仍冷关闭。"}
```
