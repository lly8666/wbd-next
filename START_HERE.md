# WBD Next｜main 接续

**M0 当前入口（任务发布；真实进度须刷新远端）**　先读[根约束](AGENTS.md)、[永久接班提示词](docs/prompts/M0.md)、[分配](.governance/registry.json)与[游标](.governance/workstreams/M0/cursor.json)。本次用户授权[双端 Rust TCP 与 Windows 简化施工方案](docs/decisions/M0-DUAL-RUST-TCP-CONSTRUCTION-20261126.md)；指定实验分支 `experiment/m0-dual-rust-tcp`。每次接班先主动核实际HEAD/PR/Actions，不以旧记录代替当前事实。以下为历史资格索引。

**历史：029B/029日常H2137限域PASS；H2162 Game2/4全20分流策略原生PASS_SCOPED；H2169 Game启动填充Game2/off-FEC与Game4/fixed-FEC × off/tls/flows 6场真网络PASS_SCOPED；H2177 新增**原生Linux x86_64/ARM64各服务端＋客户端五模式10/10真实内核TCP/UDP/Stop PASS_SCOPED**；**H2186 Linux原生双ISA各8场随机填充/AES/MTU/Stop真网络16/16 PASS_SCOPED**；完整技术出口仍OPEN、030未开。** [PR35](https://github.com/lly8666/wbd-next/pull/35)非冲突设计已合入，依据[029B提示](docs/prompts/M0-PLAN029B.md)与[方案](docs/decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md)施工。028保留限域FAIL、不重开多Wintun/旧矩阵；030未开。029旧H2077仅`PASS_SCOPED`。

**H2205–H2208（2026-11-19）**：Win2025原WinForms 409项GUI/Go与Linux ARM64原TLS 12/12 [H2205证据](docs/evidence/M0/PLAN029B-H2205-H2204-WIN-GUI-DRIVERS-ARM64-SCOPED-RELEASE-20261118.json) **PASS_SCOPED**；H2206服务端指定网卡唯一IPv4已实现；H2208短RouteKey改轻量v2离线计算一次、私有缓存复用，Win/Linux Go单测限域通过。Android仍仅设置组件、OpenWrt仅试验配置，真实JNI/路由器联网NOT_RUN。

**H2209–H2213（2026-11-19）**：普通TLS同端口旧P2 Decoy仅占独立8条转发，不耗WBD Rust owner；H2213 Rust native**16→32 lane**、Linux Go cold表**32→64**、普通访客**每条随机15–45秒**自动关闭。Windows真实32个prepared owner/第33个拒绝，Go真实TLS超时归还名额与原生Linux x86/ARM两轮真TLS/UDP/Stop [H2213 Rust](https://github.com/lly8666/wbd-next/actions/runs/44446847868) / [Go](https://github.com/lly8666/wbd-next/actions/runs/44446847713) / [Linux](https://github.com/lly8666/wbd-next/actions/runs/44446847738) **PASS_SCOPED**。32真实客户端满载、公网NAT/移动实机NOT_RUN，029整体OPEN；[M0 cursor](.governance/workstreams/M0/cursor.json)。

**H2216**：双端 TTL-persona 检测已取消，TTL=0 拒绝；限域PASS，物理未测。

**H2224（2026-11-19）**：用户报告H2223实体业务通；[PR48](https://github.com/lly8666/wbd-next/pull/48)合入WinGUI READY/OS双回执、FEC双向状态、Linux owned MASQUERADE和冷Health随机。Action44564552571 WinGUI426项＋Linux ARM64真NAT/Stop **2/2 PASS_SCOPED**；新版本公网长稳NOT_RUN，029 OPEN、030未开。

**接续路径**：先读[AGENTS](AGENTS.md)、[章程](PROJECT_CHARTER.md)、[M0 cursor](.governance/workstreams/M0/cursor.json)、[registry](.governance/registry.json)及在途Actions，唯一真状态以同SOURCE验收记录为准。历史限域证据：[H2169](docs/evidence/M0/PLAN029-H2169-GAME2-GAME4-STARTUP-PADDING-SIX-NATIVE-PASS-20261118.json)、[H2177](docs/evidence/M0/PLAN029-H2177-LINUX-X86-ARM64-TWO-ENDPOINT-FIVE-NATIVE-PASS-20261118.json)、[H2186](docs/evidence/M0/PLAN029-H2186-LINUX-X86-ARM64-EIGHT-CROSSPLATFORM-NATIVE-PASS-20261118.json)、[H2202](docs/evidence/M0/PLAN029-H2202-ONE-V2-LINUX-WINDOWS-ANDROID-OPENWRT-SCOPED-20261118.json)。旧028/029失败不销账，PLAN029技术出口与实体跨ISA/DPI/p99仍OPEN；主线单写者，不重复已经PASS的旧矩阵。

**硬门：**[TLS](docs/architecture/TLS_HANDSHAKE_CONTRACT.md) ClientHello前无私有前导；[MTU](docs/architecture/MTU_CONTRACT.md)用户外层默认**1460B**，1500仅显式，内层Rust预算+OS读回。历史029B FakeIP 语义保留为旧资格；本次新任务明确在Windows阶段删除FakeIP，见施工方案，未施工前不冒称已删除。未测不作PASS。历史：[027](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)/[027A](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)/[028](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)，[功能卡](docs/features/README.md)。
