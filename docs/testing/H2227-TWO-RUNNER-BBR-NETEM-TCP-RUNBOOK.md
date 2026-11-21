# H2227 — main 上可复用的双 Runner 原生 TCP / BBR / 丢包压力实验

## 触发方式与边界

进入 **GitHub → Actions → `H2227 genuine two-runner TCP business` → Run workflow → 选择 `main`**。手动运行真实 x86_64+ARM64 两台 GitHub Runner，不依赖本地机器；如需针对一个 PR 测试，可在 Run workflow 选择包含此工作流的待测分支，其 `GITHUB_SHA` 就是唯一源码锁。不要由已有一次旧 PASS 来代表新提交。

通常 `push` 只做 Python/Bash 语法及 H2227 负例/矩阵静态单测；**仅 `workflow_dispatch`** 触发完整两台 Runner、原 Go TLS/Rust M3/M4 构建、真正内核 TUN、Tailnet 二层 VXLAN 和 `iperf3 TCP`。任一身份、组网、编译、有效业务证据缺失都必须 FAIL/BLOCKED，而非 0Mbps、PASS 或单机 netns 偷代。

## 已配置的外部先决条件

- GitHub Repository Secrets：`TS_OAUTH_CLIENT_ID`、`TS_AUDIENCE`。Tailscale GitHub OIDC federated identity 需 `auth_keys:write` 能给 `tag:ci` 发临时节点，且尾网身份策略允许 `tag:ci→tag:ci` 的 UDP/4789（VXLAN）与 TCP/18727（只允许临时随机 token 的 netem 控制面）。
- Workflow 的 OIDC 权限 `id-token:write` 仅用于真实 Runner 作业，静态作业不需要；两端节点独立密钥/真实 100.64/10 IP、原生 ISA 必须配对。可从 Action `h2227-*peer` source 和两端 `topology-*.json` 的相同 run ID/SHA/不同 VM 地址核对。不要将这些凭证写入仓库。
- `tailscale ping` 的 direct/DERP 结果和 0% 丢包的同对 Runner iperf3 直连基线非常重要。若 DERP/基础设施自身低于 800Mbps，性能结论必须为 `INFRA_OR_TS_LIMITED...`，不归因于 WBD 80Mbps；崩溃和掉链测试仍可判定。

## 真正跑什么

- ARM64 上原始 Go TLS + Rust M4 的 Linux `wbd-v4-server`/TUN/业务 iperf3；x86_64 上同 `GITHUB_SHA` 的 `wbd-v4-client`、现有原生伪 TCP/重传以及内层 `iperf3 -C bbr`。Linux 原始 `AF_PACKET` 需要可收发 Ethernet，故用 Tailscale 内加 VXLAN+独立 bridge/veth、每端测试专有 netns `h227peer/wan0`；不能直接把 L3 tailscale0 认作可用 Ethernet 原始套接字。
- BBR 是 **真正的 Linux TCP socket 的拥塞控制**，不等于对 WBD 外层 raw FakeTCP 加上了 kernel BBR，更不代表绕过物理容量。**外层表演式重传保持 `--outer-repair on` 且源码未改；不存在恢复逐包 M2 的步骤。**
- 在两端专有 `wan0` 配 `tc netem delay 5ms loss 0/0.1/1/3%`，绝不在 Tailscale 或 GitHub 管理网卡施加 impairment；每档对比同两 Runner 的直连 4 并发 BBR TCP vs WBD Normal Off / FEC最高（Rust *真实* applied profile6）。
- 每档业务 `iperf3 -t3 -P1` 上行首发崩溃门槛；之后 `-t12 -P1` 双向、`-t12 -P4` 双向，以真实 TCP 业务多流模拟 fast-like。0% 单独对照 Linux TUN `fq600` 与显式 `fq0`，不会改变产品默认设置。
- 仅在业务结束、原生监控 Stop 后核实 `V4_PUBLIC_FEC2_READBACK mode=fixed requested=applied profile=6 pending=false`；原始代码仅在 Stop 输出这一行。不能将业务开始前的 pending 当作 FEC 失败，不能用 requested 代替 applied。

## 读结果，不看单一绿色/红色

- `h2227-client-result/summary.json` 是机读收敛摘要；`classification` 为 `REAL_TWO_RUNNER_APPPATH_SCOPED` 只表示这次声明矩阵完整且 iperf3 均真实完成，不表示物理 Windows Npcap/ISP 问题解决。`FAIL_REAL_TWO_RUNNER_APPLICATION_OR_WORKER` 表示原样业务/Stop问题；`FAIL_INCOMPLETE_TWO_RUNNER_APP_MATRIX` 明确列出缺少的真实 case 名称，**保留已有全部业务速度与错误**。
- 原始痕迹在 `h2227-x86-client-diag`、`h2227-arm64-server-diag`：逐 case JSON 与原始 iperf 输出/逐秒 Mbps/TCP retrans，Go/Rust 两端日志、`netem` 的真实内核 dropped、1Hz CPU/RSS、TUN backpressure / queue_full_drops、内层 `ss -tinm` 的 BBR、`client_worker_alive_after`、session READY/Stop，以及 FEC6 Stop 后实档证据。若 `summary.json` 缺失只说明夹具本身失败/超时，绝不可宣称测得零业务吞吐。
- `capacity_reference=COMPARABLE_800MBPS_BASELINE` 才允许用本次 CI 比较 WBD vs 同路径直连速率；不代表和用户 xray 实体同 ISP/硬件完全等价。`physical_windows_isp=NOT_RUN` 持续保留。

## 当前已知物理与 CI 开口

用户实体报告 xray 1Gbps、Windows WBD 80/160–200Mbps 与 TCP 上行 3秒偶发即断；H2227 Linux 双 Runner 的 0% 配置丢包基线已达到约1Gbps、WBD Normal Off 单流约400Mbps/多流约600Mbps，**不能由 Linux PASS 覆盖 Windows 实体崩溃**。第一轮高 FEC 被错误的 pre-Stop readback 门槛阻断，修复夹具后需再次检查真实数据；会话代际失联、TUN 队列满和真实 FEC6 生效各作为独立排查线索。详见 `docs/devlog/M0/20261120-H2227-TWO-RUNNER-BBR-NETEM-TCP-THROUGHPUT-AND-UPLINK-CRASH-FIXTURE.md`。

此夹具是**实验和证据工具**，不会自动“修好 TCP”、改变 OS BBR 外层行为或变更 WBD 表演式重传代码。
