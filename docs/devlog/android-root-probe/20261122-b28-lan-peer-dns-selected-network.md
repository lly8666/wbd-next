# B28｜Android未验证公网的局域网服务器域名由已选Network冷解析

基线 `9d449f8f7bb0f446adde8f02b925d41c9e1b927c`：B27源码/功能卡/Host/签名APK软件门已成功，Android实体LAN和应用流量尚未跑。B27 修正了物理Wi-Fi/Ethernet没 `NET_CAPABILITY_INTERNET` 就无法选/Service注册的问题，但原 Android `--peer-host` 入口仍只由原 Go向选定物理网络上的固定公网DNS `223.5.5.5` 做引导；无公网但局域网DHCP DNS知道 `wbd.home.arpa` 时仍可能启动失败。此片补最小**冷控制**，不动WBD应用数据面。

- 复用原 `PhysicalNetwork` current OS handle/ifindex/MTU/IPv4，额外记录Android是否 `NET_CAPABILITY_VALIDATED` 供用户标识（不改变 `same` 或owned Stop）。无公网上网验证且用户的服务器为合法hostname时，原 `RootClientService.runRoot` 已有后台执行线程在Root启动前用 **选中的** Android `Network.getAllByName(peer)` 解析局域网 A/AAAA；生产纯Java `PhysicalPeerIPv4Choice` 从结果中找可用IPv4。非独立系统DNS代理、未触碰新TUN/RAW读线程或原 Go/AEAD/PN；直接IPv4或Android已验证Internet的网络仍沿旧Go入口。
- 如果获得本地IPv4，再验证同一Network/内核链路完整且仍有效，传给原 `OriginalGoCommandArgs` 作为 `--peer-ip`，SNI/RouteKey保持用户配置不变。若本地无A记录/Android选网DNS超时或失败，**不改变旧公共物理DNS行为**：保持主线原Go `--peer-host`/223.5.5.5引导作后路。PhysicalNetwork丢失直接失败，不误用其他默认接口。错误文字不输出服务器IP、域名、密钥。
- 真实 `PhysicalPeerIPv4ChoiceTest` 使用纯Java构造的离线IPv6/IPv4结果，覆盖AAAA在前、LAN 192.168优先、loopback/IPv6单独无效；App Host源锁检查 `Network.getAllByName`、handle匹配、Service在同线程把解析IPv4给原Go、不加线程也不改 TLS/内核路由。冻结SOURCE后双ABI、签名APK、Linux服务端Oracle与feature card以其Actions为准。
- Android普通 App 的getaddrinfo仍由系统netd/DnsResolver集中处理，本片 **不能称netd DNS捕获PASS**；应用IPv4 TCP/UDP真实E2E、LAN服务器身份验证/性能仍NOT_RUN。参考Android官方 `Network.getAllByName` API文档（只在指定Network解析）：https://developer.android.com/reference/android/net/Network#getAllByName(java.lang.String)。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B28 cold selected-network Android LAN peer IPv4 lookup on unvalidated link with unchanged original-Go physical DNS fallback and authentic TLS/M3 hotpath"}
```
