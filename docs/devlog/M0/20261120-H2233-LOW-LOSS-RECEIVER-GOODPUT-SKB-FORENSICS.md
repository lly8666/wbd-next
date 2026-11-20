# M0 H2233｜1%/5% 接收端 goodput 与 netem skb 粒度诊断（独立施工分支）

状态：**SOURCE_ONLY / REAL_THREE_RUNNER_NOT_RUN / PRODUCT_OPTIMIZATION_NOT_YET_JUSTIFIED**。本提交不修改原 Go TLS/认证、Rust AEAD/PN/TUN/ACK10、FEC、Health、机会式原密文重传、no-HOL 或 Stop。主线另有 PR #55 的 H2231/H2232 P99 author，不能覆盖或 rebase 其活动分支。

## 为什么只测 1%/5%

用户与既有 H2231 高速实测（Action 44749068787，SOURCE 24cd1260）发现 1% 目标下直连/WBD 的路由器 tc skb drop 计数和发包粒度差异；相同 netem 参数不等于对业务TCP段施加等价擦除。历史 summary 上传使用 iperf3 `sum_sent` 而非 `sum_received`，短测特别会高估实际交付。当前不能把差距直接归因于 ACK、重传、队列或 CPU。

## 本 SOURCE 仅做什么

- 复用原三独立 Runner（x86 客端 / ARM64 无 NAT 内核 L3 relay / x86 原 Go+Rust 服务端）及真正 kernel BBR、TCP iperf3、源锁/账号隔离/Stop。独立 SOURCE 下原本 27 例收为 2 个无损纯直连容量标尺 + 1% 和 5% 各 direct 与 WBD 上传/下载四流20秒，外加各档 WBD 原3秒单流上行存活门；共 12 例。
- 20秒业务 Direct 和 WBD 均下发 iperf3 TCP `-M 1037`；必须记录真实 `start.connected[*].mss`，否则 `UNKNOWN_OR_MISMATCH`，不得将参数写入当真实MSS对齐。干净 8流参考不改变 MSS，继续核 >=800Mbps 双向且 Tailnet DIRECT。
- 原 `mbps` 留作历史口径，新加 `receiver_goodput_mbps`、`sender_mbps`、双侧 bytes、实际 MSS；比较只能取同一个 case 的 `sum_received`。缺失/iperf 失败 => null，绝不补0或用 sum_sent 替代。
- 每例前后分别 remote ARM relay `tc -s -j qdisc`、`ip -s -j link`、`ethtool -k`，计算实际 qdisc 发出 skb、丢弃 skb、虚拟接口TX包数、GSO 比率线索。**skb 丢失率不是 inner TCP segment/用户字节丢失率**；需要原始 pcap 或后续 offload clamp 进一步断因。
- 首个分支 push 使用固定单程 200ms、零额外 jitter、1%/5% GE burst；`workflow_dispatch jitter=normal` 则是另一个单独Action，添加15ms stddev、25%相关性。Netem只作用 ARM 真实双向出口，没有 rate cap；未符合路径资格仍留完整实验结果但 FAIL_CAPACITY。
- 按案例保存原始 stdout、source SHA、run_id、MSS、TCP retrans、双方向 router qdisc delta、进程存活；不要从其他 Action 造同源CPU因果。H2231 的 UDP RTT P99 /CPU/RSS 在其现有独立PR维护。

## 退出/下一步

当固定延迟 + 抖动两个独立源锁合格样本有了，优先比较 netem skb 与内层 MSS/RTT/cwnd、receiver bytes。固定延迟下差距显著缩小则沿 jitter/packet scheduling 排查，若保持则查 Linux native WBD TUN TX queue/raw socket/service starvation：按秒入队/出队/年龄/唤醒/driver/drop 原有 owner 插入**诊断可关**计数，再做精准小补丁。队列放大、额外TUN排队、Go逐包、按序重排、外层重传修改都不是这步的猜测性修复。一次无效 Runner 若 DERP，判 INFRA_UNQUALIFIED 而不美化性能结论。

```feature-impact
{"kind":"none","reason":"H2233 only adjusts opt-in real three-runner Linux benchmark tooling, actual receiver iperf accounting and qdisc/MSS diagnostics. No runtime product feature or protocol modification."}
```

## H2233 固定200ms无抖动源锁真实结果

[Action 44764736732](https://github.com/lly8666/wbd-next/actions/runs/44764736732)，产品/夹具 SOURCE `6c1996ca21df742bde30f647513a037985cb64fa`，三台独立 Linux x86/ARM64/x86 Runner，原 Go TLS＋Rust native TUN，静态/ARM relay/server jobs SUCCESS；真实 TCP **12/12 完成**，但无损直连接收端 upload612.631 / download805.920 Mbps，**上行低于预定 800Mbps**，整轮 Action FAIL_CAPACITY。Tailnet flags DIRECT_CANDIDATE 不足以取代真实容量门。

1% GE burst + 每方向额外固定200ms、无15ms附加jitter：接收端直连 vs WBD 上行338.939/233.146Mbps、下行361.145/240.597Mbps（WBD 分别为68.8%/66.6%）。5% 上行243.588/130.708、下行178.258/81.684（53.7%/45.8%）。这是 **本轮测量事实**，不能同另一VM的旧15ms jitter Action相除称为产品收益或确证 jitter 因果。

单TCP case 前后真实 ARM qdisc：1% Direct 上/下 qdisc dropped/(emitted+dropped) 为0.1522%/0.1197%，但 netem emitted 与 link TX packet 比6.51/8.87；WBD约1.01%/0.98%且计数比接近1。5% Direct 上/下0.8678%/0.818%，相应比6.18/6.12；WBD 5.05%/5.09%，比约1。**qdisc skb 计数非 on-wire TCP segment计数**，历史“Direct实际仅丢0.2%”应保留为未证明的说法。原始 pcap/内核 segment 级擦除、RTO分解仍OPEN。

每条真实20s业务 iperf3 本轮请求 `-M 1037`，原 stdout `start.tcp_mss=1037` 只回显测试参数，不是已实测协商 MSS。第一个SOURCE在 `start.connected[*].mss` 寻找不存在的字段，故 `actual_mss_readback=UNKNOWN_OR_MISMATCH` 是正确的诚实资格。下一SOURCE使用测试中一次 `ss -tinm`，按原 iperf `start.connected[].local_port` 精确对齐，缺失不冒充MATCHED。

归档回执：[evidence JSON](../../evidence/M0/PLAN029-H2233-FIXED-LOW-LOSS-RECEIVER-SKB-20261120.json)；Action artifacts：summary 14646525298、x86 client 14646080452、ARM router 14645400731、x86 server 14646100470。原始 iperf/ethtool/qdisc 与真实Stop在本 SOURCE artifacts，不从下一 SOURCE 倒填。
