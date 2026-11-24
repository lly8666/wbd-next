# B27｜Android无互联网标记的局域网真实物理出口接线

基线 `c48d59235cc2801f7779883e3213f0b159304a03`（B26 Host/双ABI签名APK/Linux Oracle 11 SUCCESS+4 SKIPPED）。当前实体Root App仅允许 `NetworkCapabilities.NET_CAPABILITY_INTERNET` 的Wi-Fi/蜂窝/Ethernet；Service的 `NetworkRequest.Builder` 也强制INTERNET。用户若在离线LAN／热点／有线网络中直接连接同网段 WBD 服务器，真实Android LinkProperties IPv4、内核ifindex和接口MTU全有效，但会在选网或网络回调被拒。这不是权限安全工况，而是日常本地服务器使用能力被错误的“公网标记”挡住。

- 统一生产 `PhysicalNetwork.physicalUnderlay` + 纯Java `PhysicalUnderlayPolicy.accepts`：只认真实Wi-Fi、Cellular、Ethernet，明确排除VPN；**Internet/VALIDATED标记不再是路由资格**。其它原生 Network.getNetworkHandle、LinkProperties接口/IPv4与OS网卡IPv4同源、ifindex、MTU、非loopback链接检查全部保留。
- 同一 `RootClientService.watchPhysicalNetwork` 只订阅三类TRANSPORT，不再通过Internet能力限制回调，变更/丢失/禁用仍使用原NetworkScopeGate和严格同一handle/LinkProperties/原native owned Stop，不自动切换到另一网卡，也不启动第二Native M4/TUN owner。
- Root App在无Internet capability的候选Network行明确标“仅本地链路”，用户提示此情况下直接填同LAN WBD服务器IPv4及独立TLS SNI；现有Go Android `--peer-host` 原物理223.5.5.5 DNS bootstrap并不会因此获得互联网。默认Normal/off及原TLS、AEAD/PN、路由和DNS模式均不变。
- 生产Java Host test覆盖WiFi/CELL/ETH/LAN-only接受与VPN、未知Network拒绝；Host源码门核对真实Service注册未带INTERNET要求、Activity与Native共用policy；签名 APK/双ABI/原LinuxHost Oracle按本SOURCE Actions验证。没有运行个人手机或服务器，不将编译成功升级为真LAN可达/应用TCP UDP/系统netd DNS/吞吐CPU实测。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B27 root Android real LAN-only WiFi/Ethernet underlay, exact physical Network selection and generation watcher without requiring INTERNET capability; original Go/Rust M4/UID Stop preserved"}
```
