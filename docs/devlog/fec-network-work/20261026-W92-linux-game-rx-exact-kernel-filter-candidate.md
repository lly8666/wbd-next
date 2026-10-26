# W92 | Linux Game 2/4 raw RX 精确内核过滤（待 Actions）

本阶段在 W91 ARM64 原生构建 [40212344161](https://github.com/lly8666/wbd-next/actions/runs/40212344161) 完整成功、无损 3Mbps 混合真实业务 [Game2 40212643000](https://github.com/lly8666/wbd-next/actions/runs/40212643000) 与 [Game4 40212646332](https://github.com/lly8666/wbd-next/actions/runs/40212646332) PASS 后展开。两项同源、不同 VM；新旧 CPU 不能直接比较。W90 fixed6/fixed0 六项真实产品失败并且已撤回，不能因此恢复。

## 证据与选择
`v4_game_public_kernel.rs` 为每个认证 lane 打开一个绑定同网卡的 `IPPROTO_TCP` raw RX FD。`linux_raw_carrier.rs::recv_one_into` 每次调用会有界 poll/recv/用户态完整 4-tuple 筛选，因此别的 lane 报文会被重复内核复制/用户态解析。当前 `receive_ready_batch` 同样循环 poll/recv，不具备 `recvmmsg` 系统调用减少证据，**不能冒充真正批量**。

TX/RX owner 全拆锁会触及 `GameAdapter` 内 `tx/rx/lanes/arena` 和 Go-owned stop/ffi，当前优先保留验证正常的 RX 唯一性/Stop。阶段 B **评估中而非完成**。用户允许共享入口侵入过大时先做精确内核过滤作为 C 的小步替代。

## 代码改动
- `ScopedRawIpv4Rx::open_exact_tuple`: 经已验证的 `GoFlow` 精确 4-tuple 生成 13 指令 Linux cBPF，在绑定源接口后的 raw socket 上通过 `SO_ATTACH_FILTER` 原子安装；**安装失败 fail closed**，没有解除身份检查/认证。BPF 使用动态 IPv4 IHL 而非假定 20B；内核预过滤只减少用户态收到的无关流量，原 `parse_data_packet` 及每条 lane 独立 AEAD/PN、共享逻辑去重原样保留。用户态无额外逐包分配/hash/新线程。
- 单元测试检查 4-tuple、跳到拒绝分支、IPv4 IHL 和非法零端口；现有 ARM64 构建追加专项并让平台文件变更触发。
- W91 原功能、FEC OFF、外层复制数学和 Common Normal/原外层算法没有修改。Windows 该工位 TEMP_SKIPPED_USER_20261025。

## 待验证/停止条件
精确 ARM64 build/native pass，然后沿用 W91 3Mbps clean Game2/4 **同 VM 顺序 old/new A/B**；外层流量/CPU/RSS/p99/TUN 和 TCP 真实交付先守门。任何更差/无法安全接入应撤回此候选，原 W91 可运行基线保留。高负载容量停止、fixed6仍 UNSUPPORTED，merge_ready=false。

## Actual validation (W92)
- Candidate first source `58c1eaece7ea` Action [40213051826](https://github.com/lly8666/wbd-next/actions/runs/40213051826) **COMPILATION FAIL** E0425 (per-lane loop bound `_` yet indexing i); fix exactly in `96522e95127641d9f8ac99436cdb7363ef36b0b0`.
- Fixed exact ARM64 original Go native build + Game AEAD, Linux BPF tuple and existing native FEC suite [40213234927](https://github.com/lly8666/wbd-next/actions/runs/40213234927) **FULL SUCCESS**, frozen artifact 12606701246 ZIP sha256 `1c704254dfac0f38e54c8ca0240ff19a6216e0c30c4d4f7bf845e2dd3f443a7a`.
- Same VM Game2 A(old W91)/B(filter): [40213467037](https://github.com/lly8666/wbd-next/actions/runs/40213467037) full TCP/UDP/Stop PASS both, client/server CPU 1.66/1.67 → 1.64/1.65 CPU-s; ~1.2% is **inconclusive**.
- Same VM Game4 AB: [40213471471](https://github.com/lly8666/wbd-next/actions/runs/40213471471) full genuine delivery both, CPU 2.61/2.66 → 2.35/2.38 CPU-s, ~10% lower, p99 ~77.5ms unchanged.
- Same VM Game4 reversed BA: [40213802360](https://github.com/lly8666/wbd-next/actions/runs/40213802360) full genuine delivery both, B 2.46/2.51 then A 2.71/2.78 CPU-s; ~9–10% lower despite order reversal, stable zero clean loss/TCP backpressure/TUN drop/Stop. No cross-VM CPU % claim, only within-job comparisons.
- Decision: retain low-risk Linux kernel exact-tuple filter for scoped clean Game4 CPU benefit; Game2 improvement unproven. No Game+fixed6 reenable. Windows remains TEMP_SKIPPED. Full shared RX entry and actual `recvmmsg` not proven.
