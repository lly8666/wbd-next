# PLAN-001 已交付：详细架构与模型/契约验证

2026-10-14。设计源码 `a6c92f516d9deafea4f1f21af37c181a209de565`，Actions [38476692329](https://github.com/lly8666/wbd-next/actions/runs/38476692329) SUCCESS，**46项**自动检查通过。下载artifact 11854880705，核archive SHA-256与manifest内6份文件size/hash，0 mismatch；精确收据见 `docs/evidence/M0/PLAN-001-model-governance.json`。

检查覆盖新增AB/BA同job契约、拒绝跨job/错来源/配置/时间重叠/未跑冒充PASS，以及独立枚举FEC/重试小例、极端概率/容量边界。数学输出明确THEORY_ONLY，产品和物理均NOT_RUN。未编译Rust产品，没有实际新旧产品A/B。

方案按原始聊天和最新旧源码明确：原成熟Go控制层+Rust长期路径；Game共享FEC；GF256/独立AEAD成熟后端；无HOL两次有限恢复/10%预算/稀疏例外；按PPS和RTT计算缓存；R0–R6逐步实施。测试先编译复用、同job配对、广覆盖、能力不足停止更重工况。旧N2/N4/MTU/80s问题原样保留。

最后交叉审阅发现详细治理正文仍留着原“禁止同runner顺序AB”一句，已与用户最新要求统一；M2提示词同步指向现行参数。入口未引入全量历史，热上下文仍通过预算检查。

push显示管理员绕过required Governance期待检查，这是仓库已知enforce_admins=false事实；随后独立核真实run，不声称分支保护阻止了此次push。未改变保护配置。

下一项是R0最小共享类型/ABI、旧版基线/依赖固定、编译复用入口；M1–M4仍reserved，具体分配时再激活。用户本轮要求的方案已完成，不用先写空壳Rust证明开工。结束时单独H确认本次S并保留精确last_tested_source；之后自动push检查不把源码身份改成“全产品通过”。
