# PLAN029 · 原生吞吐与交付效率

2026-11-21，M0 当前施工包。先 Linux ARM64 Normal/off，再 Linux x86_64、Windows Wintun/Npcap 和受影响模式。本文发布设计，产品资格待测。029/029B 的其他出口继续开放，030 未启动。

## 目的与已有证据

以接收端唯一有效业务字节为分母。提高可持续 goodput，同时降低两端 CPU 秒/GiB 和线上字节/有效字节，保护稀疏流首响应、及时交付率及空闲开销。原 Go 标准 TLS 1.3/OS 与 Rust 长寿命 owner 继续分工。独立已认证 DATA 首到即交付；新业务不等旧 PN、另一个租约、坏 lane、ACK 或 FEC 缺口。TCP-like ACK/SACK/window 和 TLS-like 外观、表演式机会修复沿用[章程](../../PROJECT_CHARTER.md)，只用原 Seq/PN 冻结密文、最多一次、已有总量与寿命边界，无持续 DATA PTO。认证/完整性、隔离、generation、防重放、真实驱动回执、[MTU 契约](../architecture/MTU_CONTRACT.md)和 owned Stop 是业务正确性边界。

| 已观测 | 改变哪个决定 |
|---|---|
| [H2236](https://github.com/lly8666/wbd-next/actions/runs/44787582885) 无损高包速时原 M4 TX 接近一核。raw 发送段中同步 syscall 占经过时间约 96%，含等待。 | 单独提高服务能力。先分清内核 CPU、调度等待与批量摊销。 |
| [H2240](https://github.com/lly8666/wbd-next/actions/runs/44839906785) GE1% 同机一流/四流/一流，Rust full 为 0/20064/14。四流 20 秒仅用 5.19 TX CPU 秒。 | 局部突发可先于平均 CPU 饱和。[整 reader 暂停](https://github.com/lly8666/wbd-next/pull/62)会把丢包搬到 TUN。 |
| [H2244 GE1%](https://github.com/lly8666/wbd-next/actions/runs/44858024963) 固定 450 降低 ARM 本地丢包，但吞吐和 CPU/GiB 都退化。[无损 x86](https://github.com/lly8666/wbd-next/actions/runs/44858243522) 固定 1200 使接收 1256→991→1247 Mbps、每批约 28→16→26，小 TCP 尾时延反而改善。 | 把服务顺序、批次和总准入分别试验。保留原版和已否决结果。 |
| [H2239](https://github.com/lly8666/wbd-next/actions/runs/44838335306) GE5% 直连与 WBD 的 netem skb 分段粒度不同，关闭测试卸载后两者比值大幅变化。 | 核实际 MSS、GSO/GRO 与双向损伤，再解释剩余差距；绝对 goodput 同报。 |

## 施工顺序与改判条件

1. **ARM64 第一增量，隔离公平调度。** 基于最新干净 main，在一条已登记短分支复用 [H2244 夹具与小流回显](https://github.com/lly8666/wbd-next/pull/66) 所需最小部分，先核原路径与旧实验差异。拒绝过的 reader gate、固定 cap 不随测试栈带入产品。原生三 netns、原 Go/Rust、真实 TUN/raw、Normal/off。在同 VM 做原 A → 候选 B → 恢复 A′。B 只改变已就绪业务的服务顺序，保留原既有速率设置、预算和 driver；租约之间公平，租约内流公平，空闲份额可借用。单包即发，有多包才批发，有界轮转；不等凑批、不停共享 reader。复用原 owner、队列与唤醒点，确需分类才增加有界状态。先 GE1% 四流叠一条稀疏 UDP 和新建小 TCP，再独立做 0% 高供给反例。若仍伤高线或 CPU，拆分定位分类成本、批次破碎与排队年龄；若公平本身足够，跳过额外调速器。
2. **独立提高服务能力。** 在入口固定时比较相同包长/PPS 下的每批已就绪数、实际 copied prefix、调用数、用户/内核 CPU 与调度等待。优化实测大头，优先去重工作、复用缓冲与原生批次。[#59](https://github.com/lly8666/wbd-next/pull/59) 的合成后端对照仅作线索，保留路由/PMTU/接口与 Stop 语义并经真实产品 A/B 后才采纳。若 TX 提速但应用无收益，沿反向内层 ACK、对端 RX/认证/TUN、应用读速找下一个饱和点；测上传和下载。每项先独测，再与公平候选组合以发现抵消。
3. **确有持续过载才加入总准入。** 原 M4 每批结算的 kernel accepted prefix、wire bytes、有效批量、活跃时间是本机服务量；每路需求、积压年龄与满丢指示入口压力。区分需求不足、本机服务饱和及下游受限。总预算按实际共享出口分配，多开流不多领租约份额。压力持续才收紧；需求仍在而积压退去，用真实流量小步向上探测，过载快速回撤。突发量由服务批次字节、MTU 和延迟预算推导，低速首包即时发。只在状态实变时用既有冷 OS owner 应用、核 generation/ifindex 和读回；无逐包 Go FFI、假探针或空闲轮询。内层 TCP ECN 要看到协商、真实标记和发送方响应；不响应的 UDP 在本租约内有界丢弃。验高→低→高和空闲→首包，能解除自身限速才采用。
4. **移植与出口。** ARM 可复现收益后，Linux x86 用本机旧新对照检查 ISA/内核差异。Windows 复用公平、批次、计账和反馈语义，使用原 Rust Wintun/Npcap 读写与唤醒、原 Go 冷管理。单 Wintun 同宿主顺序验证；按同一代际对齐实体 80–200 Mbps 与上行约 3 秒中断的 socket、TX/RX、Health/Stop。实体权限或机器缺失则保留 OPEN，先做可做阶段。验证慢/快双租约、丢旧包时另一租约新包、换代/Stop，以及受影响的 Normal Fixed/Auto、Game2/4，冗余与 FEC 独立计线上成本。跨机归因沿用无损双向 Direct ≥800 Mbps 的现有门；DERP/容量不足只作诊断。成功增量尽快集成，未验平台保持原默认。

## 参数可改，按量纲决定

可直接调大计算上不足的内部批次、缓冲或预算，可删重复的热路径检查、分配、复制与轮询。写明现值、负载假设、预计收益、最坏等待/内存与回退值；复用在入口、每批或代际已证明的条件。参数同步双方、平台、配置/文档及老配置行为。举例按 1000 B/包、1 Gbit/s 约为 125 kpps；若输入短时比服务量高 300 Mbit/s、持续 2 ms，积压约 75 kB。若出口仅 400 Mbit/s、排队目标 1 ms，可容约 50 kB，这股突发仅靠扩队列无法兼顾目标。若实际时间预算容得下且内存有界，可直接试算出的更大值。往返 400 ms、1 Gbit/s 的在途量约 50 MB，属于端到端窗口，不能直接用作 SharedTun 队列。以上是算例；产品值由真实包长/成本、租约数和尾延迟确定。

## 如何验收与停止

- 每次同一 runner/job 内顺序旧新，按项目契约分 leg/请求，保留恢复原版和短直连参考。记录准确的产品、夹具、配置、构件哈希及 run/attempt；ARM、x86、Windows 各算各自配对变化。保存机型/核与配额、内核/驱动、offload、实际 MSS、丢包注入单位与争用。原版前后漂移足以覆盖增益则记 INCONCLUSIVE，查条件；跨 runner 只比结论是否复现。冻结二进制复用，容量不足停同族重测。
- 同一观察窗记录接收有效字节、两端整机及 TX/RX CPU 秒/GiB、线上放大、每批成功前缀、队列年龄、RSS/唤醒。内核 qdisc 父子重合丢包给上下界，TUN 驱动与 Rust full 分列。小流同时报新连接首响应、已有连接 RTT、UDP 截止前到达数/全部请求、分位数和未回。160 次 echo 供筛选。分开租约 A 受损与 B 新流首到，确认 B 能独立交付。
- 测前写明本增量首要指标、旧版漂移带及可接受代价。无损高线、低损竞争各有绝对接收吞吐和单位成本。只改善一个计数、把损失挪层或以慢流饥饿换峰值则拒绝默认；有真实成本取舍按用户的性能优先级报告。每个增量只补受影响场景，累计完整资格后再推进默认。收到否证即保留旧路径和失败依据；完整出口还包括合格跨机、真实 Windows、独立小流和精确 Stop。合理候选均被配对反例否决且没有可区分的新假设时，交付约束点、负结果、可重开条件并结束该研究增量。

当前第一动作是登记并恢复 ARM64 公平候选的单工作线。历史测试证据与工具见 [H2244 汇总](https://github.com/lly8666/wbd-next/pull/65)。本文件和旧 PR 均不构成新产品 PASS。

## 2026-11-24 M0 外层机会重传专项已同步，不等于 TCP 吞吐资格

用户授权后，该实验分支已经用 [`12341395`](https://github.com/lly8666/wbd-next/commit/12341395c30b5fcafa4adb651c06f611d6b0fbe1) / [`ffb19f07`](https://github.com/lly8666/wbd-next/commit/ffb19f0744ed36da29d82701a99413be8cf8d324) 两次非强制双亲合并接收 main 的 Game Normal-v3 原密文机会式外层重传实现、源锁验证、失败试验与完整历史证据。所有本分支既有 ARM/Windows NPF/GoTCP 高吞吐、服务公平、窗口、CPU/容量研究保留，不因同源导入取得额外真实性能PASS。

专项权威收口记录：[`docs/devlog/M0/20261124-OUTER-REPAIR-SCOPED-CLOSEOUT.md`](../devlog/M0/20261124-OUTER-REPAIR-SCOPED-CLOSEOUT.md) 与 [结构化证据](../evidence/M0/20261124-M0-OUTER-OPPORTUNISTIC-V3-SCOPED-CLOSEOUT.json)。回归 CPU 只承认各自同 VM 真正配对；最终 Windows 原生共享 ReceiptState 和物理WAN仍是独立 OPEN。后续 PLAN029 仍按本文的真实业务 goodput、CPU/GiB、P99 与容量关口验收。
