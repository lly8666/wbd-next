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

## 初次 Actions 状态：真实双 Runner 被认证门槛阻止，不是产品故障

- [H2227 Action 44681556694](https://github.com/lly8666/wbd-next/actions/runs/44681556694)：Python/Bash 夹具静态与负例检查 **SUCCESS**；两个实体跨 Runner 任务都在源码构建/网络连接**之前**由缺失 `TS_OAUTH_CLIENT_ID` / `TS_AUDIENCE` 停止，结论 `BLOCKED_TAILSCALE_OIDC_MISSING`，绝无可报的 TCP 测速、产品崩溃或 netem 结果。
- [H2227 Action 44682549769](https://github.com/lly8666/wbd-next/actions/runs/44682549769) 在补齐 3秒过早终止/DERP 限速/FEC6 applied/低频CPU-RSS 证据后：`fixture-static` **8/8 tests SUCCESS**；两真实 Runner 仍严格 `BLOCKED_TAILSCALE_OIDC_MISSING`，无已运行 iperf3 业务样本。此项不能报告产品 FAIL、80Mbps 重现或已解决。
- 追加基础设施完整性检查：服务端每次唯一随机控制令牌，按原始 Source SHA + Run ID + 成员真实架构验证；真实 Tailscale direct/DERP 路径记录；原始 iperf JSON、每秒速度斜率、TCP retrans、1Hz CPU/RSS/qdisc；3秒测试必须跑满请求时长的一定比例才算 PASS，进程存活而连接代际重新 READY 也算失败。FEC 最高档必须看见真实 Rust `profile=6 pending=false`，否则拒绝当成“最高 FEC 测试”。
- 全面夹具验证需由有授权的仓库管理者配置 Tailscale OIDC/tailnet ACL 后重跑。现阶段无法从本工具自行伪造 OAuth 身份或证明外部 runner 联通，**先保留草稿 PR，不合并冒充通过**。

## 后续根因路线（待实际故障日志）

按源锁定案例逐层区分：1）同链路直连 BBR TCP 能否达参考容量、是否 DERP 中继；2）业务 TCP `ss` 拥塞窗口、RTT、kernel retrans、iperf 每秒爬升曲线；3）TUN fq/queue 与 0 vs 600 A/B；4）Rust M3 AF_PACKET 原始 TCP 发送/接收、Go TLS/背压和内存/CPU；5）异常代际 3秒首次 Health/remote retire 与同会话服务器时间线。用日志证明具体一处错误以后再单独修 TCP，其余参数不漂移。

```feature-impact
{"kind":"none","reason":"H2227 adds only source-locked two-runner authenticated Tailscale/VXLAN BBR+netem iperf3 fixture and tests, without touching product protocol, per-record M2, outer performative retransmission, Health or default parameters.","ids":[]}
```

## H2227 run attempt 2 — 已真实联通、真实业务流、结果 FAIL（2026-11-20）

- [Action 44682549769 attempt 2](https://github.com/lly8666/wbd-next/actions/runs/44682549769)（H2227 测试源码 `1e833b3bf27d6ca6acb5ad9a1610b98647d47306`）：新 Tailscale 授权生效；x86 + ARM64 真实 Runner 组网、VXLAN、真实原 Go TLS/Rust M4、BBR 与 iperf 均实际运行。**静态 8/8 PASS，产品矩阵 FAIL，绝不是虚构 WBD 性能 PASS。**
- 0% 配置丢包 + 每侧5ms：同双机网络直连 BBR iperf3 4流上行 1,001.856 Mbps / 下行 844.284 Mbps；WBD Normal Off 1流上行 438.628 Mbps / 下行 414.164 Mbps、4流上行 650.781 Mbps / 下行 600.924 Mbps。3秒上行完整结束 454.057 Mbps，未重现实体 Windows 3秒崩溃。这一环境只有 Linux x86 原 Go/Rust 与 ARM64，而非 Windows Npcap；不能将其当作实体 80Mbps 病因已排除。
- TUN owner 0% Normal Off 稳态后 `queue_full_drops=153453`（600Mb fq）及 `204168`（fq0），伴随百万级 TUN TCP packets/backpressure。0% A/B 在4流上行约651 vs646 Mbps，fq600不是这组多流的单一硬限速原因；需要进一步跟踪 TUN 队列、原始 Rust send/CPU、受控流负载及同路径吞吐比。
- 当轮 FEC6 被夹具**错误提前停止**：源码 `r0/go_overlay/internal/v4productcli/linux.go` 的 `V4_PUBLIC_FEC2_READBACK` 是 `monitorPublicNativePeer` 退出以后、真实 Rust Stop 时才打印；夹具在首次业务前等待这一行，必然只看到 requested1/applied0/pendingtrue，导致“FEC6未生效”是假阴性，而非 WBD FEC6 真实性能证据。H2227 已修为先跑完整 iperf3，上行/下行结束后真实 Stop 读取 requested==applied 且 profile6/pendingfalse，不通过仍 ERROR。
- 不同丢包下后续建链也出现早退/未READY（0.1%、1% Normal Off 等），3% Normal Off 又能连接并完整跑3秒上行 197.138Mbps 和4流上行 520.756Mbps；不符合简单单调丢包阈值。失败来源应区分原始 TLS冷建链/同一服务端持有旧 lease/空闲Health90/本地进程退出，**尚无已证实的唯一根因**。
- 初次报告汇总器错误地规定必须有62个成功 `case` 才能产出任何 summary；这会把实测34个案例（27 PASS、7 ERROR）丢成 `FAIL_NO_REAL_MEASUREMENTS`。已修为按**精确12组直连 + 50组业务预期名称**计算缺失，保留所有真实 Mbps、错误、原始 JSON 与 FEC6 Stop 回读；结果 FAIL_INCOMPLETE 而不造假PASS。
- Main 复用方式：合入后 Actions → `H2227 genuine two-runner TCP business` → **Run workflow** → branch main，采用手动 workflow_dispatch，不把需要真实 tailnet 凭证、可能因现存产品错误红灯的长程双 Runner 压测作为所有 main push 的常驻必需 CI。当前 `push` 仅针对 H2227 开发分支的夹具改动自动触发，便于修夹具时复验。

## H2227 完整手动化推广与第二次跨机真实运行

- [Action 44697076045](https://github.com/lly8666/wbd-next/actions/runs/44697076045)，修复 pre-Stop FEC 错误后的源码 `eb025b436cd519cae338bee6bd59550a28217a4d`：静态9/9通过，两个独立 Runner 的 OIDC/VXLAN/原 Go TLS/Rust M4/BBR、内层真正 iperf 均实际运行。两端 Tailscale 本轮走 DERP，0%直连4流基线 **仅21.670Mbps**，所以不得将本轮 WBD ~20Mbps 叫做产品硬上限。
- 第二轮按来源锁定 **12组直连基线全部保留**、预期50个WBD案例实际观察30个（其中5个 FEC6 冷建链未READY，25个 iperf 成功），另缺失25个应有业务 case；摘要现为 `FAIL_INCOMPLETE_TWO_RUNNER_APP_MATRIX`，逐 case 状态、丢包、RSS、原始 iperf 数据均保留，不再误写 `FAIL_NO_REAL_MEASUREMENTS`。
- FEC6 无业务出量仍**不能**认定原生 FEC6 已通过。去除 pre-Stop 假门槛以后，其在这次跨机/同用户名连续建链场景仍卡在`V4_PUBLIC_PATH_CANDIDATE` 后、没有客户端READY；服务端未见对应认证FEC会话。原因未定（可能为复用用户名/前代会话、冷认证、丢包/调度或其他），不可直接写成真实 FEC 编解码错误，也不能以此停止未来测试模式的可复用性。
- 两次实验证明夹具本身可搭**真实不同 Runner**网络并测到真实内层 TCP；但产品高FEC及部分建链 FAIL。main 长期复用只开启 `push` 的 static 单测，**仅 workflow_dispatch 才连接 Tailscale / 启动两个独立 Runner / 做完整压测**。任何真实业务/认证失败保留红灯、归档原始证据，不设“让测试绿”的伪兜底。因主线无产品代码变动，主线治理与性能产品能力不可混为一谈。
- 机读证据：`docs/evidence/M0/PLAN029-H2227-TWO-RUNNER-BBR-NETEM-REAL-TCP-20261120.json`；使用说明：`docs/testing/H2227-TWO-RUNNER-BBR-NETEM-TCP-RUNBOOK.md`。用户实体 Windows Npcap 的3秒上行崩溃尚未在此 Linux 夹具复现，原表演式外层重传未更改。
