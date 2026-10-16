# PLAN-003：热路径成本优先补充方案与任务分配

用户明确要求将最新性能审计落实为详细方案和开发后的同Actions测试，并由M0完成后再分配后续开发测试。规划基线main `d30fc4a`；沿用原Actions38920819286及精确源码333c1b3的证据，不补造产品性能结论。

新增 `docs/decisions/M0-hotpath-cost-first-2026-10-16.md`，定义缓存失效/MTU安全、方向所有权、ready批处理/复用、低成本观测、必要功能回归，以及同VM优化前Rust/优化后Rust的有限AB/BA集合和停止规则。治理不再扩展，计量与机制验真不能反过来成为逐包成本。

registry仅把M0当前任务改为 `R1-M0-HOTPATH-COST-024`，职责/权限/epoch/revision/其他worker分配不变。project、固定提示词、接手入口、架构/测试/模块说明和旧分配决策同步链接，避免旧H102下一步抢先做分片。原023与所有未验硬门保留。另一M0 cursor仍由其本人在恢复/接手后更新，本次不覆盖其事实、请求、源码或测试记录。

本次只交付计划与分配，没有实现性能修复；产品/物理测试NOT_RUN，不能将规划或治理PASS写成024实现完成。执行验证使用既有Actions治理完整回归，验后在本日志记录精确SOURCE/run；本地只审diff/引用/并发范围。

方案/分配 SOURCE `270943800a2d12165d48db4f52134a67b8c91baf` 的 [Actions38927633898](https://github.com/lly8666/wbd-next/actions/runs/38927633898) attempt1 SUCCESS：169项治理回归、工作流语法/结构/账本/模型检查通过。下载核验 artifact12057392120，ZIP SHA-256 `1c59e4248ccd970365c320ce766b814ccb2c9cc4e0f0a697a56097637cc685ea`，structure仍明确product/physical NOT_RUN。后续仅修正“统计范围”措辞并补此验收记录，不冒充优化已经开发或测出收益。
