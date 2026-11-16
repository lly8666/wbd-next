# PLAN029 H2007｜原生签名 Direct UDP 事件唤醒修复真实最终收件

- 历史Agent H1988/H1991仅削减重复空WSAPoll CPU，H1989/H1990的TCP16 shard WAIT_ANY公平已有实现；此前**Direct UDP物理socket未进入任何WAIT_ANY event**。H1974/H1978真实Win QPC+应用SHA/Stop方法适合追踪最早调度边界，H1995分段吞吐同机物理对照避免误判。
- H2000源 `839e161a` 原签名 [Action43858907438](https://github.com/lly8666/wbd-next/actions/runs/43858907438) **SUCCESS**：物理/Direct UDP 96/512/1200B p99 **0.347/21.725ms、0.282/25.684ms、0.350/24.974ms**。720/720交付、全部360个Direct RTT≥8ms，包长无关，与旧 Rust TX物理UDP只有 `WSAPoll(0)` + 10ms等待、无FD_READ事件吻合。
- H2002首次事件唤醒源 `67e4cda` [Action43870817399](https://github.com/lly8666/wbd-next/actions/runs/43870817399) **SUCCESS**：只将前16个真实Direct UDP物理socket注册 WinSock FD_READ，沿原Rust TX WAIT_ANY（Stop绝对优先、TCP旧16 shards/跨组公平、35句柄上限）直接唤醒；超限保持旧10ms有界探测。原签名360 Direct+360物理同机/720总完整、Stop通过，Direct p99 **0.492/0.561/0.530ms**，物理p99 **0.421/0.345/0.425ms**。但首次版recv后ACK可能清除连续排队FD_READ，不作为最终产品收件。
- H2005修复 `WSAEnumNetworkEvents` 先确认再单次非阻塞recv，避免一个socket两包排队时丢第二次FD_READ（微软官方语义：FD_READ level-triggered、recv re-arm）。Windows真内核双排队UDP事件及Linux Rust组件 [Action43871804541](https://github.com/lly8666/wbd-next/actions/runs/43871804541) **SUCCESS**；最终同源真实Win2025/WSL2签名 [Action43871804786](https://github.com/lly8666/wbd-next/actions/runs/43871804786) **SUCCESS**：原WinGo/Rust/Wintun/NPF/Linux真实kernel、720/720唯一、零丢无错、DNS唯一、双方owned Stop PASS。
- H2005最终同VM物理/Direct **p99**：96B **0.312/0.771ms**（Direct max4.457ms）；512B **0.302/0.427ms**（max0.457ms）；1200B **0.292/0.451ms**（max0.490ms）。**360/360 Direct低于8ms**，全三包长p99<1ms。单个96B max4.457ms保留真数据，但不再为一条波动做盲目调参。新旧源不同VM，仅判断几十毫秒→亚毫秒显著改善，不作精确微秒级因果。
- H2006修旧H1940静态断言，既保留原Stop/TCP公平又核对总≤35句柄，[治理Action43872068538](https://github.com/lly8666/wbd-next/actions/runs/43872068538) **SUCCESS**。此前失败Action原样保留，不删除历史。
- **取舍：就此停止UDP性能调优**。小TCP已有physical/Direct p99 0.410/0.699ms仅+0.289ms，不值得本轮过度优化；4MiB unpaced 51.970/97.260ms还是单独OPEN；H1974历史5×61ms TCP长尾同样仍OPEN，不从这次UDP结果抹除；PLAN029整体 IN_PROGRESS。绝不加入新极限压力、逐flow线程、改DNS/MTU/数据面协议。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2007 records independently signed H2005 direct UDP event-wake sub-ms p99 and both owned Stop in feature summary without new product implementation changes."}
```
