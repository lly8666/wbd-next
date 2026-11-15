# PLAN029 H1897｜签名持续30+30秒直连TCP成本结算：稳定交付，但CPU归因尚不足以改热路径

- [H1896 exact signed Action43683524510](https://github.com/lly8666/wbd-next/actions/runs/43683524510) 完整SUCCESS，SOURCE 29883ab1f674840df715542540d83ae3e240e5fb，Win2025原Go+Rust／签名Npcap/Wintun对WSL2 Linux真TCP。相同FakeIP源租约一条TCP46118连续连接，每个方向先warm2s16MiB，Windows上传 **240MiB/30.173939s=7.9539MiB/s**（真Linux收齐且SHA/FIN），Linux下载 **240MiB/29.995503s=8.0012MiB/s**（原Windows真收齐SHA/FIN），原双方owned Stop及OS/防火墙恢复PASS。
- 96B真实Tunnel UDP贯穿所有测试，各端4890/4890总报文；上传窗口1996包p99 **1.061ms** / maxgap22.868ms，下载窗口1995包p99 **1.024ms** / maxgap16.019ms。快测4MiB原物理62.165ms/Direct153.993ms（本VM倍率2.477，额外91.828ms主要回传63.224ms），P2短期端到端仍OPEN。不同runner倍率不可做算法提速归因。
- 原Go+Rust**整个进程**Win32 GetProcessTimes 上传用户态0.218750s、内核态0.578125s、总0.796875s /240MiB，即用户**0.933333s/GiB**、内核**2.466667s/GiB**、总**3.4s/GiB**，单核2.6409%。下载用户态0.250s、内核态0.500s、总0.750s/240MiB，即用户**1.066667s/GiB**、内核**2.133333s/GiB**、总**3.2s/GiB**，单核2.5004%。以上均包含同期Tunnel UDP和原Go/Rust所有线程的正常工作。
- 关键辨识限制：前置同机8秒、持续UDP、尚未新建长TCP时原进程CPU速率用户0.01562395+内核0.0292949=**0.04491885 CPU秒/秒（单核约4.492%）**，高于两个连续长TCP阶段单核2.641%/2.500%。背景扣减非因果且截0；**绝不将这4个零作为“Direct TCP零CPU”**，也不能从内核时间在整个进程的占比推断内核驱动瓶颈。驱动ISR/DPC、Linux Guest、Python生成器与host-wide CPU都未测。8MiB/s是绝对限速目标，不能冒充最大吞吐或饱和吞吐。
- 原 Rust TX终结只作工作量描述：WinSock shard_wakes12966、socket枚举25924、FIFO峰值1/最大等待2ms、relay25351次、零进展11733次、内侧读WouldBlock4117/9461、外侧7599/15865、内侧写阻塞26、外侧1。持续负载下空读不少，但**原进程CPU非常低且背景波动更大**，不能仅凭计数盲目换IOCP、调队列或优化复制。保留当前单TX、16分片、双腿FD_READ架构。
- 下一步只做有限的成本辨识与环境饱和对照：同一VM、固定SOURCE、同样UDP背景，记录原进程pre/load/post CPU和host+生成器成本，再做不混杂的单因素对照；若8MiB/s尚有可靠余量，才可探索更高但稳定的定速点。最新纯Tunnel V4/V3 P1 CPU/GiB+9.41%另属独立同VM基准。差异与噪声相近则收口，不刷探索性10-20%的数字。
- 128条真Wintun已经H1892/H1895局部PASS，P1/P2性能总出口、Game4 CN、GUI Connect/Stop、真实IPv6和D1–D5仍OPEN，PLAN029 IN_PROGRESS，PLAN030未启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1897 exact signed 30s each sustained real Windows/Wintun to Linux TCP 240MiB/phase with per-phase original process user/kernel CPU/GiB and 96B Tunnel p99; safe scoped PASS, but UDP-only baseline CPU exceeds load and prevents Direct-only attribution."}
```
