# W13 50 Mbps 独立原生产品：RX 容量修复限域通过，A/B 复现边界仍未清除

**暂时收口记录（2026-10-24）**。独立分支 `experiment/fec-network-tuning`，修复 SOURCE `ec344557fa8cbf4d717a81833d36f92584263478`，原生 ARM64 编译 [40087393299](https://github.com/lly8666/wbd-next/actions/runs/40087393299)，artifact `12558215058`，ZIP SHA256 `bd22744ae29bcb0ec8b57cba9bdcc7b10228911e9af628791501ff7623b008d3`。新旧测试产物**一律按精确 SOURCE** 冻结；这里不合 main、不覆盖网络岗位。

源程序修复：RX 保留原 150ms 组生存期与原 128 block 重排跨度，`MAX_ACTIVE 32→96`、`MAX_STORED_BYTES 1MiB→8MiB`，不再尝试 W11 失败的「已完整组提前退休」。Stop 只输出一次有界数值 `V4_PUBLIC_FEC2_RX_CAP`，现有 harness 实际解析容量/拒绝原因；认证/AEAD/PN、M4 首次交付、Parity 源头和 outer OFF 不改变。原生 5 RX 单测、Maximum rows、原 Linux netns 确定性缺源+parity→真实 TUN/反向 M2、harness 合同均通过。

## 实际 W13 PASS（单场景，一 measurement job）

[GitHub Action 40090193642](https://github.com/lly8666/wbd-next/actions/runs/40090193642)，结果 artifact `12559170488`、ZIP SHA256 `aeea1dd50cce86e0a9b0f1a89ad7e5f8e62a5b680e79df47fb9f354067e9c42f`，SOURCE `ec344557fa8cbf4d717a81833d36f92584263478`。原 W8 的 50Mbps/方向、IID30%、300ms 单程、99% 1287B 1% 64B 包型、netem 每方向200Mbps、15s warmup/30s steady/30s drain、outer-repair=off、Fixed Maximum profile6、真实双端 applied/readback。

| 指标 | C→S | S→C |
|---|---:|---:|
| 真正注入 Mbps | 49.9991 | 50.0005 |
| 交付 Mbps | **49.9851** | **49.9898** |
| 实发/交付/最终缺失 UDP | 147083 / 147007 / **76** | 147087 / 147014 / **73** |
| 业务残余 | **0.05167%** | **0.04963%** |
| 首次成功到达 p99 | 304.6 ms | 304.7 ms |
| 真正接收组恢复→TUN（接收侧） | 服务端 66417 | 客户端 67115 |

两端 decoder rejected、capacity/codec/conflict/invalid reject、pressure_evicted、refused_bytes 都 **0**；实际 peak_active 客户端57、服务端58，peak_stored_bytes约1.922/1.923MiB（确实超旧1MiB与32槽限制，但远低新96/8MiB）。真实原生 outer OFF 双端、生效 profile6 revision1、外层 DATA 重传0、真实反馈 reverse_reports 12753/12633、TUN 源端 / root qdisc drop 0、Stop drain 成功。netem 真实近30%（29.996%/30.058%）。

进程测量 CPU client/server **12.54/12.67 CPU-s 每30s**；RSS 峰值 **29.72/29.57 MB**。CPU PSI 峰值8.83%、未见资源停压。相对旧 W8 50Mbps 4.360/3.905% 残余，新产物单独场景实现代表性的业务恢复目标，CPU/RSS没有出现数量级膨胀；不是同VM严格因果提速结论。

## 必须保留的 W12 同 VM AB FAIL

同一旧/新顺序 [W12 40089406842](https://github.com/lly8666/wbd-next/actions/runs/40089406842) A较接近基线 `a969217e`、B本 SOURCE，在同 VM 两段完整业务跑完。A 双向残余约4.03%/4.06%、decoder rejected 19688/18368。B **S→C 仅缺43包、C→S却缺18025包（约12.23%）**，尽管 B RX decoder rejected 0、peak_active 58/59、pressure eviction0，B FEC TX parity 真正 kernel copied 279164/279144、M1 admission 222353/222327、M4/source parity noncopy/retry0。**B 客户端外层 veth 稳态计数286.89MB、服务端326.11MB**；W13 单独运行客户端/服务端则326.27MB/325.81MB。B 所见失速不在已拆分 FEC RX 解码拒绝里，且同机第二段与独立单段存在差异；不能在证据不足时断言是顺序串扰、网卡 fq、CPU 或 FEC 算法。

**资格口径：** `50MBPS_STANDALONE_PASS_SCOPED`；同VM新旧可重复性 `UNRESOLVED`，全档/100–200Mbps `NOT_RUN`，75Mbps历史失败保留；`merge_ready=false`，Auto 动态真实升降档仍暂停待验。容量停压继续保持，当前不再启动新的场景、不覆盖其它岗位进度。若将来必须完成多轮高率稳定性，可优先用保存的 W12/W13 标准网卡/源统计排查成功 native-M4-copy 到 netem-interface 的时间线差，而不是再次盲目扩 RX 或升高负载。

