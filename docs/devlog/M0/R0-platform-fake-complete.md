# M0 R0 fake-driver/fake-clock 发送所有权门收据

2026-10-14。交接时重读main治理入口、00/11、固定prompt、cursor9，checkpoint `6c9244115e5c122c58375d312326ea0894ffa1b3`→HEAD `1af6f2a2328238f53dd7a478408e336fd3800169`仅cursor H，先前run全部success，无open PR，M0 main active epoch1/revision1，CLEAN不代表产品PASS。

**why_now**：cursor唯一下一动作是I01/B01：在native C ABI sentinel之后，固定Rust平台模块的前缀/不确定发送和借用关闭边界，以测试代替隐式假设。M0选择 R0 最小独立`wbd-platform`，仅依赖`wbd-types`，不倒置依赖到engine。生产不实现socket/回调，fake部分仅`#[cfg(test)]`。

**S** `1f1f8e9af7fd4f7620ead56d7fbc16d1d26c07c2`：`crates/wbd-platform`含Monotonic Clock trait、deadline boundary、`PnAllocator`于seal前消耗PN、`FrozenFrame`不可变Arc字节、`TxBatchOutcome`的accepted_prefix/uncertain_index严格合法性检查、`TxLedger`只计驱动确定syscall接受（非ACK）、`BorrowFence`/loan可跨owner drop并在stop前显式等待。编译前依赖锁Cargo.lock有新增workspace成员，无外部crate；R0模拟driver/test clock不在生产module运行时读实钟。

**真实Actions**：[fake-platform38516057707](https://github.com/lly8666/wbd-next/actions/runs/38516057707) attempt1 SOURCE`1f1f8e9af7fd4f7620ead56d7fbc16d1d26c07c2`，Rust1.85.1 Ubuntu24.04 native amd64；build job115695007988编译一次platform与预编译Rust单测，consumer job115695101127核对源码/二进制SHA256和source/run并运行，7/7顶层Rust tests PASS，0失败。构建ZIP id11872072639 SHA256 `3c9455177db7755748aed83714ffbe410f58a760a496fb763aac33fde054d19d`，结果ZIP id11872227435 SHA256 `edcef246e0edefe741044129dfda0da88138a2686b0d6fb3595c551c4975017c`；测试二进制SHA256 `0555ab255bf701e535689dc8ec8fef37f1c1ef8b9ac0aec9e9b5e16411aac422`。没有外部再次下载zip进行独立复验。

**同SOURCE回归**：原生Go↔C↔Rust ABI [38516057635](https://github.com/lly8666/wbd-next/actions/runs/38516057635) 成功（build115695007716/consumer115695202061），Rust旧types [38516057741](https://github.com/lly8666/wbd-next/actions/runs/38516057741) 成功（build115695008123/consumer115695088421），Governance [38516057624](https://github.com/lly8666/wbd-next/actions/runs/38516057624) 成功。后三项仅属于各自验证范围，不把多job当同VM性能对比。

**test IDs**：R0-I01 前缀两个已被syscall接纳+下个uncertain+最后not attempted；0前缀WouldBlock不阻断独立fresh；非法outcome不计账。R0-C01 失败Seal烧PN，MAX不回绕。R0-B01 loan在驱动已经返回以后仍活着，stop禁止新借用并等待loan完成；所有权Arc阻止过早free。R0-R01 fake clock门限与u64溢出。

**限制**：本次是内存 fake I/O，非真实内核copy、send syscall失败、平台driver或真实Rust稳态数据引擎。只有R0 Rust内部platform trait，并未接引擎/C产品ABI。产品/性能/物理NOT_RUN，Windows/ARM NOT_RUN，生产V4 features=0仍禁用。R0全局partial，M1–M4 reserved。

**本轮子任务done_when**：七项Actions原生Rust已编译/消费运行并记录证据，达到既定范围，收口。

**唯一next_action**：用Actions构建Windows x64与Linux ARM64多目标 Rust平台/ABI产物，校验ABI布局与依赖边界，清楚区分cross-build vs native execution，不把cross-build冒充实测。继续拒绝生产V4与正式worker提前开工。
