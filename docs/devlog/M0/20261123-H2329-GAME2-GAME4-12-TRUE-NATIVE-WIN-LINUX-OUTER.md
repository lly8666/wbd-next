# M0 H2329 · Windows 原 GoTLS/Rust 客户端 ↔ Linux 原服务端 Game2/Game4 外层真实表演复制：12 场

## 原始 source 和证据读取约束

- 全部 12 个独立真 Windows2025 Npcap/Wintun/签名 Go EXE+Rust DLL ↔ WSL2 Linux 原 GoTLS/Rust server 的 Action `native-public-two-os` **确切产品 SOURCE** `92920fb96f2d77ca11abcfdf4a4069d24731f62b`，**夹具/工作流 SOURCE** `71e8304532f77236f4aa635afd9f4d004eba2db2`。60s，双向 10Mbps，250ms，真实 netem 0/5/30%，Game2/4 FEC OFF/fixed6，同一个签名二进制从已合格 [45111958268](https://github.com/lly8666/wbd-next/actions/runs/45111958268) 复用、实际每文件 SHA256 校验；双方 Go TLS/原 Rust M4、source/TUN/Stop 真读回。
- 12 个底层 Windows Game 原生 runs **全部 `conclusion=success`、`PASS_BOTH_OWNED`**（高损也有双向首发业务）；上层 [H2325 12-case controller #45118015225](https://github.com/lly8666/wbd-next/actions/runs/45118015225) 的 lossy 组红色，是验证器误把 Windows `WBD_GAME_NORMAL_SHARED_OUTER_STOP` 用在 Linux 日志上，造成 `linux_outer=NOT_MEASURED`，**不是底层业务失败**。错误修复见 H2328，仅未来校验自动适用；本记录从已上传的**底层原始 artifact**分别核验 Win 原 Rust Stop、Linux Go `V4_PUBLIC_GAME_OUTER`、Linux Rust `WBD_GAME_{OFF,FEC}_LINUX_NORMAL_OUTER_STOP`，Linux Go 重传计数与 Rust copied 完全相等，F/R 字节来自真正 Rust Stop 而非 parity。
- 下表 Win 一栏在 GameFEC 使用原 Rust `copied_appearance`（非 settled）并另记 settled 数；FEC OFF 则取 `repair_accepted` 每 lane 求和。Linux R/F 分母为 Linux Game Rust 原首发的 `first_record_wire_bytes`；不是两端应用 goodput、FEC parity 计数，也不可用作 Windows 的 R/F。CPU 是 Windows Go+Rust 整进程秒，不是单独外层算法 CPU。
 
| 模式 | 丢包 | Win 复制次数（fixed6: 已承认次数） | Linux 原反向复制次数 | Linux Rust R/F | Linux parity_copied（独立） | Windows 整进程 CPU-s |
|---|---:|---:|---:|---:|---:|---:|
| Game2 OFF | 0% | 2 | 364 | 0.2280% | 不适用 | 8.17 |
| Game2 OFF | 5% | 2 | 364 | 0.2384% | 不适用 | 4.88 |
| Game2 OFF | 30% | 2 | 360 | 0.2314% | 不适用 | 5.19 |
| Game4 OFF | 0% | 1 | 727 | 0.2406% | 不适用 | 31.56 |
| Game4 OFF | 5% | 1 | 737 | 0.2430% | 不适用 | 30.42 |
| Game4 OFF | 30% | 1 | 727 | 0.2427% | 不适用 | 21.80 |
| Game2 fixed6 | 0% | 1,519 (1,457) | 374 | 0.1033% | 109,611 | 23.03 |
| Game2 fixed6 | 5% | 1,506 (1,455) | 378 | 0.1042% | 109,441 | 25.09 |
| Game2 fixed6 | 30% | 1,510 (1,431) | 376 | 0.1063% | 109,596 | 23.28 |
| Game4 fixed6 | 0% | 2,781 (2,452) | 781 | 0.1048% | 106,098 | 44.47 |
| Game4 fixed6 | 5% | 2,787 (2,468) | 781 | 0.1075% | 105,936 | 44.86 |
| Game4 fixed6 | 30% | 3,007 (2,912) | 790 | 0.1053% | 109,409 | 31.50 |

## 真实结论与仍未过的资格

1. **事实**：Windows Game2/4 ON 外层复制不是零，Linux 反向两个原 owner log 也不是零，源/二进制/双端 Stop 真实，parity 与 outer 明确区分。底层 signed Win/Linux source-locked 功能/mechanism/Stop scoped PASS。
2. **外观不均匀**：Windows FEC OFF 在 30% 高损只有 Game2 两次、Game4 一次，几乎不能呈现历史 9% 视觉比例；Windows fixed6 在 **0% 丢包也发 1,519/2,781 次**。Linux server Game 无损也 ~0.1%–0.24% 原首发字节，且有损比率基本不增长。说明 Game 的现有 time-paced/ACK-hint 混合方案非损失敏感；**不是** Normal 的无损近零→30%约9%表现。是否属于产品外观资格需按用户低 CPU/旧阈值单独判，不能因 `native-public-two-os success` 算 performance PASS。
3. **开销不可归因**：fixed6 进程 CPU 增长还包含 FEC 符号编码、更多 lane、Game4 数据复制；没有相同 VM、相同 FEC 的 ON/OFF 同构 pair，不能将 CPU 差全归外层重传。Windows Game FEC 只给 copied/settled 次数，未直接给可靠线宽 F 字节，**Windows Game byte R/F=NOT_MEASURED**，不可混用 Linux 分母。
4. **能力边界**：此矩阵是真 Windows **客户端**↔真 Linux **服务端**双向流，不是 Linux client→Windows server。Linux client↔Linux server 的独立同源码双向 18 档在另一工作流核收，源 `d5c64d2` / 主线修正后的 `00906b7` 要分别记账，不得 cross-source PASS。
5. **后续判断**：GameFEC 无损复制及 Game OFF 30% 极少复制属于 **PRESENTATION_POLICY_NEEDS_EVALUATION**；不应为了强行凑比例新增不受真实边界限制的高 CPU 全量索引、定时 PTO，或把历史已废弃的 M2 per-record Receipt 复活。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Preserve 12 actual signed Windows-to-Linux Game2/4 original outer-copy bilateral owner counters, parity-separated and source-frozen; identify policy/CPU limits; no product runtime change and no retroactive green on original false-red controller."}
```
