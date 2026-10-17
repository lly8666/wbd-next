# M1 -> M0 · 共享构建/线程验证依赖协调（非阻塞首个模型）
时间：2026-10-14；role M1 revision2 epoch1；branch `work/m1-r1-runtime`。
请求类型：G2 共享 Cargo / 工作流、非生产 ABI。M1 没有写 `Cargo.toml`、`Cargo.lock` 或 `.github/` 的权限。

1. 后续真正跨线程 owner 通讯需按 02-RUNTIME 的 `rtrb` 有界 SPSC；请 M0 审核固定版本/锁文件并接线；现首个无新依赖模型使用 owner-local `VecDeque` 和有界 `std::sync::mpsc::sync_channel` 最后引用 return，并明确不声称已经具备 SPSC 热路径资格。
2. 需要 `loom` (dev-only) 覆盖 armed/queue/stop 竞态；现有 native 测试为确定性交错和线程 join，不是 loom 枚举，也没有 OS Waker。
3. M0 后续组合 `lib.rs` 消费 M1 的 owned buffer 与 M3 真 seal/wire、M4 driver outcome；当前不请求改变 frozen trait/公共 ABI。

在 M0 审定前，M1 仅履行本轮局部证明，不扩大路径、不修改共享构建。

## PACK-011 staged owner output (source-locked)
SOURCE `89a3acb23616a46ecc65fc2dcd0b75182b6b482a` proves owner-local preallocated 0/1/32/33, cooperative 100us turn alternation, bounded 64+32 return of 96 multithread producers, retry wake after injected first failure, and parity bytes including unequal wire record sizes; native38998296147 **98/98 PASS**. This is **not** integration of `rtrb` bounded SPSC, platform eventfd/mio/Windows auto-reset wake, loom model, actual 3x64 owner wheel 100k jump or M0 engine real I/O lease. These need root Cargo/workflow/dependency decisions and actual M0 owner adapter; M1 cannot edit those shared paths. Existing `ReadyTurn::run`, `Arena::drain_returns_bounded(64)`, `WakeGate` and `TxOwner::with_parity_share` provide scoped integration signatures; old `drain_ready_batch` and full `Arena::drain_returns` remain available rollback. Do not enable product/ABI features on this request.

## Live R1-M1-DIRECTIONAL-OWNER-SPSC-WAKE-012 dependency BLOCKED

Main registry rev2 epoch1 active M1 012 assigned. At SOURCE `3c2b079ab88676a5c9c62ffecb90e8ae2b735ac2` worker native [39006176250](https://github.com/lly8666/wbd-next/actions/runs/39006176250) **103/103 scoped PASS**, includes five genuine direction-exclusive OS-thread and original-owned queue pressure tests. However main `Cargo.lock` and engine `Cargo.toml` **do not pin/declare `rtrb`**; only M0 has paths to edit shared root. M1 safely provided `runtime::directional::{split_tx,split_rx,DirectionProducer,DirectionConsumer,TxIngress,RxIngress}` on bounded `sync_channel` as **compatibility fallback** with no per-item handle cloning, not a fake `rtrb` PASS. M0 action: once pin known-supported `rtrb` version to workspace / engine / lock with offline GitHub native runner package availability (and dev-only `loom` if viable), hand exact dependency ref to M1 for replacement and source-exact interleaving tests. For true OS eventfd / Win event backend, M0 also owns shared platform dependencies and actual Go/driver event signal wiring. M1 will not modify Cargo/CI without delegation and retains PARTIAL until true rtrb proof. No second wire/ABI needed to run independent stage.
