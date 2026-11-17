# PLAN029B H2109｜仅治理 cursor 热读预算修复，真实 B3 不重复派发

H2108 SOURCE `5bb367e86c81cb61b68be7c9772c0ea866f69fde` [governance Action44102947353](https://github.com/lly8666/wbd-next/actions/runs/44102947353) 最终 **FAIL**，原ZIP14336478652 SHA256 `28590733b2d70ac2815ee8abe266375788dc01d62dce3b3a69aaa60e4297bd74` CRC通过，`structure.json` 精确首错 `combined hot byte budget exceeded: 33101`（治理硬限32768，超333字节）。原feature-catalog ZIP14336093609 SHA256 `00729800d10f91007617677747fdec0871eefb36729c03020343669d37101c9b` CRC通过，`feature-check.json`为PASS，121项相关单测全PASS；只是共同调用治理校验导致两job最终FAIL，不是Rust/DNS/IPv6数据面错误。只压缩当前 M0 cursor 重复的 why/current/next/summary 约1546字符，保存 evidence_refs、SRC、历史FAIL、任务边界和无全局IPv6证明，Hot bytes预计低于32768。新治理Action还未回执，不预记PASS。

H2108 原 [签名 B3 Action44102947133](https://github.com/lly8666/wbd-next/actions/runs/44102947133) 来源已冻结，不取消不重派；一场真实Wintun测试only /128、16次AF_INET6与12次真实IPv4混跑及原Rust Stop待同源原ZIP。H2107 source5a80另有Normal/off原生回归，在途单独核对。此次不修改Go/Rust、原夹具、性能算法、旧WFP、DNS或路由，也不重开028/030；B4多代真实GUI/Stop及Game、B5同VM10Mbps CPU/p99仍按NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"H2109 only compress M0 hot-read cursor text for original governance budget failure; exact real B3 source remains in flight and unmodified"}
```
