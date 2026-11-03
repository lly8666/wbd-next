# PLAN028 H1073｜原产品冻结同字节，双端真实 netns 抓包

上一轮 [H1072 Action 41696747514](https://github.com/lly8666/wbd-next/actions/runs/41696747514) 复用H1071原 Go/Rust x86 SOURCE `d7bd355389c1233c54eaa6a4553ebadcbe0eeb70`，manifest/3 ELF SHA256 PASS，真正TLS服务器证书验证、受保护账号和5真实UDP echo、Rust Stop已通过，但内核 tcpdump 的 `wbdvs0` PCAP 只有24B global header，**0包**，因此不能判定 ClientHello 首载荷，也不能对项目标准TLS外观给PASS。放宽单接口BPF为IP后仍0包，继续刷同样单侧抓包无意义。

H1073 **仅变更测试夹具、离线审计器**：原 Linux client和server两个隔离netns各起一份无BPF的 `tcpdump -i any`（SLL/SLL2 cooked frame），并在临时runner内部用严格的同一TCP443四元组、TCP序号去重/重组执行原审计；支持Ethernet、802.1Q、Linux SLL1/2，校验第一payload确实TLS ClientHello、server不先发、实际ServerHello、TLS records与ClientHello扩展/SessionID32长度。输出仅有结构/record hash/字节计数，PCAP不会上传，进程和临时文件即使失败也清理。**没有**伪TLS、修改内容或将任何实际业务PASS推广成外观PASS。

只派一个已存在的 `m0-plan028-tls-wire-frozen-x86.yml` Action，继续下载 H1071 编译完成的工件 [41694943009](https://github.com/lly8666/wbd-next/actions/runs/41694943009) `13260387707`，逐SHA/ELF验证；本次commit `[frozen-fixture-only]` 会让原构建Action跳过，避免重新编译。测试一场景 x86_64 client+server，完成后才可确认原 ClientHello/证书/私有password和Rust业务并合；若任一端PCAP仍无真实 TCP，继续限定FAIL并定位 AF_PACKET 抓取路径。

**未完成**：完整TLS版本/长度与标准baseline比对和Game各lane、新ARM64双端真实native资格。Windows signed Wintun 原生 Action 仍独立收存，不重复派发。保留 H998 live MTU FAIL、原ARM64 Game4FEC Action FAIL、Windows物理切换/远端ICMP/CPU因果未证。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1073 reuse SHA frozen H1071 Go/Rust x86 binary for no-BPF two-network-namespace kernel TCP capture SLL2 structural TLS first flight test; no product changes, exterior still not qualified until results."}
```
