# PLAN-004：剩余规划的集成易错点

用户要求停止继续刚才的优化任务，仅提前澄清后续规划。读取基线main `9d8ff68`（含H104及其精确性能/MTU收据），本次不实现产品修复、不重跑024性能、不改registry/project/其他agent的cursor，不覆盖其当前任务与事实。

改动直接进入既有modules/TEST_PLAN/固定M0入口：首发parity不占repair额度；SPSC按真实最后释放线程判断；高速seq32回绕；MTU下降后的分片不混stride、DF/IP/LINK层级；FEC退役与buffer归属、切档drain；Normal/Game rotation去重差异；Wake失败重试、旧revision与配套发布入口。删去00中把R0初始mock状态写成永久当前状态的文字。所有反例并入既有ID/manifest，已测同路径证据复用，不另造治理系统或逐断言任务。

核源码时观察到两处需要在对应集成阶段核清的边界：基线 `crates/wbd-engine/src/v4_owner_crypto.rs` 的TX seq仍为u32 checked_add；`runtime/mod.rs` 当前按连续十个Fresh后选repair/parity的组件策略，不能直接充当20:20持续parity服务保证。这里记录实现与目标的差距，不宣称已运行复现、已修复或已证明旧80s中断根因。seq完整绕行时间的68.7s计算以外层TCP payload 500Mbps为分母；业务速率与FEC/Game放大不能混用。

范围只有规划文档与此日志；所有产品、性能和物理验证本次NOT_RUN。沿既有维护分支发布PR，使用Governance maintenance核文档变更后的仓库结构/工作流/工具回归，结果只属于该范围。主线M0下次按既有S→H机制纳入已合并文档，不由本聊天替写其交接游标。

方案SOURCE `caf8f61f0af5acfe1a8a08bd05957f5fee473ced` 的 [Actions38943160375](https://github.com/lly8666/wbd-next/actions/runs/38943160375) attempt1 SUCCESS：169项治理回归、workflow语法、structure、资格账本审计及模型检查通过。已下载核验artifact `12064211584`，ZIP SHA-256 `65359afd956eee7b021729e3febea2313a05c6dfaf5d1956dc2286ebec41da65`；structure明确product/physical NOT_RUN，资格账本也不宣称本次native/product通过。[PR8](https://github.com/lly8666/wbd-next/pull/8)只包含上述规划、固定提示词与日志；本段是验收收据，不是产品修复或新增性能资格。
