# M0 / H2227 — 实体 TCP 上行即断、80–200 Mbps 平台：双 Runner BBR/netem/iperf3 证据夹具（先夹具，不改重传）

## 用户提供的实体观测（不得改写为 Actions 已复现）

- 同线路同服务端 xray 约 1 Gbps，WBD Normal Off 与最高 FEC 业务只到约 80 Mbps，后来 iperf3 曾缓慢上升到 160–200 Mbps；多次高流量客户端崩溃或重新认证；上行 TCP iperf3 测 3 秒左右立刻断链，行为与前次早退一致。
- 用户早先明确纠正 fast.com 非根因：部分建链代际可以在持续测速下长久稳定，另一部分较早掉线。此处 `fast-like` 是多流量负载特征，**不是 fast.com 浏览器源码、HTTPS 协议或因果结论**。
- Off 与最高 FEC 的相近平台排除了仅按 FEC 比例解释，不证明外层表演式重传造成了拥塞。严禁因怀疑中间盒或拥塞算法直接修改/关闭既有外层表演式重传。先对 3 秒崩溃做 fail-closed 的源锁定实体复现。

## 测试拓扑：两个不同 Linux Runner，禁止单 VM 冒充

- `ubuntu-24.04` 原生 x86_64 与 `ubuntu-24.04-arm` 原生 AArch64 **两台独立 GH-hosted VM**，各自从当前提交 `GITHUB_SHA` 用 `tools/m0_plan029_linux_dual_native_build.sh` 构建原始 Go TLS 及 Rust M3/M4 ISA-L SO；任何 source SHA、run ID、architecture 或对端 Tailscale 100.64/10 IP 相同均 fail closed。Linux 上行不是 Windows Npcap 实体机重现。
- 两个临时身份用 Tailscale OIDC、`tag:ci` 进入相同 tailnet；`gh run download` 的 source+run 绑定元数据仅做 rendezvous。再用 UDP/4789 VXLAN 连接两台主机的**独立以太网** bridge/veth；真实 raw AF_PACKET FakeTCP 在其专有 netns `h227peer` 的 `wan0` 上运行，而非在 L3 tailscale0 上伪造一台 runner。
- 内部 `10.247.27.1/2`、外层限制 `wan0 MTU=1200`、Go 原始 V4 `--outer-mtu 1160`，避免 1280B Tailscale 下 VXLAN 额外包头导致测试基础设施分片。MTU 是实验参数，**不代表产品实体的1460配置**。宿主 `tailscale0` 及 GitHub 管理连接不施加 tc/qdisc。
- ARM64 同源 `--mode shared` 服务端、`10.66.0.1` 原始 TUN 和 `iperf3 -s -B 10.66.0.1:5201`；x86 客户端以 Native Go original TLS/Rust 开链获真实 `V4_PUBLIC_LEASE_APPLIED`/32。另开 `iperf3 -s -B 10.247.27.1:5202` **直接穿同一跨 Runner 加密 L2 网络但不经过 WBD**，记录基础设施上限。
- `sysctl net.ipv4.tcp_congestion_control=bbr` 且真实读回；只对原生内层 iperf TCP 和直接基线的 kernel TCP 生效。**外层原始伪 TCP 不具有 kernel TCP socket 的 BBR**，不开“强制绕过 TCP 拥塞控制”假门槛。

## 不偷改产品的参数矩阵

- 两个方向都施加 tc netem 到各 Runner **专有 wan0**：每侧 delay 5ms，独立 loss 0%、0.1%、1%、3%；每档先测同链路 4 并行流直接 kernel TCP BBR iperf3（5202），再测原始 WBD `--mode normal`（Normal Off）和 `--mode fec-fixed --fec-profile 6`（最高档）。两者都显式 `--outer-repair on`，不得修改代码中表演式重传。
- WBD 每一 mode/loss 使用真实原始 Go+Rust 新建链代际，需冷 READY 和 OS 租约实收，再 `iperf3 TCP -t 3 -P1` **先测上行崩溃**，然后 12s/1 流上下行、12s/4 流上下行模拟 fast.com 多并发爬升。`-R` 是真正 Server→Client 业务 TCP，不是外层 TCP ACK。P1/P4 的业务流、连接建立、上下行与 FEC 分离记录。
- 0% 丢包下单独做 Linux 产品 `--tun-fq-maxrate-mbps 600` 与显式 `0` A/B，其他 0.1/1/3% 保留默认600；仅为排除已有每流内层 TUN fq600 上限，**不修改产品默认值**。
- 每一阶段保存 `iperf3 -J` 的 end 和每秒 `interval_mbps`、内层 TCP retransmits、`ss -tinm` (含可核对 BBR)、`tc -s -j qdisc` 真实内核计数、link bytes/drop、client/ARM server 原生 TLS/Rust stdout/stderr、READY/lease/peer_retire/Health 字段及 client pid 存活与崩溃结果。失败数据记成 `ERROR` 和原始报错，决不以零 Mbps 冒充业务观测。
- 只在 0% 直连 4 并发流基线 >=800 Mbps 时，才将 WBD 上不去视为本夹具可支持的产品吞吐差异；若直连在 Tailscale/DERP/VXLAN 或 GH VM 上也 <=800 Mbps，则 ``INFRA_OR_TS_LIMITED...`，仍可验证 3 秒断链，但不能量化实体 xray 1Gbps 对比。哪怕基线够快，本夹具仍不是 Windows Npcap + 实体 ISP。

## 实际运行先决条件与受限状态

- 需要 repo secrets `TS_OAUTH_CLIENT_ID` / `TS_AUDIENCE`，tailnet `tag:ci` 和具有 Auth Keys Write scope 的 GitHub OIDC federation 身份，并授权仅 CI 节点相互 UDP 4789、TCP 18727；不能由构建脚本伪造私钥、直接加入别人的 tailnet。缺任一认证身份 **两个真正 Runner 的任务明确 BLOCKED/FAIL，任何本地 static selftest 不得宣称远程性能测试成功**。
- `tailscale/github-action@v4` 的临时节点在 Actions 作业结束后自动退出；不在日志泄露任何生产 route key 或账号。CI 使用仅本轮 run ID+SHA 的测试密钥、测试用户，不复用实体服务端密码。
- 先运行 `fixture-static` Python/Bash/负例和多 Runner 安全/矩阵校验，再按通过的真实 x86/ARM 接口与 iperf 原始日志确认造成 3 秒崩溃的首次状态转移。**本阶段仅测试夹具，不修任何 WBD 热路径、Health90、重传、缓冲、pacing 或拥塞控制策略。**

## 后续根因路线（待实际故障日志）

按源锁定案例逐层区分：1）同链路直连 BBR TCP 能否达参考容量、是否 DERP 中继；2）业务 TCP `ss` 拥塞窗口、RTT、kernel retrans、iperf 每秒爬升曲线；3）TUN fq/queue 与 0 vs 600 A/B；4）Rust M3 AF_PACKET 原始 TCP 发送/接收、Go TLS/背压和内存/CPU；5）异常代际 3秒首次 Health/remote retire 与同会话服务器时间线。用日志证明具体一处错误以后再单独修 TCP，其余参数不漂移。

```feature-impact
{"kind":"none","reason":"H2227 adds only source-locked two-runner authenticated Tailscale/VXLAN BBR+netem iperf3 fixture and tests, without touching product protocol, per-record M2, outer performative retransmission, Health or default parameters.","ids":[]}
```
