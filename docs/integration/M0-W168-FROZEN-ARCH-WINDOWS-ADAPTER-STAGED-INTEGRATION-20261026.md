# W168 冻结架构 → Windows 测试分支 → main：分阶段真实合并合同（2026-10-26）

> **状态：真实双亲 Git 合并已进入独立 staging PR #28，Windows/Linux 合并后功能资格未确认，绝不批准合 main。** 实际 merge commit `fea9cd94a8cabcb6ef3d6958f9ba8db8300721d5`，parent1 `9c1ad625334339d7971ef8a19efb158e2dd8cb7f`（继承 W），parent2 `254cf4110c1df3878c7bd0e782145fc381189b8f`（W168 F）；新同源码真实 Actions [40354611434](https://github.com/lly8666/wbd-next/actions/runs/40354611434) 的结果必须核实。** 按最新用户指令：实验已完成并冻结，允许取此固定版本进入独立 Windows 功能集成；Windows adapter 适配实验架构及 **W168 最终外层重传策略**，不得倒退实验核心。产品安全/真实驱动/Stop 严格不降级。性能测量暂不做，主线原验证门不删除。

## 1. 两个真实 source 与已有证据（先锁定后合）

| Authority | 不可变 SOURCE | 事实 |
|---|---|---|
| 实验 Linux/FEC/Game/TUN | `freeze/fec-linux-w168-20261026` = `254cf4110c1df3878c7bd0e782145fc381189b8f` (F) | 当前 experiment HEAD 恰好等于 F；相对旧暂存 `6852734` 多 **112 commits**，67个变更路径；代码与 W168 收据必须完整更新 |
| Windows Original Go TLS/Npcap/Wintun | `fix/m0-windows-functional-wiring-20261026` = `05d25fade4768feb4a6e2ad8109aa89cbf94e6c7` (W) | 原生 TCP/UDP/Stop 已经在其源码祖先 `0dc7b58d5a043d73e590e00586d80f7312f1cdb4` 的 [Action 40311271021](https://github.com/lly8666/wbd-next/actions/runs/40311271021) **PASS**；W 后两提交仅文档证据 |
| main (暂不写) | `7a6a289147d423c20b949697b0bcd4d8d70aaade` (M) | 主线 Windows M0 治理/历史 WL-N0 失败和性能硬门仍独立；W 相对 main +4 commits / 6 changed paths |
| W168 matrix 实测源 | `0776fc4ede72fabd711e8333568eb88a58e8a6ea` | [Action 40345202316](https://github.com/lly8666/wbd-next/actions/runs/40345202316) Linux 双架构56/56 scoped UDP cases SUCCESS，另 ARM64 高压 scoped PASS / AMD64 250Mbps INCONCLUSIVE。F 比这个实测源晚2个提交，主要收据+小范围 harness 变更，仍需验集成最终源码。 |

F 的现存 `docs/evidence/fec-network-work/status.json` 依旧是 `merge_ready=false`、`capacity_stop=true`；用户最新“冻结开发结束”允许**隔离集成与功能验收**，不等于原岗位自动全平台 PASS，绝不篡改 F 的 status、历史红灯、PSI/容量负面数据。实验源码资格和 Windows 原生资格按确切 SOURCE 分开记。

## 2. 真实分支拓扑（禁止 PR#26 copied-blob 伪合并）

```
main M -------------------- (held until Windows mode-gates)
   \-- Windows functional W (PR #27, draft, W is green Normal/off)
        \-- integration/w168-freeze-windows-adapter-20261026 (THIS isolated branch)
             \-- real git merge [current integration-first-parent, F as second parent]
                  \-- Windows adapter integration patches and exact-source native Actions
                       \-- merge-commit to W test branch after all functional gates
                            \-- re-review/merge-commit PR #27 -> main after main-owner gates
F freeze/fec-linux-w168-20261026 -----------/
```

**本分支已建立真实双亲 merge commit `fea9cd94`：未做最终七模式代码接线/资格测试。** 不允许直接更新/强推实验 F、现有 W、main。正式首次 merge 对候选源码必须包含 F 的真实 parent ancestry，不能复制 700+ 文件、不能 squash/rebase 破坏以后 F_n→F_(n+1) 的 merge-base；检验 `git merge-base --is-ancestor F final-candidate`、`git cat-file -p <merge-sha>` 双亲及 tree SHA。一旦 final binary SOURCE 与 tested SHA 不同，重新执行相应 Actions。

PR #26 是过时的只读大型冲突审查，绝不作为主线晋级；PR #27 是最后的 Windows→main Draft，保持不提前合。候选可单独 Draft PR 指向 **Windows W 测试分支**，待真正 merge 且 CI 功能门全部合格，再通过 merge commit 引入 W；随后 PR #27 对 main 也必须使用 merge commit（不 squash）。

## 3. 新权威文件及语义冲突处理

### F = 架构 + FEC/Game/TUN + shared outer DATA retry policy

- `crates/wbd-engine/src/v4_embedded_go.rs` 及 `v4_fixed_stream.rs`、`v4_game_lane.rs`、`v4_game_public_kernel.rs`、`v4_game_fec.rs`、`v4_fec2_live_rx.rs`、共享 memory/runtime、Linux native CLI/bridge/harness：**F 整体结构和最终行为是权威**。不要倒回 main 的 older owner/queue/TUN ingress/RX Game/shared FEC 算法。必要的 main 纯 bugfix 用最小、mode 守卫移入，优先不修改核心执行图。
- **非常重要：旧 2026-10-26 rolling-merge 合同中的 “FEC-only 外层 DATA repair OFF” 在 W168 上已过时。** W167/W168 公共原 Go Linux CLI `--outer-repair=on` 为默认；用户明确要求 W168 outer policy 优先，Windows 必须按冻结实现对 Normal OFF/Fixed/Auto 与 Game2/4 OFF/Fixed6 逐模式读取原生 runtime ON/OFF，与显式 OFF 回退相同语义。不能用旧 main 的 80ms / 2次 repair/RACK policy 覆盖 F。是否真正存在可计量 repair 依 F 的账本（Game 外层 DATA retry占比目前 NOT_APPLICABLE/NOT_OBSERVED），不可用游戏首发副本/parity 假充。
- W168 Game4 Linux 正式默认复制时序 `0/4/50/140ms`；保留显式 `stagger-4-20-60`、`immediate` 回退。Normal 长丢包全新分批 profile 在 W166 **MODEL_ONLY_NOT_IMPLEMENTED**，不得把模型预想当产品代码。

### W = Windows 原始 Go TLS/Npcap/Wintun、Adapter、本机完整生命周期与功能证据

| 文件/层 | 最终解冲突动作 |
|---|---|
| `crates/wbd-engine/src/v4_windows_owner.rs` | 在 F 的 ABI/架构约束下**重组 Windows adapter**。保留 W 的真实认证 reverse M2 生成/完成、`v7_reverse_m2_feedback_due/result`、真实 NPF firstsend 成功才 M2 admission、1536 shadow/Normal 2048 M1/5MB合理容量、受限输出 preflight 不暗耗 PN/SEQ、RX unique/open 和 Stop。容量和 repair 时机依冻结的 runtime contract 再核，不把 main 旧 repair 算法一同移入。注意 F 版此文件 shadow=768 且缺 reverse kind1 API，原样取 F 会使 Windows 已通过功能回退。 |
| `r0/go_overlay/cmd/wbd-client/m0_native_v4_peer_windows.go` | 使用 F 新 ABI 调整结构，但保留 W 的 `rustFeedbackOne`、真实 Npcap `ReportOriginalM2NpcapFirstsend`、严格 Rust SEQ = Go sendNext、`rx.NoteAuthenticated` 4MiB高水位、仅 M3 唯一认证后 Wintun 交付、无伪造 ACK。配套 `m0_native_v4_rx_window_windows.go` 一起审核。 |
| `r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go` | F 现为旧268行，W 315行；保留 W 真实 Windows Underlay/WSL verified MAC、route/WAL/OS Scoped Apply/Stop，接入 F 新模式/策略。不要整文件采用 F 而丢掉已通过的宿主环境接线。 |
| `r0/go_overlay/assembly/manifest-plan020-m0.json` | 等全部最终 Go overlay 文件确定后重算真实 blob/assembly SHA，完全复检同一 source 的原始 Go TLS protected files；不能把旧 manifest 当作合并结果。 |
| `.github/workflows/m0-wl-public-normal-full.yml`、`tools/m0_wl_public_normal_e2e.py` | W 的 **真实 Npcap/Wintun + WSL2 原生双向 TCP/UDP + owned Stop** 功能证据为底，保留 main 原高压 WL-N0 门不被 F 的旧 smoke 覆盖。候选测试只触发 scoped functional 功能，不让 10Mbps/60s 性能消耗阻止接线。测试防火墙规则严格 IP+TCP45902 范围并 cleanup，绝不变产品默认策略。 |
| `.governance/workstreams/M0/cursor.json`、M0历史 FAIL/devlog、官方 workflows | main 当前 owner/governance 规则优先，保留 M0 freeze 源误删除的原证据路径（实验相对 merge-base 有 M0 历史文件删除），不得因 F 目录覆盖把主线凭据、证据和硬门删了。实验新网络 workflow 则照 F 同源引入。 |

**不自动覆盖、不以文件名把代码/策略责任一刀切**。编译失败需查 exact API/feature/owner 而非删 ABI guard；`PRODUCT_APPLIED=0` 是 Rust crypto owner 不可自行宣称全 OS APPLIED，不等同于 FEC profile 认证的 Applied revision。冻结后的 mode contract 和原始 OS WAL 必须共同满足。

## 4. Windows 接线功能验收：先通，性能另议

同一 source 先完成 Windows native Rust DLL/Go overlay/manifest ABI + Linux genuine original Go TLS Rust server 的 native Actions build。真实同源运行不能借用 W 的历史 PASS 当新源码 PASS。

按依赖顺序逐批完成，不做高载/丢包矩阵：

1. **Normal/off 先回归**：真实凭据 TLS、Npcap→Linux raw/TUN、Wintun、双向 UDP+TCP kernel app marker 确切字节、真实 M3 unique authenticated receipt/retire、Go/Rust seq/PN一致、BoundOriginalM2Reverse、RX highwater/late-gap、真实 Stop + 资源恢复。反向 TCP 仅 scoped test Windows firewall rule。已存原 W 测试仅对旧 SOURCE 合格。
2. **Normal Fixed6**：Go 真实 feature7协商，Rust M1/M3/FEC2 实际 k≤16 的有界成组和 partial deadline，真实 RS16 repair parity+各自独立 PN/seal，双向真实业务，已认证 mode/repair/M2 profile revision readback，Stop。仅 `source0` 每包新 block 的假组包不合格。
3. **Normal Auto**：在 Fixed 的产品路径上对接 F 的有据反馈、Auto revision 应用（不能从 Go 控制变量虚构），至少两种有效档位变更、双向独立读回、UDP+TCP通和 Stop；不要求全曲线性能优化。
4. **Game2 OFF/Fixed6、Game4 OFF/Fixed6**：2/4 条独立的 Go TLS / Npcap real lanes，同 Rust GroupAdapter、对端 Linux 对应 lane / duplicate first-delivery / parity共享/offset session readback、物理 lane 的唯一 PN owner、一个 lane 丢失的真实 Stop/保底送达、小规模 TCP/UDP双向字节。W168 Game4 wide default 当真实 native readback；不能把单 lane 的 Normal 进程当 Game。
5. **最终 7个公开组合功能表**（Normal OFF / Fixed6 / Auto / Game2 OFF / Fixed6 / Game4 OFF / Fixed6），每格独立 source-locked authentic two-OS Action，真实 OS Apply/Stop、one-time delivery、bounded queue + strict security PASS 才对外标 `WINDOWS_FUNCTIONALLY_WIRED`。没有覆盖的格子为 `NOT_RUN/UNSUPPORTED`，不得解锁 Rust mode-capability mask。

只要真实功能不通立即阻断下一格，复用当前 Action 构建工件后按模式拆包验证，避免在每个测试重复编译或打开高负载矩阵。

**特别保留未验证事项**：此前 main 10Mbps / 60秒 `WL-N0` 发生 +103 byte TX sequence mismatch [Action 40295748769](https://github.com/lly8666/wbd-next/actions/runs/40295748769)，低速 UDP/TCP PASS 不证明那条历史高压根因完全消失。本期用户说“不需要性能测试”，故 N0/N1/N5、500Mbps、物理网络、GUI全局WFP/DNS除非明确另授，全部 `NOT_RUN`，主线硬门仍存在不得清掉/变绿；若保护规则要求完整性能测试才能晋级 main，保持待合并状态、告知用户需要相应资格，而不是绕过。

## 5. 合并完成标准与不可做项

- 候选必须有**真实** F 冻结祖先（最终 two-parent commit ancestry 可查）；测试工作流合 W 的 native functional 约束、全部 Rust feature/API 同源编译、manifest真实hash无错、7组合每个 native proof、每模式 readback 和 Stop。
- 完成后**先 merge commit 到 Windows 测试分支 W**；重新核这次 W head 精确 source 的 CI/模式是否全部通过；继续保留 PR #27 Draft，直到复核 main 保护规则、M0 writer 最新 cursor/主线变化和验收约束，再走不丢实验 ancestry 的 merge commit。
- PR #26 copied files 审查基线和过时的 FEC-only OFF 文字禁止被再次拿作合并标准。遇独立实验历史上红灯、W168 AMD64高压 INCONCLUSIVE，完整保留；不回写实验 F 的 status/cursor，也不主动向原实验分支 push。
- 现有 `integration/w168-freeze-windows-adapter-20261026` **已经完成源锁定双亲候选树，含 F 原生核心、W 原生 adapter 和历史证据保留；尚未取得合并后真实 Windows 七模式 PASS**。不允许把本 staging 分支当前状态报告为 “已经合并冻结版”。
