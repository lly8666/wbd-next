# PLAN028 H1541｜近三日修复的默认产品源码接线审计＋Game2 跨代混组原生修复

本轮按用户“最近几天修复默认应用”检查 **真实原 Go checkout 装配链、Linux x86／ARM64、Windows canonical manifest、Rust native source+ABI**。截至主线父 SHA `9a0efb6cb22a50af9fe8d86d1e4031957d503023` 逐项结论如下。

### 原始 H1540 真正回归（不是编译或报表代理）

- [真实 Linux loss30 Action42798005082](https://github.com/lly8666/wbd-next/actions/runs/42798005082) ZIP13754549150：0–600s真实双向外层 **303.015 Mbps**、200ms双向30% tc、六个独立 native Stop 全有；Go真实预分流 64/65 条正反单测均 PASS。H1531 被旧Go交接Abort导致缺失的**五次 Game4 热lane M4在服务端全部真实提交**；lane3源59341发生早期暂存容量满，`transition_state=1=Prepared`且成功 native M4，表明 H1285 11文件默认安装修复生效。Game4 这项 **PASS_SCOPED**。
- 这**不是整场 PASS**：Carol Game2 客户端第8代真实lane1/2是 `57255/57256`；服务端旧第7代失败残留 lane1 `49336` 与新lane2 `57256` 被同一 protected principal+tunnel+epoch 误配对为 Rust M4 cohort，服务端第8代原生完整M4**不成立**。真实 app 双向 receive gap **154170/144290ms**、TCP收0；整体 **FAIL_REAL_NATIVE_OWNER_OR_BUSINESS**，保留原始证据。

### 产品修复与每次默认组装检查

- `r0/go_overlay/internal/v4productcli/game_linux.go`：保持原 Go TLS 认证和 epoch 不变，给同一 client-source/one-server-destination 同代连续2/4源端口的候选增加 `originalGameColdFlowKey`；多条独立旧/new暂存组在 bounded map **分别等待、分别过期、分别Stop**。只把可读的真实 TCP 5tuple 当 **同代join constraint**，绝不是 TLS 身份、Rust M4/Health或来源路由授权；一个旧候选无法再假冒完整新 cohort。Game4 hot单lane仍用原 native ReplaceSlot，新的 5tuple key 只管 cold全组。原先 same protected epoch单独分组不再可触发跨代假提交。
- `r0/go_overlay/internal/v4productcli/game_cold_cohort_linux_test.go`：精确模拟旧 `49336` 与新 `57255/57256`，验证同账户epoch不可混组；同时四lane、server目的443、physical客户端IP、端口越界均强校验。
- `tools/arm64_public_go_rust_bundle.sh`：之前锁了一份旧手工 Realityfront+v4productcli复制名单，且末尾出现拼接错误的未闭合 `go test`、重复构建块；即使 main 修过代码也可能**打出旧ARM64产品**。现在改为与 Linux x86 **一致**：同一原始Go a7a82、同一 11 文件SHA manifest安装脚本、同一受保护 Realityfront覆盖/两测试例外、`cp r0/go_overlay/internal/v4productcli/*.go` 一次完整当前 Go、原 Rust ISA-L feature flags/源 hash 不变；命令单份、源与构建binary SHA256 manifest。ARM64真实原生功能仍 **NOT_RUN**，不能因脚本修复自动PASS。
- `tests/test_m0_plan028_default_assembly.py` 添加永续审计：11个源锁 Go、H1285原代码、x86和ARM相同默认当前源码、Windows选择权威manifest-plan020及五Wintun回归、Game2防混组、ARM bash -n/无重复构建，每次 main cheap workflow执行，不依赖附加参数。Window5原 WFP `LUID != self`及共享/server/32、/1 所有权**未解决**，不会错误地默认开启多设备或把别人路由改成自己。
- 唯一新真实 [H1541 workflow](https://github.com/lly8666/wbd-next/actions) 用本次SOURCE重编原Go两端，保存原版Rust已验证 SHA256/ISA-L（不伪称Rust新编译），继续只跑原始失败的 loss30 600s、外层300–350、验证本代Game2服务端 M4 与5个Game4 hot、业务和6Stop；**不重跑已过的Linux loss0 333.930**。
- `.github/workflows/m0-wl-public-normal-full.yml` main cheap gate每次执行本审计，既有 product two-OS remains source-pinned。功能卡继续实验态，新增 H1540 FAIL 证据，不把最新未测 H1541 写成功。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Fix original Go same-protected-epoch Game2/4 cross-generation cohort mixing by exact observed TCP 5tuple and consecutive source port grouping; include every current Go TLS/M4 repair by default in ARM64 and Linux x86 original-source product assembly, with CI source-lock audit; preserve existing authentication, AEAD, 64-packet bound, WFP fail-closed, 1460 outer default."}
```

### H1542 触发路径纠正（仅CI工作流，不动产品SOURCE）

原H1541新增workflow内 `on.push.paths` 误写成历史重命名路径 `m0-plan028-h1541-linux30-pre-detach-source-fixed.yml`；H1541主线commit **确实启动既有源码触发的常规回归**，但唯一指定的 loss30 600s **NOT_TRIGGERED**，不是失败也不是通过。已将过滤器精确指向真实 `m0-plan028-h1541-linux30-game2-cold-cohort.yml`，此修订自动触发**一场** H1541 定向原生场景。此前 [main Action42808628492](https://github.com/lly8666/wbd-next/actions/runs/42808628492) Cheap current assembly gate/job129804103164 **PASS**，含永续默认装配一致性审计；后续必查真正原始 Go/Rust 测试输出，不能拿这里的静态 PASS 冒充原生600s。
