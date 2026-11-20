# H2231 — 三台 Runner 真实网络下的应用 UDP RTT P99 和 TCP 吞吐/RTT 长尾

## 操作

在 GitHub Actions 选择 `H2228 Three distinct runners routed ARM relay 200ms one-way 1-20% real TCP`，点击 **Run workflow**，选择 main，输入 `model=burst`（可额外以 `iid` 作为丢包模型 A/B）、`mode=normal`（可选 `fec-fixed`，必须在原 Rust Stop 回读真实 FEC6）。仓库须已配置 `TS_OAUTH_CLIENT_ID` / `TS_AUDIENCE` 且 `tag:ci` ACL 允许 CI 节点三机互联。正常 main push 仅执行静态单测；manual workflow 才启动真实三个 runner。

组网为 x86 原生客户端 → ARM64 独立 **Linux kernel L3 router** → x86 原生服务端（两段不同的 VXLAN Ethernet over Tailscale），客户端/服务端为原始 Go TLS+Rust native 真 AF_PACKET FakeTCP+TUN。ARM 中继只在两个路由出口施加 `tc netem` 200ms **额外每方向**延迟、15ms stddev jitter 和 GE 0/1/5/10/20% 丢包（`iid` 是对照，不是同一模型），不加 rate cap。网络自身的 RTT 还包括 Tailscale/VXLAN 宿主开销。BBR 只用于本机真实 TCP，不用于外层原始伪 TCP。

## P99 与 P01 的正确含义

### 业务 UDP 应用 RTT

每个 20s TCP `iperf3` 档位另外有一个**同时发生**的真实 UDP echo 小包探针：直接线路连接服务端 underlay `10.248.82.2:45902`；WBD 则在认证后的原生 TUN 连接服务端 `10.66.0.1:45901`。每100ms一包，计划120包；不超过15s（同一 iperf3压测期）。独立随机实例 nonce、序号、回显源和二进制载荷均实证匹配，仅计唯一有效回复。计算 P50、P95、P99、平均、最大值、丢失比例、最大连续丢失包数，以及相邻成功请求 RTT 变化的 P99。P99 至少 **50 个实际有效回复** 才被认证为一个样本分位；高丢包、未建链或3s短流若不足就标记 UNKNOWN/null，不擅自补0。

这叫 **UDP 应用往返 RTT P99**，包括本机排队、TUN、Linux server UDP 应用 echo 等，不是独立路由单程时延，也不是 WBD 原始 FakeTCP ACK 或 TCP重传超时。

### TCP/iperf3 业务和内核拥塞反馈

逐 `iperf3 -J` 秒级 interval 统计 Mbps 的 P01（低尾）、P50、P95、P99、平均/最大/最小，标明是 **每秒吞吐统计** 而非每包时延，剔除 iperf3 `-O2` warmup `omitted=true` 区间。额外保留 90%实测峰值首次达到的秒序号、掉速慢桶数、`sum_sent.retransmits`、每GiB重传数；内核发送端流量的每 stream 每 interval `rtt` 用微秒转换成 ms 并独立计算采样 P50/P95/P99；若没有 ≥50 实际发送端 RTT样本，P99=null。以上均不可冒充物理机 TCP RFC准确的 per-packet RTT P99。

## Artifacts 与资格判定

- `h2228-x86-client-evidence`：`case-XXX-...json` 为原始 TCP 用例摘要且含 `h2231_tcp_tail`，原始 `case*.json.stdout.txt` 保留完整 iperf JSON；`probe-case-XXX-...json` 为同 case 低频应用 UDP RTT/缺包证据。`probe` 文件不能算成第28个 TCP 用例。
- `h2228-client-result/summary.json`：按 0/1/5/10/20% 的 Direct/WBD 上下行分别列出 `*_app_udp_rtt_p99_ms`、`*_app_udp_missing_pct`、`*_app_udp_rtt_variation_p99_ms`、`*_tcp_goodput_1s_p01_mbps`、`*_tcp_goodput_1s_p99_mbps`、`*_tcp_sender_rtt_p99_ms` 等。另有 `h2231_*cases_observed` 和 `h2231_tail_metrics_qualification`，未测真实 P99 的历史案例仍标 `PARTIAL...`。
- `h2228-arm-relay-evidence`：路由器两个出口 netem 的真实内核发包/丢包、相邻阶段 before/after qdisc 数量，避免把配置 20% 直接宣称为业务层实测20%。
- 只有 **双向0ms/0损伤下直连 TCP≥800Mbps，并且 Tailscale 节点实际 DIRECT**，才具备判断产品带宽上限的实验资格。若 DERP/云间中继只有 20Mbps，保留真实 UDP/TCP P99 样本和崩溃诊断，但结论只能 `INFRA_RELAY_OR_DERP_UNQUALIFIED`，不可当作 Windows实体 WAN对比。
- 只有 `GITHUB_SHA` / run ID / UDP echo source 对得上的报告才能作为本轮 P99；静态单测或别的 run 的 probe 文件不合格。业务 TCP FAIL 不因 UDP 成功而变绿；反过来 TCP成功也不自动代表 UDP RTT 的 P99有足够样本。

现存 Windows Npcap 客户端3秒偶发崩溃、实体业务80–200Mbps、FEC/Normal/Game真实路径差异等尚未闭环。H2229 既有 ACK10ms、Linux window65535、无 HOL、外层表演式重传及 M2策略**均未在 H2231 修改**。

## CPU/RSS P99/H2231 原始进程资源长尾

仅实际 WBD iperf3 用例启动低开销 `process-sample`，读取原始Go客户端 root-owned pidfile 绑定的 `/proc/PID/stat`，强制进程 `comm=wbd-v4-client` 与启动 `starttime_ticks` 每次保持一致；500ms间隔测量 CPU utime+stime 相邻 ticks 差（`%_of_one_core`，可超过100%代表多核），RSS以实际内核 RSS页数转 MiB，不用 `ps` 自启动时均值冒充瞬时CPU。输出资源 P50/P95/P99、实采样数、worker中途退出/PID复用标志。3秒数据不足10次采样则 P99 unknown；没有 native pid时不伪造数字。资源文件 `resource-case-...json` 与 `probe-case-...json` 独立，不混入固定27个TCP源锁用例。

源码绑定的 H2231 性能证据与主线治理：源 `GITHUB_SHA`/Run ID 还绑定真实UDP和资源样本，不能从其他Runner/旧源码回填；新的 `tools/governance.py validate` 负例加入夹具 static，实际 `perf` 红灯保留。如有 DERP、CPU/RSS/P99 样本不足或实体Windows未测，严格标识，不提高任何虚拟性能结论。
