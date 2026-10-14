# M0 / R0 来源锁与阶段资格对账原子计划

2026-10-14。此原子只对账，不添加网络功能、算法或性能试验。交接前重读远端main `START_HERE.md`、`AGENTS.md`、章程、project/registry、cursor seq12、00/11。checkpoint `29ad2aa37874df0fb44ec08efb5274f1b0145265` 至main `1d773acfe7d17227486554b339350ee5228b183b` 仅独立cursor H，Governance run38520023748 success，旧Actions均completed，open PR=0，M0 epoch1/revision1 active main，CLEAN（非R0合格）。

**why_now**：`r0/source-lock.json`一直停留在初始types-only/Go vectors NOT_RUN / Rust ABI NOT_RUN的引导快照，但随后的8个可定位Actions runs已经扩展出四crate workspace、原生ABI和跨目标构建。若正式派工按假旧快照作决定，将把已有证据当未测、或因重述结果而误把test fixture当生产就绪。

**本次修改**：

1. `r0/source-lock.json`保留锁定旧Go `a7a82db31fe736ffedee330795a3234d358f1984`、Go1.23.12、Rust1.85.1、本机编译target与未来ISA-L/aws-lc-rs依赖NOT_LOCKED，准确列出现有四crate。将旧`compiled=false`改为已在Actions中**测试目的的固定旧Go临时checkout+overlay编译**，并写明生产V4仍DISABLED，旧仓库未写。区分Linux amd64 native ABI/Go/codec、fake driver与Windows/ARM **仅cross-build**；产品、物理、性能仍NOT_RUN。
2. 建立唯一 `r0/qualification-manifest.json`：8条带不可变旧SOURCE、run/attempt、证据路径、workflow、实际源码测试锚点的范围级记录；40条架构ID未实际执行，4条B01/R01/I01/C01只有部分fake锚点，不将任何ID整体标PASS。source-lock指向这一份manifest，不在治理另造第二份完成清单。
3. `tools/r0_qualification_audit.py`和Actions仅静态检查Cargo workspace/lock/纯types依赖、源与工具链、旧Go锁、历史receipt字段/锚点、44 ID集合、worker仍reserved和product NOT_RUN。**这个workflow不重新执行先前go/cgo/Rust/C/跨目标测试**，也不调用GitHub远端实时Actions API；其PASS仅表示元数据自洽。历史各run的真实success须由本轮远端工具先验读取核对。

**done_when**：对账内容以S提交，Actions静态审计确实执行通过、因source-lock重触发的既有测试独立通过，S证据/devlog收据、独立cursor-only H，所有 SOURCE/run/attempt/未运行范围和下一唯一动作可接班。若审计发现不一致，先据首个失败作最小修复。

**分工阻断项**：原Go生产V4仍fail-closed，Rust wbd-engine仅features=0 sentinel；没有Rust真实record AEAD/HP的三cipher wire golden，也没有Rust LINK/FEC wire完整基准/真实引擎与OS I/O；Windows ARM64没有原生实际执行；ABI/codec/fake测试不能变成性能或物理测量。这些是后续合同的职责边界，不意味着必须等R5全部通过才能分配R1；是否正式分配M1–M4仍需独立、明确的registry与路径所有权决定，本轮不改变保留状态。

**通过后唯一下一动作**：按00/05/06/07界定剩余R0最小Rust record framing（不以裸数据模拟AEAD）和LINK/FEC wire golden/MTU基准范围与原Go oracle，选择第一条可真实Actions证明且不假冒加密的公共接口子任务；先将唯一任务与退出证据绑定，再讨论正式worker激活。