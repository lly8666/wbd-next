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