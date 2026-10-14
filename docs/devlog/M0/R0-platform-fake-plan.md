# M0 / R0 fake-clock 与 fake-platform 契约施工范围

2026-10-14。重读远端`START_HERE`/`AGENTS`/`PROJECT_CHARTER`、project/registry、M0 cursor seq9 和00/11。checkpoint `6c9244115e5c122c58375d312326ea0894ffa1b3` 后仅H=`1af6f2a2328238f53dd7a478408e336fd3800169` 修改cursor，治理38514609146 success，无PR/open tests；M0 active main epoch1 revision1，CLEAN非产品通过。

**why_now**：下一唯一任务要求 R0 类型在可检查的 fake I/O 下证明 `TxBatchOutcome.accepted_prefix / uncertain_index` 与 PN 消耗、driver buffer loan、stop fence。没有 Rust 真实engine或平台驱动前先锁最小语义；切勿拿上一轮C ABI green误当收发实现。

**边界**：新增独立 `crates/wbd-platform`，只依赖 `wbd-types`，不依赖 `wbd-engine`。公开Rust内部`MonoClock`、`deadline_after`、`TxDriver`、`TxBatchOutcome`、`PnAllocator`、`FrozenFrame`、`BorrowFence/KernelLoan`、`TxLedger`。这些是R0的最小资源与返回值基准，**不是**产品 OS native send，且不导出 C ABI。

**语义与反例**：
- 每次 reserve 在调用编码/seal 前递增PN；Seal失败/WouldBlock/IoUncertain 均不回滚；u64::MAX用完后停，不复用。该fake seal闭包非真正AEAD。
- 驱动可确认前缀已交付给系统调用（非peer ACK），对于`uncertain_index`必须恰等于`accepted_prefix`且标记`IoUncertain`；其余`NotAttempted`，不会转成接收确认或新鲜业务门。非法/非相干 outcome 整批拒绝提交统计。
- 发送的`FrozenFrame`含不可变Arc字节，driver如尚未完成copy必须显式取得`KernelLoan`；先标记`begin_stop`禁止新借，再`wait_drained`等所有借用释放；旧owner drop不导致借用内存提前free。是in-memory lease proof，无真实内核syscall。
- `MonoClock`由模拟值注入，不读wall clock；测试deadline 119/120与u64溢出。
- tests 7组锚点：I01 前缀/uncertain、I01 空前缀不阻断新包、C01 失败seal烧PN、I01 bogus outcome 失败关闭、B01 stop借用等待、B01 fake driver返回但仍借用、R01 fake clock确定性。

**执行契约**：只在GitHub Actions Ubuntu 24.04 x86_64、Rust1.85.1编译平台 crate和单测二进制一次，上传manifest包含精确SOURCE/run/attempt/toolchain/input SHA256/测试binary size/hash；consumer job只验证后运行7组既有测试，不重新构建。既有`r0-build`和`r0-native-abi`因workspace/lock变化被同SOURCE回归触发，范围不合并视作产品PASS。

**done_when**：7组Rust真实二进制通过、产物校验与受影响老workflow green，记录准确成功/失败run及剩余边界，独立cursor-only H；如失败只做首个必要修复。R0整体仍partial，M1–M4仍reserved，生产V4仍禁用。

**唯一下一动作（通过后）**：在Actions追加 Windows x64、Linux ARM64 的跨目标编译与C ABI layout/链接检查，明确 native 与 cross build 差异，仍不假称在目标机器上执行、无需物理设备；再评估R0剩余退出门。
