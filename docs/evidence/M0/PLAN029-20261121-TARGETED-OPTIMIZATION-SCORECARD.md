# PLAN029 · 2026-11-21 当天针对性性能优化结果账本

**结论：今天验收并进入 main 的性能增益 0 项。** main 仍是 `31ce49d`；实验分支 Linux Normal client128、Server64 与原 Go fq600 等并非本表的正式 main 变更。此前长期项目的 Linux/Windows 功能 PASS 不能充当今日 CPU/P99 的新收益，也没有同硬件原 Go-only vs Go+Rust 完整产品因果 A/B。

| 原生SOURCE/场次 | 真实结果与拒绝依据 | 今日产品晋级 |
|---|---|---|
| H2262 [ARM+x86 原Go TLS/Rust](https://github.com/lly8666/wbd-next/actions/runs/44901035146) | 客户端真实小TCP首片 offered/refused ARM 349/61、x86 312/46，定位小流受损并非只有 bulk 丢；不定位第一个 app seq/RTO | 诊断有效，P99未解决 |
| H2263 [ARM FQ250](https://github.com/lly8666/wbd-next/actions/runs/44902034107) | 对 A/A′ goodput -20.87%、server CPU/GiB +15.42%；UDP与小 TCP 入口拒绝改善，但代价过高；Action 报表 KeyError，原 Action **FAIL**，真实三腿可从 artifact 读取 | REJECTED |
| H2264 [ARM FQ300](https://github.com/lly8666/wbd-next/actions/runs/44902672857) | goodput -8.34%、server CPU/GiB +11.27%；小TCP p99 约297→94ms，却仍有 12 个小TCP入口拒绝、UDP 6/160 未回 | REJECTED |
| H2265 [ARM PRIO 双 fq600](https://github.com/lly8666/wbd-next/actions/runs/44905780854) | 原内核高优先队列真实发送503包，未降低 sparse source 拒绝或 UDP 未回；B goodput -0.83%、server CPU/GiB +1.94%、P99 漂移严重 | REJECTED |
| H2266 [ARM Rust M1 锁复用](https://github.com/lly8666/wbd-next/actions/runs/44909006431) | 208万借缓冲真实复用；goodput +0.294%、client CPU/GiB -0.235%、server +0.219%；小TCP p99 298/321/2785ms，A′严重漂移，P99没有可信改善 | REJECTED/实验代码回退 |

**可重复证伪的物理/软件约束：** 在此 Linux 单租约无人工损伤工况，四个 bulk TCP 各可按 Go 冷 fq600 每流申请供给，合计名义峰值约2.4Gbps，而当前实测接收约1.14–1.20Gbps。名义需求不是实际 offered；不可断言某单独层是唯一瓶颈，但持续高供给与本机有界服务容量相冲突。单纯优先分类和减少 M1 锁不保证高于服务容量的同租约入口不丢；固定限速以好流牺牲吞吐/CPU/GiB，因此未合入。原生 160 小 TCP 请求的 survivor p99 对 A/A′ 漂移敏感，完整 P99 必须扩大样本、记录未回和 TCP RTO，不可拿成功终回 160/160 充当及时率。

**下一次有价值的实验而非参数搜索：** 先量化原 TX M4 sendmmsg 真实拷贝前缀/每批数、内核耗时、CPU user/sys、共享 reader/M1 backlog 年龄和末端 ACK/反向流在同一个观察窗的服务能力（已有 H2256–H2261 stage 诊断可复用）。只有能区分“本机服务上限、上游持续过量、内核返压”的新证据，才选一个工作守恒且有界、不抢夺合法小 TCP 和 bulk 序列、不造成跨流 HOL 的产品假设。维持已否决 H2241 reader gate、H2242 CAKE 批次崩溃、H2254 UDP 抢槽、H2263/64 固定cap、H2265 优先队列、H2266 借锁微调负结果。Windows实体、物理 WAN、default outer1460、GE1%、3s断流仍 OPEN。

**完整证据：** `PLAN029-H2262-ORIGINAL-SPARSE-TCP-SOURCE-DROP-DUALISA-20261121.json`、`PLAN029-H2263-ARM-ORIGINAL-FQ250-TRADEOFF-20261121.json`、`PLAN029-H2264-ARM-ORIGINAL-FQ300-TRADEOFF-20261121.json`、`PLAN029-H2265-ARM-KERNEL-PRIO-SERVICE-ORDER-NEGATIVE-20261121.json`、`PLAN029-H2266-ARM-SHARED-M1-LOAN-BATCH-NO-QOS-GAIN-20261121.json`。源锁与历史失败一律不改写。
