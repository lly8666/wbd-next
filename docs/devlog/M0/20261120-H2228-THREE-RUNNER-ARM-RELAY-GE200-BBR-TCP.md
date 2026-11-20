# M0 H2228：三台独立 Actions Runner — ARM64 Linux 内核路由中继、200ms 单程与 1/5/10/20% 真丢包原生 TCP 压测

## 实验目的

针对用户 Windows 实体设备 xray ~1Gbps、WBD 80–200Mbps 并有 TCP 上行3秒断开的报告，独立排查模拟真实跨国/高时延有丢包链路的 **原生 kernel TCP 业务速率**；对比**经同一ARM64中继直接 iperf3** 与 **经同一ARM64中继且经真实 WBD原 Go TLS/Rust M4/内核 TUN 的 iperf3**。不得把 Linux Actions 的通过或失败误称实体 Windows Npcap 根因已锁定。

## 真实三机拓扑和基线

- 客户端 x86_64 Ubuntu24.04 GitHub Runner ↔ ARM64 Ubuntu24.04 原生 Runner ↔ 服务器端 x86_64 Ubuntu24.04 Runner；三个不同机器各自 Tailscale GitHub OIDC 登入 `tag:ci`，强制相同 `GITHUB_SHA` 和 `GITHUB_RUN_ID`、独立 `100.64/10` tailnet地址，ARM64不得兼任 endpoint。节点元数据 via `gh run download` 同一 workflow run 配对，独立真实架构 check。
- Client↔relay VXLAN VNI2281，relay↔server VXLAN VNI2282，端点分别 `10.248.81.2/24` 和 `10.248.82.2/24`，ARM64内核 `h228rt` 拥有 `rcli0=10.248.81.1` 与 `rsrv0=10.248.82.1`，`net.ipv4.ip_forward=1`，显式 `ip route` 真三层包转发、**不做 NAT、不做应用代理/数据复制，也不容许直接 L2 到另一 endpoint**。每个 endpoint 原生 `wan0` 原始 AF_PACKET FakeTCP、真正 Go TLS/Rust native和 TUN；只能路由另一 endpoint /24 经 ARM router gateway，真正 TTL 减1。
- ARM64 的 kernel router 收发两层独立 VXLAN（各端只与 ARM 的 Tailscale peer 联通）。Tailscale 是承载加密网络，**不是丢包计数的位置**：宿主管理 `tailscale0`/GitHub Actions连接完全不设 tc。客户端/服务端本地 `wan0` 也不设 netem，以避免单机净化或多重重复损伤假象。
- Relay 不设置 tc `rate`/TBF/HTB 或系统人工吞吐上限；仅 `tc netem` 在 `rsrv0` 出站作用于 client→server，在 `rcli0` 出站作用于 server→client。首先设置0ms/0% 并测相同三Runner基础线路 **P8直连 BBR TCP** 12秒上/下行，及 relay CPU、softnet_stat、真实网卡计数、tailscale ping 直连/DERP；只有双方直连方向都 >=800Mbps 且 Tailnet 两段都 DIRECT，才叫“本夹具 relay已证明非明显瓶颈”。若 DERP/ARM CPU/跨TS隧道限速，仍记录所有 WBD/直接测试，但标 INFRA_RELAY_OR_DERP_UNQUALIFIED，绝不把它归因 WBD。

## 单程200ms / 随机波动 / 丢包如何更贴近真实网络

- 每次案例 ARM64 relay 出站 qdisc 单向**添加200ms**（向 server200ms、向 client200ms），目标端到端 **附加 RTT≈400ms**，总实测RTT=基础两条Tailnet链路时延+上述损伤；内核 `ping` 实测记录 `rtt avg` 而不伪称恰好400ms。每个方向的 `netem delay 200ms 15ms 25% distribution normal` 模拟平均200ms、15ms高斯抖动和25%相邻延迟相关性；这可以模拟实际长距离线路的小幅 jitter，而非静态固定人工时钟。
- 比纯 iid 抽签更贴近部分现实网络的**簇状丢失**：采用 netem `loss gemodel p r 1-h 1-k` Gilbert–Elliott 两状态。假设坏状态每包丢失90%，好状态每包残余损失0.1%，坏状态离开概率25%（平均持续约4个包）。根据目标丢包率`L`解平稳坏状态概率 `q=(L-0.001)/(0.9-0.001)`、好→坏转换 `p=0.25*q/(1-q)`，使长期理论平均达到1%、5%、10%、20%。这是明确限定**实验流失概率的统计模型**，不是宣称用户实体ISP一定服从GE。
- 同一工作流输入 `model=iid` 可把丢包换成独立 Bernoulli `netem loss random L%`，其余网络/业务完全不变，便于因果对照。每阶段保存两条 tc `-s -j qdisc`、目标丢包与包/丢计数；样本数有限或GSO/GRO的丢包粒度影响与目标偏差都必须解释，**不能因为设置5%就说实测精确5%**。
- 两边 netem `limit=65536` 个包，不设人为 link rate，覆盖近1Gbps×200ms约25MB BDP，避免过小Qdisc在200ms出现无关人为队列溢出。两端Linux inner TCP设真实 BBR并调大内核 rmem/wmem到64MiB，满足1Gbps×400ms≈50MB 的 TCP 长肥路径窗口需求；直连与 WBD使用**完全相同的真正内层 BBR iperf3 -C bbr**。外层原始 FakeTCP 不属于 Linux TCP socket 的 BBR。

