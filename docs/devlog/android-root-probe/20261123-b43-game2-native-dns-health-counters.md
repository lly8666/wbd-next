# B43｜Game2/off 原Rust UDP53 隧道DNS、Health与M4原生计数

基线 B42最后SOURCE `a444811b7dd4`：产品 [Android Dual64 #45118530684](https://github.com/lly8666/wbd-next/actions/runs/45118530684) 11 SUCCESS/4 SKIPPED，治理 [#45118614798](https://github.com/lly8666/wbd-next/actions/runs/45118614798) SUCCESS；实体Game2仍NOT_RUN。应用户继续大类功能接线，不重新做旧网络探针。

**真实产品路径一批三项：**

1. Game2/off单个原Rust TUN读线程在原GameAdapter M1 AEAD/PN之前复用Normal的 `TunnelDnsUdpFlows` 64槽UDP/53 IPv4问题→1.1.1.1映射；两个原Rust RAW M3独立AEAD/PN与GameReceiveOwner首次交付之后，通过共享同一个64槽表还原真实原App DNS回复地址及源端口，仍由同一TUN FD写入。无Go/Java逐包、无另一套DNS格式/真实DNS socket；非DNS包继续走原Game快路径，物理/CN App DNS仍不接。
2. App显式Game2时允许原`--android-tunnel-dns`并保留选择；原Service和参数校验继续拒绝未实现的物理/CN App DNS，原Go→Rust Game M4私有ABI携带DNS enable和原`--android-native-health-seconds` 15/30。Rust HealthClock保持90s dead，未加额外轮询线程、控制包或重连协议。
3. 扩展原Game2 M4 native计数至实际RAW TX、RAW RX、已TUN回写、拒绝、DNS查询改写和回复回写。原Go已存在的1s state ticker只读真实Rust counters，Root Service复用现行状态展示纯Java解析器，不假称应用层E2E；组Stop先join完整M4再清当代DNS映射/RAW/路由。
4. 同批更新原App模式/预设/argv/状态JVM测试和原B40/B41实际生产源码门。原Go标准TLS、认证/lease、GameAdapter AEAD/PN、Linux/Windows原语义均不更改。未将Game4、Game FEC、物理/CN DNS或系统netd冒充Game2支持。

**资格**：本SOURCE Go/Rust双ABI构建、签名ARM64 APK、Linux原server Oracle和Java/Rust Host以自动Actions核实；实机双lane TLS、/32租约、真实应用TCP/UDP、DNS查询回包、owned Stop、CPU/吞吐仍NOT_RUN/NOT_PROVEN。历史B42与本SOURCE资格分开。PR #36仍Draft，main/M0单写者原样保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B43复用原Normal Rust UDP53映射至Game2单TUN双RAW M3，原Go Health15/30及真实M4/DNS计数至App；不造新协议/数据面或安全框架。"}
```

## 同源软件验收收口（不代替实体资格）

B43 产品 SOURCE `06937fa54efae83944dc4e68838244cf79783d3b` [Android Dual64 #45122281141](https://github.com/lly8666/wbd-next/actions/runs/45122281141) **completed/success，11 SUCCESS / 4 SKIPPED**：真实Android ARM64+x86_64原Go/Rust编译、签名arm64-v8a APK及原App/Java Source Gate、Linux原server Oracle/D2-S0与Rust DNS/M3等Host门独立SUCCESS；KSU原生/NativeBridge/D2-S1/TAP guest四个Android诊断Job SKIPPED。B43 [Feature catalog #45122281209](https://github.com/lly8666/wbd-next/actions/runs/45122281209) **Feature catalog SUCCESS / Governance SKIPPED**。这些是HOST/BUILD资格；真实Android Game2双lane TLS、DNS回包、应用TCP/UDP、UID/Stop及性能一律NOT_RUN，不将内核计数当业务完整PASS。
