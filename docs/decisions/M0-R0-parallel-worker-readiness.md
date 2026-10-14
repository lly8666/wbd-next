# G2 决定草案 / R0 → 有界并行 worker 派工就绪审查

日期 2026-10-14 | 审查者 M0 | 阶段仍 `R0_FOUNDATION_IN_PROGRESS` | **结论：SCOPED_ASSIGNMENT_READY；角色未激活，生产功能未合格**

## 检查输入与事实

按远端main `7f23c291d7b09d33d7a047583ba6e1b35d3c0a84` 及cursor seq16/checkpoint `8def1367960a87c34dda9ffad81512e28850872c`，checkpoint→HEAD唯一cursor-only H，Governance 38526648689 success；registry reservation_revision1、M0 active/main/epoch1、M1–M4全部reserved/branch null/epoch0；0 open PR，无本轮前未完成Actions。当前Cargo是四crate（wbd-types、wbd-codec、wbd-platform、wbd-engine），engine仅features=0的ABI sentinel；`wbd-recovery`不存在。最近真实Actions：LINK/FEC源 `ed21a3c1fd3ca9b728337e04d1053938a5e7a36a` run38525749707 Rust7 + 固定Go LINK2/FEC2 PASS；record framing38525749428 PASS；原WBC4/WBG4因新测试被错误纳入13项过滤器而run38525749599 FAILED（实际20/20 Rust断言PASS），修复源 `449d15d47b261c50f42cc19e5b4406bf0dddd1af` run38525921690 13/13 PASS；收据8def136后audit38526501450/Governance38526501465 success。

既有形式和版本锁：Go旧仓库`lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`**只读**、Go1.23.12；Rust1.85.1；C ABI V1固定size/token，features=0；R0类型和mono clock，fake TxBatchOutcome与KernelLoan stop、WBC4/WBG4、受保护record opaque、LINK 20B/FEC 56B与MTU均已有严格**子范围**测试。产品/物理/性能NOT_RUN，Windows/ARM只cross-build；44架构ID 5项部分覆盖/39 NOT_RUN，无一整项PASS。

## 已决定、但未实际实现的跨角色边界（唯一权威：00/01/02/03/04/05/06/07/08/09/11）

1. **FrameBudget/MTU唯一语义属M3 codec的 `path_budget`**，由M0冻结公开签名和消费次序：调用方提供实际outer MTU、IP/TCP实头与peer MSS、record上限、Normal fixed/off或auto、FEC预留、Game逻辑16B包络；只计算一次可用LINK payload/shard budget，保留常量record31B、LINK20B仅分片、FEC56B仅启用、Game16B每逻辑包一次。不得多模块重复扣费、扩大普通LINK包头、超MSS无声发送。旧Go`pathmtu/budget.go`在下一M3首项对照；目前**只有设计+LINK MTU64结构oracle，尚无Rust path_budget代码或真实carrier动态MSS测量**。
2. **真实加密/record受M3独占**：Rust `LaneTxCrypto::seal(keys,pn,kind,UniqueBuffer)->FrozenRecord`，`LaneRxCrypto::open(keys,&mut wire)->Result<OpenedRecord>`；只允许AEAD成功返回认证后的PN/kind/payload区间，独立8B HP；失败不回退PN，repair只重发FrozenRecord。M1只消费已加密、冻结的record handle，不得借当前`record_frame::split_one`作为业务认证；M4不得自建另一份record密码学。真实三cipher aws-lc-rs/RustCrypto版本和Cargo.lock均由M0集成锁定（当前NOT_LOCKED）。
3. **M1 runtime/memory/owner是组合消费方**：纯`wbd-types`代际键与MonoNs快照、唯一TX/RX owner、PN/seq预留、bounded queues、fresh独立调度、上界512MiB由03控制；不修改公共C ABI，engine`src/lib.rs`继续由M0串行持有。M1开始仅做fake-clock/owner/arena隔离实验，尚不假称Normal/off完成。
4. **M2 recovery纯状态机**只接收经认证receipt事件、已冻结record的handle、`TxBatchOutcome`和单调时间，输出Release/RepairCandidate/Deadline；不持socket、不封装FEC、不自行生成PN和新密文。初期可在独立`wbd-recovery`新crate完成fake-clock状态测试，真实运行时连接需等M0 workspace导入和M1/M3接口稳定。稀疏重传比例豁免与最多2次始终保留。
5. **M4 platform与Go控制桥**只负责真实I/O、driver借用/stop、原Go bootstrap保护与epoch切换；请求共享ABI变化交M0，不直接修改旧仓库、不把mock当Linux/Windows实驱动。新Go适配器只存于wbd-next专属范围，Go V4生产入口始终FAIL_CLOSED直到另有资格。
6. **M0唯一集成者**：根Cargo.toml/Cargo.lock、Rust types、engine ABI `crates/wbd-engine/src/lib.rs`、`r0/abi`、`.github/`、`.governance/`与测试/文档的公共语义由M0主线串行合并。不同worker不得并发修改这些根共享文件；需要改接口先在worker devlog给G2请求。不同SOURCE独立PASS不能合成整体R1 qualification。

