# 成本、容量与验收允许带

2026-10-18 FEC v2的新k/r、期限、头部和理论残余模型见[FEC_V2_BALANCED](FEC_V2_BALANCED.md)，可复现计算器为`tools/fec_v2_model.py`。本文旧20源/56B等示例仅作旧基线，不能作V2固定常量；通用BDP/CPU/线速计账原则保留。

这里的数字是设计计算，**不是 Rust 产品实测结果**。输入与计算在 `model-inputs.json`、`tools/cost_model.py`；Actions 输出 `cost-model.json`。所有带宽先明确“应用 payload / 内层 IP / 外层 IP / Ethernet”，所有延迟明确 RTT 或单程。

## 1. 包率、窗口和内存

示例固定每方向内层 IP 500Mbps、无分片，λ=B/(8P)，V=5ms。FEC/副本/fragment 会进一步增加 record PPS。

| 平均内层包长 | records/s（off） | RTT150ms flight | RTT300ms flight | 410ms shadow 槽 | 710ms shadow 槽 |
|---|---:|---:|---:|---:|---:|
| 1200B | 52,083 | 7,813 | 15,625 | 32,768 | 65,536 |
| 512B | 122,070 | 18,311 | 36,621 | 65,536 | 131,072 |
| 128B | 488,281 | 73,242 | 146,484 | 262,144 | 524,288 |

槽已含25%暂态余量并向上取2次幂，payload按活跃数量×slab、元数据按slots计算。96B/slot包括64B hot entry、24B timer node及索引余量，是设计预算，实际布局必须测。1200B、710ms、1536B slab约**73.7MiB**；128B、710ms、256B slab约**153.8MiB**，已超过默认128MiB/方向。未含FEC、其他队列及扩容双代重叠；小包极限要选容量档或明确降低修复覆盖，不能承诺全部支持。

4096 对 500Mbps/1200B 只覆盖约 **78.6ms**；它若门控 fresh 就会限制吞吐。新架构不门控，缓存仅决定重传命中率。适量内存可以合理换恢复余量，并非“绝不能扩大4096”。对 cache hit、expiry、pressure abandonment 分别计数。

TCP seq32 在本例 off、record=1231B 时约 **67s** 绕回；FEC 增加首次发送更快。必须用扩展序号和 generation；80s 中断不能仅凭这个数认定原因，但 wrap 是必要回归。修复使用相同 seq，不额外推进 seq。

## 2. wire 带宽和 MTU

现有 TLS-like record 成本：5B 外观头 + 8B protected PN + 16B tag + 2B 内部固定字段=31B。IPv4/TCP 不带 options 时另 40B；FEC header=56B；Game 新 envelope=16B；fragment header=20B（仅分片）。真实协商 options/MSS 以实际值计算。

```
record_wire_max = min(outerMTU - IP_header - TCP_header, peerMSS, 显式record上限)
LINK_frame_max  = record_wire_max - 31 - (FEC_on ? 56 : 0)
Game_inner_max  = LINK_frame_max - 16
```

默认 outerMTU1500、IPv4/TCP各20：Normal off 内层最大1429B，FEC on 1373B；outer1400 对应1329/1273B。正常无分片不能预扣一次并不存在的 fragment20B。TUN MTU、advertised MSS、packet size 与 peer MSS 必须一起验；大包兼容走已有分片/重组慢路径，不要求 30% 高损时大包必达。

500Mbps、1200B 内层 IP：off 加独立5%损失的两次修复，预计外层IP约 **557.39Mbps**；20:20 首次发送即约 **1105.83Mbps**（还没计修复、ACK、Ethernet、Game）。所以 1Gbps 物理链路不能承诺 500Mbps FEC20:20 内层吞吐；4lane 会再乘副本。产品层若从 UDP/TCP app payload 计数，还必须加旧 platformflow 的 20B IPv4+44B service frame 等开销，不能混口径。

Ethernet 速率预算通常另计每帧 14B header、4B FCS、8B preamble、12B IFG；抓包未必包含这些。分别报告，不拿 tcpdump 字节当完整线速。

## 3. FEC、重传和多 lane 的理论门

对 systematic MDS RS(k,r)，每包独立丢失 p：一个特定源包最终没恢复的概率

`u(k,r,p) = p × P[Binomial(k+r−1,p) ≥ r]`。

这不同于“整个 block 不可恢复概率”。仍正常收到的 systematic 必须已交付。partial block 用实际 active k 和实际 r；延迟未发出的 parity、大小分类、退役、fragment、host drop 不在理想模型里。

