# PLAN029 H1866｜真实签名Windows IPv6策略/Stop路由见证

- H1865已收H1863 P1 A/B 50Mbps真Stop PASS但CPU/GiB +7.01%、Win p99+15ms OPEN；H1864 4MiB unpaced P2 物理32.155ms/Direct131.544ms、Tunnel小UDP120/120、Stop PASS但4.091×物理慢路OPEN，不重复dispatch。
- 本批在原`[plan029-real-product-cn]`显式非CI Normal CN产品真实签名Wintun/原Go四阶段OS Apply/owned Stop中，独立`[plan029-d4-ipv6-probe]`启用**只读**PowerShell `Get-NetRoute -AddressFamily IPv6 -PolicyStore ActiveStore`，采前/Ready中/Stop后 `::/0,::/1,8000::/1` 的ifindex/metric/nextHop，并读`10.66.0.2`当前真实Wintun IPv4 lease ifindex。没有新路由/IPv6地址/防火墙WFP/全局禁用或非owned清理，不发外网IPv6；真实结果提交时NOT_RUN。
- 独立纯逻辑4例验证：物理IPv6缺Wintun /1时`OPEN_NO_GENERAL_IPV6_WINTUN_SINK`；有双/1也只`ROUTE_ONLY_PRESENT_PACKET_NOT_TESTED`；精确Wintun前后多出owned前缀Stop FAIL；缺真实租约或畸形路由fail closed。旁路on-link/绑定物理/加密DNS、实际IPv6应用收件一律不得从普通路由推断。
- 真实读取/场景若失败先定位首个边界、不绕过校验。若无Wintun IPv6 sink且物理默认可用，只能结论IPv6覆盖OPEN，下一轮有界设计少量owned捕获/阻断并实测；原保留的非本项目设置不碰。
- 此批一Action一Normal D4现场，022/028旧矩阵不重开，030未开工；GUI真Connect/Stop、Game4 CN、D1-D5余项、压力与性能仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add source-locked real original signed Windows IPv6 route-scope and owned Stop readback witness; avoid falsely claiming route-only proof as IPv6 packet blocking."}
```
