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
