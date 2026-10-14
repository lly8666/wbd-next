# R1-M1-OWNER-001 · 初始实现与验证计划
身份：M1；branch=`work/m1-r1-runtime`；registry revision=2；epoch=1。
起点：`0845e739ef5d506ff44ad1d6637cc3986929ccd5`，bootstrap cursor sequence=0/checkpoint=null，无 M1 既有 S/H。

## 本原子范围
- `memory::Arena`: 256/512/768/1536/2048 固定 class 的单 owner 预分配 slab、容量收费（含保守槽元数据与 return 上界）、代际 BufferOrigin、owner stop/quiesce；
- `UniqueBuffer` 实现 M0 的 `UniqueSealable`；`FrozenRecord` 实现 M0 的 `FrozenRecordHandle`。seal 仅将 Box 移动到 Arc，clone 复用同一分配，不复制整个密文；Rust 类型防止 freeze 后修改。
- 有界 `sync_channel` 返回队列、满时 consumer fallback backlog；每借出 handle 最终只产生一个 return，backlog 容量不大于同时借出槽位总数；stop 后禁止新借出但继续非阻塞回收。
- `runtime::TxOwner/RxOwner`：彼此独立队列，fresh/repair 独立 byte+slot+age 上限；fake `MonoNs`；ready 即取、无凑满 batch 延时；每十份 fresh 尝试一份 repair，stop 丢弃未派发项，已交付 handle 必须单独返还。
- `r1_` 单测：容量、class、冻结指针别名、退还、return 队列满、跨线程最后引用 drop 与 stop 竞态、fake 时钟过期、repair 满不挡 fresh、RX 与 TX 独立。

## 有意未实现 / 禁止资格推断
- 未连接 `lib.rs` ABI 入口、真实 TUN/raw、Wintun、socket、M3 真 AEAD、M2 shadow 重发、M4 driver lease。READY 常量仍 false。
- 本地 `VecDeque` owner queues 以及 `sync_channel` return 是边界/生命周期首轮模型，未宣称满足 02 所要求跨线程 `rtrb` SPSC / OS armed+二次检查、loom 枚举或高 PPS 性能。为共享依赖向 M0 留请求。
- 当前只测单一容量 class 一个 arena、无多页混合 free-list、jumbo、timer wheel/非空索引、DRR wire 字节、NIO 或真的 M1/M3/M4 end-to-end。
- 初始测试编译与 PASS **待真实 GitHub Actions**；本地无 Rust toolchain 不当作 PASS。验证后另存 `docs/evidence/M1/`，H 必须仅写 cursor。
