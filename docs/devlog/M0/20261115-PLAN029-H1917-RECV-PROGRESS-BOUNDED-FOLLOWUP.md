# PLAN029 H1917｜先修H1916真实4MiB回程卡住，不以Actions假红豁免
- [H1916签名原生Action43708480409](https://github.com/lly8666/wbd-next/actions/runs/43708480409) SOURCE `00c41dad927bd5846da79fcec4c42f51d650c645` **真实业务FAIL**。原Windows Go/Rust/Wintun/Npcap已真实Ready，CN DNS/Direct UDP/Tunnel UDP和旧32KiB Direct TCP真FIN+echo局部PASS。后续4MiB物理基线PASS；Direct Windows发送4194304B并SHUT_WR、Linux收到同字节及FIN、完整sendall(4194304)回显并SHUT_WR；Windows接收进度记录仅确认>=131485B，随后recv 35秒超时。记录不是“最新CPU慢”或假红。
- 原Rust事件统计：shard_wakes40、event_socket_checks76、event_take_errors0、event_read32、relay_turns92、relay_no_progress8、relay_progress_no_self_ticket26、outer_read_calls10、outer_read_wouldblock2、outer_read_event_suppressed79。提示内核事件/续读前进性风险，但目前尚**不能证明**具体底层原因；不做全局轮询、每flow线程或新TCP栈。
- H1915在正向短读成功、queue为空后取消自票据，H1916对并发FD_CLOSE补EOF票据但回程仍停。H1917保留16 WinSock shards、per-leg read_armed、64KiB单次读、8flow轮转及H1916 FD_CLOSE hint，**仅把真实recv有正字节的活跃flow续发一张有界FIFO票据**，直到该次读变为WouldBlock/EOF或没有排队尾巴；零进展没有自票据/无10ms idle poll，旧静默flow仍完全靠真实事件。纯 helper回归覆盖1/413/16KiB/32KiB/65535短读、64KiB满读、两腿、0进展、尾巴和FD_CLOSE。此修复候选尚未获真实新SOURCE验收。
- 用新SOURCE自动Actions先看Windows/Linux平台组件与原生真实32KiB+4MiB两端完整SHA/FIN/Stop；这两个门过后方可把同VM 500/700Mbps的10GiB持续负载用于CPU测量。比较优化应旧/新二进制在**同一Windows VM**轮转，不能把不同VM H1913 CPU/GiB差值算增益；小Direct TCP/UDP p99、Tunnel UDP p99、等待年龄与绝对毫秒容差是后续保护验收；若无稳定CPU收益就停该优化方向。
- 保留H1916失败/10GiB NOT_RUN和H1913旧SOURCE PASS，非产品全额Stop的Finally Scoped清理不能改写为产品Stop PASS。PLAN029其余D1–D5/P1–P2/Game4/GUI/IPv6/padding/Stop继续OPEN，028限域不重开，030未启动。凭据与pcap不入库。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1916 native real unpaced 4MiB reply timeout after short 32KiB FIN success; H1917 resumes one progress-correlated bounded ticket only, full source still NOT_RUN."}
```
