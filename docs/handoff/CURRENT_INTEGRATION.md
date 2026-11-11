# main 当前集成接续（PLAN028，2026-11-11）

**实时状态先读** [M0 cursor](../../.governance/workstreams/M0/cursor.json)、[PLAN028统一覆盖/配置/精确SOURCE表](../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md) 和 [专项验收硬门](../testing/PLAN028_INTEGRATION_ACCEPTANCE.md)。旧PLAN026入口不是现在待施工计划。用户已授权M0直接main修复/验收，PLAN028仍IN_PROGRESS；不得因单个短场成功标记完成或扩张029/030。

**当前正式入口**：Linux x86_64/ARM64 原Go TLS认证与 Linux Rust raw/TUN M4（配置见 `r0/go_overlay/internal/v4productcli/linux.go`）；Windows x86_64 `wbd-client.exe` 默认原生V4、WinForms GUI显式使用相同V4原 Go 冷TLS→Rust Wintun/Npcap稳态→WFP/route/MTU/WAL OS；由 `r0/go_overlay/assembly/manifest-plan020-m0.json` 与 `tools/prepare_windows_wiring.py` 固定正式装配。不要将CLI/GUI的保存、测试fixture或库编译等同正式OS生效。

**默认**：外层完整IPv4 MTU **1460**（1500仅显式最大）、内层Rust封装派生并OS读回；FEC **Off**、Normal 1 lane、加密默认ChaCha20-Poly1305、lease空自动/手动`/32`、机会式外层重传on；Linux默认不轮换，Windows keepalive15s/dead90s/idle0且rotate0。Game2/Game4、固定FEC/Normal Auto、AES128/AES256、轮换/休眠需显式。所有完整参数与SOURCE见覆盖表。

**当下验证**：`fd4732ec` Windows30%丢包/200ms单程 Action `43009320538` 整体成功，原Go冷TLS真实RTO三次、双方Rust M4、签名Wintun、手动/32/MTU1389、真实Linux内核反向源与原生Stop已证，仅**冷建链 scoped**；Linux x86/ARM两账号手动 Action `43009320436`、Windows五模式WAL Action `43009320389`、治理 `43009320451` 成功。旧 `dd82db7e` 真实Windows自动AES256+Linux四客户端150s UDP/TCP、Windows退出后Bob继续、六owner Stop仅PASS_SCOPED（Action overall FAIL后置报表），不可升格新SOURCE。旧 `c3e60772` 150s与治理失败亦保留。

**新真实150s**：SOURCE`8c0421c3` Action`43014043726`整体成功，签名Windows自动`10.66.0.192/32`+AES256/Rust3、MTU1389与四Linux三AEAD业务150s全端双向UDP/TCP，Alice Stop后Bob仍4 UDP、六owner清理全PASS_SCOPED。内层平均不等于outer；原始kernel outer双向总量151.96Mbps左右，末段Windows Host CPU92.6%且速率下滑，同VM暂停更重压力。详情看H1594 evidence，**600s/30%全业务仍未跑**。

**未完成硬门**：双Windows独立签名Wintun同主机不同账号/租约/AEAD的OS路由隔离 H1587 `43001721886` FAIL；不能借TLS+Rust成功跳过CAS/route/WAL。原报告误将30%冷建链标为600s，H1592修正报表及源门，不修改实测结果。本源受影响认证/生命周期150s代表场已PASS_SCOPED；但L2更重容量受同VM CPU边界约束、必要L1与代表L3仍不齐，不可将150s当L3。Android/物理公网/029/030范围外。

历史风险与此前未关闭的027A同socket在线收窄属于历史范围，不拿新认证路径结果改写原FAIL；深查旧日志前先看当前cursor引用。
