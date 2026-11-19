# PLAN029B H2105｜源锁WinForms配置已通过；真实IPv6 Wintun/128混IPv4代表

H2104 SOURCE `969ce2b1a321e3a122c7cc235db7da45a7f13a17` [Action44091381879](https://github.com/lly8666/wbd-next/actions/runs/44091381879) 原Windows2025真编译WinForms→Go CLI→同源码Rust DLL，结果SUCCESS，ZIP artifact14331293478 SHA256 `0c102af7ca7eac545fb9550c719dfab1981e6ee102bfbd4e16656153507f8f5e`，9件CRC通过，Win Go SHA `a66d9b965636d6642875321e34ab854b24a2232581896d89063fd36636bd3d46`，Rust DLL SHA `aa8579739a253677d06089abcd4465c4543e7f072fe210969890f92fcde154df`。新CN FakeIP默认false，旧配置缺键true、显式false两个各自保存重开；all/off失效Direct容量16385和停用CN规则缺文件可准入，活动CN容量/规则仍拒非法。独立原Go编译 [44091382013](https://github.com/lly8666/wbd-next/actions/runs/44091382013)、Windows/Linux廉价 [44091381897](https://github.com/lly8666/wbd-next/actions/runs/44091381897) PASS。该源**仅配置链PASS，不是签名网络/GUI OS Applied**。

旧D4源没有IPv6真实路由或发包，不能当拦截。H2105一个 `[plan029b-b3-ipv6-real]` 的签名Normal/off同SOURCE原Win2025 Npcap/Wintun↔WSL2：验证原Wintun`10.66.0.2`唯一ifindex与原`ms_tcpip6`启用绑定、无预存同一ULA地址/路由，先写测试SOURCE+ifindex owned intent，仅在这个原Wintun加临时`fd73:29b:2026::2`及目标`fd73:29b:2026::1/128`主机路由；原Windows AF_INET6内核UDP实发16次，插入12次原Linux TUN IPv4应答。生产Rust只利用现有Wintun首字节检查区分内部`ReadResult::SkippedIpv6`，丢IPv6不拷贝/转入业务/AEAD/FEC；原公平RX计数继续读下个IPv4，仅Stop时打印有界总数一次。无新IPv6模块/独立worker/Go逐包/WFP/全局禁IPv6或解绑。真实Wintun skip≥16、IPv4 echo 12、测试精确路由/地址清理和双方原owned Stop才可限域PASS；否则按真实失败/NOT_RUN记录。对宿主onlink及物理接口绑定IPv6**仍未证明拦截**。实际新SOURCE签名结果**NOT_RUN，等待原Action证据**。

B2普通H2098、高级CI FakeIP H2101、all/off H2103各保留原SOURCE限定PASS；B4完整多代GUI/Game与B5同VM≤10Mbps CPU/交付GiB、host CPU、RSS/唤醒及小TCP/UDP p99继续未验，不重跑028或弱网全矩阵。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback"],"reason":"H2104 same-source compiled WinForms/Go/Rust config PASS; H2105 limited original AF_INET6 Wintun first-byte skip and owned /128 true kernel B3 pending"}
```
