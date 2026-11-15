# PLAN029 H1881｜收 H1880 真Windows 128 socket同分片并发（不冒充Wintun）

- [H1880 Action43664841742](https://github.com/lly8666/wbd-next/actions/runs/43664841742) exact SOURCE `cab3feebb7ec778c96991ebbdc2b5e6efad48923`, native Windows2025 job132661812029和Ubuntu job132661812463均SUCCESS。**Windows实际跑了**`cargo test -p wbd-platform --lib` 52/52，其具名单测 `plan029_sharded_wsa_128_idle_two_active_same_event_no_lost_read ... ok`。128组真实Windows loopback内核TCP socket，126对保持空闲，索引15/31两个真实连接同时出数，映射到同一WSA事件分片15；首次事件原子清除后两个`FD_READ`均完整读出A/B，各1字节。起始空闲事件0ms等待Timeout，避免FD_WRITE虚假醒。
- 同SOURCE Windows Rust Engine PLAN029 88/88、V3 probe 90/90，Linux组件PASS。测试无新每flow线程/带外Wintun写者；但**这不是128条原客户端Wintun的并发真实分流业务，也没测CPU/调度队列年龄/同VM新旧性能A/B**。
- 真实首次 H1879 Windows组件测试失败 `E0277` (测试`[u8;1]`与`&[u8;1]`不相等)，H1880仅调整为byte char compare后此具名Windows socket单测PASS；保留H1879 FAIL及H1876 Windows E0502历史首错，不用绿色回写涂销。
- 最后有真原Go/Npcap/Wintun/WSL2签名的H1877 SOURCE `9fa1724a` P2：物理50.606ms，FakeIP Direct141.030ms，+90.424ms/2.787倍，持续Tunnel UDP120/120，p99 4.283ms、双owned Stop PASS。**性能出口仍OPEN**，回程下载新增61.822ms，未有同VM旧/新SOURCE消除外界变化的可信A/B；H1867纯Tunnel CPU/GiB +9.41%另行处理。
- 下一轮应设计少量定量同VM旧/新调度与真实Wintun128 idle+少量active，覆盖超时、重连世代、密集FIN、挂起缓冲、TCP53和owned Stop，不要仅以loopback组件PASS替代D1–D5/P1–P2。Game4 CN、GUI真实Connect/Stop、WinIPv6有真实socket的控制以及其它资源满退出仍OPEN，029继续IN_PROGRESS，028/030不扩大。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1881 collect exact H1880 Windows real loopback WinSock 128 kernel socket two-active same shard PASS_SCOPED with honest non-Wintun/performance limits and action IDs."}
```
