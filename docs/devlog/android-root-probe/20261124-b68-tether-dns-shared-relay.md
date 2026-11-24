# B68｜热点 IPv4 DNS 同一生产解析器及 B67 冷轮换源检查

B67 `dbecd858edb94c70e008bbf94f7b66a729f2de2e` [#45318709332](https://github.com/lly8666/wbd-next/actions/runs/45318709332) 原生双ABI/6 host/两Linux Oracle通过，旧B61轮换源码断言阻断APK（新增oldNet.same(same)需同步），治理通过；不将B67标为完整PASS。B68保留CLAT parent/NAT64身份校验并更新旧断言。

开启B65软件热点共享且选择DNS模式后，同B64/B66 Go DNS owner在实际下游IPv4网关追加同端口UDP/TCP listener，限制实际子网peer；共享原resolver/模式/缓存、物理Network和认证lease/TUN-bound upstream。独立选项关闭App TCP53仍只安装上游源路由，不新增App NAT；不修改Android DHCP、netd、热点配置。精确下游PREROUTING TCP/UDP53 DNAT到网关listener、INPUT DNAT许可、conntrack逆变换，普通数据仍原内核SNAT和Rust M4。先撤热点入口再joined DNS Stop/UID Stop，旧journal缺省字段兼容。真实loopback双入口/三模式路径及journal seam测试；热点实体、IPv6内层、Private DNS及offload仍未验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B68软件热点普通IPv4 UDP/TCP DNS复用原解析器、精确下游入口、三模式原上游和Stop/Restore；B67源断言同步。"}
```
