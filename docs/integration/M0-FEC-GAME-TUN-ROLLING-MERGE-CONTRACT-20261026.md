# M0/FEC/Game/TUN 持续双分支集成合同（2026-10-26，用户最新指令）

> 本文**覆盖** `M0-FEC-GAME-TUN-CONFLICT-REVIEW-20261026.md` 中旧的逐文件主从建议；旧记录仅保留历史冲突证据。PR #26 仍是**非编译资格的审查/暂存分支**，严禁把当前 copied-blobs tree 直接标记为集成完成。本文不改变 main/experiment 代码、权限、M0 cursor 或在途 Actions。

## 0. 实际观测（不可推广为最终验收）

- 本次检查 main `7a6a289147d423c20b949697b0bcd4d8d70aaade`，实验 HEAD `f7655d7a1e886bb1e30917e84f2ee782fd119a23`，PR #26 暂存 HEAD `450666cdaee09ddccee367832a5f0f38eb47cf1c`。审查暂存的实验最终代码冻结到 `6852734cc1968b03706bbd38f4ce4a13fad775a6`；实验之后有 17 个提交、10 个变化路径，涉及 `v4_game_lane.rs`、`v4_game_public_kernel.rs`、W142/W143/W144 测试请求及状态证据（均未自动纳入旧暂存）。
- 现有 PR #26 是**从 main 构造的最终 blob 拷贝**，并未将 `experiment/fec-network-tuning` 真实记录为合并父提交。若以普通 squash 方式直接落主线，未来 Git merge-base 不会前进到已引入的实验冻结点，造成重复冲突。
- 实验 FEC 岗位仍持续运行、`merge_ready=false`、部分高负载受容量 STOP。Linux ARM64 历史五模式/W137 等只对原精确 SOURCE 有限域资格；Windows M0 真实 WL-N0 仍有 +103B Rust/Go sequence mismatch，60s 10Mbps 双向产品 PASS **未证实**。

## 1. 合并方向与不可改变的边界

**实验分支是架构、算法及策略的 upstream authority；main 最近新增的 Windows 接线作为下游 adapter patch。** 不为了兼容旧 Windows 调用路径而倒退实验的 Go→Rust 单一 DATA RX owner、TUN ingress、M1 loan/队列、M4 kernel I/O、FEC Fixed/Auto、Game2/Game4/固定FEC、稀疏 parity deadline、Game4 0/4/20/60ms、Stop 及共享资源纪律。

1. `crates/wbd-engine/src/v4_embedded_go.rs`：以实验最终功能/结构为内容基线。仅移植仍适用的 main 功能修正（如 original feature3 10Mbps source M1 flight 容量），按实验真实 runtime feature/mode 守卫接入，不整体覆盖或回滚。
2. `crates/wbd-engine/src/v4_windows_owner.rs`、`r0/go_overlay/cmd/wbd-client/m0_native_v4_peer_windows.go`：**Windows-specific adapter**。保留 main 最近日增的原始凭据 TLS→Rust M1/M2/M3/M4、Npcap firstsend、Wintun、authenticated kind1 两向反馈、immutable ciphertext repair、1536 shadow / 2048 M1、4MiB stale carrier ACK 后认证高水位、WAL/Stop；但功能接口和调用顺序必须适配实验结构与政策。不是拿 main 整文件覆盖实验架构、不是遗漏 main 已实现的功能。
3. 全局约束不降级：原 Go TLS 唯一凭据权威；只能 Rust M3 已认证且唯一 DATA 交付 Wintun/TUN；真实 OS firstsend 才记 M2；不从 Go TCP 外观 ACK 生造收据、不伪造 Applied、不复用 AEAD PN/SEQ、不静默写错/跳过严格检查；generation/lock/Stop/driver 返回值与 WAL 原安全门全部保留。
4. 103-byte Windows Rust/Go TX sequence mismatch 是当前未修缺陷，不能把既有失败硬门当实现模板；可用实验事务/队列架构修正但必须证明 seal/控制草稿/NPF 完成原始序列的端到端守恒，不可 `sendNext=seq` 或不验证而放行。

