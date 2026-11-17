# PLAN029B H2089｜H2088真实Normal关闭业务分流证据已验，接独立B0物理DNS

源 `9f70c7e6a306602dde39bbcdbaa09130cc8fd254` 的 [Action 44053399548](https://github.com/lly8666/wbd-next/actions/runs/44053399548) 在真正Windows2025签名Wintun0.14.1/Npcap与WSL2同源码原Go/TLS/Rust产品完成**SUCCESS**。已下载原始 `m0-wl-full-public-normal-direct-h1506-legacy-44053399548` 附件ID`14315905972`，核实report/windows release manifest/实际client/server日志所有SOURCE一致、真实Windows OS Applied与Ready、两端内核UDP/TCP双向echo、Linux native Stop、Windows `wal_kernel_crypto` PASS/断连及原有owned cleanup全部通过。真实Rust V3冷日志为`route_mode=0 business_split=false cn_domain_fakeip=false cn_rows=0 domain_bytes=0`，随后只启动 DNS TCP53 公共listener，`direct_business_nat=0`；本场外层1400对应实际Windows内层1329。H2083无V3导出真实FAIL已被本次实际release DLL/驱动前PE gate排除，旧错误仍留历史。

**严守证据边界**：H2088虽真实成功，却没有额外发受管应用DNS UDP/TCP53 A/AAAA，也没测普通/高级CN、实际IPv6流、GUI全模式或B5 CPU/GiB比较，因此只是 B0 的签名Tunnel/Stop基础`PASS_SCOPED`，不是整个029B B0–B5 PASS。

H2089新增精确`[plan029b-b0-dns-real]`一次性签名原生场。在既有正常原Windows+WSL2同一TUN、同一Go/Rust原owner及驱动下，用户侧真实Winsock从Wintun lease向真实Linux TUN 10.66.0.1:53依次发 UDP A、UDP AAAA、TCP AAAA、TCP A；Linux本机拥有唯一UDP/TCP53测试监听，只准接收两次真正A上游，验证Linux TUN真实内核socket源/响应TTL2。Windows应用必须还原原事务ID、A真实203.0.113.77与TTL2、两个AAAA `QR RA RD NOERROR ANCOUNT=0`，绝不将AAAA泄露Linux上游。真正original Windows/client TCP53由同Rust DNS-only NAT处理，没有业务Direct NAT/FakeIP或Go额外产品报文泵；原内层双向UDP/TCP和owned Stop还需一起PASS。Fixture在 Linux/Windows分别为有界进程，仅测试源，不修改生产协议与加密；按cheap Python语法、原组件/源码SHA和原生态交付门运行。H2089 **NOT_RUN直到真实附件结论**。

此外H2088治理 [44053399498](https://github.com/lly8666/wbd-next/actions/runs/44053399498) FAIL唯一原因热引用32904字节超32768；H2089仅把21KB`docs/decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md`从cursor**热引用列表**移出，文件仍在Git主线并由最新029B提示词引用，治理逻辑不松绑。原所有FAIL/NOT_RUN保留。B2 CN、B3 IPv6真实应用、B4 GUI、B5同VM公平A/B随后各按必要最小场，绝不把旧028矩阵回放。

```feature-impact
{"kind":"none","ids":[],"reason":"H2089 real signed B0 DNS app fixture and source-locked workflow only, prior H2088 signed baseline evidence and bounded hot cursor; no shipping Rust/Go/GUI feature code altered"}
```
