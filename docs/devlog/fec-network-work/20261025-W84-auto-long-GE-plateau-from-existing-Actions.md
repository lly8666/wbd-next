# W84｜Auto 长相关突发：升档期与 Maximum 稳态业务丢包拆分（既有 Actions 产物再分析）

日期：2026-10-25。仅 FEC 岗位：`experiment/fec-network-tuning`。**此 W84 是离线证据分析编号，不是新增 Action、测试运行或产品修改。**

## 问题与核对范围

用户问：Auto 在长突发下 3.049% 残余是否基本是升档瞬态；如果到 Maximum 后仍高损，才按证据判断改法。逐字节复查原始 W81 ZIP SHA256 `d57bdf687b4dcf097d588b2966561bd0f0a36d47da6f9aae6aa53a4be00c30e0`（Action [40191033811](https://github.com/lly8666/wbd-next/actions/runs/40191033811)）；固定参照 W80 ZIP SHA256 `b0035e6581ba3a01a3851e93e3f8cae0e11603bba6b99c4f778f22ab9aea781e`（[40191030800](https://github.com/lly8666/wbd-next/actions/runs/40191030800)）及 W83 ZIP SHA256 `e64479fb524f0a3d92c4b21472cd46c97cb2e2e070b2976aef94cf07dae9423c`（[40191819998](https://github.com/lly8666/wbd-next/actions/runs/40191819998)）。三者为同一冻结产品 `7ad0ba91b656ff8e9ee965d0c093a18e048971fb`。

## 时间线和业务丢包

W81 原始 `A/impairment-events.json` 与两侧 `A/*-traffic.json` 使用同一宿主机 monotonic 时钟。以业务流量开始为 0s，C2S 长相关 GE [3,17,100,0] 丢包在 +45s 开始、+105s 结束，约 14.65% 外层丢包。Go `client-product-markers.log`：从干净前段已降至 Balanced 3，长突发开始后约 +6.4s 发出 High 4 的 **requested**，约 +29.4s 发出 Maximum 6 的 **requested**。中间约 18s 的质量观测为 UNKNOWN/缺反馈，而非伪造的干净窗口；控制器保持档位，收到新真实 VALID 才升最高档。日志给的是请求时间，原产物没有每一个 revision 的精确 native APPLIED 时间戳，不能冒称有。

以 client `tx_bins_10ms.udp` 与 server `rx_bins_10ms.udp` 做接收窗向后平移约 80ms（75ms 单程基线 + 处理），**以下均为时间窗中的 TX-minus-arrival 近似缺口，不是逐序号 cohort 精确匹配**：

| 长突发相对时间 | 发送 | 平移后的接收 | 缺口 | 估计占比 |
|---|---:|---:|---:|---:|
| +0～30s（主要升档期） | 44,082 | 41,920 | 2,162 | **4.90%** |
| +30～60s（Maximum 请求后） | 44,080 | 43,534 | 546 | **1.24%** |
| +35～55s（避开两端） | 29,361 | 28,927 | 434 | **1.48%** |
| +33～57s（避开两端） | 35,272 | 34,795 | 477 | **1.35%** |

接收平移改在 0～160ms 范围重算，主升档窗约 4.83%～4.94%，Maximum 后窗约 1.24%～1.37%，内部 +35～55s 约 1.31%～1.48%。全高损阶段权威应用分组 cohort 结果为 88,162 发、2,688 缺，**3.0489%**；对应接收分桶加总差额为 2,708，边界差与迟到不可全算成组缺失。按分桶诊断约 **80% 缺口出现在前半程、约 20% 出现在后半程**；这是归因估计，不是经精确 APPLIED/packet-ID 归类后的定论。

## 固定最高档对照：并非 Auto 独有持续问题

- W80 从头使用 Fixed Maximum6、同约 15% 长 GE：C2S **1.3412%** / S2C **1.5306%**，严格 1% 门失败。
- W83 同一 VM 同一进程 Fixed Maximum6、约 15% 长 GE：C2S **1.3207%** / S2C **1.3026%**；仅将坏状态平均持续长度从约 5.88 包缩为约 2.94 包的短 GE 段：C2S **0.2148%** / S2C **0.1997%**，短波门通过。这消除 W82 跨 VM 差异，但随机序列未固定、先长后短，不是绝对因果定理。
- W81 双侧原生 outer DATA retransmit=0；全部 FEC parity planned=sent（client262438/server112753），source TUN drops=0、RX capacity reject/codec reject=0、parity expired=0；原生 M2 真实认证正反馈存在，最终实际 revision 同请求且 pending=false。W81 CPU PSI peak 32.88%，不能断言毫无主机波动；但 W80/W83 peak 分别约 1.99% /1.98%，同样有 1.3% 残余，支持长期残余主要来自 correlated erasure 的结构而非 Auto 选档错误或单次宿主拥塞。

## 机制与可做/不做

真实 Go `r0/go_overlay/internal/realityfront/fec_v2_policy.go` 在 VALID feedback 下以 **IID binomial 残余**选档，有短突发临时加档，但并无基于可信 erasure-run 的完整相关模型。Maximum 对实际 k 使用 r=ceil(5k/4)，上限 k=16/r=20；这给的是有限冗余而不是任意长度 burst 保证。两状态稳态 GE，假设 **16 个源后紧挨 20 个 parity、擦除状态 [P=0.03,R=0.17]、理想 MDS 且全部幸存包及时接收**，动态规划模型的逐源平均未恢复为约 **1.77347%**。这只是演示“最高档即便数学完全正确也可能 >1%”的参考算例：真实 partial k、尺寸 class、多组交织、qdisc 序列和恢复窗口不与此简化假设相同；不得称为实测下界或实际预测。

最终工程判断：**W81 高达 3.05% 的主要原因是可接受的升级过渡，但 Maximum 后仍有约 1.3%～1.5% 的窄幅持续残余；并非持续 3%，也不是已证明的 Auto/codec bug。** 1% 的原始硬业务目标是 IID 30% 等代表场景，长相关 GE 此处是诊断扩展，不能因为超过 1% 而隐匿，也不能将它升级为未经授权的普适必达 SLA。当前不改外层重传、FEC codec/r、源首交或 CPU 热路径，不追加 Actions/更重负载。

若之后明确需要 **此特定长 GE 也 ≤1%**：优先补小体量每组 **真实 k、r_sent、源/parity 离开发送队列时间与截止前 RX 擦除数的有界直方图**，在受控同 VM、同负载、相同源版本附近评估不增 r 的 parity 跨块时序错峰/交织是否真能降低相关全组擦除；保证源 first-ready 立即发送、parity 10ms queue TTL、禁止 outer DATA retransmission、CPU/RSS 不恶化；如收益不够再明确超额冗余/带宽与协议 r<=20 上限代价。这是**方案假设，不是已验证的修复**；任何改动需复验 W80 类长 GE 与 W83 短 GE/低损保护。

对应结构化重算数据：[W84 artifact reanalysis](../../evidence/fec-network-work/20261025-W84-W81-auto-transition-vs-Maximum-plateau-artifact-reanalysis.json)。
