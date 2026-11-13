# PLAN029 H1770｜D1真黑洞零物理回退成功，推进DNS A→真实业务和TCP53帧层

- [H1769签名Action43528230244](https://github.com/lly8666/wbd-next/actions/runs/43528230244) （SOURCE `d2a1ee3a2f2cf0d339459c6e0c4f2caf3b789724`， [原始签名证据14086482885](https://github.com/lly8666/wbd-next/actions/runs/43528230244/artifacts/14086482885)）已整体 **SUCCESS**。Windows原始Go TLS/Rust签名Wintun+Linux原TUN单Normal会话：CN DNS/FakeIP物理Direct UDP/TCP 32768B+FIN、Tunnel TCP/UDP、非CN DNS正向、原生两OS Stop均PASS。新黑洞负例具体实测`no-backup.globalx.example` Windows原应用查询3次无响应；Linux唯一Tunnel`1.1.1.1:53`收目标QNAME **3次**，物理Direct DNS端收 **0次**；4次其他Tunnel QNAME单独计数且不影响原目标，完整7s窗口，Defender/HyperV/WAL精确owned cleanup PASS。本证据只覆盖指定DNS UDP/53/单源、无系统DNS TCP53推断。
- H1770并行增加 **D2部分真实业务**：新Windows Wintun应用读取先前真实非CN DNS A=`203.0.113.77`，新UDP socket直接向该A地址端口46114送业务；同会话Linux原TUN对应/32 listener实际收原`10.66.0.2`，发回显，Windows要求原`203.0.113.77`源完整收到。此测验证非CN A之后的真实Tunnel业务，**并非**D2的CN域名海外CDN与非CN域名CN IP全反例。
- 应用**TCP/53**纯Rust帧级准备：新`v4_client_dns_tcp_ingress.rs`复用已有DNS题目解析，支持2字节长度前缀任意拆包，单流只接受一个合法QNAME，严限2006B，拒压缩指针、溢出、管线额外查询与伪回复；**没有**接内核TCP监听、唯一上游及反向回注，不能记为应用TCP/53功能PASS。
- 另一条独立的[原Windows owner ABI](https://github.com/lly8666/wbd-next/actions/runs/43526475111)长期（H1766同类）在补充Go适配器时盲断言`tls.go`必须不存在，但固定`wobuzhidao@a7a82d`原仓库已经拥有此文件且内容与后续适配不同。H1770仅允许该**一个**文件沿原始固定SHA的git字节**不覆盖复用**，其他碰撞一律FAIL，保留原TLS权限边界并实际重跑独立owner ABI，不做“强行复制最新TLS”。若后继Go桥调用失败，保留真实失败并回溯，而非跳过。
- 冻结一个H1770 SOURCE自动运行已有Normal签名场景和并行Rust/Go/治理/原Windows owner ABI；不重跑028矩阵、不提前宣布029完成，GUI/配置实际有效、startup padding原AEAD真正调用与P1–P2性能尚OPEN，030不动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1769 original two-OS D1 nonCN DNS 7s blackhole 3 Tunnel/0 physical and Stop signed PASS; H1770 post-resolve A Tunnel business and app TCP53 parser source-only pending"}
```
