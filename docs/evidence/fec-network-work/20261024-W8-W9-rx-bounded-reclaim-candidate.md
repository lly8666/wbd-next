# FEC Maximum 50 Mbps 接收容量最小修复候选（待 ARM64 验证）

来源：本分支 `6cd5f7d36b6c0fd97087cec30c020aae35123aa0`；旧已验证产品 `b601f2e546bf5f071eb33a80a01beec71d91c5cf`，W8 [50 Mbps](https://github.com/lly8666/wbd-next/actions/runs/40082173102)、W9 [75 Mbps](https://github.com/lly8666/wbd-next/actions/runs/40082494664)。两场景独立 Action、均是真实产品/outer-repair OFF/FEC Maximum 30% IID 300ms。W8 双向残余 4.36/3.905%，W9 11.52/10.42%；TUN 源端 0 drop、outer DATA 0重传，绝非基于外层加压修复。

**数值定位**：业务 50 Mbps 主要 1287B，源包速率约 50e6/(8×1287)=4856.25/s。满组 k16 平均约303.52块/s，150ms 中可涉及约45.53块，超旧 `MAX_ACTIVE=32`；75 Mbps 相应 68.29块。假设满组均需完整缓存，旧1MiB/32 活跃槽位很可能先于宿主 CPU 达到边界。**只是容量压力上界相关性**，真实源块是不同 k、Parity 经 IID 30% 损伤且迟到；老总 `decoder_rejected` 不能等于 codec 错误。

**定向补丁**（只改原 `v4_fec2_live_rx.rs` 和必要原生 Stop 观测与现有 build 的单测，不改网络岗位外层修复算法）：

- FEC parity 表明准确 `actual_k` 且所有源 bit 已经被原始到达或 RS 恢复**首次交付**后，立即移除块源/Parity 缓存、释放 charged bytes，保留有限代际的 `retired` block ID；后续重复/迟到不会再交付 TUN，不阻塞新业务。未完整恢复的块仍按原150ms与容量淘汰。
- 上限有界 `MAX_ACTIVE 32→96`、`1MiB→8MiB`、`BLOCK_REORDER_SPAN 128→512`；允许覆盖真实 50/75Mbps 150ms 段，**不表示容量达到200Mbps**。没有改变 MTU、身份认证、AEAD/PN/replay、FEC math、parity 首发、Fast/PTO 外层和 Stop。
- 新增真实 RX Stop 时一次性数字汇总：`peak_active/peak_bytes`、`pressure/age/reorder_evicted`、`completed_early`、`invalid_retired`、`refused_bytes`、`reject_invalid/capacity/conflict/codec`。不能把正常完成后来的冗余 parity 视为实际漏交付。
- 新 ARM64 native 一次构建内运行 FEC RX 模拟 56块真实 k16/5源缺/5 parity 足够恢复+释放的确定性单测，保留重放/Stop/完整性单测。通过后仅 W8 同工况新单例复验，记录应用未到、p99、CPU、RSS、源端与 netem 队列 drop、实际 parity/recovered TUN。
- 容量不足**停止更大档**；无容量修复后收据时 `merge_ready=false`。Auto W10 工作暂停，历史结果保留；不得把旧 b601 ARM64 产物证明本源码。

本文件为已定位**候选修复方案**，不是“性能已通过”的宣称。
## W11 负面结果及候选策略撤回（2026-10-24）

同 ARM64 VM 顺序 A/B [40086619261](https://github.com/lly8666/wbd-next/actions/runs/40086619261)、artifact `12556763687`：A旧 `b601` 接收应用残余 C→S/S→C 3.93%/3.63%，B候选 `2674` 反而 8.81%/12.23%；B CPU 10.57/10.85 CPU-s，比 A 12.11/12.02低但**业务严重劣化，判 FAIL**。B decoder_rejected=116812/119879，大量来自完成块早退之后的晚到合法 parity。B真正 raw_observed 333382/341586 vs A363738/364280；源端 TUN 0 drop、外层 DATA 0 retransmit。这两个 SOURCE 之间还包含 Auto 公共源码，**不能仅凭此 AB 对 FEC RX 的所有因果下结论**。原报告的第一版「完整块立即退休」方案 **明确撤回，不能合并**。

下一版只保留有数字依据的 bounded hard cap：96 active /8MiB，原150ms和128块 reordering不变、完整块不早退，保留成熟源/Parity 收据直到正常 retire。新增 Stop 时一次性 `V4_PUBLIC_FEC2_RX_CAP` 数字化统计进入已有 harness 产物，拆分 `pressure_evicted/age_evicted/reorder_evicted/invalid_retired/refused_bytes/reject_invalid/capacity/conflict/codec`。重新冻结 ARM64 binary 再使用原 50Mbps场景，与更接近的新源码基线 a969 在**同一 job VM A/B**核真实修复。**本段为待验候选，无性能通过宣称。**
