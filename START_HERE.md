# WBD Next｜main 最小接续

**029B**：[方案](docs/decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md) / [提示](docs/prompts/M0-PLAN029B.md)。设计定案/产品未测；当前批次后、030前完成，进度看cursor。

**当前授权（2026-11-14）：PLAN029已启动并保持IN_PROGRESS**；PLAN028按用户限定范围收口，不重开旧矩阵，PLAN030尚未开工。先读[029接续提示](docs/prompts/M0-PLAN029.md)、[029计划§4A](docs/decisions/M0-PLAN029-CLIENT-DNS-PADDING-20261102.md)与[分流/DNS施工契约](docs/architecture/CLIENT_SPLIT_DNS_CONTRACT.md)。Normal真Direct/Tunnel业务和owned Stop已限域PASS，H1864 4MiB无pace物理32.155/Direct131.544ms，H1863 P1 CPU/GiB +7.01%仍OPEN；H1866真实Windows IPv6宿主无默认路由且应用发包NOT_RUN，产品IPv6阻断尚未合格；GUI/Game4等029仍OPEN。

源码与进度在main。启动读[AGENTS](AGENTS.md)、[章程](PROJECT_CHARTER.md)、[M0长期提示](docs/prompts/M0.md)、[registry](.governance/registry.json)和[M0 cursor](.governance/workstreams/M0/cursor.json)；收在途结果、补中断，不重复派发。

当前状态：M0在main继续029单写，实时SOURCE/cursor优先，先收在途结果不重复dispatch；Npcap移交已非阻塞，FakeIP日志已有异步写者；H1867纯Tunnel性能同VM A/B和H1868硬8资源压力原生场景在途。Game4 CN、真实GUI、IPv6应用、DNS/填充及压力剩余出口仍需完成。旧028保留[验收专项](docs/testing/PLAN028_INTEGRATION_ACCEPTANCE.md)的限定结论，不作全面PASS。

**长期硬门**：[TLS建链契约](docs/architecture/TLS_HANDSHAKE_CONTRACT.md)，真实TLS前禁止私有前导，允许预共享route-key；旧WB-R1功能PASS不证明外观合格。[MTU契约](docs/architecture/MTU_CONTRACT.md)，用户外层完整IPv4 MTU默认1460B、不含L2，1500仅显式最大值，内层由Rust派生并由OS应用/读回。同NIC/IP有效MTU变化也需进入现有重认证流程；不能恢复旧“忽略MTU变化”的提示。

历史027/027A限定收口见[H920](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)及[H998](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json)；不重开旧矩阵，不改写FAIL/NOT_RUN。

功能卡：[features](docs/features/README.md)；真实测试：[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)；诊断：[NETWORK_TRIAGE](docs/testing/NETWORK_TRIAGE.md)；历史：[INDEX](docs/history/INDEX.md)。
