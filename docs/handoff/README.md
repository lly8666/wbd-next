# 五工位接班总览（热索引，不是第二份任务数据库）

**2026-10-19解堵补充**：[PLAN-008](../decisions/M0-integration-unblock-2026-10-19.md)已核M0 H167和旧源实际目录；M1同HEAD中央审计已PASS，旧blocked需恢复留痕；M4可经registry分配真实产品冷层适配，M0不必亲写全部UI。以下2026-10-18表是历史快照，不覆盖更新的cursor/证据。详细来源只在[核验JSON](../evidence/M0/PLAN-008-integration-unblock.json)维护。

> 最近核验：2026-10-18，main `dde964768d594774ff8d63893cd168fe22d9e41c`。**每次接手必须先刷新远端 main 和指定工作分支**。本页数字只描述此时事实；登记/权限以 main `registry.json` 为准，进度/next_action 以角色 cursor 为准，PASS 以精确 SOURCE 的证据和 Actions 为准，设计以决策/架构为准。更改任务、role 和下一动作不在本页操作。

## 一眼看懂当前局面

| 工位 | 固定分支与当前任务 | 已核到的状态 | 下一个有价值的接口/边界 |
|---|---|---|---|
| **M0** 集成 | `main`; `R0-M0-V4-PROTECTED-OWNER-COMMIT-023` | **H145 partial/unverified**；CODE `dd2eeb0…` scoped native batch [39110293670](https://github.com/lly8666/wbd-next/actions/runs/39110293670) PASS；[H Governance 39110760761](https://github.com/lly8666/wbd-next/actions/runs/39110760761) PASS | 原 M1 调度 **真接入** Go/Rust kernel sender；M2 反向认证收据、sender shadow/预算/driver；R0-023 大 UDP Stop/MTU/150ms 修复 |
| **M1** runtime | `work/m1-r1-runtime`; `R5-M1-FEC2-OWNER-SCHEDULING-014` | **H19 blocked**（交接/central 证明待复查）；CODE `3f78a671…` scoped 130/130 native PASS；M0 已消费 scheduler native 接口 | 工位核自己的最新中央 G2/source 审计；M0 负责 live sender 对接，非 worker 另改 owner |
| **M2** recovery | `work/m2-r2-recovery`; `R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010` | **H25 ready_for_integration**；CODE `654a3c1…` 70/70 scoped PASS | M0 按已交付 typed ingress 接真正 reverse authenticated receipt、同一 FrozenRecord 和 driver prefix；M2 只对确证缺陷修复 |
| **M3** codec | `work/m3-r1-codec`; `R5-M3-FEC2-CODEC-NATIVE-017` | **H37 partial/unverified**；CODE `8cc5b06…` Linux x64 actual ISA-L/RS16 和同 VM ABBA 已有 scoped 证据；H/central 资格仍以最新 run 核 | 核工位 G2/中央结论，ARM64/Windows **完整 codec 原生**仍 NOT_RUN；M0 可使用已源锁 Linux x64 能力 |
| **M4** platform | `work/m4-r1-platform`; `R5-M4-FEC2-COLD-POLICY-PLATFORMS-014` | **H21 ready_for_integration**；CODE `7cef7e8…` 原 Go 冷策略 8/8、Linux x64/ARM64/Windows safe-wrapper 测试 scoped PASS | M0 接原 Go 参数目录/CLI/GUI 的 applied 固定/自动修订及真实 Windows loader；wrapper PASS ≠产品 Win native |

上表 **blocked、ready、partial** 都是 worker 分支交接属性；M0 合入的某项组合 PASS **不替 worker 篡改状态**。忙闲或“已经收尾”不得由某日未提交推测。

## 当前已真正打通的部分与产品差距

- **已验证的测试专用真实路径**：原 Go credential TLS bit2 私有授权 → 原 Rust owner AEAD/PN/Seq 与 M1 Arena/FrozenRecord → M3 FEC2 source/repair → M4 Linux raw kernel → 独立 Go 原始套接字捕获 → M3 认证去重、缺源恢复 → 原 TUN sink → 内核 UDP 应用收到 99B；三密码套件。M0 还独立验证 **M1 source-first/ParityJob→M3 RS16 组合**、**M2 收包侧 RxFeedback draft** 和反例，但这两块**尚未成为原实时网络 sender 的自动调度／反向收据**。详见 [M0 当前精确证据](../evidence/M0/M0-023-batched-M1-M2-FEC2-real-kernel-dd2eeb0dddbb3317279f9e59aea2e5c38305f0a7.json)。
- **严禁提前改成 PASS**：生产 FEC2/公开 Go bit2 默认 **OFF**；M1 live Fec2Owner scheduler 未上真 kernel sender；M2 上行受保护 kind1/反向 receipt 与 sender budget/repair 未打通；真实 Go applied fixed/auto CLI/GUI 与 revision 未完成；双端跨网络、全部原生目标、物理机、产品资格 **NOT_RUN**。
- **历史仍红/待核**：Normal/off 配置 150ms netem 的第3 cipher 第二 LINK fragment pending [39106157061](https://github.com/lly8666/wbd-next/actions/runs/39106157061)；R0-023 合法约65KiB UDP 跨轮次、MTU±1/Stop/loan/prefix uncertain；旧 codec 240s、D10/p99 回退。不要在新 FEC2 链路绿灯后删除它们。
- **已收口的中断**：源 `652f0ef…` 的首轮 FAIL 是 CI 选择器运行了 **3 个均通过的 Rust tests** 却期待恰好 **2**；修正为确切模块选择并在 `dd2eeb0…` [39110293670](https://github.com/lly8666/wbd-next/actions/runs/39110293670) 2/2 PASS，完整原 Go/kernel/M2 仍 PASS，H145 已登记。不要重跑旧假红当产品问题。

## 新 agent 5 步立即开工

1. `START_HERE.md` 读共用约束；main registry 看 **assigned_task/权限**；自己的工作分支 cursor 看 **checkpoint/last_tested_source/next_action**。
2. 精确比较 checkpoint→HEAD 的**每个提交**，核未确认 Action、failed receipt 和 requests；确认 CLEAN/RECOVERY_REQUIRED/BLOCKED。
3. 只读该任务直接依赖的冻结契约/模块说明；消费当前源码和证据，**不照旧提示词的日期执行**。
4. 做成组的能力实现与正反例；性能另分同一 job 配对真实测量；FEC2 默认 OFF。
5. S 记录精确 SOURCE+失败/排除项 → H cursor-only → 刷新 Governance/中央 Scope；所有证据留在原路径，旧档案由 `docs/history/INDEX.md` 导航。

**角色永久接手词**：`docs/prompts/M0.md` … `M4.md`。原角色长提示词逐字归档在 `docs/history/handoff/2026-10-18-pre-slim/`，旧 devlog/evidence/决策文件完整保留。不单独维护进度百分比或重复任务看板。
