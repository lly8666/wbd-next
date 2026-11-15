# PLAN029 H1910｜签名10GiB真实CPU卡点与当代M0源码哈希审计

- [H1909真签名Action43700145002](https://github.com/lly8666/wbd-next/actions/runs/43700145002)，Windows2025原Go/Npcap签名Wintun/Rust原进程与WSL2真实TCP+TUN，同SOURCE `64f6819460f7f950f13bc7d10659a6f4552b28b6`。分别先物理后FakeIP Direct跑单向2GiB和全双工每方向1.5GiB，同一原owner；两条路径累计**10GiB**，SHA／半关闭／Tunnel96B UDP11280条双方真交付／owned Stop及整个Action SUCCESS。500/700目标实际499.996/699.998Mbps（略小于精确阈值，不声称 ≥500/700）。
- 同一进程按Win32 User/Kernel CPU在同一Windows VM上按传送GiB折算（**包含原Go+Rust产品，不含完整Windows驱动ISR/DPC，也不是独立于Tunnel的分拆归因**）：单向物理0.468750 vs Direct11.679688 CPU秒/GiB，增加11.210938：用户5.882813、内核5.328125。全双工物理0.312500 vs Direct9.630208，增加9.317708：用户3.885416、内核5.432292。96B Tunnel UDP Windows p99物理单向0.968／物理双向1.037ms，Direct单向1.241／Direct双向2.693ms，证明更高负载下小包尾部成本可见。不同路径的Windows原进程工作量不同，不能将这个差额直接解释为“一次内核copy”或V3/V4因果；P2/P1性能仍OPEN。
- 同次H1909 [governance-maintenance Action43700145048](https://github.com/lly8666/wbd-next/actions/runs/43700145048) FAIL 三条**M0当前允许哈希**过期，与真实业务SUCCESS分开。已由当前Git tree确证 `manifest.json=cc0c56e1...`、`npcap_native_handoff_windows.go=9511ced3...`和`..._test.go=770a8845...`；两个Go handoff文件的Git blob等于`manifest-plan020-m0.json`且等于当代Assembly manifest实际结果。只在`tests/test_m4_frozen_windows_main_import.py`的`M0_AUTHORIZED_CURRENT`显式更新这三项，保留`M4_FROZEN`及`PINNED_FILES`历史严格不变。检查会继续对每个当前源字节、原Go manifest operations/count/M0派生边界fail-closed，不创建新的复用例外。
- 下一步在**同一编译源码**`64f6819460f7f950f13bc7d10659a6f4552b28b6`基础上由GitHub当前存活的Windows EXE+DLL artifact14156860270和Linux原Go/Rust artifact14156043330直接复测10GiB。严格校验两构件manifest、SHA256和Git产品/ABI diff=空，跳过无需的Go/Rust release编译，但对场景Python契约/廉价静态测试并行运行；高CPU负载只在一个原Windows/WSL2 VM中顺序对比，避免互相干扰。任何真实Stop/CPU或先验因果门失败均保留首错，不升格P2速度出口。

```feature-impact
{"kind":"none","ids":[],"reason":"H1910 only archives source-locked H1909 10GiB signed original CPU/UDP/Stop receipt and corrects three explicitly current M0 hash pins while retaining historical frozen M4 pins; no native product change."}
```