| 线路独立 loss | 20:4 源包残损 | 20:8 | 20:12 | 20:20 |
|---|---:|---:|---:|---:|
| 1% | 0.0000761% | 约1.87e-10% | 极低 | 极低 |
| 5% | 0.1291% | 0.0001837% | 约7.04e-8% | 极低 |
| 10% | 1.9273% | 0.03871% | 0.0002266% | 约1.03e-9% |
| 20% | 14.0694% | 3.1112% | 0.2544% | 0.0002672% |
| 30% | 28.3847% | 17.6612% | 5.7724% | **0.1301%** |

共享 Game FEC、各 lane 独立损失时，每 shard 的全部副本丢失率 q=p^m，再代入 u(k,r,q)。完全相关丢失时 q=p，不能承诺任何 m 次方收益；实验必须加入相关 burst。同 lane 不同包也相关时，二项式模型不适用，使用夹具 loss trace 逐 shard 的 oracle 计算理想可恢复率。

off 的两次修复：p=1/3/5/8% 时额外首次字节约1.01/3.09/5.25/8.64%，残余约0.0001/0.0027/0.0125/0.0512%。超过预算/反馈不及时就不按此曲线强验。一个 app 包分 m 片时，可在独立残损假设下用 `1−(1−u)^m`；相关时只给 union bound≤m×u 或 trace oracle，不能硬套独立概率。

## 4. CPU 上限不是由语言推导的常数

`CPU_seconds = packets×固定成本 + bytes×加密成本 + FEC运算 + syscalls + 唤醒/队列/定时器 + 分配回收`。分阶段计数和 profile 才能定位系数，不引用“Rust 天生快两倍”。

500Mbps/1200B、双向 off、5% 两次修复，在把 TX/RX 尝试都算入的保守账本中约109,635 events/s。若预算0.7 core，平均每 event 只有约 **6.38µs**；128B 约 **0.681µs**。这是预算，不是每包执行时间实测；驱动/内核/Go 控制层都要算。CPU-s/GiB delivered 与 CPU-s/百万首次包并报，损失严重时还报 offered 口径，防止通过丢更多包降低 CPU。

Game 若旧单 lane 的可共享 FEC/LINK 占单 lane成本 f，m lane 共享的理想总 CPU 降幅约 `f×(1−1/m)`，再减协调成本。f=30%、m=4 上限约22.5%，不是75%总开销下降。每 lane AEAD/网卡收发仍要做。组件加速 s 倍、占总时间 f，整体上限 `1 / (1−f+f/s)`；先测 f 再决定优化价值。

## 5. 初始工程目标和收口规则

硬门：业务身份/内容正确，nonce 不复用、固定密文重传、generation/MTU/资源有界、新包不等缺口、状态可关闭/恢复；不因快而豁免。

性能目标（须先基线校准）：Normal/off 的目标是同机 CPU-s/GiB 下降15–25%，Game 目标按实测可共享 f 计算，不保证达到；若真实改善只有5–10%但延迟/维护成本更好，可提交证据收口，不无限追逐25%。单点小于测量噪声记 INCONCLUSIVE。只有关键或有争议的性能结论追加反向顺序配对，不每个小提交无限 A/B。

健康容量下 p99 的候选-基线允许增加初值为 `max(1ms, 测得的同 job 背景时延差+测量误差)`，这是审查带而非“自动免检”。超过带需归因；若调度噪声大到掩盖目标，记 INCONCLUSIVE/CAPACITY_LIMITED，不能扩大允许带把回归洗掉。丢包恢复尾延迟按 RTT、W、parity32ms 和 trace oracle 解释；不可把收到的包的 p99 当全部业务体验，必须同时记录未收到和超 deadline 的包。

IID5%/off 足量、反馈和缓存正常时，可把最终残余≤0.1%作为初始实用目标，比理论0.0125%留余量；burst、高相关、多片、host drop 不套用该门。FEC 理想残余为零附近时，用 Wilson 95% 区间/零事件约3/N 上界和实际 trace 校核，不能要求有限样本绝对零等于理论充分证明。p99至少约1万到达、p99.9至少约10万用于筛查，相关时采用时间块统计并报告不足。

Agent 发现门不合理必须留下：旧目标、实际输入、反例/原始统计、修正公式、建议允许带、影响的旧资格、是否触及用户硬要求。M0 审核 G2 后版本化调整；不能在同一候选偷偷改实现与判定器。只改合理性模型不要求把所有无关测试重跑。
