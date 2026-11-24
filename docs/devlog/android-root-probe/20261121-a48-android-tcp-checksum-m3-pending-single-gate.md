# A48｜真实 API36 RAW RX TCP checksum-only mismatch：仅Android候选交M3

## 实机可重复的真实证据

真实手机 SOURCE `b34f8c3cff53bde49b80adf659b27bad0bdc25eb`，2026-11-21 API36 普通APP IPv4 selected UID、Normal/off；用户实测Chrome和ping仍不通。正常受保护 TLS/Admission/TUN /32、原 Rust M4、UID读回均过。A47b 真正的内核RAW 22数值证据：`read=114, data=0, ack=0, tcpck=113, tuple=ipck=flags=len=opts=ttl0=0`，最新真实外层IPv4 TCP头`src=2657443504`（158.101.94.176）、`dst=2887407817`（172.26.88.201）、`sport=443,dport=53367,ttl=50,lastflags=24`（PSH|ACK）；另一次40B TCP RST显示`flags=1`，不应作为合法业务。原Rust`tun=98,rawtx=98,tcp=77,udp=8,icmp=13`，实际客户端发送由原Rust完成，但`parsed=0,auth=0,rtun=0`。**即手机收到真实服务器方向的 TCP PSH/ACK，原Rust在原 M3 AEAD 之前因 TCP checksum 值被全部丢弃。** 报文不代表密码学身份已证，校验和不一致是公网路径/NAT/内核卸载状态或对端字节的表现，目前不能从仅数值证据认定哪个设备改写；不能谎称服务端错误。用户已验证同服务器与Windows公网业务正常。

原Go donor的`ParseIPv4TCP` 冷TLS解析器**没有核TCP/IP校验和**；TLS/Admission通过无法保证这台Android Bionic recvfrom获得的原生DATAs符合Rust附加的传统TCP checksum。原主线 Windows和Linux client 使用同一个严格 `rx_ipv4_tcp::parse_data_packet`，继续保留这一行为。

## 有条件只放行未认证候选，不删除 Rust M3 认证

仅在`AndroidBoundRawRx::read_original_record`调用严格`parse_data_packet`得到**恰好`RxError::TcpChecksum`**时，才复用同一原 parser 内部函数、相同实名tuple/ICMP-independent头、IP checksum、IPv4长度和MTU、非分片、TCP flags=PSH|ACK、TCP选项、非空DATA等校验，唯一不同是`require_tcp_checksum=false`，然后仅将返回的**未认证ciphertext**继续交给原Rust M1`android_extend_seq32`和原`offer_after_active`，之后仍由**原 M3 AEAD、PN/replay**决定最终收包/Health和TUN。这是对应真实`tcpck=113/114`的最小恢复，而不是“删除所有校验”；`tcpck`会继续累加观测到的坏TCP checksum，`data`会计入转交M3的未认证候选（不宣称业务成功），M3实际`auth/rejected/rtun`继续决定结果。纯 ACK、RST、不符合四元组或任何其他校验门不得借此进入 M3，特别保留 owned Stop。

新的`parse_data_packet_android_m3_pending`只在`target_os=android`或Rust测试编译启用；原公开`parse_data_packet`继续强制TCP checksum且主线Windows/Linux生产代码不可调用Android入口，纯ACK严格解析器不变。测试取原Rust writer真实生成的原数据，故意仅损坏TCP checksum，**原严格 parser必须失败**而Android未认证候选可返回同样密文；还验证篡改密文仍只返回*未经认证*候选，必须经过原 M3；坏IP checksum、四元组、flags、MTU/长度、纯ACK继续被拒。原 main H2216 Windows公网TTL测试保持完整，非变更本次TTL。原Linux Normal/off Go TLS、Rust M4、TUN UDP及 joined Stop Oracle 不改。

## 当前验证限制与下一次真实物理分流

A48新增 `cargo test -p wbd-platform --lib a48_android_m3_pending_accepts_only_tcp_checksum_drift_as_untrusted` 真正Rust test、Android源锁门和原完整产品CI签名APK。CI Host不能证明 Android live PASS。下一次用户在同一台已能和 Windows 正常工作的公网服务器上，仅选定Chrome+ping app、Normal/off；尝试真正IPv4网页与内侧TUN IP ICMP、Stop导出TXT。若`tcpck>0`而`data/parsed>0`但`auth=0,rejected>0`，进一步检查原M3密钥、序号锚/回放与原 Rust接线；若`auth>0`但`rtun=0`，检查原Rust内层LINK20重组/TUN；若真实`rtun>0`而上网仍不通，复查DNS/实际选定UID/路由和TCP等。绝不把原生RAW读到外层 PSH ACK 或 M3候选当成业务双向PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A47b API36原Rust RAW收到114包113仅TCP checksum失败，M3根本无法尝试。A48仅Android在严格parser唯一TCP checksum失败后继续未认证候选送原M3 AEAD/PN，其余头门/Windows/Linux/owned Stop不变，新增真实Rust回归与原源锁。"}
```
