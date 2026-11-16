# PLAN029 H1998｜普通大 TCP，无人为 pacing，物理对照 Direct（单网络场景）
- 用户要求覆盖多种代表性 Direct 延迟工况；H1997 已在途，真实 Windows/WSL2 同 VM 1KiB 已建连 RTT p99，当前SOURCE为 `e200061997839ef3697a826742c2eb4d1a34b41f`。
- 现有 1MiB/16KiB每4ms 中，物理295.366ms、Direct301.871ms，间距2.2%，但人工节奏**不能**检验无pace的大传输；H1864旧 SOURCE 4MiB 物理32.155ms / Direct131.544ms（4.09倍），是值得独立复核的显著差距。
- **仅原已有签名 native fixture** `[plan029-v3-real-p2-bulk]`，4MiB 真实 Windows Kernel TCP / WSL2 内核回声，物理 socket vs FakeIP Direct **同一VM顺序**，完整SHA/FIN与原双方 Stop、Direct全程96B Tunnel UDP120条。既有工具上报连接、上传/下载分段、实际交付、最长UDP回包间隔与p99；不混小连接128、ABBA、500/700Mbps/30s持续、重压、高额度、Game矩阵。
- 不修改任何 Go/Rust、协议、WFP、内核timer或产品配置，只在原工作流头部加SOURCE显式注释触发已有 Action，其他场景不调度。与 H1997 为不同已签名 Windows Action、不同SOURCE，不混结果作CPU因果。
- 当前SOURCE、Action的4MiB结果在本提交时 **NOT_RUN**，只收实际证据。后续若仍有显著大差距查首个用户态读/写与TX/RX空洞；若只是几ms或在宿主容量噪声内不继续调参。
- Direct UDP单个已验回包不等于UDP p99；新的三包长 RTT 测试脚本尚未通过源锁预检，未合并，不能冒充已经运行。此次先把现成可靠工况跑完。
```feature-impact
{"kind":"none","ids":[],"reason":"H1998 reuse existing signed original unpaced 4MiB Direct TCP P2 physical comparison without product or extreme test feature changes."}
```
