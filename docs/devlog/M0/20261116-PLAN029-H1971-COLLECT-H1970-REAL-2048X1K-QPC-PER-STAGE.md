# PLAN029 H1971｜真 Windows/WSL2 已建连连续1KiB请求，拆出分流本身与两腿等待

**原真实Action**：[43804841097](https://github.com/lly8666/wbd-next/actions/runs/43804841097) / `native-public-two-os` job `133094854307` **success**；原 `report.json` / `mode-results/normal/client.log` 存 artifact **14197958732**；当前单一 `SOURCE=dc2d1904ee3e487b9ac307086be189a8ba053a83`，**Windows原Go/Rust源和Linux original-Go/Rust同SHA**、原signed Wintun/Npcap/WSL2及双方Stop PASS。原正式产品未启用用户流提前建连。

## 正常已建立业务，不含TCP连接/FIN期
- 同一 Windows VM、单一Wintun/Rust TX及 RX owner、Linux WSL2真实独立kernel TCP:46119，首先物理Windows socket，再原Wintun FakeIP Direct socket；每条仅一个已建连TCP流，**32×1KiB预热+2048×1KiB stop-and-wait请求回显**。物理源 `172.18.144.1:59271` → Linux `172.18.151.20:46119`，Direct源 `10.66.0.2:59272` → 原Linux物理收件源仍为 `172.18.144.1`。应用两臂各2,129,920字节(含预热)、Linux kernel 2次原收件同一SHA `0c5cfc1733c1b0e54b53e2b67a1777dc4f7d27a0e77669f625aa8d8af40fa927`、FIN及原 Stop均PASS。原P2前置的1MiB paced和Tunnel UDP120条及Stop仍PASS。
- 真实Windows `QueryPerformanceFrequency=10,000,000Hz`；原Rust Stop有**2080**条Wintun TCP payload ingress QPC（22分块）、**4160**条内核两腿正向IO service events（44分块），两个丢弃数均**0**。原分析器按客户端source port、同Windows QPC、2048不重叠应用窗口和每窗口四个kernel-leg各1024B精确联合；全部2048/2048通过。没有跨Linux/Windows时钟相减或mock收包。

| 2048次单连接1KiB Windows应用往返 | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|
| 原物理 TCP socket | 94.5μs | 132.9μs | 159.2μs | 195.9μs |
| 原 Wintun FakeIP Direct | 218.8μs | 277.6μs | 318.0μs | 536.3μs |
| Direct减physical同VM分位数差 | +124.3μs | +144.7μs | +158.8μs | 非配对不可算 |

| 原Rust **实际QPC阶段** | p50 | p95 | p99 |
|---|---:|---:|---:|
| `on_packet`开始→完成分类 | 0.2μs | 0.5μs | 0.6μs |
| 分类→TCP NAT改写且加入原ready队列 | 0.3μs | 0.9μs | 1.1μs |
| 已建立inner kernel socket读完→physical socket写完 | 10.0μs | 17.2μs | 27.3μs |
| physical socket读完→inner kernel socket写完 | 2.2μs | 3.7μs | 4.8μs |

原ready ticket年龄 `n=4096`、粗整毫秒最大0，**这不排除小于1ms的真实调度等待**。四段分位数不可直接相加/相减作为同一个请求的精确会计，物理/Direct是顺序两臂而非一一配对。此次只测一台虚拟Win+WSL2、无trace-OFF控制；Windows 10MHz QPC约0.1μs计数分辨率，亚微秒结果容易受采样开销影响。

**可操作结论**：真实`on_packet`分类及NAT不占主要额外RTT（两个p99分别0.6μs、1.1μs）；已观察到inner读取到物理写出的p99 27.3μs，属于Rust/WinSock调度组合，不是纯CPU。Direct应用p50多约124μs，p99多约159μs；但**尚未源锁标记最初Wintun ReadPacket之前/之后、RX owner mailbox及SendPacket真实返回、Windows内核消费/ACK**，不能把未观测残差归因“Rust慢了124μs”或“Windows慢了124μs”。当前最值钱的后续是这些原owner边界的轻量打点以及同源无trace控制，不再追极端同IP CDN反例。

此证据只对普通已建立小请求P2**PASS_SCOPED**，不宣称4MiB/高率/GUI/Game4/IPv6或D1–D5/P1–P2完整退出；原H1958独立真实证据和历史源保持不变。用户明确要求不深究CN/非CN共享真实CDN IP极端场景。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Archive exact signed original Win2025/WSL2 2048x1KiB steady TCP QPC, Windows physical-vs-Wintun p50/p95/p99 and genuine two-leg native stage timing; preserve all historic sources and full PLAN029 open status."}
```
