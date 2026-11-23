# B44｜Game2/off三种App UDP53正式 Root App→Go→Rust M4 接线

基线：B43 原产品SOURCE `06937fa54efae83944dc4e68838244cf79783d3b` [Android Dual64 #45122281141](https://github.com/lly8666/wbd-next/actions/runs/45122281141) **11 SUCCESS / 4 SKIPPED**，[治理 #45122281209](https://github.com/lly8666/wbd-next/actions/runs/45122281209) SUCCESS。Game2实体TLS/双向业务/性能无证据，保持NOT_RUN。

本批继续同一纵向生产链，不造另一套Game、DNS服务或普通Go逐包：

1. 正式Android Root App的Game2/off不再禁止Normal已经支持的**物理UDP53、CN8503 DNS分流**；原隧道UDP53、物理UDP53、CN互斥设置/保存/原UID路由仍复用既有Android App→Service→Go参数，Game4和Game FEC仍关闭。
2. 原Go确实只在认证/租约合法的Game2两条标准TLS lane同一个 `GameAdapter` 开始时，向原Rust M4传递物理DNS启用、原Network绑定UDP53上游IPv4和先前从已验证CN8503文件读取的原始 `PinnedWire`。Rust 冷端调用原 `CNDnsMatcher::from_go_cold`，不回调Go匹配QNAME/裸协议。
3. Game2现有唯一Rust TUN TX线程复用Normal `DnsRoute::choose`，隧道模式在原GameAdapter M1 AEAD/PN前使用B43 `TunnelDnsUdpFlows`；物理模式借原 `AndroidBoundPhysicalDnsUdp` 精确绑定所选物理Network、原 Go IP/MTU/ifindex，上游原53端口，单一 `PhysicalDnsUdpFlows` 64槽请求/回复。物理回包只由该真实连接UDP socket并经原问题/QNAME/ID匹配后用**同一个** Rust TUN owner本地回写，不冒充M3认证流；CN规则命中物理，非CN继续真M3/TUN；TCP53走原隧道、不造第二套TCP53 DNS代理。
4. 同一Rust eventfd `wait_tun_and_physical_dns` 观察两个真实FD，原来三线程结构、RAW两lane独立M3不改变。组Stop join后物理Socket/当代DNS表/TUN一起准确撤销。原每秒 Go ticker 只读Rust M4物理查询/应答/错误计数，Root App原解析器兼容B43旧六计数并读B44九计数。
5. 增原Java参数/预设/状态Host测试，扩B39–B43实际源码门验证整个Go↔Rust物理/CN接线；原Linux server/Windows代码、原TLS、identity、M1/M3、PN/replay不改；不加安全加固或极端网络探针。

**资格边界**：本B44新SOURCE交同一个Android Dual64编译原Go/Rust双ABI、签名ARM64 APK、Linux原服务端Oracle、现有Host门，不重复手工dispatch；真实Game2选定App物理/CN DNS、双lane TLS/租约、TCP/UDP/Stop与性能仍NOT_RUN/NOT_PROVEN。若CI失败须保留该失败，修具体源代码，不宣称通过。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B44在原Game2单TUN双RAW M4中复用Normal原Network物理DNS socket、CN8503和三DNS App入口/原Go ABI/计数，不新增逐包Go数据面或安全框架。"}
```
