# W168→Windows 原生集成：两分钟交接（仅热摘要）

**权威仍是远端 main registry/cursor + 精确 SOURCE 的 Actions**，本页只做索引，不维护另一套任务数据库。冻结源 F=`254cf4110c1df3878c7bd0e782145fc381189b8f`；真实双亲 merge=`fea9cd94a8cabcb6ef3d6958f9ba8db8300721d5`，已可由 [Draft PR #28](https://github.com/lly8666/wbd-next/pull/28) 追溯；Windows W 原基线 `05d25fade4768feb4a6e2ad8109aa89cbf94e6c7`、main `7a6a289` 未合入/未修改。

**最新真实验证**：候选源码 `fbb281c7c8531a1e242c8368c0b11ca9545be730` 的 [Action 40361251070](https://github.com/lly8666/wbd-next/actions/runs/40361251070) Linux+Windows原生 **SUCCESS**：原始凭据 TLS、Npcap/Wintun→Linux raw/TUN、Normal/off 双向真实 UDP/TCP 应用、M2 和严格 PN/SEQ 原生回归、owned Stop+临时防火墙清理通过；`WL_N0=NOT_RUN`，**不代表 Fixed/Auto/Game 或性能 PASS**。早一版 `1b037131` [40360805219](https://github.com/lly8666/wbd-next/actions/runs/40360805219) 也同范围 PASS。新证据 [M0 W168源锁收据](../evidence/M0/PLAN024-W168-INTEGRATION-WINDOWS-NORMAL-FUNCTIONAL-20261026.json)。

**关键历史红灯**：`9137f27` [40357841232](https://github.com/lly8666/wbd-next/actions/runs/40357841232) W168与Windows初合真实 UDP Linux零接收；`6e271c1` [40360124961](https://github.com/lly8666/wbd-next/actions/runs/40360124961) 内核诊断确认 `WrongPersona`（Windows11 TTL128→冻结版 Linux hardcode Legacy64）。现在通过原始Go TLS范围的对端 persona 显式许可适配，**没有取消严格 TTL、四元组或 AEAD 校验**；原始失败仍保留。

**容量**：Windows native Normal M2 shadow **1536**、M1 **2048 slots/5MB**；embedded Go Windows Normal M1 也是2048/5MB。Linux原FEC/Game配置不改。**未收口**：Windows原M2仍有历史80ms/PTO双重重传语义，应适配W168 `outer-opportunistic-v3`（原Linux outer-repair默认ON）；Fixed/Auto真实M2 Applied及parity，Game2/Game4真实2/4独立TLS/Npcap lanes及Stop，仍未得到Windows公开模式功能资格，Rust mask不可空开。历史WL-N0 +103字节10Mbps高载 FAIL 不因低速PASS取消，用户暂停性能矩阵。W168旧状态 `merge_ready=false`、`capacity_stop=true` 与AMD64高压INCONCLUSIVE历史原样保留。

**接续**：先核准测试SRC/平台结果→仅在 #28 独立候选适配 Windows M2 outer policy→源码锁定回归 Normal TCP+UDP+Stop→Fixed/Auto→Game2/Game4 七格测试全部通过才合 #28 到 Windows W 分支；之后按 main 保护及治理合 #27，不 squash/不强推。历史找 [W168/Win索引](../history/2026-10-26-W168-WINDOWS-INTEGRATION-INDEX.md)，文件级合同见 [集成审查](../integration/M0-W168-FROZEN-ARCH-WINDOWS-ADAPTER-STAGED-INTEGRATION-20261026.md)。其他旧日志不用开局全读。
