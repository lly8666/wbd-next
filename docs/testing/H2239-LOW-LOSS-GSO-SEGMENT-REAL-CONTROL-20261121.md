# H2239｜5% 低丢包：真实分段粒度对照

**仅诊断，不改产品行为或默认配置**。M0 独立分支叠 PR58；不改 main、cursor 或 PR59 另一作者的原 raw socket 后端试验。

## 先区分三个故障

- 0% 本机 veth 极端过供给，Rust 单 M4 TX 约单核满载：是极限容量问题，不等于低丢包下每次失速。
- 1% 额外200ms：x86 真 Shared TUN 满队列曾有 65,760 次，但 M4 TX 20秒样本只运行约8秒 CPU；本地突发反压需要独立分析。H2237 600→250→600Mbps 虽减少本地溢出约56%，吞吐没有稳定改善。H2238 在600峰值下缩短 fq quantum、initial quantum，x86/ARM 都无稳定正向结果。拒绝以降峰值或短quantum作为产品修复。
- 5% 相同基底下 Rust 队列满丢包仅数百次，WBD交付仍低于 Direct。先查 Linux netem 对 GSO/TSO 聚合 skb 与 WBD 单独外包的实际损伤粒度；目标5%不是业务TCP独立段丢失率。不能把这种对照差异归咎于新可靠性不足。

## 真实产品与来源

基于 H2234：同一 Runner 中客户端、L3 router、服务器三独立 Linux netns；原 Go TLS 1.3 + Rust 单 owner + 真 TUN/AF_PACKET + 真内核TCP BBR + 原 iperf3 receiver-goodput、真实Stop。非公网WAN，也不是三物理机器。双向 router tc netem GE5%，固定单程+200ms，无额外 jitter。每个 case 两个出口都重新设定一个冻结 seed=22390517，实际 tc -d 读回。此 seed 只固定损伤PRNG，**Direct和WBD吞吐、流量包数不同，不等于让每个业务TCP段丢失同一个位置**。

阶段是 A (原始四张 veth tso/gso/gro 状态) → B (只在这四张临时 veth 上关闭所有 tso/gso/gro，并逐卡实际读回) → A' (恢复原状态并读回)。每阶段对同一GE5%执行20s四流 Direct 上行及 WBD 上行、MSS和重传与两出口原 tc skb/真实link TX计数。每个 WBD 用独立真实Go TLS/Rust连接generation和owned Stop。所有失败/缺指标须 UNKNOWN 或 FAIL，不能补零。

验收：显示原路网中实际 qdisc skb drop/(packet+drops)、网口 TX、业务实际交付Mbps、TCP 重传/GiB、Rust Shared TUN queue-full、CPU和rx Stop。绝不因关闭Direct offload造成Direct变慢就宣称 WBD 产品改好了。若两者包粒度更接近，下一步查剩余真同粒度差距与内层TCP恢复；另以项目既有低档FEC作独立对照。

**边界**：不改Go用户配置、默认fq600、Rust生产代码、外层TCP-like ACK10/原密文机会repair、FEC、AEAD/PN/lease/MTU；不增加Go逐包回调、第二TX或按序等待，乱序首到直接交付/no HOL永远有效。H2239本身不算产品性能提升，Windows、ARM真实跨机、Fixed/Auto/Game验证待首次证明产品修复后单独进行。

## Noble iproute2 控制能力降级（SOURCE 04718f0 的真实失败保留）

Ubuntu 24.04 自带 iproute2 6.1，其 tc netem 没有 SEED 参数。H2239 第一次真实 ARM/x86 场景在进入应用低损测试前被原生 tc 参数解析阻止；这不构成WBD失败，严禁用未实际生效的固定seed标签描述结果。修正方式为：每个出口优先一次真实设置并读回指定seed；旧 tc 拒绝后只退回相同真实 GE5%/200ms 参数而不加seed。每个案例分别明确保存 seed_status=UNAVAILABLE_UBUNTU_TC_SEED_UNSEEDED_GE、真实 qdisc 和最终接收吞吐；不允许把不同流量的随机损伤说成相同事件。未增加第三套模拟控制器，不刷seed，不更换网络模型。若看到两个出口的有效损伤口径不等，仍按不等价报告而非产品优化。

