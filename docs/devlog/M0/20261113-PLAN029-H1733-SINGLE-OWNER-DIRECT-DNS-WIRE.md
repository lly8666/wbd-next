# PLAN029 H1733｜同一原Rust NativeOwner内真实Direct DNS53 socket

- 之前同SOURCE H1731 Win Rust私有V3 53/53、Linux45/45、Win GNU交叉ABI通过，仅组件。此次新源码把原 Rust Wintun TX 的DNS UDP53 QNAME Direct送到唯一绑定物理源IP＋IP_UNICAST_IF的真实WinSock socket（最多256 transaction、16条readiness quantum、无每流线程、无Go逐包），用同一Rust RX已存在的256邮箱完成Wintun回注。
- 按QNAME决定出口，不以解析器IP猜方向；CN A必须在真实FakeJournal写+sync后由FakeAllocator宣布，缺文件/SERVFAIL不泄真实海外CDN A；CN AAAA、HTTPS/SVCB NODATA。Go→Rust私有V3 cold多传绝对FakeJournal路径，按repr(C)更新 ABI 与manifest live blob；V2公开产品仍未启用。一次写前文件sync在DNS稀疏路径，非普通DATA每包。
- 保留：Tunnel DNS当前只放行请求直接指向固定dns.tunnel的L3，其他fail closed，**尚未完成强制目的地转换与反向**；UDP截断必须同端点TCP但新代码还未完成该重试，保留ticket到timeout并本地SERVFAIL。Direct kernel TCP、owned Defender/无旧WFP Apply Stop、GUI live、性能/padding、D1–D5/P1–P2仍未完成。当前SOURCE Windows/Linux Actions 待结果。
- 本批完整source+manifest合并一次，不拆逐helper CI，原H1730 FAIL与H1695诊断仍保留。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Connect direct DNS53 to real physically bound socket, strictly durable FakeIP response and sole Rust native Wintun reverse mailbox in probe V3; product 029 still NOT_RUN"}
```
