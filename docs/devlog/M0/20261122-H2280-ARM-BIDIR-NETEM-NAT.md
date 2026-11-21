# H2280 · 纠正 ARM 中继“单向 netem 冒充双向 200ms”并真实核收双向 TCP

## 决定性恢复事实（2026-11-22）
- 仍属 M0-PLAN029-THROUGHPUT，唯一研发分支 experiment/m0-029-throughput-arm-fair、Draft PR#68；本实验只改三机测试夹具，不碰任何 Go TLS/Rust/Win driver/生产默认或产品 Stop。
- [H2276 x86 relay Action44925523352](https://github.com/lly8666/wbd-next/actions/runs/44925523352) 真双组三机七 jobs SUCCESS，但 Windows→x86 relay Tailscale **DERP** 导致干净0ms接收10.002/16.232Mbps，故产品效能归因 INVALID；CPU未被打满。原根因包含 H2276 夹具监听/命名、TCP45902 Tailscale未放行，已在更早提交修复，原 FAIL 不回写。
- [H2277 ARM relay Action44926156989](https://github.com/lly8666/wbd-next/actions/runs/44926156989) 双组各自 Windows2025→独立 ARM64 relay→另一 ARM64 server 全部原生4TCP+160小TCP成功，两个Windows→relay末次ping均DIRECT_CANDIDATE。干净无额外时延：48.577/78.444Mbps。新 [H2276 SRC3a6e648 Action44926695235](https://github.com/lly8666/wbd-next/actions/runs/44926695235) 同双ARM端组别干净0ms A/B **422.511/70.890Mbps**，200ms/0% **19.116/15.363Mbps**，200ms/1% **6.318/4.259Mbps**，200ms/5% **2.202/1.505Mbps**，Win allcore busy约2%–13%。证明VM/云/尾网的吞吐本身剧烈波动，失速非CPU打满造成。
- [H2279 source967c329 Action44927070942](https://github.com/lly8666/wbd-next/actions/runs/44927070942) 在同一组 Windows/ARM 真正原生 socket、0%/0ms先直连再中继：A Win→ARM289.574Mbps、经ARM relay97.436Mbps；B 直连108.051Mbps、经relay60.071Mbps，四条TCP每档均由ARM实际收 **100,663,296B**，Windows CPU依次14.972/6.395%、13.717/9.751%。**中继容量被显著压缩且跨组差异很大，未满足先前800Mbps高容量门**。因此这不是WBD产品吞吐数据，禁止用这些下层参考把低速直接归因给Rust队列。

## 新发现：旧 netem 回程错匹配（确定的夹具逻辑缺陷）
当前源工具 `tools/m0_h2276_three_runner_tcp.py` 的中继 `nat PREROUTING` 对 Win→relay:18727 DNAT到ARM:18727，并在 `nat POSTROUTING` 对向 ARM 端的请求 SNAT成中继IP。由 conntrack 处理回包后，**回到Windows的egress源是relay IP**（原ARM源已被reverse SNAT），但旧 `tc filter` 仍然筛选 `ip src ARM/32 sport18727`，把回程ACK/数据漏出netem。原设计只挂一条 parent1:3 handle30: netem，无独立按向计数；历史网络样本稀疏TCP P99 200–266ms而不是预计的400ms两段一程，印证**回程损伤缺失的高度可能性**。旧 source脚本显示的“200ms双向”不能继续用作产品P99合格证。其他证据仍保留原数，不伪造双向结果。

## H2280 有界可证伪施工
- 在同一真实 `tailscale0` egress 使用 root prio四band：默认band2完整不受损，Win→ARM经后NAT的ARM目标端口去band3，**ARM→Win回程用后NAT的relay源＋Win目标＋真实TCP sport18727**导band4；band3/4分别挂各自 `tc netem delay=200ms loss={0,1,5}% limit65536`，-1档独立不加延迟/丢包容量对照。
- 不止测试配置readback；每档真实 Windows2025 Winsock发4条bulk和160小TCP，**TCP数据收齐、双方netem `packets` 正增、1%/5%双方 `drops` 正增**且P50 RTT须至少350ms，否则FAIL_CLOSED为 `INFRA_UNQUALIFIED_KERNEL_NETEM_DIRECTION`，保留成功字节/负例/原始计数；不准把缺失的方向伪装为0丢包“性能优化”。
- 新workflow `qa-h2280-dual-arm-relay-bidir-netem-tcp.yml` 每次只用同一Action内相同源码的 a/b **两套各三台不同原生VM**（Win2025 client / ARM Linux relay / 另一个 ARM Linux server），所有工况两组同序 -1/0/1/5。只有明确标记 `[m0-029-h2280-bidir-netem]` 才启动昂贵六机，单测静态总执行；旧H2279动作路径仍只执行静态检查，不重复三机。直接双向内核TCP观察不等于WBD原GoTLS/Rust产品和Windows Wintun性能晋级。
- 边界：源H2279工作流仍记录干净Direct vs Relay 289/97、108/60；本次H2280才校验相同网络下真正双向200ms，后续在原同一真实组网加WBD Go TLS+Rust+Windows真Wintun/NPF，按网卡/RX TUN/M1/M4/local packet refill、必要时FEC2 small repair 和 CPU/P99 joint；禁止先大幅扩本机队列来掩盖排队。
- 真实 `tc -s qdisc` 的 `packets` 是经qdisc发出的packet，`drops` 是内核有意损伤;每档二者差分只作relay损伤证据，不冒称 WBD 应用 unique packet drop。内层 TCP retrans/接收goodput与它们分开，环境限制归环境。

```feature-impact
{"kind":"none","reason":"H2280 repairs only scoped two-independent-triple native kernel netem bidirectional topology, qdisc observed counters and strict no-silent-half-impairment qualification; Go/Rust product, Windows drivers, protocol, defaults and Stop unchanged."}
```
