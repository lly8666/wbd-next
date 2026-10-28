# M0 PLAN026 H326｜按真实M2截止时间唤醒 + 可选1/64 Owner锁争用采样

2026-10-28 基线main `53895b942d5a5657cd8b787e0ff5752836c678e3` (cursor H320)。其他agent建议2/3目前尚未“全部优化完成”，本次改进两个可直接审计的点，而非未量化地把 TX/RX 拆成两套加密状态机。

**第3点的调度修改**：Windows Rust TX 的 `m2_active || since_rx < 2s ? 20ms : INFINITE` 固定轮询已经替换为**`min(feedback.next_deadline(),shadow.next_deadline())`** 精确单调时钟截止时间。Win32 `WaitForMultipleObjects` 仍保持 Stop 首位、Wintun 和 TX/RX 通知提前唤醒；过期timeout=0，未到期向上取整毫秒，完全无deadline则无限等待。每次认证DATA/CONTROL到达RX会wake TX，因此不会错过新deadline。删除了对每个认证RX包写 `last_rx_ns` 的原子操作。Rust单元测试覆盖空deadline、已过期、最早控制回执优先、整毫秒和超长上限。**无新线程/Go包FFI/协议行为**。

**第2点的测量准备**：正常`wbd-engine`没有任何额外`Instant::now()`或者采样计数；仅显式启用Rust feature `win_native_lock_profile` 的诊断构建，会用轻量Atomic tick每64次TX/RX获取共享`Entry`锁各抽取一次，记录等待总纳秒、单次最大等待、样本数。仅在Rust已Join结束时打印一次 `WBD_WINDOWS_RUST_NATIVE_ENTRY_LOCK_SAMPLED`；Python实际Windows业务报告将其作为诊断字段，并不把高竞争推断为Go/Rust语言CPU。Workflow只有同时标记 `[plan026-probe-locks]` 才编进该feature；普通二进制所有诊断分支编译期删除。

**第3点的复制成本**：已把纯 TCP 外观ACK从先写独立2304B缓冲再复制到以太网帧的路径，改为直接在最终frame的14B L2头后构建40B ACK，减少一次全栈临时缓冲与copy（不更改TCP/IP checksum或驱动回执语义）。其他Wintun读入固定source slab、M1 seal入wire slab、DATA构建IPv4/TCP Ethernet frame、Npcap发送队列复制等必要或潜在可合并的阶段仍保留。本批不盲目移除其中任一：M1的唯一PN/AEAD Ready和真实NpF accepted-prefix/uncertain、Go原session的Wintun借用有效期不可破坏。等同机业务CPU/锁抽样+有效吞吐决定下一步选择（如in-place frame construction、Wintun完整批处理）。已有单锁8包优化仍保留。

**恢复后的 P200 证据**：首次SOURCE `0d09cd5e` Windows148.02Mbps/Linux108.12Mbps offered，首到约70%，双方owned Stop通过，但 250Mbps offered FAIL；发生器优化后SOURCE `c8352931` Windows249.0087Mbps/Linux198.2698Mbps offered，Windows收117.3942Mbps/Linux收108.3575Mbps，30%与更高的host额外损耗，真实业务Stop PASS，但仍`CAPACITY_LIMITED_OFFERED_BELOW_90PCT_250MBPS`。未证明250Mbps真实有效吞吐，也没有同机旧Go ↔ Rust A/B。新代码需要自身Windows真实编译、原签名driver测试与 P200 re-run，不能继承这两个旧SOURCE PASS。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"Windows Rust Normal/off M2 TX定时从20ms轮询改为共享反馈/修复最近deadline并去逐包last_rx_ns，同时增加只在诊断构建启用的锁等待抽样，两个功能卡同步源码变化及SOURCE未验收边界。"}
```
