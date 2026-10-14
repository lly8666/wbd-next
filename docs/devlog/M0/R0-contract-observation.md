# R0 S2：状态修正与首个实测范围

本次修正并不改变用户硬约束或授权：main registry 的M0在R0-CONTRACT-001已授权建立共享类型/来源/构建契约。先前project的 product_implementation=NOT_STARTED 与仓内禁止Cargo/crates规则相冲突，导致精确SOURCE c1f5ce14dbbf8e2b79dafa0e71e452b2b494849c 的 Governance run 38507997045 FAIL；不屏蔽该规则，只将事实状态更新为 R0_FOUNDATION_IN_PROGRESS。rust类型文件仍不能被宣称为可用产品。

独立的R0 build/consume于SOURCE c1f5ce14dbbf8e2b79dafa0e71e452b2b494849c 的 Actions run 38507997009 attempt1完成success。build job 115669801143、consumer 115669889266；consumer在未重新编译的情况下核SHA256/size/SOURCE并执行5个wbd-types单测（5 passed，0 failed）。bundle artifact 11868362971，archive SHA256 65168fdfb903ae5315c7671d01b584ccc6bb8e91709ffe375bb0e3b22b24c3c1；结果artifact 11868717157。精确结构化记录见 docs/evidence/M0/R0-contract-types-build.json。

这不证明旧Go wire、V4 admission、C ABI、平台ABI、多目标构建或产品/性能资格。后续唯一动作：旧Go V3原向量与V4 admission golden的Actions真实对照。R0总体done_when尚未满足，M1–M4保持reserved。
