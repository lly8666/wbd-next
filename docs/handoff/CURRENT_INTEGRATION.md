# main 当前工作导航

本页保留大致逻辑，不保存每轮日志。先刷新 main；实时 next_action/在途 run 读 M0 cursor，当前施工包读 registry.goal。

## 已经建立的基础
原 Go 建连/控制层 + 同进程 Rust 数据引擎；Windows 使用原生 Npcap/Wintun 和 owned 网络事务，Linux 使用 raw/TUN。Normal off、Fixed、Auto、Game2/4 off/FEC 的双向真实 UDP/TCP/Stop 已有 main 同源功能正例。自然 Auto 健康降档有独立来源正例。FEC 工位历史工作已结束，不重开旧接线工程。

## 当前收尾
[主线整改完工包](../decisions/M0-MAIN-CLOSEOUT-20261028.md)集中处理：偶发零损建连失败、Windows N0 稳定性/本地 drop、高 RTT 下机会式重传状态寿命、质量/receipt/keepalive 协议外观，以及正确的限速和性能验收。旧 Windows 施工单的未完成项须逐项差异核对，不能整单重新执行。

Game4 独立损伤和共同黑洞是不同问题；延迟副本导致的尾延迟不自动等于 HOL。高压 FEC 结果有效但部分用旧 ARM64 包和损后限速，不能推广成当前 Windows 或严格物理线路资格。

## 日后再补的产品能力
单公共端口/多客户端配置、认证简化、全部旧生命周期/GUI/DNS/分流/IPv6 等按功能卡迁移。现有已接线能力应做保护，未接线处明确 UNWIRED；不要借本批“收尾”无限扩包。历史 80 秒中断仍未凭本轮证明关闭。

源码/夹具/进度都回 main；旧分支只作来源档案。[历史检索地图](../history/2026-10-28-M0-MAIN-HANDOFF.md)保存查找路径和关键来源，不需要新 agent 通读日志。
