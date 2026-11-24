# B70｜双端内核 IPv6-in-IPv4 兼容业务承载（非裸IPv6 M3）

B69 `373f3a4ea87e3915ca68806e78206b3db6cd742e` [#45321649480](https://github.com/lly8666/wbd-next/actions/runs/45321649480) 10 SUCCESS/4 SKIPPED/1 FAIL：IPv6 DNS真实socket与双ABI/APK/两个Linux Oracle均过；shell regex引号因替换扩展破坏，后半rootjournal未跑。本批重建单一脚本并保留全部旧测试。

服务端显式 `--inner-ipv6`，已有私有TUN IPv4 /16..30 与受保护客户端IPv4租约（pool/manual）、实际IPv6转发sysctl与原RAW物理IPv6 egress。客户端冷配置 `--android-ipv6-gateway=10.219.0.1` 例子（用户实际服务端TUN IPv4，非公网peer）；原Go TLS/认证/租约/Rust M4 READY后使用原UID组/all排除规则，安装内核SIT与IPv6 19847 FIB，/48 ULA + IPv4租约低16位成/64，再取::1 /128。服务端同一SIT 6rd通配远端、原TUN绑定、同/16映射回原Rust shared-TUN /32，不增Go数据面；kernel SIT 6rd验证源IPv4嵌入，原AEAD/PN与IPv4 source lease验证保持不变，服务器精确proto41 ingress从原TUN、IPv6 prefix/物理出口及NAT66，Stop/Restore专有journal。Linux SIT参考 [kernel sit.c](https://linux.googlesource.com/linux/kernel/git/torvalds/linux/+/f51cae6603c05b4b1fac65c773592e5bc8037251/net/ipv6/sit.c)。20B封装，IPv6最小1280且nopmtudisc，原IPv4分片能力承载较小inner MTU。默认关闭；双方须明确同配置，不伪称TLS新IPv6能力协商、裸IPv6 M3或已验性能。Android现有KSU实际SIT/6rd模块、NAT66、原App IPv6 socket/服务器端真实公网端到端仍NOT_RUN。本地隔离命名空间内核缺SIT/dummy，无法内核实测；新增Host生产命令seam/租约映射及Stop/Restore。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B70可选双端原IPv4认证租约内核SIT/6rd IPv6兼容业务承载、UID选路、Linux原shared-TUN返回及Stop/Restore；非裸IPv6记录，实体未验；修复B69 shell。"}
```
