# M0 H2232 — TCP 建链 P99 / 三 Runner 压测心跳，不改原生协议

## 最新源码与已完成的真实观察

- 当前 main `ad6bef638faf0075e1923d2a97849dc255e6877a` 已包括 H2229 Windows/Linux Normal/Game 对外 **10ms authenticated presentation ACK**、Linux 稳态 TCP window 65535、TUN 无 HOL、原有乱序交付和表演式外层重传逻辑未改。H2232 绝不修改上述协议或 Rust hot path。
- H2231 三机 Action [44749068787](https://github.com/lly8666/wbd-next/actions/runs/44749068787) 原始源码 `24cd1260a22b693835c7fe579b2c8b4661ebbaee`；真实x86客户端→ARM64 Linux kernel L3 router→x86 WBD服务端，Netem在路由器两段出口添加单向200ms、标准差15ms的相关高斯抖动、Gilbert–Elliott突发丢包 0/1/5/10/20%。原始 WBD Rust/Go 及真实 Linux BBR iperf3 TCP 生效。无损 8路原生直连 **844.628Mbps上行、825.932Mbps下行**，Tailscale 本轮 direct candidate，至少达到800Mbps同路径容量门槛。
- 原始三机 27 案例 **26真实TCP完成、1失败**：20%丢包 `direct-downlink` iperf3约60s超时；WBD各档业务 TCP 均完成；不得把 direct 故障报告成 WBD 客户端 crash。本轮 full Action FAIL 还包括 H2231 旧脚本`python3 - <<'PY_H2231_GOV`未关单引号的语法错误；独立端和 ARM 路由原生 job SUCCESS。
- 0/1/5/10/20%时，20s 4并发真实速率（Mbps）：direct上行 `[492.818,295.845,134.953,8.651,1.678]`，WBD上行 `[315.561,118.119,40.578,43.411,1.887]`，direct下行 `[391.120,223.777,146.541,29.727,null]`，WBD下行 `[236.965,88.606,38.116,9.962,2.045]`。没有逻辑根据这些单次数据断定外层ACK/重传原因。
- H2231 保存 TCP 4流 sender `rtt` 20秒1Hz 样本 P99、iperf3逐秒Mbps的P01/P50/P95/P99、观测带宽爬升、kernel TCP retrans与cwnd、UDP应用Echo P99/missing以及 Rust/Go 原始进程500ms CPU/RSS。UDP P99 22/27有至少50个成功回复，**未包括独立TCP连接建链P99**。

## H2232 新增连接级诊断（测试夹具，不影响 WBD 业务）

- 新建独立服务器 socket：真实 Linux `TCP listen` 绑定经 ARM 中继直连 `10.248.82.2:45912` 和 WBD TUN `10.66.0.1:45911`；每个WBD与直连 iperf3 运行期间由客户端在相同 network namespace 以100ms间隔建立**最多120个真正独立 TCP 连接**，最多32个未完成 `connect()`，每次 kernel connect 失败、3秒超时及总成功数量都独立计数；不发送假SYN、假ACK、WBD per-record M2 或代理业务字节。
- 只在 **至少50个完成真实 connect()** 时计算真实成功样本的 socket `connect()` elapsed wall-clock P50/P95/P99，另报所有失败和未尝试样本的比率/原因。**3秒TCP上行门槛仅16个连接，P99为UNKNOWN**，也不以零代替。成功条件 P99 具有幸存者偏差，不能代替 TCP 失败率或精确包层单程 RTT。
- 所有 `connect-case-*.json` 与 `case-*` 的唯一对应绑定 SHA/Run ID、真实路径类型、origin、样本数、P99 数值和真实 Linux TCP socket，独立于 UDP `probe-*` 和 iperf `case-*`；缺失/伪造/样本少于50不得冒充 P99 PASS；真实 TCP iperf 应用仍以自身成功与失败判定。
- 客户端每一个20秒 iperf 案例在 **同一时间** 启动 UDP echo、TCP connect 和500ms WBD进程CPU/RSS采样，不串联等待产生人为吞吐偏差。ARM 中继仍只有内核 L3 转发、双方向 `tc netem` egress，无应用代理、无 TCP 终止或速率限制。

## Actions 编译后为什么会长时间无输出

- 三VM双方等待对端 Actions artifact `await_artifact` 在最坏情况下 `380×5秒 = 1900秒≈31分40秒`；另外三个 Runner 的身份/READY获取循环可等待 `150~160×5秒`。原先每次 `gh run download` 的 stdout/stderr被重定向到 `/dev/null`，无日志不代表正在跑吞吐。
- 单个真实完整 matrix：`2×12秒无损8流 + 5×(2×20秒直连+3秒WBD上行冷门槛+2×20秒WBD业务)=439秒≈7分19秒`，不含网络冷建链的5×最多42.5秒、ARM控制同步/短ping/高丢包TCP 60秒超时。原先所有 iperf3、UDP P99、资源采样真实日志都重定向到 evidence 文件，前台看起来像‘编译后卡住’。
- H2232 在原始测试脚本添加**每30秒跨机器artifact等待心跳、每10秒冷建链状态、每丢包档开始与每case完成摘要**（iperf业务Mbps、TCP connect成功/失败与P99、UDP echo P99）。日志不泄露密钥/PID环境和数据载荷，真实原始JSON留在Action artifacts；心跳不代替证明测试通过。
- 注意 GitHub Actions 的**静态测试失败**与产品原生 `iperf3` TCP 失败要严格分类：本轮静态 Bash heredoc 引号修复不是 Rust/Go 协议 bug；20% direct 下行超时是 TCP underlay 业务错误，不是 WBD进程退出。

## 当前待验证门槛

需要提交 H2232 源码并运行：Python/Bash 负例/治理静态检查、Windows/Linux H2229 ACK10与窗口静态确保不回退、真实三Runner相同 SHA 的直连/WBD TCP connect P99 以及原始 27 个 iperf3案例。若20%直连继续超时，须如实保留 Action红灯、TCP失败统计，不因夹具可复用而把整矩阵报绿。Windows实体3秒断链、80-200Mbps xray对照与严格 TCP P99的根因仍未定位。

```feature-impact
{"kind":"none","reason":"Only test-mode additions to a separately source-locked genuine three-runner TCP connect P99 experiment, progress heartbeat and evidence. No product protocol, ACK10, no-HOL TUN, outside retry or FEC change.","ids":[]}
```
