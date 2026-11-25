# B110｜Game 真实远端业务、原隧道 DNS、正式 RootService 自动重连

B109 SOURCE `18a687c75a038856c86232d6992bd9dd4ce0bbe3` [Action 45557921405](https://github.com/lly8666/wbd-next/actions/runs/45557921405) 14 SUCCESS / 5 FAIL / 8 SKIP。CI veth/tc/ADB carrier 已使真实独立Android↔原Linux三模式完成原证书TLS/lease/M4及实际普通App TCP/UDP 8+8、1MiB/方向逐字节校验、原Stop和内核读回：[Normal 139016385896](https://github.com/lly8666/wbd-next/actions/runs/45557921405/job/139016385896)、[Fixed 139016385905](https://github.com/lly8666/wbd-next/actions/runs/45557921405/job/139016385905)、[Auto 139016385972](https://github.com/lly8666/wbd-next/actions/runs/45557921405/job/139016385972)。不是进程内 TLS，非物理carrier资格。四Game均有客户端实际lease/M4+UID READY、服务端真实group READY及2/4各protected lane commit（共12/12）；但脚本错误要求Normal独有V4_PUBLIC_ACTUAL_PEER_SYNACK_MSS_V1的Java枚举，导致真实普通App业务未执行、独立SYNACK证据未完成；不倒推整场PASS。独立Linux普通kernel TCP carrier仍connect timeout、host tx0/rx7，历史FAIL保留；它不是产品使用场景且Android实际原RAW载体已证明，B110不再重跑该额外任务。

B110 同源6个独立guest并行：
- Game2、Game2 Fixed、Game4、Game4 Fixed：CI relay分别记录原真实SYN/SYNACK每方向distinct source port数量（只记录计数，不改IP字节、不生成回复）；四处原wire证据、客户端专属原Game READY（真实TLS 2/4 lanes + 原Rust M4/UID）、原server所有committed lanes、实际普通App TCP/UDP和1MiB双向、原Game group joined Stop与kernel cleanup。保留Normal旧SYNACK明确门，不删除任何协议或业务校验。
- Normal tunnel DNS：原RootService显式配置隧道DNS upstream=10.66.0.1，独立原server TUN上本地DNS fixture，普通App原UDP/TCP 53发向测试IP，要求准确A回答、server TUN socket真实query，两方向业务与Stop。
- Normal 自动重连：使用正式RootService既有 background_network_recovery=true。真实业务后关闭guest Wi-Fi（独立guest关闭蜂窝以确保回到同一Wi-Fi），必须由生产callback自行Stop且旧原owner确认，恢复Wi-Fi后不发CI START，要求第二个原process/lease/READY、新真实Network Handle及第二次完整TCP/UDP业务，最后原Stop及kernel cleanup。若载体因接口/地址变化失效，独立FAIL，不能用显式重连代替。

无生产代码/正式APK transport/main/协议/MTU/防御性改动。main 最新核验 a93245698d46 由其他工作线推进；PR36仍Draft，治理两workflow历史失败。新SOURCE待CI，不预判Game、DNS或自动恢复PASS。FEC实际丢包恢复与实际Game FEC readback、真实热点/IPv6 Android接管、ARM64真机和性能仍需独立证据。CI ADB carrier不能用作物理吞吐/延迟证明。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Accept three genuine Android independent-peer business passes; correct Game-specific wire receipts and verify tunnel DNS and production Wi-Fi automatic reconnect."}
```