## H2239 真内核 SOURCE 9eb676f 的最终双ISA结果（2026-11-21）

[Action 44838335306](https://github.com/lly8666/wbd-next/actions/runs/44838335306) 静态、x86和ARM双原生三netns各 **6/6真TCP case+全部真实Stop PASS**。原始 artifact x86 `14679114479`，ARM `14679084613`，真实固定网口读回/每case qdisc快照/MSS和iperf均保留。SOURCE 锁定 `9eb676f220b75863ce69a2f7435c29377b4f4f1d`。Ubuntu24.04 `tc` 不支持设置netem `seed`，两方向和所有case均是真实 `UNAVAILABLE_UBUNTU_TC_SEED_UNSEEDED_GE`，**未锁损伤随机样本**。任何读回缺失不补零。

| 平台 | offload 配置 | Direct/WBD receiver Mbps | WBD/Direct | Direct/WBD qdisc丢弃占skb群比例 | Direct/WBD qdisc emitted ÷ NIC TX packets | WBD原Rust SharedTun 满队列 |
|---|---|---|---:|---|---|---:|
| x86 | 原始A | 617.092 / 131.786 | 21.36% | 0.116% / 4.940% | 44.71 / 1.00 | 1386 |
| x86 | TSO/GSO/GRO off | 241.833 / 191.870 | **79.34%** | 4.994% / 4.954% | **1.00 / 1.00** | 508 |
| x86 | 恢复A' | 704.979 / 145.203 | 20.60% | 0.120% / 5.029% | 45.68 / 1.00 | 131 |
| ARM64 | 原始A | 516.260 / 123.466 | 23.92% | 0.188% / 5.025% | 27.63 / 1.00 | 48 |
| ARM64 | TSO/GSO/GRO off | 211.883 / 178.466 | **84.23%** | 4.982% / 4.939% | **1.00 / 1.00** | 594 |
| ARM64 | 恢复A' | 622.346 / 88.201 | 14.17% | 0.150% / 5.003% | 34.51 / 1.00 | 0 |

实验中 `iperf -M1037` 的真实 `ss -tinm` MSS：x86 A 仅WBD四流里3流回读1025，x86其他 5/5 Direct/WBD所有实际case四流1025；ARM A/A中间所有有源四流1025，ARM A' Direct仅1/4回读1025其余UNKNOWN。**不篡改缺样为全四流PASS**。

真正定案：原数据把Direct的高度聚合 skb 作为netem损伤单位，WBD将分立外层IP包作为损伤单位，故“同设GE5%”并非“内层TCP经历同样损伤”。在两个架构的同机 A/B/A 中禁用分段时二者都趋近每真实网卡包对应1个qdisc计数，qdisc层目标损伤也都接近5%；因此 **存在明显的不公平测试粒度，足以解释原5% WBD/Direct巨大比例差距的重要部分**。然而 Direct关闭TSO/GSO/GRO自身从~617→242Mbps/x86、516→212Mbps/ARM，绝不能用关闭Direct的速度来宣称产品WBD加速。A/B/A中WBD自身吞吐不同也可能受随机GE样本、TCP恢复、运行顺序影响，不同原生 ISA的绝对CPU值不可比较。GSO对齐仍余 x86约20.7%、ARM约15.8%的实际接收 goodput 差距，**尚未归因**。

下一步施工优先级：保留产品原offload与数据面；把后续低损结果按真实skb/segmentation条件分类，进一步核实 **1% 本地SharedTun独立局部突发溢出** 的时间来源（低平均CPU不代表每20ms没有局部超供给），以及5% 内层TCP的cwnd、恢复停顿、正交现有低档FEC。不要借由“优化CPU”跳过确定的真丢包，也不能为快而牺牲乱序即交付/no HOL与机会式原密文重传。全部真实证据在 [H2239 JSON](../../evidence/M0/PLAN029-H2239-5PCT-GSO-LOSS-GRANULARITY-TWO-ISA-20261121.json)，当前 **PRODUCT OPTIMIZATION NOT_RUN**。
