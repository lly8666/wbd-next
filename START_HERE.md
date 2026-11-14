# WBD Next｜main 最小接续

**当前授权（2026-11-14）：PLAN029已启动并保持IN_PROGRESS**；PLAN028按用户限定范围收口，不重开旧矩阵，PLAN030尚未开工。先读[029接续提示](docs/prompts/M0-PLAN029.md)、[029计划§4A](docs/decisions/M0-PLAN029-CLIENT-DNS-PADDING-20261102.md)与[分流/DNS施工契约](docs/architecture/CLIENT_SPLIT_DNS_CONTRACT.md)。目前Normal真实Direct/Tunnel部分交付PASS，但P2 Direct TCP 1MiB仍约6.36s/同VM物理0.296s，性能OPEN，不能称已交付。

源码、计划、进度均在 `main`。先读本页、[AGENTS](AGENTS.md)、[PROJECT_CHARTER](PROJECT_CHARTER.md)、[M0长期提示](docs/prompts/M0.md)、[registry](.governance/registry.json)、[M0 cursor](.governance/workstreams/M0/cursor.json)；只核checkpoint后相关增量与在途Actions，补中断遗漏，不重复派发。

当前状态：M0在main继续029单写，实时SOURCE/cursor优先，先收在途结果不重复dispatch；029重点修Direct-only调度、FakeIP同步磁盘跨流HOL、实际buffer分配、Game4/正式GUI/IPv6等未验出口。旧028保留[验收专项](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)的限定结论，不作全面PASS。

**长期硬门**：[TLS建链契约](docs/architecture/TLS_HANDSHAKE_CONTRACT.md)，真实TLS前禁止私有前导，允许预共享route-key；旧WB-R1功能PASS不证明外观合格。[MTU契约](docs/architecture/MTU_CONTRACT.md)，用户外层完整IPv4 MTU默认1460B、不含L2，1500仅显式最大值，内层由Rust派生并由OS应用/读回。同NIC/IP有效MTU变化也需进入现有重认证流程；不能恢复旧“忽略MTU变化”的提示。

历史限定收口：[027 H920](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)、[027A H998](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)。保留原在线同socket收窄FAIL、ARM64旧workflow FAIL、远端ICMP未测及CPU因果未证；后续新代重认证PASS不能改写旧结论。不因历史NOT_RUN重开整套旧矩阵，也不推广旧PASS。

功能卡：[features](docs/features/README.md)；真实测试：[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)；诊断：[NETWORK_TRIAGE](docs/testing/NETWORK_TRIAGE.md)；历史：[INDEX](docs/history/INDEX.md)。
