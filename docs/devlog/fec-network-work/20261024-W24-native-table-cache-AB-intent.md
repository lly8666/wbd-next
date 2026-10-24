# W24 native ISA-L coefficient-table reuse candidate (2026-10-24)

**Owner/branch:** fec-network-work on experiment/fec-network-tuning.
**Prior pinned product:** 6b08527dbb0af8a626760ff83abcd06de1d42d87,
ARM64 build Action 40099179830 artifact 12562092730 SHA256
e3509e34a11f4763011c08312d02270e560ac7d04f5136ad22f76b5990f4cda5.
W23 Action 40102994265 artifact 12563149315 SHA256
f64b606746b3a7b317e81fb5fb8849447ceed1cc21607624508743567c01f9c4.

## Computation and causal limit

At 150Mbps/side 30% IID/300ms Maximum6, accepted first-source
663652/663656 over 45s, full blocks40953/40953; 20 parity rows per
full block => five 4-row native ISA-L table initializations **per block**
on the old source. This is approximately 4550 repeated initialization
events/sec/side before accounting partial blocks. Source-side M4-copy
failures0, RX pressure0, TUN drops0, outer DATA retrans0.
W23 rplanned 830246/830265 and r_sent800359/799115, gap3.60/3.75%;
unknown_capacity2983/3054 BUT pressure_jobs0 and source_pressure0;
parity seal failure48/63; queued expired335/347. Code inspection shows
unknown_capacity also increments on in-flight job expiration; no
thread-level or codec causal benchmark yet. FixedStream Maximum closes a
job after 10ms and needs 5 M4-settled 4-row quanta. This proposal does
NOT increase the timeout or weaken source-first priority.

## Change, bounds, qualification

Reuse ISA-L Tables immutably keyed only by k, absolute row start and
row count, with a fixed 16*20*4 lazy slot set. All valid native k>=2
shapes together have at most 777600B native coefficient table payload
plus bounded slot and allocator metadata. Source payloads, PNs,
generation, sealed rows, M4 outcome, FEC parity volume and other outer
repair paths are unchanged. Scalar/non-native remains exactly as-is.
Add native cross-block different-sources complete 20-row oracle and
explicit ARM64 test in existing product-build Action. Build correctness
first; then W24 single 150Mbps 30%IID 300ms one-VM AB with A=old frozen
binary and B=new precise SOURCE, two 15s warmup+30s measurement periods,
independent cleanup and per-leg readbacks. No 175+ pressure until parity
gap and CPU pressure support it. Strict performance result NOT_RUN until
that Action finishes; no performance gain claimed from compilation.

Auto dynamic full profile transitions and truthful RTT age remain
independently OPEN; original network-matrix branch/status untouched.

## Measured outcome (source-locked, not an estimated speedup)

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
