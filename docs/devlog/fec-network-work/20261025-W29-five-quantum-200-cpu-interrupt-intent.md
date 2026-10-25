# W29 — 200 Mbps parity deadline and softIRQ/core diagnostics, FEC-only

Source A frozen W26 exact 564490bc7a8f61c9ab06be58add8138212306393 build40109847848 artifact12566326717 sha256 a1ce0b81738a9a74ac04835546479ada398e99718fd5086775c0b765625f649c. W27 175Mbps outer DATA retrans OFF /30%IID/300ms both PASS, W28 200Mbps both FAIL 4.302/4.765% residual, parity gap17.4/19.2%, expire5864/6541 and host PSI41.19 peak. No RX capacity/driver source drops. Raw /proc/stat W28 4-core total non-idle75.2%, softirq9.7% total (~0.39 core), steal0% in matched 30s window: cannot assert single CPU softirq saturated because prior artifacts omitted per-CPU or per-IRQ metrics.

NEW source B: maximum k16/r20 does 5 bounded ISA-L <=4-row quanta but they may all join a single original M4 copy confirmation **only when >=21 slots remain after fresh DATA**, reserves one authentic M2 control slot. With fewer slots emit at most floor((available-1)/4) quanta, zero = maintain owner time only. Never allocate AEAD parity PN that cannot fit within 32 total M4 records. No altered policy, FEC math, RX, deadlines, outer retransmission, source-first, original fq600, 600Mbps netem or test packet shape. Test native one-call five-quantum staging/matching rows, zero-budget no seal, genuinely acked 20, source priority.

Add FEC-only 1Hz /proc/stat per-CPU cumulative ticks, /proc/softirqs per-core NET_RX/NET_TX/TIMER/SCHED/RCU counts, /sys/fs/cgroup/cpu.stat/max and two product process thread CPU ticks/core. Shared tools/network_harness/runner.py touched only as an optional FEC owner low-overhead numeric sampling addition, no network/harness schedule or success criteria changes; scope noted COMMON_PATH_DIAGNOSTIC. This is not evidence of interrupt saturation until per-core delta inspected.

Run new frozen native ARM64 product and real kernel Fixed and Auto recovery correctness first. Then at EXACT 200Mbps/each, 30%IID loss/300ms each one-arm64-VM sequential A (W26 frozen) /B (new frozen), one scenario one Action, 15s warmup,30s measure,30s drain, 600Mbps netem unchanged, outer DATA retrans 0, real reverse feedback preserved. Business <=1% residual both sides, no TUN drops / RX overpressure / timing regression. If B FAIL do not escalate past200, instrument remaining starvation. If B PASS do not automatically claim physical capacity due shared host PSI. Preserve unrelated original network and main; merge_ready stays false.

## W29 completed outcome
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
