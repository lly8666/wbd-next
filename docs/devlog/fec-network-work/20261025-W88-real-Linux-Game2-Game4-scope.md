# W88｜FEC 已限域收口后的原生 Linux Game2/Game4 业务资格审查

日期 2026-10-25；工作分支仅 `experiment/fec-network-tuning`。**本条审查不重新启用 Windows 测试，也不修改 M0 所属 Game/Windows 工程。**

## 是否基本完工

已刷新独立工位入口、`status.json`、最新 GitHub Actions、实际原生 Game 模式/验证门。进入本次前最新 HEAD `b80b91c5ba07cf584e0ac7af8f831440ea228f3f`；FEC Linux ARM64 固定/自动真实外层 DATA OFF 有覆盖 W77–W87 及明确负例，`scoped_integration_review_ready=true`，但**不是整体已完成**：`merge_ready=false` / `capacity_stop=true`。W80/W83/W85 的长相关 GE 最高档仍超过 1% 参考门且双组已就绪 parity 交错负结果回滚；W86 Balanced3 在 IID30% 低负载 TCP 恢复 inconclusive，W87 Maximum6 低负载 TCP PASS_SCOPED。高负载 W49/W50 混合 TCP、FEC 实际 65KiB TUN（现 Fixed/Auto 拒绝非单帧 jumbo）、远端接收端持续宿主过载信号、全新组合 outer ON+FEC 仍未重验。所有历史失败均不刷绿。

## Game 产品真实能力（勿与 Game+FEC 混淆）

`tools/network_harness/config.py` 公开的产品 mode 为 `game2` 和 `game4`，其 `game_fec` 只允许 `off`。产品没有公开 Game+FEC 编码开关与验证组合；配置 `--outer-repair=off` 对 Game 也显式 UNSUPPORTED，因为 Game 多 lane native duplicate 路径不等于一条 Normal/FEC v3 DATA repair 回路，不能伪造单 lane 零修复政策或 M2/repair_byte ledger。真实 Game 必须提供两端 `V4_ORIGINAL_GO_GAME_NATIVE_READY`，每端 `V4_PUBLIC_GAME_KERNEL` 的 copied/delivered/raw_received/auth_rejected，Stop `V4_PUBLIC_GAME_NATIVE_STOP_DRAINED`，业务双向包序列去重、源 TUN/root drop。已有 `crates/wbd-engine/src/v4_game_kernel_linux_tests.rs` 为真实 Go TLS→native M4 raw/TUN 内核首交与坏 lane 不阻健康 lane 的**组件**覆盖，但不顶替本文业务性能。

## 预声明有限 Linux 原生业务（每 Action 一种配置/一个测量 job）

复用**已经构建**的 product exact source `4322a811fd63e096458f202767faa2f097a587c0`，ARM64 Action [40203220219](https://github.com/lly8666/wbd-next/actions/runs/40203220219) product ZIP artifact `12602931174` SHA256 `0ae0939bdd4c02932a6452260fa65f4e1851bf37bd79d7485c28e1895022f125`。单端3Mbps、有序 TCP 两流占4%、UDP占96%、混合64..1287B、75ms单程，15s Clean前→30s独立每lane IID20%→30s第1lane黑洞其余健康→15s Clean后，warmup15s/drain30s。Game2/4 均使用 test netem `lane_loss=independent`，每lane各50Mbps，不把它叫“共享50Mbps”。真实 netem `unseeded_recorded`，不挑seed；严格1% UDP/小包门仅在Clean前后，受损段保留实际 UDP/TCP/p99/真实源/CPU/PSI 和 lane 计数。高损和黑洞段**没有虚假的全业务零loss门**，按复制通道逻辑和正常通道可达性解释。

- [Game2 单场景](../../../tests/network/fec-work/W88-Game2-independent20-lane1-blackhole-original-arm64.json)，提交 `1ff936793f4c08b54a00ad560e5659e0cdf49d65`；Action [40206528368](https://github.com/lly8666/wbd-next/actions/runs/40206528368)。
- [Game4 单场景](../../../tests/network/fec-work/W88-Game4-independent20-lane1-blackhole-original-arm64.json)，提交 `9376214919dcc8451e8c659cfe9d70fe707dd0df`；Action [40206531539](https://github.com/lly8666/wbd-next/actions/runs/40206531539)。

Windows Game x64/Go/Wintun/GUI/packaging 依上轮用户要求保持本工位 `TEMP_SKIPPED_USER_20261025 / NOT_RUN`，**不改变 M0 Windows Tasks/CI**。不新增 Mode/FEC 协议协商、不加 Linux 压力负载、不用单 lane v3 字节账本冒充 Game 复制。结构化范围见 [W88 预声明收据](../../evidence/fec-network-work/20261025-W88-linux-gamemode2-game4-scope-and-intent.json)。当前仅预声明，必须拿到原始 Action artifact 后再赋予业务资格与完整结果。
