# PLAN029 H2058｜源码锁定真GUI+物理TC与异步进程崩溃组件收据

按独立SOURCE及真实GitHub Action、ZIP里的原Go/Rust/Wintun报告、原WinForms log、原Linux guest UDP/TCP收包、原客户端/服务器Stop归档，详见 [H2058 evidence](../evidence/M0/PLAN029-H2058-GUI-DNS-TC-REAL-FAKEABORT-20261117.json)。

- **H2055 GUI** [Action 44000778566](https://github.com/lly8666/wbd-next/actions/runs/44000778566)，SOURCE `e586ca2396535781a41cea3a454da45c32808aa7`、artifact14292293757。原WinForms真Connect，原Go TLS+Rust Npcap/Wintun OS Applied，外层1460/Windows+Linux内层1389，CN物理Direct UDP与32KiB内核TCP、Tunnel UDP/TCP回执、双端原WAL Stop、原报告`exit_code=0 product_pass=true`。H2050旧`Form.Dispose`退出异常继续保留为失败；此SOURCE只采样GUI父进程，Go/Rust CPU/RSS未验。
- **H2056 同一物理DNS TC** [Action 44001081299](https://github.com/lly8666/wbd-next/actions/runs/44001081299)，SOURCE `17ebe7e91830595d6083dd8314716f99e8c99918`、artifact14292184174：Linux真实guest UDP53收到源`172.24.80.1`同端点`172.24.95.253`的原查询并回TC1，再同源TCP53读到同ID `bce4`、同QNAME A回应；原Go `BOOTSTRAP_DNS_SELECTED generation=1`后原TLS/Rust物理+Tunnel业务、1460/1389与Stop，全套源一致`product_pass=true exit_code=0`。**重连后第二代DNS仍NOT_RUN**，不能推导已过。H2051旧UDP超时继续保留失败。
- **H2057 FakeIP async journal 子进程真abort** [Action 44001435567](https://github.com/lly8666/wbd-next/actions/runs/44001435567)，SOURCE `81748492a093495da4fa000bba9a6d745bd5dc4c`，Windows/Ubuntu Rust两个job成功：真实fsync durable ACK之后`std::process::abort`跳过Drop，父进程再开文件验证FakeIP映射/quarantine及未持久化别名不可公告。只可认定**进程级组件测试**，绝非Windows产品网卡/路由WAL突然死亡恢复。H2051五类小额度组件独立推进通过，但未同VM真Wintun满额或RSS量测。

未结项：二代真实DNS cold TC重连、真实产品DNS TTL/进程意外退出OS WAL、慢磁盘与Direct/Tunnel业务并发、五类原生同时满额、GUI有效Padding off/tls/flows及同VM off/on CPU/RSS。H2031 Padding/H2041 Game4历史真验保留，不重做，用户已排除IPv6/P1/P2旧性能/跨CDN等不扩展。全部PLAN029未整体提升到完成。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","dns-split-ipv6"],"reason":"Accept only source-locked H2055 GUI and H2056 physical same-endpoint DNS TC true original native business/Stop, plus H2057 real process-abort pure test; remaining selected scopes explicitly OPEN."}
```
