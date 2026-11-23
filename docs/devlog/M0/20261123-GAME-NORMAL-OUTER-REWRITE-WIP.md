# M0 2026-11-23｜Game2/4 外层表演重传按 Normal v3 重做（WIP）

## 目标与原约束
用户明确要求将 Linux/Windows 的 Game2/Game4（FEC OFF/fixed）外层原密文机会重传按照 Normal 已有算法**重做**，不仅仅共用辅助函数；保持原真实 first-copy、各物理 lane 的 TCP Seq/PN、AEAD/FEC/Health/Stop 和 driver 出口。不增加第二反馈控制器或盲 DATA PTO，CPU 优先。原 Normal 的源锁 Linux 0/1/5/10/20/30% loss 双端 R/F 基线分别约 0/0.45/2.36/5.3/8.9/8.9%；这是目标对照，不是 Game 已实测成绩或强制下限。

## 分支与正在施工的差异
- 开发分支 `work/m0-game-normal-outer-20261123`，PR #71 **Draft**，原 main `a2874f2434436bca6f52f06f6ab7aec4228fa17b`。
- Windows Game `v4_windows_game_outer.rs`：OFF 原双 1/2 筛选去掉一重，OFF/fixed 共用 Normal `win_v3_admit_shadow`；`OuterAckIndex` 提名 SACK 缺口不另套累计头匹配；去掉 FEC 单独 80ms 补发间隔，仍由 Normal 原生 `ReceiptState`、全局预算、真实 NPF 完成结果控制。
- Linux Game `v4_game_cosmetic_outer.rs`：移除每 lane 一个 shadow、同 ACK 滞留≥1秒、每 ACK 期一次和独立 80ms 冷却；同 Normal `OuterAckIndex + ReceiptState` 允许多个冻结候选及 ACK/SACK 真实缺口，1.2s 有界快照保留，9% pacing/10% firstsend 预算。当前 Linux 使用 Game 组共享一个 `RepairBudget`，不是跨进程 `GlobalRepairAllocator`；这一差别必须保留为待评估性能/总额度风险，不能谎称完全同实现。
- Linux `linux_raw_carrier.rs` 原 Game 单记录读取现在可选暴露 tuple/checksum 验证的纯 ACK（len=0）；Game RX 从已存在 atomic feedback 通道供给重传索引，不把纯 ACK 当 AEAD/业务/Health/FEC。

## 当前验证与待审
- 新 `.github/workflows/m0-game-normal-outer-wip.yml` 仅绑定开发分支，Linux Rust 单元与 Windows2025 单元测试编译。真实内核网络与 R/F、CPU、P99：**NOT_RUN**，旧 SOURCE 的 PASS 不继承。
- 旧通用 worker-native 失败 `unassigned branch`，属于其固定 M1–M4 分支校验，不能等同于源码编译失败；治理对新 M0 分支 role 注册要求未解决。
- 后续须根据编译日志修改；原生零损与 1/5/10/20/30% 双端矩阵、真实 copied R/F、FEC OFF/fixed、signed Windows、CPU 和 Stop 各自保留验收结果，不由单元测试臆断。
- 禁止 merge main 直到实际源码/双端测试及用户期望范围达到条件。记录一切旧 FAIL、未测、不同平台基线差别。

```feature-impact
{"kind":"updated","reason":"Game2/4 OFF/fixed Linux and Windows outer opportunistic retransmission is being rewritten on the proven Normal v3 ACK-gap, immutable shadow and byte-budget algorithm; source branch draft, not qualified.","ids":["outer-opportunistic-repair"]}
```
