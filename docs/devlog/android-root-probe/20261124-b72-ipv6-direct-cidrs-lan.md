# B72｜原IPv6兼容承载的CIDR分流与自动LAN直连

B71 SOURCE `992f77f4e81b4c8263302b3ea80523b6c3ff34cf` [Dual64 #45324658533](https://github.com/lly8666/wbd-next/actions/runs/45324658533) 11 SUCCESS/4 SKIPPED；用户要求继续大类功能接线，独立功能合批，不钻极端工况或增加安全加固。

在原IPv6 UID FIB 19847增加最多16个显式IPv6 CIDR throw，后续交给Android既有路由；原自动LAN开关在每次冷启动读取所选物理接口（CLAT时读取parent）的实际IPv6 on-link前缀，并涵盖link-local/multicast本地范围。原SIT租约地址空间及热点返回路由仍保留，原journal批量Stop/Restore撤回精确规则。设置字段进原四槽/SAF及冷恢复Intent；旧设置默认空。没有新增逐包Go/Rust线程、协议或全局路由。Host生产命令seam、配置roundtrip与同源CI待验，实体IPv6/Android转发/性能仍NOT_RUN。实际物理出口由Android后续RPDB决定。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B72 IPv6承载手工CIDR分流及真实Network自动IPv6 LAN直连，原UID FIB/Stop/Restore、四槽和冷恢复接线"}
```
