# WBD Next｜main最小接续

源码、计划和进度在main。每次默认上轮可能中断，读本页、AGENTS、PROJECT_CHARTER、project/registry、M0 prompt/cursor及features入口；只核checkpoint后相关增量与在途Actions，补recovered，不重扫历史/重复派发。

当前任务：[PLAN027A统一MTU](docs/decisions/M0-PLAN027A-MTU-UNIFICATION-20261102.md)（H932 所有CLI/GUI默认外层IPv4 IP MTU改1460；最大1500仍可显式设置；真实DF/七模式/保护性能未验）；PLAN027按用户授权已[限定范围结案](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)，旧FAIL/NOT_MEASURED不改写为PASS。

现行MTU唯一规范：[MTU_CONTRACT](docs/architecture/MTU_CONTRACT.md)。不重复旧网络矩阵，执行新增实际变更时仍守真实SOURCE、OS读回、原生Stop与一Action一场景。

功能：[features](docs/features/README.md)；夹具：[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)（历史限制以实际workflow及PLAN027为准）；诊断：[NETWORK_TRIAGE](docs/testing/NETWORK_TRIAGE.md)；历史：[INDEX](docs/history/INDEX.md)。按问题再追SOURCE/devlog/evidence，不将旧PASS迁到新源码或物理机。

当前顺序：**PLAN027已限定收口→[PLAN027A](docs/decisions/M0-PLAN027A-MTU-UNIFICATION-20261102.md)→[PLAN028–030](docs/decisions/M0-LEGACY-ROLLOUT-20261102.md)**。源码 H922 首批自动触发基础 CI，具体 PASS/FAIL 以 evidence 中精确 SOURCE 为准；暂不重复手动 dispatch。
