# PLAN028 H1277 — 按原生 30 分钟失败取证纠正 Game4 整组重连归属

2026-11-06。实际 SOURCE：H1276 `226b3fe367a4613a38c8208441b0ca29fb2fd8c8`，原生 ARM64 [Action42174970877](https://github.com/lly8666/wbd-next/actions/runs/42174970877)，build PASS、baseline/heterogeneous/pressure **均失败**，每场执行真实1800秒五认证客户端，共三个源锁定 artifacts SHA256 列于 [H1277 after-action evidence](../evidence/M0/PLAN028-H1277-H1276-1800S-SOURCE226B-ACCEPTANCE-20261106.json)。

关键发现：Baseline Game4 Dave 上行物理 1% 随机丢包，真实业务却损失45.536%（18分钟内前17分钟正常，从minute19-30交付归零），10ms 活跃发送无接收最大 **775920ms**，但同设备下行继续交付。这不是 1% TC 的随机效应，也不是一个 Go 测试告警误报。客户端在06:51:55收敛/Stop原Game4组，在06:51:59重新做真实 TLS 并使四 lane 新Rust GameAdapter READY。服务端却在06:51:57-59将全新4条本地源端口 `59881/59882/59883/59884` 逐个放进原来的 `V4_PUBLIC_GAME_SINGLE_LANE_READY` 单lane热替换分支；相同物理IP、MSS/record budget 导致旧代码误判。这直接产生双方 native group 生命周期不一致。已有 Game4 只用物理IP与budget来区别组重连，不足以区分同路径旧组失活之后的完整冷启动。

新窄修复：使用**已经在原始加密 TLS 保护内**的初始客户请求 `V4Extension.Epoch`，而不是服务端回给用户的重复 epoch。完整 Game4 启动（含原生组失活后的同IP新整组）第一lane请求 `Epoch=0`；逐lane热重认证请求显式历史非零 epoch。服务端在原有真实 `EstablishServerV4` 成功 Go credential/protected TLs + Rust M1 Commit 后冻结 requested-zero 标志。只有 `ColdSnapshot()` 验证过的 `V4LinuxGameAuthenticatedLane` 可读取，不能根据伪造 SYN、TCP源端口、未认证定制标志获得权限。服务端若发现受保护整组起始，先保持旧完整Group，放入旧 `pending` cohort；后续同 cohort 的显式 epoch lane **优先加入 pending**；只有全部四个真实原Rust M4 commit完成后才把旧组 exact Stop。仍保留此前针对真正外网IP/record budget改变的原 A→B 原生完整替换路径；Game2 全组行为不变。没有新增TLS字段、PN、AEAD、FEC/复制调度、监听端口、控制反馈或第二恢复器。

新增原始Go真实TLS单测 `TestPLAN028Game4ProtectedEpochZeroWholeGroupVsSingleLane`（同服务端逻辑epoch，新整组ZERO与单lane显式非ZERO；未认证冷快照不能赋权），构建即执行。不改变已限定共享TUN 8包/64KiB/100ms上限，仅修 H1276 队列连接已断开时重复计数的诊断笔误。

其他真实问题不得掩盖：H1276 Pressure Carol Game2 Gen8 只有客户端READY，没有匹配服务端双lane M4，双向93.3秒断流；Pressure Dave TUN overflow=3227；异构/高压 Erin 仅7次成功整组（低于10次），TLS cold候选分别40/32失败，仍有1–5秒交付空洞；Game4 异构本地7/服务端匹配5，高压9/8。Baseline Bob与Pressure Alice从H1274 ~70秒改为H1276 0–30ms只代表这次测量改善，不能证明根因消除。R实际accepted record字节baseline183.059MB、hetero432.951MB、pressure550.345MB；R/(F+R)分别0.69264/1.09642/0.73557%，不包含控制C、FEC parity、IP/TCP/L2。

新 `.github/workflows/m0-plan028-h1277-arm64-30min-game4-protected-rejoin.yml` 同SOURCE原 Go TLS与Rust库原生ARM64双端、一份产物供三台并行 runner每场完整1800秒。必须实测真实 server Game4 FULL_GROUP M4 及精确旧Stop，五客户端所有30分钟业务UDP/TCP/p99/gap/TC/CPU/RSS/每租约TUN队列/表演式repeat record；**任何report alerts/换代失败都让CI失败**，不允许构建绿灯即宣布性能PASS。首个源锁定 Action [42184053868](https://github.com/lly8666/wbd-next/actions/runs/42184053868) 在 `FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch: internal/realityfront/admission_v4.go` 处拒绝 **PRE-BUILD**，三场均 SKIPPED，绝不计入1800s产品证据。H1277 追补清单中原始受保护 TLS 实现和 Go 单测对应的两个 Git blob SHA；不得放宽 Assembly 检查。新版 SOURCE 同步 workflow push filter后再次触发，结果仍 UNVERIFIED。H998旧same-socket在线MTU FAIL及H1259/H1268 S2C间歇故障保留。

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Correct original Game4 same-physical-path full authenticated cohort restart versus existing single-lane hot reauth using frozen credential-verified TLS requested epoch and original pending/M4 owner, without new wire/policy."}
```
