# H2228 三台真实 Runner：ARM64 中继单程200ms、1%/5%/10%/20% 丢包的原生 BBR TCP 速率复现

## 运行入口

GitHub → Actions → `H2228 Three distinct runners routed ARM relay 200ms one-way 1-20% real TCP` → **Run workflow** → 选 `main`（合并后）或当前 H2228 实验分支，设置 `model=burst`（默认短突发 Gilbert–Elliott）或 `iid`（随机独立丢包），`mode=normal`（默认 Normal Off）或 `fec-fixed`（原 Rust Fixed6 post-Stop 真实 readback）；运行入口只取当前 workflow 的 `GITHUB_SHA`，源锁定 Go TLS/Rust ISA-L 构建。

实验分支 push 自动跑真实三 Runner 用于校验 fixture；main push 只跑静态单测。不得以静态 PASS 表示产品 TCP PASS。真实业务失败结果为红灯，所有完成的真实业务数值依然保留。

## 组网：两条分离的以太网、不允许绕过 ARM

Client GitHub Ubuntu x86_64：owned `h228node/wan0=10.248.81.2/24` → 同 Source SHA 的 Tailscale OIDC `tag:ci` → VXLAN VNI 2281 → ARM64 GitHub Ubuntu，root bridge `h228bc` / router namespace `h228rt/rcli0=10.248.81.1/24` → Linux `ip_forward=1` → router `rsrv0=10.248.82.1/24` → 另一个 root bridge `h228bs` / VXLAN VNI 2282 → Tailscale → Server GitHub Ubuntu x86_64 `h228node/wan0=10.248.82.2/24`。

端点的对端 /24 路由必须使用所在网段的中继 `/24` 网关。中继不做 NAT/应用代理/限速，不通过第二条同网段桥接客户端到服务端。Linux 内核 IPv4 TTL 真实减一。原生 WBD FakeTCP 在两端物理-like `wan0` 的 AF_PACKET socket、原始 Go TLS 和 Rust M4/TUN，服务端 443 + 租约 10.66.0.0/24。另直接 Linux TCP `iperf3` 服务端在 10.248.82.2:5202，WBD 内层真正 Linux TCP `iperf3` 服务端在 10.66.0.1:5201，两者都经相同ARM路由出口。

## 损伤位置与真实网络统计

仅在 ARM router namespace 的 `rsrv0` **client→server** 与 `rcli0` **server→client** 的 tc 出站装 `netem`；其他网卡 `tailscale0`、Actions 管理平面、两端本地 `wan0` 都不 shape。每方向在中继只出现一次 200ms 均值、15ms 正态波动与25%延迟相关，期待跨两方向附加 RTT ≈400ms；以端到端 ping RTT 数值为实收证据，勿把配置值当成精确测量。

默认使用 Gilbert–Elliott 突发丢失，目标长期平均 1% / 5% / 10% / 20%，坏状态90%掉、好状态0.1%掉，坏态平均4包。`iid` 单独作为独立随机损失对照。所有场景有原始 qdisc kernel bytes/packets/drops/backlog、尾网路径和 Linux 进程资源计数，用户实网不一定按GE分布；需要注意 GRO/GSO 下 packet drop粒度。Qdisc `limit=65536` 包，**没有人工 rate cap**。

真实宿主 `tailscale0` 只承载加密互联。中继控制面 TCP18727（与此前验证通过的 H2227 相同）、随机每次 token + 真实 source tail IP 白名单、仅可调用 0/1/5/10/20%、0/200ms与模式白名单；不能注入任意命令。GitHub Secrets `TS_OAUTH_CLIENT_ID`, `TS_AUDIENCE` 与 `tag:ci` 配置由用户尾网授权，不放进日志。Bbr 与 `tcp_{r,w}mem` 64MiB需在**各新建业务 netns**显式设置并读回；Raw FakeTCP 外层不属于 kernel BBR，也没有恢复 M2 或更改表演式外层重传。

## 结果口径

- 先在 relay qdisc `0ms/0%` 做直连 `iperf3 -C bbr -t12 -P8` 上/下行，共2组；若任何方向达不到800Mbps、两段 Tailscale 任一 DERP，**本次不能把吞吐差异直接归因为WBD**。中继 CPU/RSS/softnet也需查实际数据。吞吐并不保证与实体Windows 1Gbps ISP 精确相同。
- 每个 `loss=0,1,5,10,20` 在 `200ms单程+15ms jitter`：中继直连 `iperf3 -C bbr -t20 -P4` 上/下行共10组，另经真实 WBD 的 `-t3 -P1` 上行崩溃门槛、`-t20 -P4` 上行和下行共15组。**完整共27条业务样本**，必须按原始 per-case 名称核对。没有 WBD READY 不视作业务0Mbps或跳过后绿灯。
- 每档独立用户名 bench0..bench4、短期安装身份和本地源端口，减少前代同账号会话污染。FEC6 只有经业务结束/原生 Stop 后的 Rust真实 `requested=applied profile=6 pending=false` 才能证明应用，不能把提前 Stop 的 pending0 当作 FEC故障。
- 原始 JSON每秒速率曲线、真实 iperf 连接时长与错误、逐档内核丢包/qdisc backlog、实测RTT、进程与原 Go/Rust日志在 `h2228-x86-client-evidence`、`h2228-arm-relay-evidence`、`h2228-x86-server-evidence` 归档。`h2228-client-result/summary.json` 归纳每档直连和WBD的 up/down Mbps，并明确 relay容量是否已被证实。
- 完整通过 `PASS_REAL_THREE_RUNNER_TCP_MATRIX` 表示所述业务样本全部跑完，**不代表业务达到1Gbps**；`FAIL_INCOMPLETE_THREE_RUNNER_TCP_MATRIX` 列出具体缺失case且保留有效样本；`FAIL_REAL_THREE_RUNNER_TCP_OR_WBD_COLD` 表示真实上行、认证或Tcp报错。若拿不到 summary，必须先排除授权、Netns、Control、调度、构建或其他夹具故障，不能冒充产品测速。

**当前物理缺口：Windows Npcap 对 Linux 服务器的早期崩溃和同线路 xray 1Gbps 是用户实体观察；本实验只涉及三个Linux GH Runner、Tailscale/VXLAN、真实原始Go TLS/Rust M4，无法直接证实其Windows特有根因。**

## ACK10 最新主线复测门槛

H2229 main ACK10/65535 真实原产品 Windows/Linux Native 测试已完成。H2228 早期测速都来自其之前的源码，不可冒充已测试新版 ACK。H2228 最新源码在每次静态检查中同时跑 `tests.test_m0_h2229_native_ack_unified`，手动/开发分支真实三机都各自按新 `GITHUB_SHA` 构建原始 Go TLS/Rust M4；把三机新实验与旧 ACK/旧 DERP 数据分开保存。真实跨机环境可能因 Tailscale DERP 从800Mbps下降到20Mbps，必须优先看两段 direct 和0ms双向基线，再看200ms GE1/5/10/20% WBD/直连数据，且真实 TCP 测试错误不等于进程崩溃。
