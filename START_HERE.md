# WBD Next｜main 最小接续

源码、计划、进度均在 `main`。全新 agent 先读本页、[AGENTS](AGENTS.md)、[PROJECT_CHARTER](PROJECT_CHARTER.md)、[M0长期提示](docs/prompts/M0.md)、[registry](.governance/registry.json)、[M0 cursor](.governance/workstreams/M0/cursor.json)，只核上一 checkpoint 后增量与在途 Actions；不得无故重复派发。

**当前接续状态：PLAN027A 已按用户2026-11-03明确指示限定范围收口；PLAN028 已登记为 PLANNED / 等待全新 agent 启动，尚未施工。** 027 已先前限定结案（[H920](docs/evidence/M0/PLAN027-H920-SCOPED-CLOSEOUT-20261102.json)）；027A 的逐证据收口及保留失败详见 [H998](docs/evidence/M0/PLAN027A-H998-USER-ACCEPTED-SCOPED-CLOSEOUT-20261103.json) 与 [H998 devlog](docs/devlog/M0/20261103-PLAN027A-H998-USER-SCOPED-CLOSEOUT-PLAN028-HANDOFF.md)。

027A 真正已核验：同一产品SOURCE的 Windows Npcap/Wintun ↔ WSL2 Linux 11 个代表场景全部PASS，真实UDP DF0 1728/4096/65507B 至少完整重组一次且内容相等、DF1本地EMSGSIZE、64KiB TCP、真实 MSS/内层 OS MTU、Stop；ARM64 当前源 Normal1460与不对称1460/1280 PASS；H996 Normal OFF→ON 同VM性能保护和单独 Game4FEC loss0 PASS。未达到全范围技术 PASS：H995 **真实在线物理 MTU 缩窄后小流中断 FAIL**；H997 ARM64 Game4FEC两场景真实业务/FEC/Stop可见但 workflow **FAIL**（重复包计数判据）；远端用户态 ICMP3/4 NOT_MEASURED、旧/新产品 CPU 因果优化未证明。用户接受限定结案并保留上述事实，不升级全产品资格。

**下一任务**：[PLAN028 开工提示](docs/prompts/M0-PLAN028.md) → [028 会话/配置/网络切换](docs/decisions/M0-PLAN028-SESSION-CONFIG-20261102.md)。按用户稍后启动新 agent 的计划等待明确开工；028§4.1–4.2 的网络切换/MTU重新协商必须把027A真实在线缩窄失败作为已知未解决依赖，而不是已有PASS。

唯一 MTU 契约：[MTU_CONTRACT](docs/architecture/MTU_CONTRACT.md)：用户外层完整IPv4 MTU **默认1460B，不含L2**；**1500仅为显式最大值**，内层由 Rust 预算派生、OS应用/读回，只读展示。不要复制独立预算表，不把过去失败证据改成成功。

功能卡：[features](docs/features/README.md)；真原生测试：[WL V2](docs/testing/WL_PERF_HARNESS_V2.md)；诊断：[NETWORK_TRIAGE](docs/testing/NETWORK_TRIAGE.md)；历史：[INDEX](docs/history/INDEX.md)。
