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
