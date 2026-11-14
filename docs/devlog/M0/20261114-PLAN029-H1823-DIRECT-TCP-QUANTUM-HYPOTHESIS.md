# PLAN029 H1823｜P2慢路径一次定向假设：TCP Direct relay 的单轮传输量

- 已收上轮在途结果：HEAD `03da487e2695f1610a9c8098bb5b4b82fb1badd3`，H1822 后只有证据/cursor 更新，没有待收的新SOURCE/在途网测；不重派H1820/H1821。H1820 [Action43574002456](https://github.com/lly8666/wbd-next/actions/runs/43574002456) 真签名Windows Wintun + Linux物理1MiB TCP回声 312ms，FakeIP Direct1MiB 6485ms，同时120个Tunnel小UDP交付、双方owned Stop PASS；不把某次慢误称已定位根因。P1同VM +7.42% CPU/GiB 仍 OPEN。
- **可证伪的单一假设**：`windows_direct_tcp.rs` 当前每个原始TX worker服务回合，每flow的`QUANTUM_BYTES=4096`；在H1820并发UDP下原worker的wake不超过10ms。1MiB上行+1MiB回程至少512个每方向各一段的turn，理论约5.12秒附加搬运机会，接近实际6.485s而不是证据上的精确因果。这个定量瓶颈不同于盲调CPU/防火墙。
- **仅源码单点修复**：将`QUANTUM_BYTES`及单方向排队上界由4KiB/16KiB分别调整为64KiB/64KiB，仍然每flow每轮至多一个非阻塞read/write、8flow公平轮转、无每flow线程/等待/新WFP/额外隧道栈；共享8MiB待转发预算、对应flow背压、原Tunnel纯路径均未改，队列绝不能以64MiB为延迟目标。保留容量边界单测并添加64KiB与剩余global budget相交读回。
- **本批唯一真网测**：复用原`[plan029-v3-real-p2-rebuild]`编译及`m0_plan029_h1815_p2_real_mixed.py`有界同VM物理TCP基线→Direct TCP+小Tunnel UDP及owned Stop。先冻结SOURCE并检验V3真实导出；本日志落库时新SOURCE编译、签名原生业务、CPU/p99/长流idle均**NOT_RUN**，Actions成功也不代表全部029或独立性能目标达标。若有效再针对仍未覆盖的Game4/GUI/IPv6和P1因果，不能把旧纯测重跑为交付。

```feature-impact
{"kind":"none","ids":[],"reason":"Internal bounded Rust Direct TCP relay service quantum only; no new config, GUI or public behavior guarantee. Native performance evidence pending."}
```
