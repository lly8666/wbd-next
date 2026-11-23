# M0 2026-11-23｜Game2/4 外层表演重传按 Normal v3 重做（WIP）

## 目标与原约束
用户明确要求将 Linux/Windows 的 Game2/Game4（FEC OFF/fixed）外层原密文机会重传按照 Normal 已有算法**重做**，不仅仅共用辅助函数；保持原真实 first-copy、各物理 lane 的 TCP Seq/PN、AEAD/FEC/Health/Stop 和 driver 出口。不增加第二反馈控制器或盲 DATA PTO，CPU 优先。原 Normal 的源锁 Linux 0/1/5/10/20/30% loss 双端 R/F 基线分别约 0/0.45/2.36/5.3/8.9/8.9%；这是目标对照，不是 Game 已实测成绩或强制下限。

## 分支与正在施工的差异
- 开发分支 `work/m0-game-normal-outer-20261123`，PR #71 **Draft**，原 main `a2874f2434436bca6f52f06f6ab7aec4228fa17b`。
- Windows Game `v4_windows_game_outer.rs`：OFF 原双 1/2 筛选去掉一重，OFF/fixed 共用 Normal `win_v3_admit_shadow`；`OuterAckIndex` 提名 SACK 缺口不另套累计头匹配；去掉 FEC 单独 80ms 补发间隔，仍由 Normal 原生 `ReceiptState`、全局预算、真实 NPF 完成结果控制。
- Linux Game `v4_game_cosmetic_outer.rs`：移除每 lane 一个 shadow、同 ACK 滞留≥1秒、每 ACK 期一次和独立 80ms 冷却；同 Normal `OuterAckIndex + ReceiptState` 允许多个冻结候选及 ACK/SACK 真实缺口，1.2s 有界快照保留，9% pacing/10% firstsend 预算。当前 Linux 使用 Game 组共享一个 `RepairBudget`，不是跨进程 `GlobalRepairAllocator`；这一差别必须保留为待评估性能/总额度风险，不能谎称完全同实现。
- Linux `linux_raw_carrier.rs` 原 Game 单记录读取现在可选暴露 tuple/checksum 验证的纯 ACK（len=0）；Game RX 从已存在 atomic feedback 通道供给重传索引，不把纯 ACK 当 AEAD/业务/Health/FEC。

## 新增机制定位与进展（精确 SOURCE，非旧样本推断）
- **根因一**：Game 各 lane 的外层累计 ACK 过去附着在跨 lane 逻辑 TUN 首次交付；即使物理 lane AEAD/PN 已打开，也可能被兄弟 lane 去重而停滞。现在改为原物理 AEAD/PN 开启后更新 outer presentation ACK；TUN 交付、FEC/Health 与修复计数不混用。
- **根因二**：Game ACK-only 曾无 SACK，继而只带一个 SACK。Normal 原实现携带最多四个已验证正 SACK 区间，且累计 ACK 长时间停滞≥250ms时仅在 TCP 外观层跳过旧洞。现两端 Game 都复用该结构：4 个固定栈/atomic SACK 槽、250ms 外观跳洞，无新 worker，无盲 DATA PTO。
- **指标**：Go/Rust 现有原生 Linux Game M4 readback ABI 从四计数向后兼容可读六计数：追加真实成功 first outer IPv4+TCP DATA 字节 F、实际成功原密文补发字节 R。真实现场按 R/F 验 10% 高载上界；0% 期望接近0；原始第一次和修复均不伪造。
- **构建**：Go overlay 位于无 go.mod 的扩展目录，独立 `go test` 不是正确入口，只有原始 Go 包成品可以验证。Windows source lock `manifest-plan020-m0.json` 的 Game Linux overlay result Git blob 已精确重钉。M0 非主短分支的通用治理仍因 `unassigned branch` FAIL，不是代码失败；source-frozen experiment 分支治理检查通过。

