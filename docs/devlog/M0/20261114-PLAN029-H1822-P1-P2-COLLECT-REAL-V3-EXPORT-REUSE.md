# PLAN029 H1822｜收完整V3导出、P2混合真实业务及P1同VM性能，明确性能风险

- **H1820** SOURCE `b7b688573326580e39571c1e748663b8566d5fc2` [Action43574002456](https://github.com/lly8666/wbd-next/actions/runs/43574002456)全绿：原Go与Rust ISA-L+m0_v4_probe构建，Windows ctypes实际加载 DLL 读取 wbd_m0_win_native_v3_start 导出，才安装签名Npcap/Wintun。Windows真实物理绑定TCP1MiB回声312ms vs 经真实Wintun租约/FakeIP/Rust Direct TCP1MiB回声6485ms，两次真Linux guest物理源与payload SHA相等；后一程120个96B Tunnel UDP同时真实前进，Windows/Linux产品原有DNS/Direct/Tunnel及双方owned Stop PASS。**P2功能通过，但Direct慢路径是性能风险，不是优化目标PASS**。旧H1818/H1819缺V3 symbol失败仍保留。
- **H1821** SOURCE `241418ff0e78a80894ffdc344afaab73c77a3b0e` [Action43574961780](https://github.com/lly8666/wbd-next/actions/runs/43574961780)全绿：从H1820产物严格验证GitHub run/SOURCE/构建feature/每文件大小SHA256/产品目录diff及本VM再次实际加载V3符号，Windows单VM A旧V4纯Tunnel→Stop→B新V3/all纯Tunnel→Stop，每腿真双向50Mbps/25ms0%/60s、TCP/UDP/OS Stop/近100%唯一交付。每腿约0.6984GiB，Win Go+Rust PID CPU/交付GiB A10.5599s、B11.343s，B高7.42%超过5%调查线；Win单时钟UDP RTT p99均47ms，Linux分别53.738/55.739ms。A旧V4/B新V3并非只开一个分类器位，不可将所有7.42%归因于分类器或真实驱动CPU；不为凑5%多跑不必要极端工况。
- 对应P1和P2不同SOURCE分别落独立evidence/功能卡，历史记录均保留；明确**Action SUCCESS表示本场原始功能和量化数据有效，不表示P1相对性能验收通过**。PLAN029仍IN_PROGRESS，D4 IPv6、D5 GUI-origin签名联网、Game4实际单Wintun的CN双出口有实质缺口，下一批按新假设补，不重复Win/Linux x86、ARM64已绿纯测或028完整七模式矩阵。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","normal-off","windows-native-transport"],"reason":"Record exact source-locked signed P2 functionality/latency risk and P1 same-VM Normal A/B +7.42% CPU-per-GiB over target, preserving prior failure evidence and unqualified performance scope."}
```
