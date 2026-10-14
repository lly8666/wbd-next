# M0 · R1 Normal/FEC off 第一业务包集成接线（共享编译依赖与退出条件）

2026-10-14 | 所有权 M0（主线唯一 Cargo/lock/C ABI 集成者） | 当前状态 **INTEGRATION_PORTS_PREPARED, E2E_NOT_RUN**

## 巡检事实

起点main `694bfaae5ef03827e057726c73262b2110f5d5a2`，cursor seq19 checkpoint `572de3c508a797124b12e3f32830ca43d1ffea5c` 到HEAD仅一个cursor-only H（治理38535803104成功）。registry revision2/M0–M4均active。M1–M4四条work分支HEAD均 `0845e739ef5d506ff44ad1d6637cc3986929ccd5`（shared M0 G2修复源，**没有任何角色自提交**）；各自cursor seq0/checkpoint null/planned，角色身份审计绿仅证明该身份。远端目前没有未结束run、open PR、任何worker requests/文件或新 `r1_`/`r2_` 专属workflow运行。不能推断会话本地是否在编码；也不能把未推送内容合并。

## 本次实际公共阻断与解除

原`crates/wbd-engine/Cargo.toml`只有`wbd-types`依赖，意味着M0不能组合M3 codec、M4 platform、M2 recovery，而worker不能修改这份根引擎crate定义。同一基础的`tools/r0_qualification_audit.py`把所有crate（包括engine）严格限制到types，拒绝未来正常的组合编译。此处只在**M0持有的root依赖和审计**中加入以下单向边（不引入第三方依赖），并更新`Cargo.lock`、`r0/source-lock.json`的**R1 assemble compile-only**说明：

```
wbd-types (纯类型, 无依赖)
  ↑         ↑           ↑
wbd-codec  wbd-platform wbd-recovery  （三者仅依赖types）
  ↖         ↑          ↗
            wbd-engine （唯一组合 crate，依赖types+三者）
```

不让M1/M2/M3/M4直接改根 Cargo/lock或C ABI，保留`wbd-engine/src/lib.rs`的 features=0 sentinel 及旧Go生产V4 fail-closed。检查每个`Cargo.toml`和`Cargo.lock`方向均严格一致且没有第三方依赖；这只解除未来Rust组合的**编译依赖阻断**，还没有增加真实收发行为。

## 各角色接线输入及先行最小出口

- **M1**（`work/m1-r1-runtime`）：交付实现`wbd-types::buffer_contract::{UniqueSealable,FrozenRecordHandle}`的真实owner/arena、冻结后不再可写、bounded return和queue，以及`LaneKey/SeqOffset/RecordPn`稳定快照；只改M1目录。交付文件/公有符号/测试记录写到自己S与cursor/requests。没有真实M1 handle前，M0不得用mock Arc<Vec>冒充零拷贝实测。
- **M3**（`work/m3-r1-codec`）：先交付唯一`FrameBudget` Normal/off普通包头减费一次（31B record；20B LINK只在分片），紧接真实Rust可运行AEAD Seal/Open、独立8B HP；真实`wire`上未认证PN/kind不得交付。加密实现库需M0在root lock审查钉版本，算法输出以固定旧Go oracle同字节见证。
- **M4**（`work/m4-r1-platform`）：限定可测试的`TxBatchOutcome` accepted_prefix/uncertain/borrowed completion与readonly`DriverRead`，stop有单调deadline并且超时不得释放未回收loan；实际OS送包另测。第一包可以用标为`IN_PROCESS_LOOPBACK_ONLY`的传输adapter，不能标真实Linux/Windows网络驱动。
- **M2**（`work/m2-r2-recovery`）：独立纯receipt/repair状态机工作；**Normal/FEC off第一包不能被R2反馈或FEC阻塞**。M0未来组合recovery时可直接依赖已解耦的wbd-recovery，当前不调用它的假回复驱动首包。

## 集成验收（未来实测，不是本次PASS）

在同一精确R1 SOURCE/run/一个native执行环境里，构造确定的业务字节（含二进制0与空值边界）→ M1真实拥有缓冲（记录owner+generation和capacity）→ M3预留唯一PN/seq、真实AEAD/HP按固定原Go wire格式Seal一次并冻结handle → M4读取同一不可变密文、Normal/FEC off无20B额外LINK头、send结果只有accepted prefix不是ACK → receive侧调用M3真实AEAD Open认证PN/kind/字节 → M1向业务deliver完全相同原始payload。

同一测试明确检查：`original_sha256==delivered_sha256`、sealed wire字节及长度 `payload_len+31`（无padding且不分片）、PN失败不可重用、record auth失败零业务输出、冻结record repair不能修改密文、无无界stop、关闭/return queue缓冲不泄漏。必须证明真正测试的具体模块和native驱动scope；mock FakeUnique及旧Go自己的Open/Seal证据不能拼成真实Rust产品通过。

**只有完整原生Rust闭环的Actions build-once + separate consumer PASS才能把`R1_NORMAL_FEC_OFF_IN_PROCESS`标为局部PASS。** 目标平台native driver/跨语言生产V4与性能/物理继续NOT_RUN，生产feature=0。M0不因Cargo编译绿灯标任何端到端产品成功。

## handoff与所有权

本巡检未收到任何worker已推送请求或实质S。因此不快进/重置四条工作分支，以免覆盖会话正在本地编写的改动。需要新的root crate依赖时，worker只能在自己requests里提出，M0在main串行完成，然后用无force、基于实际HEAD的协作方式将main改动带入其分支。新源的实际Actions证据与最终checkpoint另存 `docs/evidence/M0/`。下一次集成巡检首先核worker refs与requests，再按每人自己的S/Actions/H审核，不跨角色代写。