## 实际业务矩阵、失败与证据

- 0ms/0%直连基础容量：8并发、12秒，上/下行2组。随后 `200ms +15ms高斯jitter` 且 0%、1%、5%、10%、20% 丢包分别执行**经relay、不经过WBD的 4并发真TCP iperf3 20秒上/下行**，以及**同relay、经原 Go TLS/Rust M4/内核TUN的 WBD TCP**（先3秒单流上行早退回归、再20秒4流上行/下行）。共12组直连 +15组 WBD，全部附 case-id、原始 iperf JSON和逐秒Mbps/重传、Netem qdisc、Linux netns、原生来源/真实OS租约/Go-Rust日志；部分故障不能把完整成功矩阵伪造出来。
- WBD `--mode normal --outer-repair on` 是默认控制，手动 `mode=fec-fixed` 是独立真实FEC6变种，**只可在业务发完并真实Stop后以 Rust`requested==applied profile=6 pending=false`认定实际应用**，保留H2227首次夹具 pre-Stop 误判的纠正。
- 每个损伤档位分配唯一 `bench0..bench4` 客户端账号/安装身份/原始TCP源端口，避免错误把前一个session的重复账号lease当做TCP重连根因。服务端同一443真实共享 Go TLS/Rust owner，跨档不改业务代码。仍会诊断真正的早退和session抢占，不假定已修复。
- `H2228`只修改 `.github/workflows/`、`tools/`、`tests/`、`docs/`，原生 Go/Rust `r0`、Health90、FEC策略、表演式外层重传及M2逐包控制**全部未改**。CI静态自测通过只表示夹具语法与约束通过；真实三Runner互联、TCP性能必须看单独真正应用数据。用户实体 Windows↔Linux WAN 仍 NOT_RUN。

## 复用入口

Actions → `H2228 Three distinct runners routed ARM relay 200ms one-way 1-20% real TCP` → Run workflow → 选择 `main` 或本实验分支，选 `model=burst`（默认）/`iid`，`mode=normal`（默认）/`fec-fixed`。普通 main push 只跑快速夹具静态测试，不跑高成本真实跨机；本实验开发分支 push 可自执行三Runner实测以修复夹具。OAuth/OIDC secrets 沿用已有 TS_OAUTH_CLIENT_ID、TS_AUDIENCE 和 tag:ci，不在客户端日志泄露凭证。

```feature-impact
{"kind":"none","reason":"H2228 adds three distinct runners / ARM64 routed kernel netem / BBR iperf3 benchmark tooling and documented evidence only; no WBD product protocol, retransmission, FEC, Health or runtime changes.","ids":[]}
```

## 2026-11-20：初始 Actions 故障分型（不冒充测速结果）

- [Run 44703215435](https://github.com/lly8666/wbd-next/actions/runs/44703215435)：真实三Runner登录及ARM64 Linux 两独立 VXLAN+内核转发成功，x86原始Go/Rust构建成功；服务端新 netns 只读取 BBR 未显式设 BBR 导致 `H2228_FAIL_CLOSED_NAMESPACE_BBR_READBACK`。这是夹具设置错误，无任何已测业务吞吐。改为每个 namespace 写入并读回 BBR；新增单测。
- [Run 44704087379](https://github.com/lly8666/wbd-next/actions/runs/44704087379) 和 [Run 44704214589](https://github.com/lly8666/wbd-next/actions/runs/44704214589)：上述BBR改正后，3台独立Runner均实际在线、ARM中继和x86原 Go/Rust服务端启动；客户端开始前通过 `http.client` 连中继的 TCP18728 控制面超时。是 Tailnet ACL/控制端口基础设施问题，不是WBD TCP中途崩溃，**不能给这些动作报测速 Mbps**。初始版 H2227 已在用户 Tailnet 成功使用 TCP18727，本版修复成同一 proven `18727`、先验证 relay socket bind、客户端有界轮询健康探针、明确 FAIL 而非 Python traceback。
- 后续只有出现真实 `h2228-client-result/summary.json` 且包含 `12` 组直接TCP与 `15` 组WBD TCP、对应每档实际 qdisc/RTT，才允许总结五个 loss 档速率。中继如果走DERP或无损直连8流低于800Mbps，还要单独标 INFRA_UNQUALIFIED，不允许诊断 WBD“只能80Mbps”。
