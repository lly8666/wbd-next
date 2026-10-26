# W168→Windows 原生集成：两分钟交接（仅热摘要）

**权威仍是远端 main registry/cursor + 精确 SOURCE 的 Actions**，本页只做索引，不维护另一套任务数据库。冻结源 F=`254cf4110c1df3878c7bd0e782145fc381189b8f`；真实双亲 merge=`fea9cd94a8cabcb6ef3d6958f9ba8db8300721d5`，已可由 [Draft PR #28](https://github.com/lly8666/wbd-next/pull/28) 追溯；Windows W 原基线 `05d25fade4768feb4a6e2ad8109aa89cbf94e6c7`、main `7a6a289` 未合入/未修改。

**最新真实验证**：Windows W168 v3修复源码 `4fb263dd38b68e6a1763e7d79f5654b611f4ac8b` 的 [Action 40362898805/1](https://github.com/lly8666/wbd-next/actions/runs/40362898805) Linux+Windows原生 **SUCCESS**（包含原生短反馈不烧PN/SEQ、无无据PTO两项回归）：原始凭据 TLS、Npcap/Wintun→Linux raw/TUN、Normal/off 双向真实 UDP/TCP 应用、M2 和严格 PN/SEQ 原生回归、owned Stop+临时防火墙清理通过；`WL_N0=NOT_RUN`，**不代表 Fixed/Auto/Game 或性能 PASS**。前一版 `fbb281c7` [40361251070](https://github.com/lly8666/wbd-next/actions/runs/40361251070) 和 `1b037131` [40360805219](https://github.com/lly8666/wbd-next/actions/runs/40360805219) 也各自同范围 PASS；不能替代新源码的资格。新证据 [v3补恢复SOURCE收据](../evidence/M0/PLAN024-W168-recovered-Windows-v3-native-run-20261027.json)；[旧独立SOURCE收据](../evidence/M0/PLAN024-W168-INTEGRATION-WINDOWS-NORMAL-FUNCTIONAL-20261026.json) 保留。

**关键历史红灯**：`9137f27` [40357841232](https://github.com/lly8666/wbd-next/actions/runs/40357841232) W168与Windows初合真实 UDP Linux零接收；`6e271c1` [40360124961](https://github.com/lly8666/wbd-next/actions/runs/40360124961) 内核诊断确认 `WrongPersona`（Windows11 TTL128→冻结版 Linux hardcode Legacy64）。现在通过原始Go TLS范围的对端 persona 显式许可适配，**没有取消严格 TTL、四元组或 AEAD 校验**；原始失败仍保留。

**容量**：Windows native Normal M2 shadow **1536**、M1 **2048 slots/5MB**；embedded Go Windows Normal M1 也是2048/5MB。Linux原FEC/Game配置不改。**未收口**：Windows原M2旧80ms/PTO双重重传已经由 `4fb263dd` 改为 W168 `outer-opportunistic-v3` 并取得上述原生功能PASS；但真实弱网和新策略预算性能未测，不能推广为全部修复资格。Fixed/Auto真实M2 Applied及parity，Game2/Game4真实2/4独立TLS/Npcap lanes及Stop，仍未得到Windows公开模式功能资格，Rust mask不可空开。历史WL-N0 +103字节10Mbps高载 FAIL 不因低速PASS取消，用户暂停性能矩阵。W168旧状态 `merge_ready=false`、`capacity_stop=true` 与AMD64高压INCONCLUSIVE历史原样保留。

**2026-10-27 权威任务更正**：用户明确先前 Fixed6 是笔误。当前 M0 的同一任务是**完整 Windows 客户端↔Linux 服务端产品接线**，Windows 各阶段以 Linux 已验证的 Go TLS/Detach、M1/M2/M3、opportunistic-v3、共享 FEC2/Auto/Game、原生驱动及 Stop 为蓝本；不得擅自单独设计恢复/调度。权威现已落在 main registry 与 PLAN020，rev3/epoch1/同一任务编号不变。Fixed6 各次历史 FAIL 保留，但不再是单独执行优先项，也不强制独立网络测试。

**刚结算的中断项**：源码 01d8b7291d0d675a8e1ee8c56e0aa28c2422dd88 的 [Actions 40379315293/1](https://github.com/lly8666/wbd-next/actions/runs/40379315293) **FAIL**；Linux/Windows 同源原生编译与 Windows 原 Rust/Go 回归和驱动准备 PASS，真实双系统入口未完成，job detail 日志 BlobNotFound、未上传 Windows 报告，首个失败原因 **UNKNOWN**，绝不可继承先前 Fixed6/M2 的错误原因或声称通过。历史 main WL-N0 +103B 失败及 N1/N5 NOT_RUN 保留。

**实际横向接线审查**：Windows 公开能力 ABI 曾返回 supported_modes=3（Normal+Fixed），虽然只有 Normal/off 曾获完整真实两端业务/Stop 正例；Windows Auto 非 Normal/Fixed 分支仍用 Go pending+retries，Game2/4 入口拒绝多条真正 TLS+Npcap lane，Fixed 则只具独立模块单测而缺整条核通路；OS /1 全局 WFP/DNS 及 GUI 原生 Applied 不由 TEST-NET scoped 业务证明。因此只保留已真实资格的公开能力，下一工作应复用 Linux 的共享接口一次补整个路径依赖，不能凭能力位/单模式单测报 PASS。详见 [本次全链路恢复与差异清单](../devlog/M0/PLAN024-W168-Windows-whole-product-wiring-recovered-20261027.md)。

**当前接续**：隔离 PR #28 继续 Linux→Windows 原 Go 建连、原 Rust owner、双向网络、FEC/Auto/Game、原生 WFP/WAL/GUI/Stop 的连续产品接线；现有功能 Actions 聚合跨模块原生回归、五模式能力拒绝门和已接通的 Normal 双向业务，不再附加独立 Fixed6 真网络实验。后续仅在各有效模式完成实链路时增加该模式到同一个可核验功能批次；WL-N0/N1/N5 和物理仍各自资格门。保留 W168 F 双亲合并祖先、PR Draft、不 squash/force push、不贸然合 main。历史索引仍见 [W168/Win 索引](../history/2026-10-26-W168-WINDOWS-INTEGRATION-INDEX.md)。
