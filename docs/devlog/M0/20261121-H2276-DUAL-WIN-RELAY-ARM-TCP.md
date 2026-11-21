# H2276 · 双套真实 Windows–Linux 中继–ARM64 TCP 性能容量前置（WIP）

## 恢复事实
- main registry 仍为 M0-PLAN029-THROUGHPUT，main cursor H2245 过时；继续已登记 `experiment/m0-029-throughput-arm-fair` / Draft PR #68，未启动030。
- 当前分支最新产品修复 H2270（SOURCE b2743dd）Linux ARM64 1%/5% 原密文机会修复 R/F=1.089%/4.192% 成立，但同场 4TCP goodput 61.32/23.69Mbps、稀疏 TCP P99 727/1996ms，五端性能资格未过。高RTT场景 client SharedTun full=0，不能将零损高供给 H2261 的 SharedTun full 归为同一瓶颈。
- H2271 Windows source bb32770 signed Windows+WSL2 1%/5% Action44921318653/44921321136 全部 FAIL 于测试新监听 `H2271_REAL_KERNEL_TCP_LISTENER_NOT_READY`，不是 Windows TCP 性能失败；旧 Windows 10Mbps 主要 UDP H2269 也不代表 TCP 传输能力。
- H2272 SOURCE7e7df341 Action44922352895 1%/5% Linux ARM64 独立真实修复OFF三段 Nagle=0/1/0 通过。1%小TCP P99 1223.6/823.7/1709.3ms、bulk79.77/68.77/74.06Mbps；5% P99 2320.3/1407.3/2448.4ms、bulk42.66/38.14/44.05Mbps。显式服务端 TCP_NODELAY 可改善测试回显尾时延，但 CPU/总TCP吞吐并未改善，不能据此修改所有产品 socket。
- H2228 [Action44705243325](https://github.com/lly8666/wbd-next/actions/runs/44705243325) 原独立3runner是Linux x86客户端＋ARM relay＋Linux x86服务端；某批次 Tailscale DERP 曾把干净8流参考压到约19Mbps，故不合格网络不能把差距归因于产品。此前没有 Windows 客户端＋ARM Linux 服务端两套三runner同配置实测。

## 用户本轮明确目标和 H2276 最小施工
双独立组 a/b，每组恰好三台不同 GitHub VM：Windows2025 原生 Winsock 客户端、Ubuntu x86 Linux 内核转发relay、Ubuntu ARM64 Linux 服务端；Tailscale OIDC 临时身份、本组 SHA/runid/role 精确匹配。不同组同时执行，但每组内始终顺序干净无额外时延/0%、单程200ms/0%、200ms/1%、200ms/5%，每档相同真正内核TCP四bulk＋160稀疏TCP echo。Windows socket 本机单调钟计算 RTT P50/P95/P99和未回，服务端实际收取字节回执、真实 CPU 指标、每档实际中继 qdisc、最后Tailscale ping是直连或DERP独立保留。relay 内核 DNAT/SNAT 只变IP不终止TCP，tc prio 独立业务带只损坏TCP46973两方向；管理/Tailscale控制不进netem。无缓存填满/无产品源变动；两组均保留结果，不挑好组。无损零延迟容量参考达不到800Mbps或 DERP 时记 INFRA_UNQUALIFIED，仍作为业务诊断，不标记产品速度退化。

本增量复用现有 H2271 真正 OS socket 测试应用，单独加有限 server accept 等待；新增 `tools/m0_h2276_three_runner_tcp.py`、`tests/test_m0_h2276_three_runner_tcp.py`、`.github/workflows/qa-h2276-dual-win-relay-arm-tcp.yml`。**此增量仅是真正三机 TCP 拓扑/容量前置**，并未接上 Windows 原 Go TLS/Rust Npcap/Wintun 和 ARM 原 Rust TUN；因此这一前置成功仍**不是WBD产品 TCP PASS**。随后在已证实可承载的三机路由上接回原产品、同时测 Direct 和 WBD 四bulk、稀疏首次交付、各段 raw→M1→M4→peer RX→TUN的接受/丢失/CPU，再有针对性增加有界本机队列、批处理、服务预算；零损参考低于硬容量门不做异机的CPU归因。

计算边界：RTT约0.4s，200Mbps BDP约10MB、800Mbps约40MB，意味着端到端TCP在途窗口应按容量衡量；但 BDP **不等于**SharedTun M1 暂存队列应膨胀至相同字节。若将40MB缓冲在200Mbps本机服务前，单该层潜在排队就是1.6s，已明显违背 P99。必须区分内核TCP窗口、短时本机排队和上游损伤，不能凭128/64字样不经定位直接暴涨。

## 验证与交接
此次治理/测试源码 freeze后，先查询同SHA/同workflow Actions，不重复派。工作流分两套六个 runner，并强制实际 Win/ARM 收发及 kernel tc readback、源身份、原始 ZIP。静态或环境失败只保留错误阶段，不冒充三个完成的网络结果。若本轮途径经 TS/DERP 无容量，下一步换可验证直连方案，不拿受限下层替罪产品。跨端真实 NPF/Wintun/Rust、控制认证隔离和Stop依章程仍OPEN。旧 H2271 失败不擦除。

```feature-impact
{"kind":"none","reason":"H2276 isolated 2x3 native OS TCP throughput/latency topology and test-only bounded listener await; no production Go/Rust/config/default/driver/Stop change."}
```

- 额外竞态恢复：前期 H2271 夹具曾遗漏 CLI，已由独立 c5066db H2273 真实修复并启动新 1/5% Actions；另有 H2274 FEC2 并行 Action 44923756259 在途。本 H2276 是**不同的** Windows 原生跨机 TCP 容量前置，不将两个相同编号的研究合并或取代它们。当前 TCP 应用 PORT=45902 由最新分支源锁读入；H2276 仅 import Python server/client，不改 c5066db 活动文件。

## H2276 首轮已发生的夹具失败与修复
- 同一精确SOURCE `1ccf31022e54a73f29484340e82714c635f3f556` [run44924127257](https://github.com/lly8666/wbd-next/actions/runs/44924127257) attempt1：静态/单测 job SUCCESS，两套 Windows client、relay、ARM server 六个不同 Runner 已并行启动、组内相互拿到真实 peer artifact。**两套 relay job 136906426541(a)、136906426561(b) 都在内核 iptables/tc 配置完成后构造 relay-ready JSON 时 TypeError**：`dict(**own, control_token=own["control_token"])` 重复关键字；relay-ready 未上传，因此未进行本增量的任何跨机 TCP 吞吐/P99 业务样本。此错误仅为新夹具，不是 WBD TCP 真实性能失败；原 Action FAIL 如实保留，后续不能重用旧 SOURCE 重跑。
- 只删除多余 `control_token` 显式参数（既有 `own` 中已附带该 token），保留已有真实同源跨组认证、独立 Netem 分类/Stop。增加实跑 `configure_relay` 的 Python 全方法单测（mock OS 命令但实际执行 ready 组装）防止廉价静态只覆盖分散函数而漏掉返回值错误。新 SOURCE 的真实三 runner 网络结果保持 NOT_RUN 直至对应成功 Actions/ZIP 验明。

## H2276 两组真实三机连接失败、诊断性试验变更
- [Action44924415761](https://github.com/lly8666/wbd-next/actions/runs/44924415761) attempt1：两套 A/B relay 同run身份/真实Tailscale peer、port45902 DNAT/SNAT + 双向 TC 都完成配置，Windows与ARM真实监听亦运行；但两个 Windows client 均连接超时 `WinError10060`，ARM服务器第一档真实TCP accept超时，所有四档**没有吞吐/P99有效样本**。b组 Tailscale 最末ping对relay/ARM均是 direct candidate；所以不是已经证实DERP限速，也不是WBD产品失败。b组诊断 ZIP id14714503680与Windows id14715271982留档，内核netem预损伤读取发包0；无业务后一帧的细分iptabes计数，因此尚不能确定在哪个forward hook丢SYN。
- 跟当前 Tailscale 官方netfilter/source代码核对：Linux relay `tailscale0` 入→同一 `tailscale0` 出，Tailscale stateful new forward 规则可能先于自建iptables放行而丢包；这只是**可检验假设**，不是对发生原因的断言。下轮在原GitHub ephemeral relay的现有一次性tag/OIDC会话把该内核stateful filter设置为off；仍保留精确组内源/目标TCP45902的独立DNAT/SNAT/FORWARD ACL和两端TCP真实性，退出前恢复为true。增加只读业务后 `tc -s`、原port匹配 NAT/FORWARD 计数快照，真实Windows首次连接失败也保存结果+诊断（不假装payload/保密明文）。当前H2276候选下轮 `NOT_RUN`，任何缺失视INFRA_FAIL，不作产品效率资格。
- 若同一失败重现但计数能判断入relay SYN/出relay SYN，下一次针对实际零计数处修改;不重复推相同双组六runner。若内核路由仍不通，再比较H2228成熟VXLAN两段桥方案，不以用户希望吞吐高为由改产品队列。
