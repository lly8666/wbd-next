# FEC-only V3 公共代码合并与原生 ARM64 代表验收报告

**更新：2026-10-24。分支：** `experiment/fec-network-tuning`。**适用产品源码：** `b601f2e546bf5f071eb33a80a01beec71d91c5cf`，原生 ARM64 build Action [40078403217](https://github.com/lly8666/wbd-next/actions/runs/40078403217)、bundle artifact `12554277143`、ZIP SHA256 `552a9c19ca4b9045cabe08abeed4f80e440f73f8fcc34a5f06670f4450d9fde6`。以下实际产品运行 W3–W7 均复用这同一 SOURCE 构建的冻结二进制，夹具请求源码各自独立。

## 合并和边界

V3 双亲合并 [1a04e791](https://github.com/lly8666/wbd-next/commit/1a04e791d28d860107f31bcfe463846cf3f5c2ac)，第一父 `9cfd72968e21a63834f455a96afc71a5d35737db`、第二父网络冻结 `040741820b2f917b5868c285c438d4cc21c6193a`，共同祖先 `45325c9c965e56080f2035bafcf235aa02a1a6c0`。保留网络 V3 公共数据通道、机会式 DATA 修复、半量独立 frozen ciphertext shadow、首发 F 字节账本、批量预算、统一 MTU、真 TUN 与产品自有 fq600/flow_limit256；仅在原公开 Go CLI→bridge→native owner 实装 `--outer-repair=on|off`，默认 ON 不退回 v2。OFF 不建立修复候选和密文副本、不重发外层 DATA，但保留真实 M2/FEC feedback、DATA 首发账本、FEC source/parity 首发。Linux public Game OFF、Windows GUI/系统不在此次产品资格内。没有覆盖原网络岗位进度、请求或合并 main。

最小 Fixed/Auto applied 修复 [b601f2e5](https://github.com/lly8666/wbd-next/commit/b601f2e546bf5f071eb33a80a01beec71d91c5cf)：只将「整个 2s 观察窗零 UNKNOWN」的过严 *档位 applied 证明* 改为「原 M4 已复制 source+parity、同代际 revision，且有成熟 authentic unambiguous positive receipt、无容量审查」。UNKNOWN 与 censored 质量仍保留原义、不伪造成零损或 ACK。原生 ARM64 maximum-row/回执单测 [40078693263](https://github.com/lly8666/wbd-next/actions/runs/40078693263) 和 harness contracts [40078693315](https://github.com/lly8666/wbd-next/actions/runs/40078693315) 通过。

## 实测：功能及成本

| 场景（每个性能 Action 一个测量 job） | 两端真实 native/应用事实 | CPU / 内存 / 首次交付 | 资格 |
|---|---|---|---|
| W2 [40077795567](https://github.com/lly8666/wbd-next/actions/runs/40077795567)，旧合并 SOURCE `1a04` | Outer OFF 双端零 DATA retransmit/候选/shadow；FEC 确认交付 TUN 恢复 532/518；Fixed 一侧 `applied=0,pending=true` | CPU 1.87/1.94 CPU-s，RSS 约19.9/19.5 MB | **FAIL 原反例，历史保留** |
| W3 [40078693282](https://github.com/lly8666/wbd-next/actions/runs/40078693282)，Fixed5 0→5% IID，双向各2Mbps，单程25ms | 两端 `requested=applied=1`、pending=false、outer OFF/0 retransmit；Recovered TUN 521/519，IID5 应用缺失 0/0 | p99 41.3/44.3 ms；测量 CPU 1.66/1.67 CPU-s、RSS ~19.9/19.7 MB | **PASS_SCOPED** |
| W4 [40078980002](https://github.com/lly8666/wbd-next/actions/runs/40078980002)，Auto clean 各2Mbps | 两端 `requested=applied=1,profile5`，outer OFF，真正 parity 首发；无业务缺失 | p99 25.3ms，测量 CPU 1.03/1.03 CPU-s | **PASS 启动强档，不代表动态 Auto** |
| W5 [40079244149](https://github.com/lly8666/wbd-next/actions/runs/40079244149)，Fixed 最大档，真实IID30%/one-way300ms，双向各12Mbps、线路各50Mbps | 两端 profile6 applied1；outer OFF 0 retransmit；恢复并交付 TUN 27,035/27,247；C→S 缺57包，S→C 缺45包（业务残余0.081%/0.064%） | 首次到达 p99 315.3/315.2 ms；CPU 7.92/7.84 CPU-s，RSS 22.4/21.9 MB；无源 TUN drop | **PASS_SCOPED，高损代表容量足够，不加压** |
| W6 [40079302195](https://github.com/lly8666/wbd-next/actions/runs/40079302195)，Normal V3 ON→OFF，同 job/同 ARM64 VM 顺序 AB，双向各2Mbps、IID2% | ON 真实 repaired DATA 131/127、repair wire 147322/150339B，缺失 95/90；OFF 两端 0修复、0候选、0缓存，缺失212/182。两组各单独 TUN/Stop，无重复测量 job | ON CPU总观测 1.39/1.43s、p99 25.5/25.4ms；OFF 1.29/1.32s、p99 25.2/25.2ms。观测级同机比较，不作严格因果提速宣称 | **PASS 默认ON及真实OFF保护** |
| W7 [40079564452](https://github.com/lly8666/wbd-next/actions/runs/40079564452)，Auto 非对称 2/0→20/1→1/0%，双向8Mbps、单程75ms | high C→S缺10包（0.021%）、S→C缺0；TUN恢复 client511/server10929，outer OFF/0 DATA repaired。两端始终 profile5、revision1，无在线升降档 | high C→S p99 92.9ms；CPU 15.53/15.16 CPU-s；RSS ~21.3/20.7 MB | **PASS 业务/静态Strong，动态Auto FAIL/NOT_WIRED** |

所有总量都是原生 CPU/主机观测或应用收支，不把 CPU-s 等同单核利用率，不把净损伤率当业务缺失率；W6 AB 非复现同一损伤随机序列。Linux kernel fq600/flow256 的真实产品 owned TUN readback 由网络冻结点原验收及本合并后 harness 继承；W3–W7 未重新声称 Windows fq。

### W5 理论与完整性解释

按系统性 MDS 码、独立损伤和幸存分片及时到达，单源残余 `p × P[Bin(k+r−1,p) ≥ r]`。最大档真实发送 parity，理想 p=30% 时：`k=16,r=20` 为 **0.022826%**；`k=8,r=10` 为 **0.380782%**；`k=4,r=5` 为 **1.73903%**；`k=1,r=2` 为 **2.7%**。W5 每侧约 `5442` 个满组 `k13..16`，但另有 `k=1` 2501/2372 组，且小 partial 组不会有和大组同样的容错。实际确切 `k=2..4,5..12` 目前仅桶聚合，不能虚构精确逐 k 理论或用“收到的 r”替代发送 r。该场景实测双向残余小于 1%，不是理论零丢包。

## 未完成与平台边界——不得误标全绿

1. **Auto 真动态控制仍未接线（功能未过）。** Go `v4ProductFecMonitor.start` 在首次 mature ACK 后直接退出；W7 两端 profile5/revision1 在 20% 高损和降损后均不变化。不能因 W7 业务残余很小就宣称上行、下行独立 profile 升降档通过。下一实现须从同代际真实 firstsend mature windows、actual-k/host censor 形成可信 `FecV2Snapshot`、执行 2s profile 决策、在不撤销旧块的 quiescent 边界 stage 新 native revision，且双端真实 readback。已有 `fec_v2_runtime_controller.go` 与 `FixedStream::quiescent_change` 可复用；尚不能把线损 netem 值或 FEC recovery outcome 当伪样本。
2. **RTT 读回边界。** OFF 有真正 `V4_PUBLIC_FEC2_M2_PROOF.reverse_reports`，W5 client14735/server14773，W7 client29832/server25487；但是外层 shadow RTT `timing_samples=0,srtt_us=600000` 是关闭修复后的默认诊断，不是实际测得的 FEC-only RTT。需要独立真实 M2 confirmation-latency/RTT 低开销读回，不要为填数字造 shadow/cipher cache。
3. **确定性缺源恢复的合并 SOURCE 专项仍未复验。** Rust codec/stream 单测及 `r0/go_overlay/internal/realityfront/bridge_v4_live_fec2_kernel_linux_test.go` 有相关已存在的精确缺源、真 parity、内核 TUN 交付测试源；本次未在合并后 b601 对该专门确定性测试跑 Actions。W3/W5 是 *真实有损 FEC recover-to-TUN 正例*，但不冒充可复现指定某 PN 丢失。认证、generation、replay、MTU、Stop 均在当前公共系统约束内未削弱。
4. **未测试：** 多业务极限 HOL、Windows 产品、Game+FEC 动态、物理链路、未知更高单核容量边界、全 k 档逐组概率的精确对应；不再放大容量压力。原网络独立已知混合 RX 问题属于 COMMON_PATH、不能由 FEC 收据覆盖。

**交付资格：** 合并 V3、真实外层 OFF、Native Fixed5/Maximum 及默认 V3 ON 保护已形成可复用、可审查的单分支**限域合并候选**；**完整用户 FEC Auto 目标未验收，故整体 `merge_ready=false`，不自行合入 main。** 不应重复跑已通过的 W3–W6 或旧 `7ad7e0e1` 二进制。继续工作必须针对 Auto 真实观测/安全在线修订与独立 RTT 证据，而非原网络岗位 `next_action`。

## 2026-10-24 Maximum50 容量修复专项补充（Auto 仍未完整通过）

最新独立 RX source `ec344557fa8cbf4d717a81833d36f92584263478`：原生 ARM64 build [40087393299](https://github.com/lly8666/wbd-next/actions/runs/40087393299) + deterministic actual parity-to-TUN 单测 PASS；[W13 单场景](https://github.com/lly8666/wbd-next/actions/runs/40090193642) 真 50Mbps/方向 30% IID 300ms，双端 delivered49.985/49.990Mbps，残余0.0517%/0.0496%，native Fixed Maximum profile6 两端 applied，outer DATA repair=0，RX decoder reject0/0，FEC recovered TUN67115/66417，CPU12.54/12.67s、RSS29.7/29.6MB、p99 304.6/304.7ms，源 TUN/root qdisc drop0。RX bounded 96 blocks/8MiB，原 age150ms、reorder span128，峰值57/58blocks、约1.9MiB，Stop typed error counters齐全。[专项证据](20261024-W13-max50-scoped-PASS-and-W12-AB-boundary.md)。

**独立单次 W13 PASS 并不覆盖 [W12 同VM顺序 AB](https://github.com/lly8666/wbd-next/actions/runs/40089406842) 的 B 单向 C→S 12.23% FAIL**；后一收据含 client veth 286.9MB，W13 client326.3MB，虽两次 FEC RX 拒绝和 native M4失败均为零。顺序效应/本地出口节奏尚未归因，需另行验证才能声称全场景性能可靠。75Mbps历史失效依旧，100–200Mbps未测；Auto 真升降档仍未验收，保持 `merge_ready=false`、容量停止继续。用户要求暂时收口，本轮不再刷全绿或扩压。


## 2026-10-24：后续逐档 75→100Mbps 验收与硬容量边界

分支 `experiment/fec-network-tuning`，冻结新原生源码 `ec344557fa8cbf4d717a81833d36f92584263478`，ARM64 产品 build Action [40087393299](https://github.com/lly8666/wbd-next/actions/runs/40087393299) artifact `12558215058` SHA256 `bd22744ae29bcb0ec8b57cba9bdcc7b10228911e9af628791501ff7623b008d3`。沿用已真实 applied 的 Fixed Maximum profile6；双端 outer DATA repair OFF 且 parity 首发独立，双向 30% IID、300ms 单程、99% 1287B/1%64B、15s warmup+30s measurement+30s drain、每档一个 Actions 测量 job。线路 cap 取业务带宽4倍，是避免外线路自己限死高吞吐，不代表保持同一外网 cap 的吞吐曲线。原 W12 同VM AB 第二段本地出口丢量异常**仍未解释**，本报告为 standalone 观测，非连续运行保证。

| 每方向业务档 | 实际交付 C→S / S→C | 首次p99 | RX peak slots(客户/服) | RX pressure eviction(客户/服) | 判定 |
|---|---|---|---|---|---|
| 50 Mbps, netem cap200 | 49.985 / 49.990 Mbps | 304.6/304.7ms | 57/58 | 0/0 | W13 [PASS](https://github.com/lly8666/wbd-next/actions/runs/40090193642) |
| 75 Mbps, cap300 | 74.967 / 74.979 Mbps | 303.5/303.5ms | 83/83 | 0/0 | W14 [PASS](https://github.com/lly8666/wbd-next/actions/runs/40091124249) |
| **100 Mbps, cap400** | **99.956 / 99.968 Mbps** | **303.1/303.1ms** | **96/96（等于硬上限）** | **29,425/29,425** | W15 [业务 PASS、RX 容量触顶](https://github.com/lly8666/wbd-next/actions/runs/40094982877) |
| 125 / 150 / 175 / 200 Mbps | **未测** | — | — | — | **W15容量不足停止加压，不得编造** |

W14真实 75Mbps netem 损伤29.948%/30.011%，业务未到119/92包，FEC recovered-to-TUN 客户99625/服99396；RX peak bytes2.84/2.87MiB；客户/服测量CPU16.79/16.93 CPU-s、RSS34.44/35.10MB，宿主CPU PSI峰值14.33%，outer retransmit0、源TUN drop0、Stop drained。Action 产物 `12559275827` digest `b897193008c3203ca9014d826b27bc1a306261d1d7e298eb35c5db7ce819fad7`。

W15真实 100Mbps netem 损伤29.940%/29.855%，业务未到191/150包，FEC recovered-to-TUN 客131785/服132456，实际 parity 接收388371/388503；RX decoder_rejected0/0、reject_capacity0/0、拒绝Codec0/0；RX peak **96/96、pressure_evicted29425/29425**，内存字节峰值仅3.606/3.606MB（小于8MiB）。因此第一明确的硬容量是**活跃block槽位**；`pressure_evicted` 指本地旧组状态的容量性淘汰，不等于实际丢失了同数业务包（业务仍然PASS）。客户/服测量CPU19.40/19.54 CPU-s、RSS39.69/39.92MB、PSI峰17.76%；Source TUN drop0、外层 DATA 重传0，Stop drained。Action 产物 `12559509835` digest `877d3177d03268adc325aa1aa8b5e418d597c8d1ac223f9030671a683a721175`。

**结论：** 这一版 FEC-only Maximum 至少可在独立 Action 中达到双向各 **100Mbps 业务交付接近100Mbps**，但在 100Mbps 已遇 96块接收槽位上限的明确瓶颈。按照逐级容量规则立即停止更高档位；*不能*声称200Mbps已测或瓶颈实际发生在200。若未来继续性能优化，只在 FEC RX 有界维护处测算 active-time 与流速、最小扩槽；修复后重新构建精确 SOURCE，先原100Mbps反例及相关保护，再放行下一档，而不是直接盲加负载。W12原相同 VM AB 异常和 Auto 真动态另行未完成，`merge_ready=false`，未改网络岗位 status/main。


## 2026-10-24：用户授权继续350Mbps，但原生RX扩容后100Mbps业务复测未过

所有档位为每方向 UDP业务、99%1287B/1%64B、IID损伤30%、300ms单程、Maximum6、外层 DATA repair真正 OFF、15s warmup + **30s实测** +30s drain。各档位外层线路cap设为业务的4倍（100业务cap400），避免让线路速率天然卡死FEC冗余。用户要的「真实外层带宽，连重传都算」使用两个方向原始虚拟网卡 TX 字节差值 ×8/30s，包含首发、FEC parity、真实DATA重传及控制/反馈，不额外加任何子项。**这是网络namespace下 netem-veth interface TX 账本，不等于物理L1总字节，也不是分母45s的 native first_wire_bytes。** 数据已在各自 Action 的 `measurement_cpu.outer_tx_bytes/outer_tx_mbps` 和原生数值里。

| 来源 | 业务 Mbps/方向 | 业务交付 C→S/S→C Mbps | CPU-s 客户/服（30s） | RSS峰 MB 客/服 | 真实外层 TX C→S / S→C Mbps | 双向合计 Mbps | 原生 outer DATA repair | 判定 |
|---|---:|---|---|---|---|---:|---|---|
| [W13](https://github.com/lly8666/wbd-next/actions/runs/40090193642) RX96 | 50 | 49.985/49.990 | 12.54/12.67 | 29.72/29.57 | 87.006/86.884 | 173.890 | 0 | 单档PASS |
| [W14](https://github.com/lly8666/wbd-next/actions/runs/40091124249) RX96 | 75 | 74.967/74.979 | 16.79/16.93 | 34.44/35.10 | 130.329/130.180 | 260.509 | 0 | 单档PASS |
| [W15](https://github.com/lly8666/wbd-next/actions/runs/40094982877) RX96 | 100 | 99.956/99.968 | 19.40/19.54 | 39.69/39.92 | 173.655/173.827 | 347.482 | 0 | 业务PASS，96/96压力29425/端 |
| [W16](https://github.com/lly8666/wbd-next/actions/runs/40097487779) RX640 | **100** | **94.579/99.979** | **18.57/18.15** | **40.13/40.14** | **164.164/173.350** | **337.515** | **0** | **业务FAIL，RX压力=0** |
| 125、150、175、200、225、250、275、300、325、350 | — | **未测** | **未测** | **未测** | **未测** | — | — | W16 100业务失败，遵守 stop-on-first-failure |

W16真实 netem损伤29.984%/30.015%，业务C→S注入99.99863Mbps、交付94.57897Mbps、丢15993包；S→C注入100.00206、交付99.97866Mbps、丢129包。p99 303.1/303.2ms。FEC RX peak109/109 of640、bytes峰3.829/3.775MiB of48MiB，**pressure_evicted0/0、decoder_rejected0/0、reject_capacity0/0、reject_codec0/0**。真实FEC恢复到TUN client132655/server127783，源端TUN drop0、outer DATA重传0、native M4 source+parity非copy0，FEC parity rsent client554439/server554434，Stop drained。CPU PSI峰16.5%，没有CPU/内存高压抢占证据。W16产物 artifact `12561303555` SHA256 `0cc77ea7e6cc55bed5f1adacbd554bf90be64944b419996eadba2a92597e4d94`。

**分离不同时间窗的首发与重传真账本：** W16 native `V4_PUBLIC_M2_OUTER` 记原始首发账本（含 native 首次DATA/parity及相应record的独立 owner policy）client **1,376,830,446 B** / server **1,376,844,261 B**，覆盖 warmup+measurement **45秒**，平均 client244.770Mbps / server244.772Mbps；**实际 outer repair accepted=0B，uncertain=0B、retransmit copied=0**。这45秒首发 ledger不能与30秒 netem-veth接口 Mbps相加。外层网络 qdisc/netem记录约30%随机损伤，其中部分包被丢弃，真实送达接口TX数值不同；没有证据支持把整个差额称为物理线路限速、FEC codec错或CPU瓶颈。

**关键：** 与历史 W12 的同 VM 后段类似，W16在原生发送计数两侧接近（FEC rsent 554439/554434、原生 45s firstwire差不到14kB、双方注入均100Mbps）时，**客户端真实外层 egress 164.164Mbps，服务器173.350Mbps**，且接收服务器收到 source/parity 相应偏少。没有串行重传；旧 W15 单跑100Mbps双向通过，但新W16 100Mbps单跑出现显著非稳定性。已排除新RX slot压力，不可断言无证据的具体网络丢包根因。

**本轮收口条件：** 先修复或界定100Mbps可重复业务收支和 M4复制→netem接口送出差；不继续发125–350请求，不用刷种子掩盖回归。测试范围未涉及物理链路或任意重传ON，Auto动态和W12已知异常继续独立OPEN；`merge_ready=false`，没有更改上游network岗位。


## 2026-10-24：W19–W23 单向IPv4邻居根因及150Mbps首个性能拐点

**已确认根因范围：** W19 Action40100361068在 S2C 单向丢12.25%期间，服务端原生TUN依旧吞入约4900包/500ms、Rust M4 kernel copied持续，但服务端 veth/netem TX停止2.5-3秒，内核ARP peer NUD=INCOMPLETE探测4→6后REACHABLE时立即恢复；客户方向正常。内层wbntun0的原fq maxrate600Mbit flow_limit256仍启用、无TUN source/root fq drops。直接连接的实验veth对在root netem下让**ARP管理帧一起遭遇30%随机丢包**，因而使Linux邻居解析阻塞真实IP业务，即成功sendmmsg到netem接口之间的内核链路停顿。这是实验链路L2控制面的问题，不是 FEC source/Parity 计算失效或 fq600 的因果堵点。

最小修复提交87846904只改**测试专用** config/runner/合同：strict opt-in owned_veth_static_neighbour，默认false；仅在两个临时namespace安装彼此真实MAC的PERMANENT邻居，双向readback，不碰host sysctl、路由、生产产品、fq600或FEC数学；DATA和Parity依旧经过同样netem30%丢包与300ms延迟。W20 Action40101978371 500ms采样两端邻居PERMANENT各130/130、业务PASS；W21 Action40102339446关闭采样在原fq600下也双向PASS。原 W12/W16的类似出口中断仍保留旧失败数据，不直接断言所有实例都因ARP而失败。

| 原生Action | 业务Mbps/方向 | 真正交付C→S / S→C Mbps | 真实外层TX C→S/S→C Mbps | 总外层Mbps | CPU客户端/服务端 CPU-s (30s) | RSS峰客户端/服务端 MB | 残余/压力结果 |
|---|---:|---|---|---:|---|---|---|
| [W19 40100361068](https://github.com/lly8666/wbd-next/actions/runs/40100361068) 动态ARP | 100 | 99.965 / **87.746** | 173.311 / **152.439** | 325.750 | 18.22 / 19.28 | 39.71 / 39.88 | **FAIL: S2C NUD INCOMPLETE** |
| [W20 40101978371](https://github.com/lly8666/wbd-next/actions/runs/40101978371) 静态邻居+只读500ms诊断 | 100 | 99.969 / 99.985 | 173.549 / 173.523 | 347.072 | 19.79 / 19.62 | 40.40 / 39.93 | PASS，双端PERMANENT130/130 |
| [W21 40102339446](https://github.com/lly8666/wbd-next/actions/runs/40102339446) 诊断关闭 | 100 | 99.984 / 99.976 | 173.413 / 173.439 | 346.852 | 20.19 / 20.18 | 40.06 / 39.95 | PASS，RX pressure0 |
| [W22 40102622202](https://github.com/lly8666/wbd-next/actions/runs/40102622202) | 125 | 124.961 / 124.940 | 216.869 / 216.578 | 433.447 | 22.28 / 22.42 | 45.19 / 45.13 | PASS，CPU PSI>20占83% |
| [W23 40102994265](https://github.com/lly8666/wbd-next/actions/runs/40102994265) | **150** | **148.869 / 148.893** | **254.056 / 254.237** | **508.293** | **24.20 / 24.33** | **50.23 / 50.42** | 业务PASS**但性能拐点，停止加压** |

这些外层 TX Mbps来自各方向 netem-veth **30秒**接口真TX bytes差值×8/30，已经包含所有实际首发DATA、FEC parity、控制/反馈及任何重传（所有这些FEC-only样本真正original DATA retrans=0包/0B）；这是该层虚拟接口口径，不是物理L1线速。不能再加45秒native first_wire_bytes做总占用。

**为什么W23停止再上负载：** 150Mbps真实netem损失 client30.039/server29.958%，业务残余C2S0.754%、S2C0.738%（仍在1%门槛内但已无余量），p99 311.0/310.9ms，比125Mbps 306.1/305.8ms高约5ms。RX峰163/640、存储5.83/5.85MB<48MiB，解码拒绝及压力淘汰仍是0；TUN/root源端0丢包。但宿主CPU PSI峰**30.62%**，30秒样本超过20%占**100%**。FEC native计划的Parity行 client830246/server830265，M4确认rsent client800359/server799115，未发送缺口分别29887(3.60%)和31150(3.75%)，而125Mbps缺口client1358/692474≈0.196%、server1385/692502≈0.200%。150Mbps存在显著的期限内Parity调度/算力余量信号，原始原生 `unknown_capacity` client2983/server3054、`parity_seal`失败48/63需另案拆分；不能将计划差额等同于业务实际丢包，或用CPU PSI单独断言哪一个线程是根因。W23原始result artifact12563149315 digest f64b606746b3a7b317e81fb5fb8849447ceed1cc21607624508743567c01f9c4。

**停止条件：** 用户要求仅当未遇瓶颈才继续推向350；现于150出现Parity按时交付和宿主CPU调度压力，故175/200/225/250/275/300/325/350全部NOT_RUN（不是失败性能值）。后续若继续，先对 native TX parity deadline与各线程CPU/内核出口作窄域测量，保护优先发送原始DATA、真M4复制、有限内存及Stop；不要扩大队列导致延迟增大，也不要无证据调整产品fq600。Auto动态完整验收另行未完成，merge_ready=false；未合并main、未改原网络岗位状态。

## 2026-10-24 W24：150Mbps 旧/新同 VM 原生系数表复用 AB — 双腿未过容量门

独立 FEC 代码提交 [cf00a47c](https://github.com/lly8666/wbd-next/commit/cf00a47c9564d67b15409d50178a956416227a8a) 仅改动 `fec_v2.rs` native ISA-L 跨块不可变系数表缓存、单元等价测试及 ARM64 构建验证；静态槽位 `k∈[1,16]` × 20 × 4（最多 1,280），合法 native 表数据合计上限 777,600B，绝不缓存明文或 AEAD PN。源码没有增大队列或延长首次 DATA。新 SOURCE 构建 [40105262367](https://github.com/lly8666/wbd-next/actions/runs/40105262367) **SUCCESS** (产物12564910143，ZIP SHA256 `39809b55b380b4a161f47b367f734c2e45efa526efc36817e3ac6eb500c21d03`)，真实 ISA-L 跨块完整 Maximum 20 行与 oracle 对照2个PASS，固定及 Auto 的原 Go TLS→FEC→TUN 真实缺源恢复内核回归均 PASS；Maximum 原生行合同 [40105262390](https://github.com/lly8666/wbd-next/actions/runs/40105262390) PASS。

**性能 Action** [40105506052](https://github.com/lly8666/wbd-next/actions/runs/40105506052)，一次请求 `W24-maximum150-native-shared-tables-AB-arm64.json`，**同一 ARM64 runner 同一测量 job 顺序 A 再 B**，复用原冻结 A SOURCE `6b08527d` 构建40099179830和新 B SOURCE `cf00a47c` 构建40105262367；每腿 15秒预热＋30秒测量＋30秒排空，双向150Mbps，固定 Maximum6，30% IID 未固定种子但观测到 29.96–30.05%，300ms 单向，原始 owned TUN fq600、测试专有 veth 永久邻居、修复开关实际 OFF 和反向真实反馈保留。产物12564980324 SHA256 `cf2ba13a6a7876ba186f42fd424845bbc49b3a4c870137a3a10158204c581d98`，harness contracts [40105506150](https://github.com/lly8666/wbd-next/actions/runs/40105506150) PASS。

| 口径 | A旧源 | B系数缓存 |
|---|---:|---:|
| C→S 真交付 / 残余丢包 | 146.817Mbps / **2.153% FAIL** | 147.576Mbps / **1.642% FAIL** |
| S→C 真交付 / 残余丢包 | 146.376Mbps / **2.453% FAIL** | 147.302Mbps / **1.826% FAIL** |
| client Parity `rplanned / rsent` | 830151 / 749061 (9.77%缺口) | 830055 / 763348 (8.04%) |
| server Parity `rplanned / rsent` | 830134 / 737230 (11.19%) | 830127 / 754905 (9.06%) |
| client/server `queued expired` | 915 / 1102 | 817 / 882 |
| client/server `unknown_capacity` | 7679 / 8708 | 6295 / 7145 |
| client/server 30秒 CPU秒 | 23.91 / 24.46 | 23.98 / 24.32 |
| client/server RSS峰 MB | 50.57 / 50.36 | 49.39 / 49.71 |
| C→S、S→C p99 | 311.3/311.3ms | 311.2/311.2ms |
| 宿主 CPU PSI峰 / >20%样本占比 | 27.55% / 100% | 31.78% / 100% |
| 源TUN丢包、RX容量淘汰/codec拒绝、外层DATA重传 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

**判定：** 新 native ISA-L 表复用的 *功能* 合格，但改善幅度仅每方向约 0.76/0.93Mbps 与 parity 缺口1.73/2.13百分点，进程总 CPU 无显著下降；B 宿主 PSI峰更高。**A/B两腿均不能满足≤1%残余门限，禁止把旧 W23 单点 PASS 当作150Mbps可重复资格。** 原生45秒 Parity累计不可与30秒净业务包数混作相同分母。无 BA、未固定netem及共享主机容量拥塞限制因果判定；性能收益 *观察到趋势*，不能宣称严格归因。先定位10ms关闭后作业有效期内的逐量子 CPU/M4排队时间，不能仅因 `unknown_capacity` 字段名就增加接收缓存；在无新增原因前不再测175–350Mbps。自动档全动态阶跃/非对称与测量真实RTT年龄独立OPEN。**merge_ready=false**；不改原网络岗位的恢复算法及进度。


## 2026-10-24 W25：Parity 两个4行量子共用一次M4，150Mbps新源码限域通过

针对 W24 150Mbps 每侧失发 Parity 8–11% 和每秒910+个满块的 5 次 sendmmsg/结算，FEC-only 原生修复在一次 owner turn 先密封所有新 DATA，再只在空余≥8个M4 record槽时将**同一个** ParityJob 的两个≤4行原生M3量子一起密封，原生 M4 同一 syscall 按PN顺序归责；否则仍使用旧的≤4行单量子。代码 commit [aab45f7c](https://github.com/lly8666/wbd-next/commit/aab45f7cc304c09065e3614d0b5c61cff2097b56) + [ab7ea894](https://github.com/lly8666/wbd-next/commit/ab7ea894100f245d6a510137282736781bd017ce)（首个编译尝试原 Rust 二重可变借用失败，修复保留证据）；新精确SOURCE `ab7ea894100f245d6a510137282736781bd017ce` ARM64 build [40108972702](https://github.com/lly8666/wbd-next/actions/runs/40108972702) 成功，产物12565424535 ZIP SHA256 `9bf5b07eee3e90a37a69844b23fb08834c38a9d5781f0f1635c27543bbba7067`。包括 native staged prefix确证、不复发 PN、新 DATA 无阻塞、真实ISA-L和固定/Auto真正内核恢复回归 PASS；Maximum20 行合同40108972687 PASS。

[W25 Action40109234114](https://github.com/lly8666/wbd-next/actions/runs/40109234114) 同 VM **一个场景一个测量 job、A→B顺序**，旧A `cf00a47c`（构建40105262367）/新B `ab7ea894`（构建40108972702）均复用ARTIFACT，不在测量 job 编译。150Mbps **每方向**，原始fq600、Static owned veth邻居，30% IID实际netem 29.98–30.06%，单程300ms、最大档Fixed6 applied、外层真实DATA重传0包0B（parity另算），15秒warmup+30秒measure+30秒drain，双方Stop owned清理，源TUN/root drop0，RX pressure/decoder reject0。结果artifact12565917569 SHA256 `6dae0f82569e28a8c72785c126c1d18a3c6d322538a250b1f287d6f331705683`。

| 指标 | A旧源码（业务FAIL） | B双量子同M4（业务PASS） |
|---|---:|---:|
| C→S净业务/残余 |147.123 Mbps / **1.951%** | **149.938 Mbps / 0.0542%** |
| S→C净业务/残余 |147.379 Mbps / **1.774%** | **149.953 Mbps / 0.0485%** |
| 首次交付 p99 C2S/S2C |311.3/311.2ms | **303.3/303.2ms** |
| client parity rplanned→rsent |830066→745874（缺10.14%） | **830367→829702（缺0.080%）** |
| server parity rplanned→rsent |830066→753112（缺9.27%） | **830361→829936（缺0.051%）** |
| queued_expired jobs C/S |985 / 848 | **15 / 8** |
| unknown_capacity C/S |8049 / 7399 | **51 / 31** |
| 30秒进程CPU-s C/S |24.24 / 24.06 | **24.85 / 24.58**（无CPU节省声明） |
| RSS peak C/S MB |49.84 / 49.62 |50.12 / 49.78 |
| 30秒真实veth outer TX C/S Mbps |244.85 / 246.52 | **259.68 / 259.85**（包括更多真实Parity） |
| host CPU PSI peak |27.42% |29.61% |

**结论：** 新 B 150Mbps FEC-only 满足≤1%残余交付且 p99 相比 A低8ms；性能成果是 Parity按时发送与首次交付改善，**不是更低总CPU/总外层带宽**。B 发出了更多真实 Parity，故 CPU-s、外层 TX Mbps略升是合理成本，不能把少发 parity 的 A当作节能资格。整个 Action 按用户验收脚本判 *FAIL（A旧腿失败）*，但 B 腿原生产物 `PASS_SCOPED_OBSERVATION`；与W23孤立通过不同，本次是在旧版同机失败的情形下 B 正向通过，不过仍为一次未固定netem随机序列的AB而不是 BA/持续压测/物理保证。

**容量停止继续：** W25新B宿主CPU PSI峰29.61%、30秒持续高压力，175–350Mbps 继续 NOT_RUN；RX低占用、外层DATA retrans 0不代表宿主CPU可继续加压。Auto真实动态升降档、反馈RTT真实性以及 Windows 和整体合并仍未过；`merge_ready=false`，只改独立FEC分支与自身状态，不接管原network工作包。


## 2026-10-24 W26：取消每源包临时Vec及重复复制，150Mbps同机AB双腿PASS

在 W25 Fix Maximum6 150Mbps真实双向残余降到0.05%的基础上，本次只优化 FEC source 密封的CPU成本。旧 `original_fixed_stage_source` 每个源包先调用 `source_owned()` 创建新 Vec，再将同一 10B头+真实源字节复制到原 M1 arena，额外每侧约663,000次源包heap申请/45s。新精确SOURCE `564490bc7a8f61c9ab06be58add8138212306393` ([commit](https://github.com/lly8666/wbd-next/commit/564490bc7a8f61c9ab06be58add8138212306393)) 使用现有 `source_into` 对原 owned arena 精确 `[14..14+SOURCE_HEADER+len]` 写入，source/TICKET/budget校验、AEAD PN、复制确认、所有frame字节相同；不改 M3 Parity调度或外层恢复/真M2。Exact source ARM64 [构建40109847848](https://github.com/lly8666/wbd-next/actions/runs/40109847848) 全绿，zip artifact12566326717 SHA256 `a1ce0b81738a9a74ac04835546479ada398e99718fd5086775c0b765625f649c`，包括 dirty arena 源wire等价及 Fixed/Auto 内核缺源回归。

[W26 performance Action40110100061](https://github.com/lly8666/wbd-next/actions/runs/40110100061) **SUCCESS**：唯一场景、同一ARM64 runner/同一job、旧A `ab7ea894` →新B `564490bc` 顺序比较；各自warmup15s+measure30s+drain30s，双向150Mbps、真实netem IID约30%、300ms单程、固定最大6真正applied、外层DATA修复0包0B、真实首发Parity照常、原TUN fq600及owned测试静态邻居不动；Stop owned清理、TUN/source root丢包0、RX压力淘汰/codec reject0。结果artifact12565693815 SHA256 `d7127551bec2574ec38858e232cce03a65f3c76020c71856be9f389fb81e9051`。

| 同机30秒量纲 | A原双量子 | B+直接arena |
|---|---:|---:|
| C→S 实际交付/残余 |149.874Mbps / 0.1015%| **149.897Mbps / 0.0836%**|
| S→C 实际交付/残余 |149.871Mbps / 0.0954%| **149.926Mbps / 0.0623%**|
| 首次p99 C→S/S→C |304.5/304.0ms|303.7/303.8ms|
| CPU-s 客户/服务 |25.36 / 25.27 | **24.87 / 25.39**|
| CPU-s 双端合计 |50.63 | **50.26（少0.37s，-0.73%）**|
| RSS峰 客户/服务 MB |49.90 / 50.17 |49.85 / 49.71|
| native parity rplanned→rsent 客户 |830379→829009|830269→829411|
| native parity rplanned→rsent 服务 |830337→829059|830185→829614|
| 30秒outer veth TX 客户/服务 Mbps |259.71 / 259.49|259.85 / 259.81|
| Host CPU PSI峰/over20持续比 |30.58% / 100%|30.25% / 100%|

**资格**：W26 A/B两个方向、两腿各自产品级功能/业务均 PASS_SCOPED，B无Parity/首达回退；修订消除一次真实 source Vec 分配和重复copy。CPU 客户 -0.49s、服务 +0.12s，合计 -0.37s /30s，只有同机一次AB观测，**不能据此宣称有稳定0.73%硬件加速**。150Mbps比125Mbps多20%吞吐，CPU总秒不应硬压到125的绝对数而不减少真实Parity；更高175+依然 NOT_RUN，因为宿主CPU PSI持续>20%。独立 FEC Fixed 功能代表已具备150Mbps scoped资格；Auto真实损伤阶跃动态profile、真实反馈RTT age与Windows/组合资格仍未完成，merge_ready=false。现不再无限提高业务档或刷种子。


## 2026-10-25 W27/W28 用户要求：175Mbps与200Mbps原生双向逐档试验（外层DATA修复OFF）

产品冻结：Rust/Go 原生ARM64 W26 exact source `564490bc7a8f61c9ab06be58add8138212306393`，build Action40109847848 / artifact12566326717 / ZIP SHA256 `a1ce0b81738a9a74ac04835546479ada398e99718fd5086775c0b765625f649c`。两次性能Action均一个独立单腿场景（非同runner AB），依次先175后200；均为 ARM64 GitHub VM，Fixed Maximum6 真实双端applied，repair_enabled=false原生readback/实际outer DATA repair=0；原TUN fq600和owned静态veth邻居，150档延续的600Mbps外层netem rate不变，30% IID netem实测29.94–29.98%、单向300ms，15s warmup+30s measurement+30s drain，99%大小1287B，真实性能/PN/M2/RX和cleanup报告原样保留，不改代码不重新编译。速率仅改变 app offer `175/200` Mbps each。

| 双向重要指标 | W27 175Mbps | W28 200Mbps |
|---|---:|---:|
| 原生业务门 | **PASS_SCOPED_OBSERVATION** | **FAIL 2方向残余>1%** |
| C→S 交付 / 残余 |174.822 Mbps / **0.1187%**|191.462 Mbps / **4.302%**|
| S→C 交付 / 残余 |174.746 Mbps / **0.1661%**|190.519 Mbps / **4.765%**|
| C→S/S→C 实际首达 p99（仅已交付样本） |306.0/306.7ms|312.0/312.0ms|
| 客户端原生Parity rplanned→rsent |968003→965077（缺0.302%）|1106096→913794（缺**17.39%**）|
| 服务端原生Parity rplanned→rsent |967928→964020（缺0.404%）|1106095→893380（缺**19.23%**）|
| Parity队列过期Jobs C/S |69 / 96|**5864 / 6541**|
| 原生unknown_capacity C/S |116 / 172|**9320 / 10186**|
| 每侧进程CPU-s/30s C/S |27.11 / 27.53|28.64 / 29.08|
| host CPU PSI均值/峰值 |33.00% / 35.51%|**38.38% / 41.19%**|
| RX peak active C/S |183 / 183|209 / 210|
| RX capacity拒收/压力淘汰、原始TUN根fq/source drop |全部0|全部0|
| 真实外层DATA重传 / 假造反馈 |0 / 无|0 / 无|
| Stop原生命名空间清理 |PASS|PASS|

[W27 ARM64 Action40127642866](https://github.com/lly8666/wbd-next/actions/runs/40127642866) SUCCESS；请求 `tests/network/fec-work/W27-maximum175-W26single-static-owned-fq600-arm64.json` at `3a694dea12653eebe24bf5174f9c0c57e1cf533a`；result ZIP artifact **12573724068**, sha256 `00722004b9fbd1fc59e244b69045ff95ca0cdbe8ab008d4df1aa4bc9a5b0b7a0`。

[W28 ARM64 Action40127866107](https://github.com/lly8666/wbd-next/actions/runs/40127866107) FAILURE：仅两方向 `declared loss allowance exceeded`；请求 `tests/network/fec-work/W28-maximum200-W26single-static-owned-fq600-arm64.json` at `11774fb26d720f99f3c8801c5dfb843498f5dae8`；result ZIP artifact **12573539799**, sha256 `a5937ac9939a1d51c3693099b6a05163e09b2d5fbe9c8fe7c89efe0c4f7d9f53`。

**边界/解释**：175 Mbps业务单次限域达标，宿主CPU高争用不能保证多次/真实物理稳定；200 Mbps 双向残余显著超过1%，即使只看已交付的 p99 312ms貌似不高，也不能忽略50k+未交付。200Mbps对比175Mbps parity 未发比例突升至17–19%，作业到期数跃升，RX/源TUN均无压力拒收，因此首要调查发送端 Parity编码/调度在10ms期限下的CPU与M4排队，但单次共享runner不能全归产品CPU瓶颈。**容量STOP：不再压测225/250/350，不刷seed，不延长原生过期窗口，不降低loss资格要求**。Fixed-only 175有正例、200有确定反例；Auto真实升降档仍待独立资格，merge_ready=false，原network角色与main未动。

## 2026-10-25 W29：200Mbps两向PARITY发送时间堵点已修，CPU / SoftIRQ分核证据

**新 product 源码** [6246aa82](https://github.com/lly8666/wbd-next/commit/6246aa82df5140807914545b2fc9343b8c70a1aa)，ARM64 frozen build Action [40144596602](https://github.com/lly8666/wbd-next/actions/runs/40144596602) PASS，artifact **12579619244** ZIP SHA256 `f6baae3d9ca042d80b854fff1b217da8a11a2d8ce4aaf852935f2b641fdfcb7c`，Maximum20合同40144596591及真实Fixed/Auto原生FEC缺源恢复PASS，harness合同40144596705 PASS。区别旧 W26 `564490bc`：在原M4源包先密封后，严格以实际 32 个 kernel record槽位为上限，额外留 1 个反向真实M2反馈槽；有空位时最多一次聚合 5 个原M3 <=4行编码量子，0槽时只维护 owner deadline，不密封新Parity PN。每一行使用原owner唯一AEAD PN且仍等原生M4 definite-prefix确证；FEC r/k、T=10ms、源DATA优先、外层修复OFF、RX有界内存均不变。

[W29 同VM A→B Action40144809020](https://github.com/lly8666/wbd-next/actions/runs/40144809020)，一个200Mbps双向Fixed Maximum6相同网络场景，A=W26 frozen, B=W29 frozen，同一ARM64机器先后独立warmup15s、measure30s、drain30s，loss30% IID netem/oneway300ms/outer rate600Mbps/静态owned veth/FQ600，外层真实DATA重传两腿均0，真实TUN恢复、真M2反向反馈保留。结果artifact **12580009264**, ZIP SHA256 `786088a21a27c70623b344e2cfef5249c587005d2b103daf58a4a7b4600910a8`.

| 200Mbps each | A=W26 2个4行/原M4 | B=W29 最多5个4行/原M4 |
|---|---:|---:|
| 两向业务门 |FAIL/FAIL|**PASS/PASS**|
| C→S delivered / residual |191.527 Mbps / 4.271%|**199.546 Mbps / 0.2392%**|
| S→C delivered / residual |190.441 Mbps / 4.813%|**199.594 Mbps / 0.2201%**|
| 首达p99 C/S仅已交付样本|312.1/312.1ms|309.9/309.3ms|
| client Parity planned / sent |1106049 / 916875 (17.10%失发)|**1106174 / 1099275 (0.624%失发)**|
| server Parity planned / sent |1106089 / 899841 (18.65%失发)|**1106169 / 1099573 (0.596%失发)**|
| Parity queued expired client/server |5872 / 6537 |**330 / 310**|
| Parity sealer fail client/server |5949 / 5673 |**0 / 0**|
| unknown_capacity client/server |8701 / 9326 |**72 / 72**|
| CPU seconds /30s client/server |28.04 / 28.74 |30.61 / 30.38|
| CPU PSI mean / peak |37.78% / 40.84% |42.24% / 45.3%|
| CPU CPU time / 4 CPUs |74.5% nonidle |~76.9% nonidle|
| 软中断占整机CPU |10.05% |10.35%|
| 整核steal、hard IRQ CPU、cgroup throttled_usec |0 / 0 / 0 |0 / 0 / 0|
| 源TUN掉包、RX压力淘汰/reject、外层DATA重传 |0 |0|
| Stop清理 |PASS|PASS|

**分核真实内核证明**：新增FEC-only每秒numeric-only `/proc/stat` 所有CPU、`/proc/softirqs` NET_RX NET_TX TIMER SCHED RCU、`/sys/fs/cgroup/cpu.stat`及两个产品PID下线程级CPU ticks；`/sys/fs/cgroup/cpu.max`在此VM为UNAVAILABLE，不能从此字段直接确认配额类型。B测量窗口四核非空闲比例 76.55/76.90/78.02/76.16%，软中断CPU比例10.54/9.95/10.85/10.10%；NET_RX事件四核448058/437217/477315/447350，NET_TX四核522217/510686/548083/519130，并未集中在一个满负载核。cgroup `nr_throttled=0`、`throttled_usec=0`整个真实测量窗口均无增长，steal=0（不能排除<1Hz瞬时突发或宿主底层隐藏争用）。两端产品名截断的两个 `wbd-original-m4*` 高CPU线程分别约10.6~13.7 CPU-s/30s，说明TX/RX真正消耗CPU，非RAM短缺。

**机理与结论**：200Mbps上一版被固定Parity10ms期限+3次M4结算限制，平均全核未满仍有毫秒级等待，导致送出的r不足；`unknown_capacity`是deadline/capacity-known非内存malloc错误，且pressure_jobs/sources=0、RX容量拒收0；新B通过在同一次真实M4最多提交20行，消除额外kernel结算和原来超槽Pariy的失败，把两向业务从4%+残余带到0.22–0.24%，这是**同机一次比较下的限域通过**，并非持久、物理网络、高于200Mbps的容量保证。宿主CPU PSI仍高而且B需要更多真实Parity及CPU，保持200以上capacity_stop、merge_ready=false，原network角色与main不改。Action整体FAIL是故意保留的A旧版失败，B真实`PASS_SCOPED_OBSERVATION`。

## W30 (2026-10-25): 220Mbps frozen ARM64, narrow single-run PASS

Native W29 SOURCE 6246aa82, build40144596602 artifact12579619244 reused; original fixed Maximum6, real outer DATA repair OFF, authentic reverse M2 preserved. One standalone ARM64 job Action40145722367 artifact12581285466 ZIP SHA256 c2acba0adf8de8ae3cb7599e69930ba4e2582df0e4677f34632612010abd0e35. Real 30%IID actual client30.032/server30.002%, 300ms one-way, outer rate600Mbps, original TUN fq600, own static neighbor, each app rate220Mbps, 15s warmup/30s measure/30s drain.

C2S delivered218.145889Mbps, residual0.850472%, p99=312.0ms, missing5504. S2C delivered217.874079Mbps, residual0.977346%, p99=312ms, missing6325. Overall PASS_SCOPED_OBSERVATION but 0.02265 percentage points S2C margin to <=1% loss gate; no repeatability guarantee.

Native parity planned/sent client1216607/1186004 gap2.516%; server1216680/1182083 gap2.844%. Jobs expired1398/1588; unknown_capacity396/427 but pressure_jobs/sources=0 and parity_seal=0. Original TUN and root fq no drops; RX peak236/234 of640, bytes~8.9MB/48MB, pressure eviction/codec/capacity rejects0; no outer DATA retrans; genuine FEC recovered TUN 284121/285276, Stop cleaned.

CPU 30s client32.0/server32.11s; host CPU PSI mean45.53%, peak48.47%, >20% all samples. Each core nonidle79.16/80.22/80.36/80.93%, softirq CPU10.16/10.37/10.24/10.97%, NET_RX/TX balanced, steal0, cgroup CPU throttles0. Full-run original native TX thread21.6 CPU-s vs RX16.6 CPU-s EACH, not a 30-second counter. This is scheduling/CPU headroom, not memory exhaustion or one saturated IRQ.

Code-specific next candidate: StagedParity::next_quantum makes 4 new parity Vec + a Vec of mutable row views on each <=4-row ISA-L quantum, up to5 quanta per k16/r20 full block; W30 each end60k+ full blocks. Reuse four bounded row output buffers per stream for identical math, no change to AEAD, PN, deadline, first-send or copied prefix. Test against frozen W29 once, same VM old/new AB 220Mbps, after native function regression. Do not escalate >220, merge_ready=false.

## W31 (2026-10-25): 220Mbps per-stream Parity scratch same-VM AB

Exact new source 3b16e79698d33ef49628dfa8f67a47550438ebbc native ARM64 build Action40146207152 PASS, artifact12580177860 ZIP SHA256 69c14dbc1f3a65040c7013844c02d6af036b4a238c6d78262f6edc65d891b30f. W31 reuses only four bounded plaintext Parity row Vec per FixedStream, eliminates one temporary Vec row views per quantum, zeroes on Stop; exact independent scalar full Maximum20 parity row comparison and real native Fixed/Auto TUN recovery PASS, original PN/M4 prefix untouched.

W31 sameVM sequential A(old frozen W29 6246aa82) then B(new3b16e796) Action40146429352 artifact12580747651 ZIP SHA256 cf2ec141c998ea3a0259be51c43e95f2971af3f56017d2e1a92e5e2d254eb667. Both request outer DATA repair OFF actually0; Fixed Maximum6 both applied, original fq600 test permanent neighbors, 30%IID/300ms one-way, rate220Mbps each, outer rate600Mbps, 15s warmup30s measure30s drain, source root/TUN drop0, native RX pressure/capacity rejects0, Stop full cleanup.

| Measure 30s each | A old (INCONCLUSIVE) | B new (PASS_SCOPED) |

|---|---:|---:|

| C2S delivered Mbps / residual |218.704 / 0.5991%|219.322 / 0.3226%|

| S2C delivered Mbps / residual |218.825 / 0.5467%|219.244 / 0.3526%|

| First p99 C2S/S2C ms |311.4/311.4|310.4/310.7|

| Source injector S2C send errors |2|0|

| Client parity planned / sent |1216620/1197346|1216772/1207605|

| Server parity planned / sent |1216630/1198153|1216724/1206714|

| Expired jobs client/server |889/864|424/463|

| CPU process client/server seconds |30.97/30.87|30.95/31.24|

| Host CPU PSI mean/peak pct |44.26/47.54|44.18/50.44|

Important: Entire W31 Action failure is A INCONCLUSIVE due 2 genuine injector errors (APP_SEND_ERRORS_OR_MTU_REJECTION), not B failure. A observed business residual values are descriptive only, not a strict A PASS. B both directions true PASS_SCOPED_OBSERVATION, parity sent ~0.75/0.82% deficit vs A 1.58/1.52%. CPU total increased 61.84->62.19 CPU-s, cannot claim net CPU saving; may reflect sending more parity, runner variance, unseeded netem and source A injector error. Host PSI peak B50.44%, so no rate above220 and no sustained qualification.

Next plausible bounded CPU work visible in original codec: PreparedBlock per-job table reference BTreeMap, per-quantum dynamically allocated src/dst slice views inside encode_prepared_into, and original authenticated M4 TX. Profile before replacing; no CPU overhead attribution without timing breakdown. Keep outer DATA retrans OFF, native Auto dynamic unfinished, merge_ready=false.

## W32 2026-10-25: user-authorized 250Mbps diagnostic FAIL

Action40147431966 one ARM64 native W31 frozen source3b16e796, true Fixed Maximum6 dual applied, outer DATA repair=0, authentic reverse feedback, netem 30%IID/oneway300ms, app250Mbps each, outer600Mbps, original fq600, owned static-neighbour veth, warmup15/measure30/drain30.

C2S injected249.986Mbps delivered243.173Mbps residual2.7395% p99 successful313.3ms missing20146; S2C injected249.901 delivered243.547 residual2.5504% p99 successful313.3ms missing18749. Real injector UDP send errors C2S39 and S2C245, mirrored kernel Udp.SndbufErrors39/245: strict both business FAIL and injector contamination separately, no exclusively FEC cause claimed.

Original native parity planned/sent client1382114/1263176 (8.605% unsent), server1381771/1263279 (8.575% unsent), queued expired jobs5610/5587; neither pressure_jobs/sources nor parity seal/m4 noncopy nor RX capacity eviction nor original source TUN drops. CPU process30s client32.20s server32.49s, host PSI avg47.19% peak50.66%, >20% all samples; four CPU nonidle80.4/82.87/77.93/83.05%, softirq CPU10.42/11.45/9.63/11.44%, no percore IRQ saturation or cgroup throttle. Real artifact12581258712 ZIP SHA256 2d14df2efc9231f84fda1d1727529093d2eda7f5ed5a4a233a3be56dfe21d03a.

Follow-up bounded FEC W33 source e99a4afff validated real ARM64 build40147815858 and native Maximum40147815849, eliminates two slice Vecs each <=4-row ISA-L quantum and five coefficient BTreeMap nodes per full block; only limited fixed table refs and input/output stack arrays, retains exactly same Cauchy/ISA-L, AES/PN, source-first, reverse feedback, outer repair-off, FEC TTL=10ms, original fq600. 250Mbps W34 A old /B new single sameVM action40148014701 in progress. Do not claim pass or CPU gain until result; no higher pressure or branch merge.

## W34 2026-10-25: true 250Mbps sameVM old/new both PASS, host CPU variance explains earlier W32 failure

W33 source e99a4afff3e9e55e3a11113ed30097e1789e86af (fix of compile-only E0502 failed source ac4d9b21), native ARM64 build Action40147815858 real Fixed/Auto missing-source to TUN PASS artifact12580544395 SHA256 e1ec27312a833e03762a4b9bc6201ff143867b65a6dba02ce17a12a8bb9221eb; Maximum native row contract40147815849 PASS. Codec still exact global ISA-L (k,row,count), instead of per-quantum two heap-allocated pointer Vecs and per-block five BTreeMap coefficient reference entries uses fixed MAX_K16/MAX_BATCH_ROWS4 borrowed stack arrays and bounded 80-slot coefficient pointer array per in-flight block. No different mathematical output or FEC policy/M4 settlement.

[W34 A/B Action40148014701](https://github.com/lly8666/wbd-next/actions/runs/40148014701) **SUCCESS** single 4CPU ARM64 VM sequential A=W31 source3b16e796/B=W33 sourcee99a4aff, exact 250Mbps each, 30%IID netem/300ms one-way, outer netem600Mbps, unchanged original fq600 and owned static neighbors, original outer DATA retransmission truly0, authentic M2, warmup15 measure30 drain30. Artifact12581460257 SHA256 b64b94cebf5aa465421ee89bb310071401623820b9ed021630097fb92b5b785c.

| Metric | A old W31 | B new W33 |

|---|---:|---:|

| C2S delivered / residual |249.950Mbps / 0.02869%|249.936Mbps / 0.03631%|

| S2C delivered / residual |249.947Mbps / 0.03100%|249.950Mbps / 0.03127%|

| first-arrival p99 C2S/S2C |301.9/301.9ms|301.9/301.9ms|

| Parity planned/sent client |1382007/1381992|1381912/1381912|

| Parity planned/sent server |1381927/1381927|1381924/1381924|

| native parity jobs expired client/server |1/0|0/0|

| injector UDP send errors C2S/S2C |0/0|0/0|

| process CPU seconds/30 client/server |27.76/27.86|27.73/27.68|

| host CPU PSI mean/peak |33.66% / 36.11%|33.48% / 35.90%|

Both A/B true business/FEC-only scoped PASS and all native Fixed applied/zero source TUN and original root qdisc drops/zero RX pressure and codec reject, real recovered-to-TUN and Stop cleaned. **No causal W33 throughput gain:** observed combined CPU -0.21 seconds over30 (-0.38%); both parity complete and very similar p99/delivery; residual slightly higher B C2S. One AB cannot prove stable CPU saving.

**Cross-VM counterexample:** W32 on other shared Actions host, exactly same W31 old source3b16e796 at same250Mbps 30%/300ms, FAIL residual2.740/2.550%, real injector SndbufErrors39/245, native parity deficit8.61/8.57% and expired5610/5587; mean/peak CPU PSI47.19/50.66 versus W34 old A33.66/36.11. Host scheduling contention/CPU headroom and injector capacity are proven major sensitivities, no single-core IRQ saturation or cgroup throttling; cannot declare stable product250Mbps under high CPU pressure. Stop >250, no claimed host-fixed capacity, merge_ready=false. Further work should measure original TX M4 slot scheduling and high-PSI deadline age rather than chase ISA-L tables or enlarge RX buffers.

## W35–W38 2026-10-25: task-deadline-before-TUN / source symbol workspace / first packet-realistic 200Mbps A/B

Suggestion 1 verified: original TX worker called blocking poll(TUN,10ms) before checking owner 10ms post-close Parity and authentic M2 feedback deadlines. W35 source e2aeba7a fixed by computing nearest deadline before poll, waiting at most floor(time-to-deadline_ms) ≤10ms and zero if queued/already due; rechecks after poll. No new busy thread, M4 kernel proof/AEAD unchanged. ARM64 native PASS.

Suggestion 2 verified: each k16 FEC block used k separate Vec math symbols, despite already shared parity scratch and ISA-L tables. W36 source 861f0396 uses one contiguous zero-tailed k*symbol_len source workspace, reuses it across blocks only after synchronous true M4 copied-prefix settlement, scrubs on Stop, keeps Scalar/ISA-L math exact and first send unchanged. Corrected deterministic test expected 16*137B for mixed first-source135B plus15*77B block; native Fixed/Auto true TUN and Maximum20 PASS Action40150749260, artifact12582379708 ZIP SHA2565f9f587a4d1d44a3cf482c4c46a5be5b52cc71fdb4080935de153dc85f89f7e5.

Suggestion 3 examined: split ingress already exists for Normal/off using bounded channel512; Fixed/Auto intentionally keep one reader/TX. Under high host PSI do NOT add reader/thread without phase latency evidence; measured W38 shows product CPU and source TUN drops, so separate thread is not justified yet.

W38 same-VM real 200Mbps each, 96% UDP/4% two TCP socket, 35% count size64–256B and larger 512/900/1287B, 20Hz sparse64B probes,30%IID/300ms one-way, original outer600Mbps,fq600; first-arrival small actual application UDP cohort p99 and 10ms 300ms-delay-aligned gap, 15s warmup30s measured30s drain, real source zero-drop required, original outer DATA retransmission zero, authenticated M2. Action40150988880 FAIL both A/B, artifact12583045399 sha256 c90496f5f074082ac174de109d1830b3289f3f24d83ea61678e1df67d9cadb26.

| Metric | A W33 e99a4aff | B W36 861f0396 |

|---|---:|---:|

| C2S UDP residual |13.3746%|5.5686%|

| S2C UDP residual |13.7190%|6.3371%|

| C2S real small UDP<=256B residual / p99 |13.6155% /316.2ms|5.4765% /320.5ms|

| S2C real small UDP<=256B residual / p99 |14.0161% /316.2ms|6.3845% /321.3ms|

| TCP 8Mbps target each dir actual C2S/S2C |0.132/0.102Mbps|0.386/0.238Mbps|

| Client/server FEC jobs expired |40824/42260|14479/16998|

| Client/server Parity rplanned→rsent |1935490→1075756 /1932987→1042770|1926712→1628512 /1928128→1577641|

| Host CPU PSI mean/peak |43.48%/46.31%|56.57%/60.32%|

| Source TUN drops steady client/server |296/0|390/1017|

All outer DATA reTX0, RX decoder reject0 and RX capacity/pressure eviction0, exact native sender/rx recovered real TUN and Stop cleanup. CPU measurement in host process full-run (includes warmup/drain), not mislabelled 30s. Source drops and TCP backpressure explicitly disqualify. More FEC sent in B also raises CPU PSI, so don't claim stable CPU efficiency or full 200Mbps mixed capability. Lower effective app-byte target still increases packets/s enough to overload four-core runner. B improves parity deadlines but insufficient, do not extrapolate 250Mbps mostly1287B tests.

Size count distribution is illustrative workload (6/8/10/11/15/20/30 per 64/96/160/256/512/900/1287B), NOT externally trace validated representative Internet distribution. A 20Hz 64B distinct probe provides sparse small signal; W39 will provide true one-way first-arrival and loss distinct from RTT, at SAFE 100Mbps lower diagnostic after the W38 200Mbps capacity stop.

Status capacity_stop true, merge_ready false. No main or upstream network branch touched.

## W39 2026-10-25: 100Mbps same mixed packet distribution safe diagnostic with real sparse 64B first-arrival

After W38 mixed200 A/B both failed with source TUN drops/CPU PSI peak60% and TCP heavy backpressure, W39 intentionally de-escalates to single low-load 100Mbps each so it does not re-stress the capacity_stop host. This is not an attempt to replace or erase user's 200Mbps requirement.

Exact native W36 product source861f0396264734f97658243156060f13e6a2f74f build Action40150749260 artifact12582379708; original true Fixed Maximum6, outer DATA retrans OFF with genuine0, real M2 reverse, 30%IID netem actual,300ms one-way, outer600Mbps, source fq600, static owned veth, 15s warmup30s measure30s drain. Packet weights by count 64:6 96:8 160:10 256:11 512:15 900:20 1287:30 (35% <=256B). UDP96%=96Mbps, two actual Linux TCP socket flows share4%=4Mbps, separate20Hz64B probes.

[W39 action40151444036](https://github.com/lly8666/wbd-next/actions/runs/40151444036) SUCCESS true PASS_SCOPED_OBSERVATION, artifact12582309090 zipSHA256 80fa6550e58c62bdd884d22c816cf7a2f1ec6c5bd45fbe133d5f7723f62f80e0.

| Original business metric | C2S | S2C |

|---|---:|---:|

| UDP delivered / residual |95.958Mbps /0.0464%|95.978Mbps /0.0309%|

| 64–256B UDP sent / delivered |180355 /180240|180355 /180236|

| small UDP residual / p99 |0.06376% /308.6ms|0.06598% /308.7ms|

| netem-aligned longest offered small UDP 10ms zero-delivery gap |0ms|0ms|

| TCP 4Mbps offered / actual |3.9997Mbps, backpressure0|3.9998Mbps, backpressure0|

| TCP framed-record first arrival p99 |943.3ms|925.9ms|

| 64B 20Hz sparse probes sent/peer-real-first-arrivals |595/593|595/593|

| sparse probe one-way p99 / separate reverse RTT p99 |307.1ms /610ms|306.7ms /610ms|

| native Parity planned→sent / expiry |client1019107→1019107 /0|server1020072→1020072 /0|

Both source TUN warmup+steady drops=0, original fq root drops=0, RX capacity rejects0, outer DATA reTX0, Stop drained. Host CPU PSI mean37.65/peak40.43% still high; shared VM cannot establish physical/Windows capacity. Sparse probe first-arrival records receipt before reverse echo and is not inferred from the RTT; 2/595 real missing each side explicitly retained.

**Interpretation:** 100Mbps genuine mixed UDP+TCP and 64B sparse does recover correctly; previously W38 at200Mbps with same packet weights FAIL even though older mostly1287B250Mbps benchmark passed. Small packet count/second and kernel TUN throughput /20-row Parity encode scheduling (not a fundamental 64B header or decoder defect) are primary next questions. 200Mbps mixed is NOT qualified. Do not rerun overloaded 200 or increase rates without CPU headroom. Keep capacity_stop=true merge_ready=false.