## 下一次独立G2事务建议登记（**以下未执行/不是现有权限**）

| role | 建议唯一分支 | 建议非重叠allowed_paths（前缀以 / 结束） | owned_semantics | 首个可独立验证原子 |
|---|---|---|---|---|
| M1 | `work/m1-r1-runtime` | `crates/wbd-engine/src/runtime/`, `crates/wbd-engine/src/memory/`, `crates/wbd-engine/tests/`, `docs/devlog/M1/`, `docs/evidence/M1/` | `runtime_owner`, `buffer_arena`, `normal_off_scheduler` | 双owner/fake-clock、满return/stop交错，B01/M01/R01的局部反例；不碰ABI sentinel入口 |
| M2 | `work/m2-r2-recovery` | `crates/wbd-recovery/`, `docs/devlog/M2/`, `docs/evidence/M2/` | `receipt_state`, `shadow_repair`, `recovery_budget` | receipt事件/bitmap源状态、PN洞和过期/双重试fake clock；不发socket |
| M3 | `work/m3-r1-codec` | `crates/wbd-codec/`, `docs/devlog/M3/`, `docs/evidence/M3/` | `record_crypto`, `link_mtu_budget`, `fec_codec` | `path_budget`单一owner、旧Go MTU oracle与真实AEAD/HP接口起步；FEC实现分阶段，不假标SIMD |
| M4 | `work/m4-r1-platform` | `crates/wbd-platform/`, `r1/go-bridge/`, `docs/devlog/M4/`, `docs/evidence/M4/` | `platform_driver`, `go_bridge_adapter`, `lifecycle_integration` | 驱动prefix/borrow/stop与Go桥接独立测试；无实机不标原生驱动PASS |

上述**worker间路径及semantic不相交**；M0的global writer只串行组合，不能冒充worker已有权限。branch/cursor/epoch/registry revision全由下一独立G2事务在main授权，建议revision从1→2、各初次assignment_epoch=1；控制分支main上的registry与每条worker分支cursor必须一致。不要让未激活worker仅凭本表开工。需要同一时间四条线真正前进，还必须有四个独立worker会话主动领取各自已激活分支；写入registry不会自动产生正在运行的agent。

## 并行激活的硬前置（下一事务的一部分，不是R1产品硬门）

- M0以单一锁定源码基线为四条worker创建非冲突分支、生成各自`.governance/workstreams/Mi/cursor.json`，将每人task_id、why_now、done_when、next_action与revision/epoch完整登记，再在main修改registry；只允许各分支一个active writer。审核实际分支HEAD与唯一性。
- 对`wbd-recovery`在M0协调下建立最小Cargo空壳并加入workspace/lock；为M1的engine runtime/memory模块设可编译挂点且M0保留ABI入口，M3的public`FrameBudget`方法冻结后才让组合代码依赖它。公共crate/test文件变更由M0串行，worker首次代码验证不得依赖不存在的module入口。
- 将`tools/r0_qualification_audit.py`当前硬编码“workers均reserved”和workspace恰四crate的**R0历史证明假设**调整为区分“历史R0输入”和“新分工实际状态”，保留所有旧测试精确SOURCE、R0 foundation仍partial。新增/变更角色时必须使Governance只接收revision/epoch一致状态，不能为抢跑选择忽略CI失败。
- 固定Go生产V4 DISABLED、ABI sentinel features=0、无真实驱动/三cipher/Rust FEC或性能实测资格，root依赖升级必须经M0。若任何一步无法满足，单独标`BLOCKED`，不能把`READY_FOR_G2_TRANSACTION`误认为worker已经active。

**R1 Normal/off并行开发可在完成该G2授权与基础接线、并且worker已实际领到独立分支后立即开展。** 不要求先完成R1的三cipher、R2恢复、R3 FEC、R5负载或用户物理机器测试；那些分别是后续阶段交付门。下一唯一动作是**执行一次有界G2正式分配事务（含最小workspace/cursor/branch/CI接线）并由Actions验证，不启用V4产品**。