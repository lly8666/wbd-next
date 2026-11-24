# B75/B76｜普通App IPv6 DNS与双栈热点直连

B73/B74 SOURCE `7b3e10352047d8f3af0284286fb0b8edfd676348` [产品 #45334679723](https://github.com/lly8666/wbd-next/actions/runs/45334679723) 9 SUCCESS/1 FAIL/5 SKIPPED：Rust UDP DNS逆映射、Go普通/系统/热点IPv6 DNS Host、双ABI及原Linux Oracle通过；ARM64 APK在旧B29 Python源码固定计数断言停止，未完成签名包。 [目录 #45334679721](https://github.com/lly8666/wbd-next/actions/runs/45334679721) SUCCESS。更新B29及原RX候选检查至B73真实实现，不关闭检查。

B75：原SIT IPv6承载+三DNS模式启用时，普通App直接IPv6 UDP53经原UID FIB选择SIT后进入精确OUTPUT REDIRECT；TCP53随既有App TCP DNS开关；复用B69 IPv6 loopback内核监听与同一B73上游、CN matcher、DNS resolver和Stop。系统netId DNS可与普通App共用一个监听，无新通用DATA线程，直连或其他网络的流量不命中SIT OUTPUT。

B76：软件热点IPv4和IPv6共享显式手工/自动LAN CIDR，IPv4私有19844 FIB throw回落Android既有后续RPDB；保留更具体的本地下游返回路由，IPv6同样处理下游内的更具体CIDR。实际物理出口由Android后续路由决定。原DNS模式、协议、默认无直连不变。

Host新增普通IPv6 App UDP/TCP规则/Restore、共享监听及IPv4热点直连/Restore正常组合测试，统一CI；实体Android热点/IPv6、业务与性能NOT_RUN。未操作真机或服务器，main/M0未写。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B75普通App IPv6 DNS复用原relay/B76双栈热点CIDR分流与Stop，更新B73源码判据"}
```
