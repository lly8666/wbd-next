# G2-001 · 四个独立worker的限域正式授权（2026-10-14）

**本事务唯一目标**：从M0复核过的`main`基线`b6604f1405fb311ad63cc55dee5d1b8a65abc7be`完成正式分工权限初始化。依`docs/decisions/M0-R0-parallel-worker-readiness.md`及00/11设计，原role revision1的M1–M4均是reserved。本次将main registry revision提高到**2**，仅M1–M4成为scope-limited active，assignment_epoch首次为**1**；M0仍main/global_writer/epoch1。**角色激活 ≠ AI worker已经有独立运行中的会话，更不等于R1产品合格**。

| 角色 | 正式独占工作分支 | 只允许的源码和私有结果范围（外加自己cursor/requests） | 第一原子 |
|---|---|---|---|
| M1 | `work/m1-r1-runtime` | `crates/wbd-engine/src/runtime/`,`crates/wbd-engine/src/memory/`,`crates/wbd-engine/tests/`,`docs/devlog/M1/`,`docs/evidence/M1/` | R1 owner/arena/fake-clock stop与返回队列，B01/R01/M01局部证明 |
| M2 | `work/m2-r2-recovery` | `crates/wbd-recovery/`,`docs/devlog/M2/`,`docs/evidence/M2/` | R2 receipt纯状态、control/失败PN洞、影子缓存、TTL和次数门 |
| M3 | `work/m3-r1-codec` | `crates/wbd-codec/`,`docs/devlog/M3/`,`docs/evidence/M3/` | R1 唯一FrameBudget与旧Go pathmtu真实oracle；后续独立原子真实三cipher AEAD/8B HP |
| M4 | `work/m4-r1-platform` | `crates/wbd-platform/`,`r1/go-bridge/`,`docs/devlog/M4/`,`docs/evidence/M4/` | R1 bounded TxBatchOutcome/borrow-stop 驱动；再做Go冷控制桥 |

**跨边界冻结**：M3拥有`FrameBudget`一次性计算（outerMTU/实际IP+TCP+MSS/record31/FEC56/Game16，LINK20仅分片，不为Normal off小包加头），也独占认证后的record seal/open与8B HP，M1和M4不能自发明数据面加密。M2只处理经认证receipt与FrozenRecord重发候选，无socket、无自己的PN、无新加密。M1的TX/RX owner负责协调有界内存、SPSC/clock与fresh独立，M4独占驱动借用停止和Go控制桥。M0串行维护`Cargo.toml`/`Cargo.lock`、`crates/wbd-types/`、`crates/wbd-engine/src/lib.rs`、C ABI/header、`r0/`共用fixtures、根CI、tools、registry与main。任何跨界调用或锁库需经M0 G2整合，worker不能扩写主线文件。

**最小真实可编译入口**：M0初始建立纯`wbd-recovery` crate，只依赖wbd-types，包含`RECOVERY_ENGINE_READY=false`的显式非资格标志；Cargo workspace/lock从四crate→五crate（无第三方Rust依赖）。给wbd-engine追加runtime/memory两个源码module挂点，保留ABI v1 features=0；worker M1只能更改该两子目录，不得改`lib.rs`。旧R0 10个范围门及所有历史SOURCE/run不修改，`r0/source-lock.json`只登记新的未资格化worker bootstrap，并同步修改静态audit旧“4crate/全reserved/revision1”断言及原governance测试revision fixture。

**分支原子化顺序与故障**：先将五crate与权限+五份cursor在main同一实质S提交，包含必要test更新、静态清单的分工状态。该S触发Actions。随后按精确S创建四个branch refs；每条分支HEAD必须等于该S，树内含本人bootstrap cursor（seq0、checkpoint=null、planned、unverified true、没有证据），它首次新S+H前`audit_remote`会正确报告`RECOVERY_REQUIRED`，不能标CLEAN。创建分支不是假造worker代码结果。验证main+4个refs、权限无路径/semantic冲突以及真实Actions后，另写证据收据S，再写M0 cursor-only H。任何branch create失败须记录`PARTIAL_G2_UNRESOLVED`、不谎称四者已可领取。拒绝force push、拒绝用过期SHA覆盖用户动作。

**风险/非资格**：如新role独立分支跟踪会话未启动，则实际并发编码人数为0；本次只让权限可以被未来会话领取。rust codec目前只结构和opaque wire，真正AEAD/HP/FEC GF、OS驱动、R2状态机仍未实现。Go源`lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`不写，Go生产V4仍DISABLED，Rust engine features0，Windows/ARM native运行、产品/性能/物理仍NOT_RUN。项目phase维持R0 foundation partial，R1/R2工作可在独立scope中起步，主线集成/阶段升级由M0据确凿结果另行决定。

**下阶段唯一动作**：派四位角色分别领取各自分支的**首个原子**，M0仅串行合并共享依赖/接口并维护R0/R1整体门，不替代M3大量密码学或M1完整owner实现。任何release或生产开关单独通过资格审查。
