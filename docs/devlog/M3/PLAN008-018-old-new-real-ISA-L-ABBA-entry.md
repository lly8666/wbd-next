# PLAN-008 / M3-018 · 同机旧新版真实 ISA-L 恢复 ABBA 测试入口

## 测量对象与冻结版本

- 旧版 A：M0 已接受的 FEC2 源码 `8cc5b06d6832565a80b60402a5fe2e1078e9ab2e`，其 `crates/wbd-codec/src/fec_v2.rs` Git blob `26881b892af8845120721d66108a4a03154be223`；只在 `crates/wbd-codec/tests/support/fec_v2_code8cc.rs` 留一份**精确相同的测试用旧版源文件**，不用于产品。
- 新版 B：已完成默认/scalar 回归、但原生新增实现未跑的 CODE `437cc721d1009c835cb900384dadbdbf3ebea800`。同一测试二进制通过 `wbd_codec::fec_v2` 访问当前分支优化代码，通过独立 `accepted_code8cc` 模块访问旧实现。
- 工况：**唯一** `k16/r16/1200B/e4`（缺源 1、5、10、14）、0x11d Cauchy，固定 original frames、固定已经认证的 repair body。基线标量生成的 parity 先与优化版本标量生成的 parity 严格逐字节比较，再共同用于两个版本的原生恢复；初始化/预热、第一次构表不计 steady cost。
- **同 VM、单进程、同一 Release 测试二进制**：A→B→B→A，每腿200万次 `recover_missing(...RequireNative)`，结果校验和必须四腿一致，后端必须每次确认为 `NativeIsaL`。只测恢复，不混编码吞吐或 scalar/native 竞赛。
- 测量指标：`/proc/self/stat` 进程 CPU ticks、wall nanoseconds；单个测试进程中以 test-only 全局 `System` 代理计数成功 heap alloc/alloc_zeroed/realloc 次数和 gross requested bytes。B 还报反矩阵、ISA-L 表、padding workspace payload；A 未包含对应统计 API，不能以 A 显示0字节解释其真实 RSS。**实际复制字节/指令未被计数**，需标 `NOT_INSTRUMENTED`，不可将分配请求字节代作复制量。
- 严格资格：每腿 wall≥1s、CPU≥100 ticks 才可给本场景 `CPU_WINDOW_VALID`；其他输出 `CPU_INCONCLUSIVE`，不能算性能收益。性能比须比对 A/B 前后两次的 CPU，分配计数亦同一程序获取。宿主 `getconf CLK_TCK`、CPU配额/CPU型号、官方 ISA-L 源码及 ABI/lock/binary的 hash 由同一 Actions manifest 记录；无外部 manifest 时不宣称正式资格。

## 使用方式（需已有 M0 权限内 native-isal Actions 入口）

旧版 fixture 是 tests/support 的非自动独立 crate，不影响产品/默认 backend。基线和当前版本均通过同一个 Release Cargo 测试二进制编译。M0 依已审过的真正 ISA-L build.rs、官方 ISA-L source pin 安装 `WBD_ISAL_PREFIX`，固定 worker HEAD、`Cargo.lock`、wrapper、libisal.a、bin/test hash，运行：

```sh
cargo +1.85.1 test --release --locked -p wbd-codec --features native-isal \
  --test fec2_plan008_abba --no-run
cargo +1.85.1 test --release --locked -p wbd-codec --features native-isal \
  --test fec2_plan008_abba m3_plan008_fec2_e4_old_new_abba \
  -- --exact --ignored --nocapture --test-threads=1
```

GitHub Actions 测量与功能必须使用同一源码 pin/二进制/单 runner 配置；可先运行完整 F2 原生用例（尤其 `r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact`）以免将功能错误当性能收益。源码可由 M3 提交，但 `.github/workflows`、官方 ISA-L build.rs、`r0/` benchmark 和 root Cargo 的共享变更均属于 M0/M4。若没有可用共享 native 执行入口，**只能交付 READY_TO_RUN / NOT_RUN，不能伪造 CPU 结果**。

## 意图、回滚与停测

本文件与精确旧版测试源、ABBA test 合并为**一次源提交**，普通 worker-native 只会编译默认 crate 而不执行 `--features native-isal` 的 ignored benchmark。单次正式测量无需改变协议、k/r/e/profile或启用能力。失败时保留原始 Actions FAIL，修复只能在 M3-owned codec/test 内进行；本次优化的回退基线固定 CODE8cc。产品 FEC2 **OFF**、NET/Go/GUI/p99/physical **NOT_RUN**。
