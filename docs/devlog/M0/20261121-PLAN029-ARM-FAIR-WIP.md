# 2026-11-21 · M0 PLAN029 ARM64 首增量 WIP（未验证）

- **任务/授权**：main registry 的 `M0-PLAN029-THROUGHPUT`，H2245 预登记 `experiment/m0-029-throughput-arm-fair`；从 `main@18a1a0b620f0223ce9cb6dc771de9bd6f5204f20` 建本远端短分支。只改本增量的 Linux Normal/off 共享 TUN 服务次序与必要夹具。无默认速率、Go TLS、路由归属、密文/PN/修复、Windows/FEC/Game 改动授权。
- **先查旧证据**：H2240 GE1% 单→四→单流队列溢出 0/20064/14，0% 服务能力与 GE1% 局部突发是不同问题。H2244 固定 TBF450/TBF1200、reader gate 带来吞吐/CPU 或丢层反例；这些 **不得** 顺带合入。
- **实际源码边界**：`crates/wbd-engine/src/v4_embedded_go.rs` 的单 `SharedTunReader` 按已认证 /32 路由，每租约 `sync_channel(64)` 后另有 bounded pending 8 包/64KiB/100ms；`flush_shared_tun` 当前遍历 `HashMap::values_mut()`、每租约最多8，全轮64，未显示跨轮游标。单租约四条 TCP 流共享一个 route，跨租约公平本身不能证明改善这种工况。
- **首个可否定的假设**：如果多租约积压且全轮预算先耗尽，轮转服务次序可提高受损/健康租约的有界待处理公平；如果局部丢包主要在同租约 M1/之后，改变共享 pending 服务次序不会显著增加四流 goodput。先小范围单因素测试、再按测量决定是否引入流级分类。
- **成本和硬门**：保持单 reader、每租约 FIFO、现有 count/byte/age 限界、准确 original kernel copied prefix、generation fencing/Stop；不按 packet 产生 Go FFI/OS 轮询、不等满批、不移动缺失到下层。新增调度状态若有，须常数有界、只用于 backlog 非空。
- **待验证**：与原 A/A' 同 VM、同真实 Go/Rust/TUN/raw 源、ARM64 Normal/off；GE1% 四流叠真实新 TCP+稀疏 UDP、0% 高供给；对比接收端 unique goodput、双端 CPU/有效 GiB、每批 copied、Rust/TUN/qdisc loss、已回与未回、小流首响应及 owned Stop。旧 H2244 只是历史，不计本 SOURCE 产品 PASS。
- **已经验证**：原生 source `ee5f3af` 下 ARM64/x86_64 各 9 个 SharedTun + 1 个 budget-expiration 单测 PASS；原 Go TLS/Rust ARM64 五模式真实双端和 Stop 的 source `894f887` Action 44866505807 PASS_SCOPED。新分支后续参数源码不可继承旧 PASS。
- **G1 参数候选**：1Gbps/1000B ≈125kpps，64 个真实 M1 inbox 槽≈0.512ms，另 8 个 pending≈0.064ms；假定服务间隙约2ms，理论需求≈250包。测试 256 槽≈2.048ms，单租约多 192 个槽；按1000B平均增加约192KiB/租约，**最坏65,535B jumbo 则可增加约12MiB/租约**，是正式启用前的内存风险。仅 `m0_v4_probe` 编译且显式开发环境变量可选择，默认原 64。公平转轮另由 `WBD_M0_029_FAIR_LEASE_TEST=1` 显式启用，不能混入单租约参数因果对照。
- **新真实网络夹具**：已在分支添加原 Go/Rust 三 netns、同 runner A64→B256→A'64、四条内核TCP+各160 UDP/TCP 小回显和 owned Stop；GE1% 按 H2228 原 stationary 公式 p_good_to_bad≈0.252809%/bad_to_good25%/bad_loss90%/good_loss0.1%，并使 direct 与 WBD qdisc 计数窗口分开。历史错误 GE 0.16% 实为理论 0.67%，其 SOURCE 不得记 GE1% 合格。性能新 SOURCE NOT_RUN（待 Actions）。
- **状态**：WIP / NOT_RUN。此日志记录施工事实及待验边界，不是产品验收收据。

```feature-impact
{"kind":"none","ids":[],"reason":"Single Linux shared-TUN internal scheduling candidate and tests only; no public config, default, mode admission, wire, or GUI behavior changed."}
```