### 外层数据修复政策同样由实验分支决定

- Normal/off：采用实验共享 opportunistic-v3（而不是从 main 复制旧 RACK/PTO/two-repair 或 main S879 原值）；模式协商、成熟有据缺口、一次原始 immutable repair 与有界共享预算，具体按**冻结源**原生 readback。
- FEC-only Fixed/Auto：外层 DATA repair **OFF**；保持 firstsend/真实 authenticated M2 质量、FEC parity 和控制，不得以关闭 entire receipt 伪造 OFF。
- Game2/Game4：按实验最终公开 outer policy/OFF 合同运行；无 Game Auto。Game fixed6 与错峰等真实实现仍由实验 upstream 维护。若某模式未接线须 `NOT_RUN/UNSUPPORTED`，不得凭 main default ON 或绕过 readback 自动启用。
- 每个实际会话的 CLI/Go/Rust/native 两端 readback、修复尝试、真实 kernel accepted、shadow live、parity/数据首发都要一一核对；冻结于 SOURCE 的策略和历史报告不能被后续改标签而重解释。

## 2. 七项旧冲突的**新**处理原则

| 路径 | 新的合并处理 |
|---|---|
| `.github/workflows/m0-wl-public-normal-full.yml` | 保留 main 的**真实同 SOURCE** Windows→Linux WL-N0/IFB/tc 60s/Stop 硬门；实验功能 Actions 另外按原运行合同并入，旧烟测不得替代 WL-N0。 |
| `.governance/workstreams/M0/cursor.json` | main 当前 M0 职责唯一权威，保持其主动 cursor；实验陈旧 cursor 不落回 main。 |
| `crates/wbd-engine/src/v4_embedded_go.rs` | **实验为架构基底**，只移入主线缺失而仍必要的原始 Normal/Windows 接线兼容代码，逐函数/按 feature 合并。 |
| `crates/wbd-engine/src/v4_windows_owner.rs` | **以实验新架构接口为约束重组 Windows adapter**，功能上补齐 main 双向反向 M2、Rust ABI、shadow/arena、认证、Stop，勿将旧 core policy 偷带入新结构。 |
| `r0/go_overlay/assembly/manifest-plan020-m0.json` | 在完整 Go/Rust 适配后按实际最终 Go overlay SHA 重生成，每项原始受保护 blob 不变、生成 blob hash 精确匹配，Actions 验真。 |
| `r0/go_overlay/cmd/wbd-client/m0_native_v4_peer_windows.go` | **Windows Go adapter 跟实验最终 Rust ABI**，保留 main 原始产品功能，但允许重构调用；连同 `m0_native_v4_rx_window_windows.go` 的认证高水位实现一起适配。 |
| `tools/m0_wl_public_normal_e2e.py` | main 真实产品 WL-N0 硬门为权威；允许实验单模式场景单独增加，不回退短烟测/旧二进制。 |

旧实验树中的主线过期历史删除/工作流更名须逐路径核对，不能因“实验优先”破坏 GitHub 治理权限、历史原始 FAIL 或关键 Windows 硬门；但也不能因 main 存在过期文件，就让旧算法/配置作为默认运行路径复活。**不设置通配 `.gitattributes merge=ours`、不自动静默偏袒任一边。**

## 3. 本次必须是真实双亲合并，不是复制 740 个文件的假合并

