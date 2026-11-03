# PLAN028 H1043 — Windows/Linux 原生通知 200ms/500ms

2026-11-03 最新用户要求 Windows/Linux 原生路由/IPv4网卡通知及200ms静默、最长500ms的事件合并，取代H1034历史两秒冷轮询。H1034已验结果保留为历史限定证据，不重写旧PASS。

恢复已编译过的H1033 Windows IPv4 IP Helper NotifyRouteChange2/NotifyUnicastIpAddressChange 回调和H1026 Linux NETLINK_ROUTE LINK/ADDR/ROUTE订阅。回调只发冷路径单槽通知；合并后对numeric server endpoint从OS取真实物理ifindex/interface和源IPv4。自身TUN、单纯gateway/route/MTU事件不建新TLS，但新物理路径仍重算H1031 per-route MTU cap并按原Rust M4安装读回。Windows仍Stop-first重新TLS，不谎称A+B；Linux Normal auto保留既有A→A+B→B。无新状态控制器、探针、逐包FFI或wire/FEC改变。

治理卡片 H1022–H1024 重复历史说明已合并到一条，原 verification、证据与 devlog 引用保持；这只是16KiB卡片限额修正，不扩张PASS。\n\nH1043 同源 Linux 原生 [Action 41648749803](https://github.com/lly8666/wbd-next/actions/runs/41648749803) **SUCCESS**：真kernel netns RTNETLINK、原GoTLS/Rust A→A+B→B及新路径MTU/Stop验证。Windows同源 [Action 41648749762](https://github.com/lly8666/wbd-next/actions/runs/41648749762) 的Go生产编译、Rust单测成功，但真实双OS整体FAIL：原Game2/Game4/FEC变体第二FakeTCP lane bootstrap stream deadline exceeded；Normal/Fixed/Auto子场景通过不能推广成Windows整包或网卡真切换PASS。证据源锚在 `docs/evidence/M0/PLAN028-H1043-SOURCEA92C-NATIVE-OS-NOTIFY-20261103.json`，H1042不同SOURCE证据仅在历史文件/功能卡引用。

本SOURCE新原生Action成功前为IMPLEMENTED_NOT_TESTED；Windows真物理网卡切换、自然Health90及七模式切网仍未验证。500ms是通知合并预算不是TLS/首包SLA。H998在线缩窄FAIL、ARM64 Game4FEC FAIL、远端ICMP未测及CPU因果未证保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1043 restore native Win IPv4 IPHelper and Linux RTNETLINK notifications coalesced 200ms quiet/500ms max while retaining H1031 route-MTU and exact generation Stop."}
```
