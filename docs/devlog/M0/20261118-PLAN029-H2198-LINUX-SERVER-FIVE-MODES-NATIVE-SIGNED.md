# H2198｜Linux原客户端＋服务端五模式随机启动填充，20/20双ISA原生PASS_SCOPED

已核冻结产品SOURCE `e82ba704dd3c36941cc21e7e3fcd85e1a2ab7be6` [原生Action 44296499335](https://github.com/lly8666/wbd-next/actions/runs/44296499335) **completed SUCCESS**：Ubuntu native x86_64/aarch64分别独立构建原Go+Rust/ISA-L bundle，各五模式×tls/flows 10场，20/20真实原Go TLS、认证原Rust M1/AEAD→M4 AF_PACKET成功复制随机填充、真实内核TCP与UDP双向、双TUN owned IPv6/MTU/DF与双Stop和netns清理均PASS_SCOPED。

重点是**Linux服务端自己填**：20个scene server每个都有非零 copied padded_records/bytes，同时client各场也非零；服务端与客户端20/20场累计随机字节不等。例 x86 Normal/tls client 2条209B vs server 2条739B，Fixed/tls 147B vs 481B，Auto/flows 991B vs 985B，Game2/tls 776B vs 1470B，Game4/flows 2408B vs 3637B；ARM64各10场原始值均在[签名 evidence](../evidence/M0/PLAN029-H2197-LINUX-SERVER-FIVE-MODES-X86-ARM64-TWENTY-REAL-NATIVE-PASS-20261118.json)。server game2 fixed6 flows和game4 fixed6 tls都实测；不把parity kind3当填充。两个GitHub原ZIP分别190成员CRC全PASS，SHA与三binary digest在同Evidence。

代码仅将认证epoch派生给非加密startup-pad的随机种子做client/server方向分离；**不改**受保护Go TLS epoch、PN、AEAD KDF、原始业务IPv4/FEC符号/修复、Group lane；Off无跟踪表，默认仍off；参数仅在cold新generation生效。历史H2186/H2193/H2195不同SOURCE真PASS不重跑。当前仍无该SOURCE下shared默认443多模式同时混合业务、auto-IP物理MTU动态重认证、实体ARM板、跨ISA物理链路、完整应用TLS、CPU/p99及弱网FEC恢复证据，不能把限域PASS写成029技术全部完成。离线route-key TLS红线继续保留、030未启动。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2198 actual source-locked native Linux x86_64/aarch64 5×2 server/client independently padded original Rust AF_PACKET copies 20/20 PASS_SCOPED, distinct per-direction lengths and original OS/TUN/Stop; no complete PLAN029 promotion."}
```
