# WBD Next｜main 最小接续

**当前授权（2026-11-07）：PLAN028功能冻结，进入集成可靠性专项验收与缺陷收口，仍为IN_PROGRESS。**不再围绕旧H号重开已经完成的开发；也不能把“功能基本接通”写成已交付。先收最新cursor在途结果，按[专项验收](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)完成已知阻断、分层回归、渐进压力与最终有限长测。M0自主选择最有效的修复/测量方式，以理论计算、实际业务和宿主容量综合判断。

源码、计划、进度均在 `main`。先读本页、[AGENTS](AGENTS.md)、[PROJECT_CHARTER](PROJECT_CHARTER.md)、[M0长期提示](docs/prompts/M0.md)、[registry](.governance/registry.json)、[M0 cursor](.governance/workstreams/M0/cursor.json)；只核checkpoint后相关增量与在途Actions，补中断遗漏，不重复派发。

当前执行：[028接续提示](docs/prompts/M0-PLAN028.md) → [028功能范围](docs/decisions/M0-PLAN028-SESSION-CONFIG-20261102.md) + [专项验收](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)。已完实现一笔带过，历史细节遇问题再查；状态/精确SOURCE以cursor及evidence为准。029/030入口在[移植总览](docs/decisions/M0-LEGACY-ROLLOUT-20261102.md)，不能因本次收尾授权自动新增功能。

**长期硬门**：[TLS建链契约](docs/architecture/TLS_HANDSHAKE_CONTRACT.md)，真实TLS前禁止私有前导，允许预共享route-key；旧WB-R1功能PASS不证明外观合格。[MTU契约](docs/architecture/MTU_CONTRACT.md)，用户外层完整IPv4 MTU默认1460B、不含L2，1500仅显式最大值，内层由Rust派生并由OS应用/读回。同NIC/IP有效MTU变化也需进入现有重认证流程；不能恢复旧“忽略MTU变化”的提示。

历史限定收口：[027 H920](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)、[027A H998](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)。保留原在线同socket收窄FAIL、ARM64旧workflow FAIL、远端ICMP未测及CPU因果未证；后续新代重认证PASS不能改写旧结论。不因历史NOT_RUN重开整套旧矩阵，也不推广旧PASS。

功能卡：[features](docs/features/README.md)；真实测试：[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)；诊断：[NETWORK_TRIAGE](docs/testing/NETWORK_TRIAGE.md)；历史：[INDEX](docs/history/INDEX.md)。
