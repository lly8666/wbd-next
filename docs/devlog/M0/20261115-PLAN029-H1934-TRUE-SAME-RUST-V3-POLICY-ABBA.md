# PLAN029 H1934｜同Rust分流策略4臂ABBA真实Windows原生接线
- H1933已先以纯评分器和8项低价测试确认真正同Rust V3 all/CN/CN/all、同Windows VM original Go EXE+Rust DLL/WSL2 Linux同SOURCE/同binary、各自真正Stop、按首交付GiB计CPU和Rust TX/RX原Win32 TID/真实UDP p99。H1931物理TCP约0.3s/GiB是原Rust客户端空闲进程，因为物理流量绕开它，绝非分类器低成本。
- 本次只改原有测试工具/工作流；真实原Go/Rust产品数据面未改。四独立60s双向50Mbps 25ms0loss场景，每段同源可追踪重启和WAL owned Stop，复用测试专有Linux TUN真实 owned 203.0.113.77/32公有别名；无论all或CN均**走真实原Rust Tunnel**，绝不把10.66.0.1 LAN/Direct混进B。B冷源加载4096不连续CN/32和8192域名，A不载，严格取原Rust cold日志cn_rows/domain_bytes。所有其他TLS、FEC、MTU、性能工况不变。
- 新四臂marker `[plan029-v3-real-p1-tunnel-ab]` + `[plan029-v3-real-p1-policy-abba]`启动单个真实Win2025+WSL2 Action, 1850s per-child守时；旧H1814 V4-vs-V3两臂对照另保留。新旧无混用不假装统计显著、4臂真交付量差>3%标INCONCLUSIVE而不是PASS性能赢。守原Linux公有alias owned清理、两端Stop、同二进制SHA/证据路径。
- H1934新原生结果尚未获得，不宣称CPU改善。后续单独测旧新NAT**两者都经过Rust Direct**同VM ABBA，并通过ETW/WPR系统级Windows内核/驱动归因；不再用物理socket的原进程闲置窗口当分流开关反事实。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Test-only source-locked original same-Rust V3 four-stage all/CN policy A-B-B-A under identical real Tunnel exit; original network result pending."}
```
