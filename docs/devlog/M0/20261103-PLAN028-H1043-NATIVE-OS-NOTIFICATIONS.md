# PLAN028 H1043 — Windows/Linux 原生通知 200ms/500ms

2026-11-03 最新用户要求 Windows/Linux 原生路由/IPv4网卡通知及200ms静默、最长500ms的事件合并，取代H1034历史两秒冷轮询。H1034已验结果保留为历史限定证据，不重写旧PASS。

恢复已编译过的H1033 Windows IPv4 IP Helper NotifyRouteChange2/NotifyUnicastIpAddressChange 回调和H1026 Linux NETLINK_ROUTE LINK/ADDR/ROUTE订阅。回调只发冷路径单槽通知；合并后对numeric server endpoint从OS取真实物理ifindex/interface和源IPv4。自身TUN、单纯gateway/route/MTU事件不建新TLS，但新物理路径仍重算H1031 per-route MTU cap并按原Rust M4安装读回。Windows仍Stop-first重新TLS，不谎称A+B；Linux Normal auto保留既有A→A+B→B。无新状态控制器、探针、逐包FFI或wire/FEC改变。

治理卡片 H1022–H1024 重复历史说明已合并到一条，原 verification、证据与 devlog 引用保持；这只是16KiB卡片限额修正，不扩张PASS。\n\n本SOURCE新原生Action成功前为IMPLEMENTED_NOT_TESTED；Windows真物理网卡切换、自然Health90及七模式切网仍未验证。500ms是通知合并预算不是TLS/首包SLA。H998在线缩窄FAIL、ARM64 Game4FEC FAIL、远端ICMP未测及CPU因果未证保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1043 restore native Win IPv4 IPHelper and Linux RTNETLINK notifications coalesced 200ms quiet/500ms max while retaining H1031 route-MTU and exact generation Stop."}
```
