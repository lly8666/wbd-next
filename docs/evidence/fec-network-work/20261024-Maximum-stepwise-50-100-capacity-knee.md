# 2026-10-24 FEC Maximum 上行至 200 Mbps 的逐档容量门槛报告

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