### Linux 真实原生 netem 数据
- SOURCE `8f86d1adcff7860005bb882fd35c5930ac250a74`（250ms 跳洞、单 SACK、真实 F/R 计账），Actions [45169262321](https://github.com/lly8666/wbd-next/actions/runs/45169262321)：Game2 OFF 30% 双端 R/F=8.920%/8.920%，Game4 OFF 30%=8.909%/8.908%，Game2 fixed FEC 30%=8.863%/8.854%，Game4 fixed FEC 30%=8.897%/8.897%；Normal 30% 双端 8.933%，Normal0%=0%；Game2 OFF0%=每侧1次（R/F 0.000097%）；但 Game2 OFF5%=8.792%/8.775%，偏离 Normal5%≈2.36%，这**不算曲线收口**。
- SOURCE `91170a8ff92de8c47f46bbaae1543eaddce2a360`（4真实 SACK、250ms 跳洞、F/R 回读），Actions [45170955001](https://github.com/lly8666/wbd-next/actions/runs/45170955001)：Game2 OFF0%=0.000097%/0.000097%；Game2 OFF5%=**2.415%/2.356%**，CPU 2.85/2.98s，业务首次交付≈9.99Mbps；Game2 OFF30%=**8.918%/8.914%**，CPU 3.39/3.71s；Game4 OFF30%=8.909%/8.908%，CPU6.36/6.78s；所有已读取样本为原始 Linux RAW/TUN 双端产品测量。1/10/20% 任务先因 `scenarios/...loss1/10/20...json` 不存在而未进入网络测试；现在已按原5%场景结构创建对应原生 60s netem 档位，新 SOURCE [45172010956](https://github.com/lly8666/wbd-next/actions/runs/45172010956) 正在执行，不能预写结果。
- CPU 注意：旧低频 Game4 fixed FEC30% SOURCE `50f1563` 双端约9.55/9.87 CPU秒，源 `8f86d1a` 高密度 FEC30% 约18.01/18.49 CPU秒。外层补发字节大幅提高，但真实额外 CPU 尚无 ABBA 正规同源开销分解，**性能关口未完成**。

### Windows 真正签名原生状态
- 当前原生 Windows2025 NPF/Wintun+WSL2 构建测试对应 frozen SOURCE `6f8859d3f8cf1b2286dc7658bc0768c72b9bf157`（4 SACK+manifest pinned），[45171406732](https://github.com/lly8666/wbd-next/actions/runs/45171406732) 已见 Cheap assembly、Windows Rust 单元、Windows Go 编译、Linux Rust 单元通过，后续真实原生测试仍需读结果，不能视为已通过。
- 较旧 frozen SOURCE `50f1563` 的 Windows 真原生网络测试因 WSL2 `wsl.exe` 命令 120s 超时、Linux RST 规则不可用，网络场景 `NOT_RUN`；较旧 `6e555ea` 因 Go overlay manifest 未重钉被廉价 preflight 拦住，均不可等同当前算法失败。

## 尚未完成/改判条件
- 当前真实 Linux source `91170a8f` 的 1/10/20% 原生新场景和 Game2/4 FEC30% 后续结果；Windows Game2/4 OFF 与 fixed 双端新源码真实 R/F、首次业务交付、Stop；高密度补发 CPU（尤其 Game4 FEC）与 Normal/原旧源同场景 ABBA。Linux Game 使用 group-local `RepairBudget`，Windows 用原 `GlobalRepairAllocator`，资源域尚未完全同算法。
- `main` 未修改；PR#71 必须维持 Draft，不把 Rust 单测成功或 Linux 单一成功当成 Windows/全项目通过。无盲 DATA PTO、旧 M2 receipt 复活、额外 worker、逐包加密。

```feature-impact
{"kind":"updated","reason":"Game2/4 OFF/fixed Linux and Windows outer opportunistic retransmission is being rewritten on the proven Normal v3 ACK-gap, immutable shadow and byte-budget algorithm; source branch draft, not qualified.","ids":["outer-opportunistic-repair"]}
```