1. 选两个不可变基点 `M=<fresh main SHA>`、`E=<selected experiment qualified freeze SHA>`，记录对比结果、在途实验 action、仍 OPEN 的能力范围。实验持续开发不被阻塞；只从冻结 SHA 集成，不能跟随浮动 HEAD 反复重做。
2. 在**隔离的正式 integration 分支**上，先用实验 E 的 core/runtime/policy 文件与完整所需依赖组成目标树，再按 Windows adapter patch 将 main M 的新增产品能力映射到实验 ABI；主线治理/真实 WL-N0 hard gate 另按 owner 保留。不能以 PR #26 现有 copied-blobs tree 宣称编译合格。
3. 精确 source 的原生 Linux（至少五模式所涉新版功能与 Stop）和 Windows Go/Rust build/ABI/transaction/real 2-OS WL-N0 逐层验证；+103B 原失败仍存在则阻止产品完成。仅 Actions；成功只提升实际跑过的功能范围，保留未跑/失败。
4. 通过静态/功能门、准备晋级 main 时，构造**真实合并提交**，至少包含双亲 `[M,E]`，tree 必须是完成适配且测试过的实际源码（用独立预集成验证时，最终 hash 若不同要重新作资格确认）。使用正常 merge commit 保留 ancestry，不用 squash/rebase 或 copy-blob 提交取代实验 ancestry。不要向其他 agent 正写的 main 强推；main 若前进，重新审查 main-only 增量并以 CAS/正常 PR 合并。
5. 晋级后核验 Git ancestry：`E` 是 main 的祖先、合并树与 Actions source 对应，且 main 的 registry/cursor 合规。若 GitHub squash 使 `E` 不再可达，不能报持续合并准备就绪。

## 4. 实验后续开发的增量接纳（避免下一次再解一次七个冲突）

- 以后每次在 **main 中上一已接纳实验 SHA E_n** 与新的选定实验 freeze `E_(n+1)` 之间做 `git merge --no-ff E_(n+1)`（在隔离集成分支进行）；Git 已有正确 merge-base，只带本批**新的**实验增量。之前 Windows adapter 仍保留在主线，通常无需重移植全部功能。
- Git 冲突只有三类：**实验架构升级影响 Windows API** → 改 Windows adapter（最好将平台 shim 独立模块）；**实验策略演进** → 按实验新策略修改 mode/readback；**治理/Windows 测试合同** → 以 main 最新为准。核心算法文件非必要不长期叠 main-only 修改，避免每轮在 `v4_embedded_go.rs` 反复冲突。若 Windows 真需要共享接口，只增最小无副作用 hook，优先争取实验 upstream 接收这个平台中性接口。
- 每轮只允许上一批之后的新 source-locked tests/ABI/gate 再次运行；已验证旧 SOURCE 证据是对照，不继承为合并 SOURCE 的 PASS。高负载遵守实验当前 `capacity_stop`，不替独立 FEC worker 改 status/dispatch。
- 平台 adapter 维护紧凑回归：模式->native outer-policy readback；Windows v6/v7 exact ABI；auth+PN+SEQ transaction；真实 Npcap firstsend 与 kind1；Rx 4MiB ACK gap；Stop/abandon; Linux TUN unique DATA owner; Linux/Windows native build。PR 备注记录 M/E/merge-tree SOURCE、Windows patch 涉及文件、当前红灯/未测。
- 自动化应做 **变更侦测、ABI/build 与源锁定校验**，不得定时自动合 main，也不得“实验优先”全文件强覆盖。一轮只要 experiment 又有新提交，标记 `upstream_new_since_freeze` 并下一轮接续；不因此撤销本轮已经完成的独立 Actions 证明。

## 5. 当前执行约束

- 旧 PR #26 是大规模文件清单与冲突诊断载体，应继续 DRAFT；下一步正式代码集成新开**有真实 experiment parent 的集成候选**，通过后替代旧 PR 的晋级路径，避免 reviewer 点击 copied snapshot merge。
- 实验分支持续更新的 W143/W144 Game RX P2 测试/状态尚在发展，不能因为最新动作 workflow SUCCESS 就把未读原生验收全数宣称通过；等明确 freeze / scope 后按增量吸收。不得向实验分支写代码或干涉其运行中请求。
- M0 main H274 和用户允许的独立实验工作均保持现状。Windows WL-N0 的源锁定失败、N1/N5 未跑、Stop 与安全原证据必须持续可见。本文件是**决策与重复集成程序**，不是已经执行两亲 merge、修复 ABI 或取得 Windows 产品资格。
