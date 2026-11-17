# PLAN029 H1966｜真实已建立TCP连续1KiB稳态QPC，不追极端工况

## 用户优先级与最小实现
- 用户已明确不要求CN/非CN同真实CDN-IP极端反例；下一项聚焦正常连接、Windows系统/Rust分流额外微秒毫秒，**不能把建连、TCP FIN和完整事务都叫Rust开销**。本H1966按此改主线，不重新做H1958四次4MiB preconnect A/B，也不灰度提前建连（普通产品 OFF）。
- 在 **原** `wbd-platform::windows_direct_tcp::TcpDirectRelay` 添加来源受控且默认关闭的`RelaySteadyQpc`，只在已建立并注册WinSock事件的原TCP :46119 有效：实际内核 inner.recv 完成、physical outer.write 完成、physical outer.recv 完成、inner.write 完成QPC，保留每次真实读/写字节与现有ready ticket毫秒年龄；每次被服务的同一量子记录起止QPC。**写入完成不等于Linux收到**；读写等待另算非Rust CPU。
- `NativeSplitWorker::on_packet` 只在签名CI原 Wintun Source→真实Direct TCP46119 DATA包记录 Win32 同QPC：入`on_packet`、冷策略分类之后、NAT重写并转入原reverse-ready队列之后；附真实客户端源port、TCP序列号、payload长度。这是 **on_packet入口**，尚不能冒称Wintun `ReadPacket` 最早时刻，更不冒称原 RX owner `SendPacket`后内核已消费。
- 两个有界Ring均<=8192源锁行、单Stop按96行分块输出；**无每包printf、无Go热泵、无额外Wintun读线程/新WFP**；非CI普通产品所有QPC开关OFF。若drop或缺任何样本，原场景FAIL，绝不插值制造p99。

## 一条真实内核TCP流+同VM物理socket对照
- 新fixture `tools/m0_plan029_h1966_steady_tcp_qpc.py`：单源原Windows app物理socket→同WSL2内核 TCP46119，然后独立单源原Wintun FakeIP TCP46119→**同一个Linux kernel guest**，各自1条已建立连接、32条预热、**2048条1KiB stop-and-wait echo**，两臂同`TCP_NODELAY=1`。每次应用原 Windows QPC send前/send后/recv后记录，Linux每条流按ID核对**整份字节SHA/FIN**；应用数组和两条Linux物理真实内核收件报原source。只比一个Windows系统QPC频率，绝不拿Linux时钟和Windows时间相减。
- 原P2`run_p2`会先执行既有1MiB/120 Tunnel有限功能校验、owned Stop仍由**同一Go/Rust实例**完成；新fixture在旧P2完成后运行，避免新压测混入Tunnel小包和4MiB高并发。新Scene必须是`[plan029-v3-real-p2-rebuild]`＋`[plan029-v3-real-p2-steady-qpc]`，无bulk/small/preconnect/ABBA标记。
- `tools/m0_plan029_h1966_steady_qpc.py`只在**原始两端owned Stop后**分析：源/hash/QPC频率/Win客户端源port/2048个非重叠请求窗口、每窗口精确1024B原Rust Wintun，以及两腿实际各1024B接收/写入必须齐全。TCP是字节流，不按一个recv猜一个应用包；原Rust Stop没有行/队列overflow/缺阶段/跨Windows时钟 => 直接FAILED。
- 报 p50/p95/p99 原应用RTT、分流入口分类与NAT耗时、实际inner read→outer write与outer read→inner write、ready ticket粗毫秒年龄以及同VM物理Direct差。**这些仍含Windows TCP栈/线程/WSL2/guest，不能全部记为Rust成本**；尚缺Wintun ReadPacket初始、RX SendPacket内核消费、CPU专项，必须标`unobserved`。
- H1966提交本身只有新增源码/纯合成单测及工作流**待原生实测**，不以编译/Python绿色谎报任何RTT数值。先收cheap、Windows/Linux Rust编译；若原native失败，只按source锁真实stage日志修复。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add opt-in, bounded original Windows steady-state Direct TCP QPC stages and same-source 2048 x 1KiB WinSock/WSL2 kernel echo with physical baseline; normal product unchanged; actual native performance remains NOT_RUN."}
```
