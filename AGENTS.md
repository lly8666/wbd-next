# WBD Next｜全体agent硬约束

1. 以最新用户授权为先。主目标：真实业务**首次到达**、低时延、无跨业务HOL、低系统成本；允许有界内存换CPU。保留认证/完整性、账户和地址隔离、epoch/generation、原密文修复、MTU与owned Stop。具体产品边界见`PROJECT_CHARTER.md`。
2. M0在**main**直接开发/测试/留痕；只有独立明确授权的并行角色才用其他分支。每次从`START_HERE.md`八文件起步，刷新HEAD，核`registry.goal`、M0 cursor checkpoint增量与在途Actions。旧FEC工位已结束，旧分支/旧聊天/历史FAIL不是新任务。
3. Windows Option B：Go负责原FakeTCP/TLS认证、OS/WFP/WAL/GUI与低频换lane；Rust独占稳态Wintun/Npcap/M2/FEC/Game/Health。**不允许Go每包FFI、Go空轮询、双热控制器**；Windows尽量固定两Rust I/O worker，真实事件/最近deadline；Linux已稳定I/O先不重写。具体本批依赖/Auto/Keepalive/测试按`docs/decisions/M0-PLAN026-FEC-GAME-AUTO-HEALTH-LOW-COST-EXECUTION-20261029.md`。
4. 每批先补齐全部产品实现/调用/有效配置与CLI/GUI适用项/测试/夹具/装配manifest，再冻结SOURCE执行Actions；可随写静态检查。先便宜编译/core，后Fixed/Game，**Auto与Keepalive/服务器超时协同最后**；不为helper反复全链路，不无限架构重写。失败先找首异常，区分产品/夹具/容量/错判，仅重跑原反例及受影响保护。
5. 功能可合批，性能每Action一个场景一个测量job，旧Go与新Rust同机先后A/B。按实际offered/delivered、tc drop、真实Stop、CPU+线程/内核、RSS/idle wakes报告；主机达到容量停更重同族，不将锁/单核瓶颈假称环境。生产不留逐包计时/日志，诊断仅显式opt-in稀疏采样。
6. 用户可见功能唯一入口`docs/features/README.md`，变更同步对应卡/新短devlog的feature-impact；experimental不自动成为formal。历史日志和证据归档保留，不复制到热提示词。权限冲突/硬要求变更/未授权部署之外自行连续完成，阶段边界cursor-only H；禁止force和整树覆盖。

详细流程仅按需读`docs/GOVERNANCE.md`、`docs/history/2026-10-28-M0-MAIN-HANDOFF.md`。