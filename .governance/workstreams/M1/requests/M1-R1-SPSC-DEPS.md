# M1 -> M0 · 共享构建/线程验证依赖协调（非阻塞首个模型）
时间：2026-10-14；role M1 revision2 epoch1；branch `work/m1-r1-runtime`。
请求类型：G2 共享 Cargo / 工作流、非生产 ABI。M1 没有写 `Cargo.toml`、`Cargo.lock` 或 `.github/` 的权限。

1. 后续真正跨线程 owner 通讯需按 02-RUNTIME 的 `rtrb` 有界 SPSC；请 M0 审核固定版本/锁文件并接线；现首个无新依赖模型使用 owner-local `VecDeque` 和有界 `std::sync::mpsc::sync_channel` 最后引用 return，并明确不声称已经具备 SPSC 热路径资格。
2. 需要 `loom` (dev-only) 覆盖 armed/queue/stop 竞态；现有 native 测试为确定性交错和线程 join，不是 loom 枚举，也没有 OS Waker。
3. M0 后续组合 `lib.rs` 消费 M1 的 owned buffer 与 M3 真 seal/wire、M4 driver outcome；当前不请求改变 frozen trait/公共 ABI。

在 M0 审定前，M1 仅履行本轮局部证明，不扩大路径、不修改共享构建。
