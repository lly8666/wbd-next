# FEC Maximum单向故障确认及 fq600/真实CPU、外层带宽拐点

2026-10-24 独立分支 experiment/fec-network-tuning；原生ARM64完全冻结 source 6b08527dbb0af8a626760ff83abcd06de1d42d87 / build 40099179830 artifact12562092730（没有改原网络岗位或 main）。Fixed Maximum6，outer DATA repair=OFF且native实际重传0，真实30%IID，300ms单程，99%1287B/1%64B，每方向业务/外层cap=1:4，15s warmup +30s steady +30s drain。

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