# M0 / R0 scoped parallel worker split readiness — 完成收据

2026-10-14，M0依seq16 `next_action` 独立完成**正式派工前**界面/路径/职责/权限审查，未修改registry，未建立worker分支，未激活任何worker。

**入口与交接**：远端 `main` HEAD `7f23c291d7b09d33d7a047583ba6e1b35d3c0a84`，cursor seq16、checkpoint `8def1367960a87c34dda9ffad81512e28850872c` 到HEAD仅一笔cursor-only H，Governance38526648689成功，open PR0、无未结束run，M0 active/epoch1/revision1，M1–M4 reserved/branch null/epoch0。交接CLEAN不是产品PASS。

**事实查证**：Cargo workspace四crate types/codec/platform/engine，`wbd-recovery`未创建；`wbd-engine`只实现C ABI v1 sentinel features=0；`wbd-codec`已实现严格WBC4/WBG4、opaque record、20B LINK+56B FEC结构与有限MTU，但**尚无Rust统一`path_budget::FrameBudget`、真实三cipher `seal/open`、FEC GF和重组**。`wbd-platform`只有fake borrow/stop/TxBatchOutcome；Go控制V4生产fail-closed、没有真实稳态网络引擎。旧Go锁源 `a7a82db31fe736ffedee330795a3234d358f1984` 未写。旧测试10个范围gate、44反例中5部分覆盖/39未跑，无完整架构ID PASS，Windows ARM只是cross-built。

**G2决定**：审查结果`READY_FOR_SCOPED_G2_TRANSACTION_NOT_ACTIVE`。按既定设计，FrameBudget唯一M3 codec/path_budget（外层MTU/实头/MSS/record31、FEC56、Game16只扣一次），三cipher和HP/record authenticated PN/kind只M3，M1 engine runtime/memory，M2新recovery纯状态，M4 platform与wbd-next中Go冷桥；根Cargo/lock、types、engine C ABI lib.rs、共享编译/CI及registry均由M0串行持有。详细精确路径、branch、semantics和每条worker的第一原子任务见 [`docs/decisions/M0-R0-parallel-worker-readiness.md`](../../decisions/M0-R0-parallel-worker-readiness.md)。Worker间路径与语义无交叠，M0总线集成是唯一例外。

**下一事务必须处理**：将四条worker从reserved正式登记为active并给每人唯一branch/cursor/epoch/revision，先创建明确baseline与可编译`wbd-recovery` workspace/engine owner挂点；修改`tools/r0_qualification_audit.py`目前要求4crate与所有worker reserved的历史断言，确保新revision完整匹配；工单/公共接口变动经M0统一集成，Actions按实际SOURCE验证，不能忽略阶段中暂时不绿。**本次并未完成这些动作，所以下一个worker仍不能开始写代码**。四条并发会话也不会因仅创建branch自动出现。

**审查SOURCE与真正静态Actions**：实质决策 S [`6efaa1371f67ae974efbcb960e19cbf265f0b4c6`](https://github.com/lly8666/wbd-next/commit/6efaa1371f67ae974efbcb960e19cbf265f0b4c6)，`r0/qualification-manifest.json`的退出status仍`BLOCKED_NOT_QUALIFIED`、唯一把派工就绪栏改为`READY_FOR_SCOPED_G2_TRANSACTION_NOT_ACTIVE`；`tools/r0_qualification_audit.py`按该当前状态核查，保持历史role均reserved。资格静态audit [38528184760](https://github.com/lly8666/wbd-next/actions/runs/38528184760) attempt1 job115733435495 SUCCESS，artifact11877280166 digest sha256:0b6ce2ece4ebe63250b04b4a4f679b9eb123ba7276897f9147232ea82dd23ede；Governance [38528184766](https://github.com/lly8666/wbd-next/actions/runs/38528184766) job115733434684 SUCCESS，artifact11876980800 digest sha256:dc2625f52e1f6e2b0667690228e08ed6f8d0dbbe175f5d2fd66cdbb2e4e603a7。两工作流验证数据/权限结构，不编译新产品、也不运行Windows/ARM或性能测试。

**done_when**：精确源/边界/候选work branches/写入权限/每人首项及R0仍未达产品门的事实落库，两个受影响Actions绿，本任务完成。

**唯一next_action**：由M0执行正式G2 worker分配与最小可编译workspace接线事务，以定版baseline创建四独立worker分支和cursor，调整registry、epoch/revision及资格审计，再复核Go V4持续DISABLED及所有受影响Actions；结束后才可正式分流R1/R2独立代码任务。无需等R5性能、物理机测试或M3先写完整三cipher，不能凭此收据直接声称已并行。
