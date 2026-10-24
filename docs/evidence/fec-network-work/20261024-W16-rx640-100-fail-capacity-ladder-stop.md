# FEC Maximum，逐档业务带宽与真实外层占用：100 Mbps 回归失败，停止 125–350

2026-10-24，独立分支 `experiment/fec-network-tuning`。第一轮旧 RX96 active 在 [W15 100 Mbps](https://github.com/lly8666/wbd-next/actions/runs/40094982877) **业务 PASS 但缓存压力淘汰29425/端**，激活数96/96。用户明确授权算清并推进350，于是修补 RX 上限640块/48MiB/1024重排并优化每包 O(n) 全扫描为 BTreeSet touched-time 索引 O(logn)/增量退休，150ms 原生命周期/源到达立即交付/已完成块不早退，保留认证 replay/Stop。源码 `8ec552bdd146cf33233130c4779ed5339e27a3c7` 的 [ARM64 build Action40097251707](https://github.com/lly8666/wbd-next/actions/runs/40097251707) **PASS**，artifact `12561755643`, sha256 `866aae86f355e76b8269ea86a72fd15748ee0448d4095085a374695678f45674`，原生450并存live块/定时成熟退休测试、真实缺源→Parity→TUN、Go+Rust回执测试 PASS。产品没有预分配48MiB缓存。

## 固定时长口径与真实测量表

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
