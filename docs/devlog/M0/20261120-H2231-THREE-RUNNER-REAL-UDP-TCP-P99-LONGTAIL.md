# M0 H2231 — 双段 ARM64 三 Runner 200ms/1–20% 网络下补齐真实业务 P99 性能长尾

## 已恢复的可靠进度

- H2229 原生 ACK10ms/65535/Linux Normal/Game、Windows Normal/Game 4/4 通过，真实业务乱序交付无新增 HOL；不得为吞吐擅改表演式外层重传、逐包M2或冷建链 Health90。
- H2230 [Action 44733044743](https://github.com/lly8666/wbd-next/actions/runs/44733044743) 同源码 Linux x86客户端 → ARM64 kernel三层中继 → Linux x86服务器，200ms额外单程延迟（jitter σ15ms、correlation25%）、GE目标0/1/5/10/20% 丢包：27/27 真实TCP应用用例通过，**但0损伤双向参考只有19.310/19.836 Mbps，因DERP/中继容量不合格，不能判断实体 Windows 80–200Mbps 的真实瓶颈**。历史证据不能擅自修改旧 `source_sha`，新增 `docs/evidence/M0/PLAN029-H2230-ACK10-ARM-3RUNNER-REAL-TCP-20261120.json` 独立描述 H2230 同源数据。
- 当前 main `ad6bef638faf0075e1923d2a97849dc255e6877a` 因光标 evidence_refs 历史证据 SHA 与 last_tested_source 不对应导致治理结构校验失败；H2231 调整 M0 cursor 为单一真实 H2230 source8f 的新证据，保留旧证据只读不重写，并缩短光标满足 32KiB 热预算。

## 真正测量的两个独立数据面

**TCP**：三 Runner 夹具 `iperf3 -J -C bbr` 原始 stdout 按 case 保留，`tools/m0_h2231_three_runner_metrics.py` 在真实 iperf 命令结束后解析逐秒 `intervals[].sum.bits_per_second`，输出每秒业务 Mbps 的 P01低尾、P50、P95、P99、平均、最小、最大、有效秒数，90%实测峰值出现于第几个秒桶，低于 P50/10 的停滞桶数。此“吞吐 P99”是**时间桶分布的高分位带宽**，P01才指向掉速长尾；不得把 P99 Mbps 当成网络尾延迟。若实际 interval 缺失，值为 null 而非 0。真实 Linux iperf sender 每 stream/interval `rtt`（微秒）转 ms 后给出 TCP RTT P50/P95/P99 和样本数量，`snd_cwnd`、TCP retransmits、每 GiB TCP retrans；只有 >=50 sender RTT samples 才输出 P99，不将 ICMP/外层伪 TCP 混入。

**真实业务 UDP RTT P99（原 ABBA/perf 关注的指标）**：在 x86 **服务端真实原生 WBD TUN** `10.66.0.1:45901` 与纯 ARM 中继两段直连 `10.248.82.2:45902` 分别监听小包 UDP 回显；Linux x86 客户端的同一测试网命名空间、同一个实体内层/直达路由中，在 iperf3 TCP 吞吐运行期间同时发送每100ms一个带当前实例随机 nonce 和序号的小包。20秒压测内发 120 个 UDP 请求，计算可信正确、唯一 echo 的应用往返时间（`monotonic_ns`，非外层 FakeTCP ACK）、业务 UDP 包缺失比例、连续缺失 burst 峰值、相邻 seq RTT 变化的 P99，实际 RTT P50/P95/P99 和 sample_count。>=50有效应用回包才标定可靠样本 P99；3秒案例只发16个以保持短生命周期崩溃检验，因此 P99=null且显式 UNKNOWN，**不伪造较大的样本数**。

同链路 Direct 与 WBD 应用 UDP 回显使用完全独立端口与 source 标签，并与 TCP iperf3 独立统计：UDP 收到不等于 TCP成功；TCP按原 iperf 完成/worker存活硬门槛；未观察真实UDP时 P99 `null` 且 status `UNKNOWN_NO_REAL_APP_UDP_PROBE`，不装作0ms。记录端到端业务 RTT，包括队列、调度/echo处理，不能冒充纯网络单程延迟。后处理只添 `h2231_tcp_tail`，`probe-case-...json` 独立文件不会混入 27 个 iperf 的 `case-*` 业务数。

## 夹具不引入瓶颈/不伪装直连

- ARM 中继只负责 Linux kernel IPv4 L3 forwarding + 双出口 qdisc `netem`；**无速率限流**，也不运行 UDP echo 服务。echo只在真实服务器 netns；低频每100ms百字节探针只有 kbps 量级，瓶颈判定仍要求完整三Runner Direct链路无损双向>=800Mbps且真实Tailnet DIRECT，DERP则仅可信故障而不做容量归因。
- P99 与 tcp 业务数据在一次测试里同源 `GITHUB_SHA`/run ID、原Go TLS/Rust、200ms/1/5/10/20% GE loss，公开在 `h2228-x86-client-evidence` 每case原始日志和 `h2228-client-result/summary.json` 的 per_loss 字段。全部历史旧 H2228 记录缺 P99 应标记 `PARTIAL_OR_NOT_RUN_OR_MISSING_REAL_METRIC_RECEIPTS`，不得倒填合成量。
- 兼容 H2228 branch 自动真实三Runner；`main` 上原状保持 push 仅静态 + 手动 `workflow_dispatch` 完整真实压测。若 GH Runner Tailscale DERP 不直连，保留明确 `INFRA_RELAY_OR_DERP_UNQUALIFIED`，不放宽基线阈值。

## 本阶段结论边界

H2231 仅修改测试夹具、指标分析、Actions 及 M0 证据/光标，不修改原生 TCP ACK10ms、窗口65535、TUN乱序交付/FEC/重传，更未处理实体 Windows Npcap 上行3秒偶发重启。新的跨机实测 P99 只有在对应 GitHub 运行产生真实 `probe-case-*.json` 时才能报告数值；单测不构成该证据。

```feature-impact
{"kind":"none","reason":"H2231 adds source-locked optional three-runner real UDP echo/tcp P99 performance harness, tests, evidence and cursor correction only. Existing Linux/Windows native data/ACK/FEC protocol and outer performative retransmission are unchanged.","ids":[]}
```
