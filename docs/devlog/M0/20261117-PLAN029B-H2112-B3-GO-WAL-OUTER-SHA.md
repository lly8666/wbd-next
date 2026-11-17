# PLAN029B H2112｜Go旧代阶段摘要不影响外层WAL验签；唯一新SOURCE真IPv6场景

H2111 SOURCE `d2b70092215adcfd61d1e3adea502f4096bef901` [Action44107631933](https://github.com/lly8666/wbd-next/actions/runs/44107631933) 终态：廉价流程、Windows Rust 416+R2、Linux Rust、原Go编译全PASS。WinRust original ZIP artifact14338783388 SHA256 `eccb455f0afcfbe28b0a4caadb05942411e1a3671722886ac57be93d526b2ff3`，WinGo original ZIP14337554692 SHA256 `65875d38b1109315099ae50491a5b5c17aa390df61da4bce1b580d2ddbebea07`，CRC/源锁均PASS。治理 [44107630112](https://github.com/lly8666/wbd-next/actions/runs/44107630112) 和维护 [44107630421](https://github.com/lly8666/wbd-next/actions/runs/44107630421) 均PASS，**因缺B3 marker原native job有意SKIP**。当前源增加原Go v2四阶段 WAL SHA256+代际+PnP/index/GUID/alias与Windows`Get-NetIPAddress`、`Get-NetIPInterface`交叉验证，Win可列举适配器时更严格核GUID与启用绑定，而不是过度依赖显示名称。此次H2112再收紧原WAL的字节级验签扫描：原stage baseline可以自身带`sha256`字段，真正**最外层**Envelope的末次delimiter才可作为原Go Walsh checksum，不错误要求唯一出现。合成内层`sha256`正例与外层伪SHA/坏alias/cleaning阶段负例；其它原夹具和所有Rust/Go产品无改动。

H2108 SOURCE5bb [真实签名Action44102947133](https://github.com/lly8666/wbd-next/actions/runs/44102947133)原TLS/Wintun/OS Applied、双方owned Stop和原Rust背景IPv6跳包17都真实，但旧Get-NetAdapter身份预检FAIL在B3自发包前。H2112唯一 `[plan029b-b3-ipv6-real]` 标记现在才重新派发原Win2025 signed Win+WSL2内核场景。要求真实`AF_INET6` 16 UDP通过测试自有/128到原Wintun首字节skip计数，12次IPv4 TUN回显后证明无饿死，测试专用IPv6源/路由全部清理与双方原owned Stop。缺一个即FAIL；不要从历史背景17跳包冒充自己的16，也不宣称强制物理绑定、on-link与全宿主IPv6拦截。B4高级→普通→all多代真实GUI/Game、B5 sameVM <=10Mbps CPU/GiB/p99后续独立验收，029B/029不收口、030不启动。

```feature-impact
{"kind":"none","ids":[],"reason":"H2112 adds nested-sha Go WAL parser regression and one source-frozen signed B3 /128 test, not production IPv6 or CN route behavior"}
```
