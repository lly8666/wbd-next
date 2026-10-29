# WBD Next｜main 最小接续

**M0的产品代码、夹具、任务事实与结果只在main；不创建M0实验/预检分支。** 独立并行任务仅按另行明确授权。旧FEC工位已完工，历史分支/旧next_action不派活。

## 每次启动的八文件
本页＋`AGENTS.md`、`PROJECT_CHARTER.md`、`.governance/project.json`、`.governance/registry.json`、`docs/prompts/M0.md`、`.governance/workstreams/M0/cursor.json`、`docs/features/README.md`。任务看最新main registry.goal，进度看main cursor，资格看精确SOURCE/Actions/证据。先刷新HEAD、核checkpoint之后提交与在途结果，不按旧聊天自增epoch、不全仓扫旧devlog。

## Normal/off 既有验收基线（不是当前施工门）
Windows Rust NativeOwner **Normal/off 已基本完成接线和测试**：原Go TLS冷交接、Rust 两worker 独占真实签名Npcap/Wintun、双向UDP/TCP与owned Stop 已有 SOURCE055 功能 PASS；SOURCEa123 有 10Mbps/300ms 单程/240s N0 PASS；SOURCE7fc 有 150Mbps/300ms 单程/60s 真实首次交付性能 PASS，详见 `docs/features/entries/windows-native-transport.json` 的精确SOURCE证据。旧SOURCE下存在容量上限、波动和回滚负例，不能把历史结果伪称当前HEAD/物理全绿；但**不得把Normal/off重新接线、N0重跑或Go/Rust CPU对照作为进入Fixed/Game/Auto施工的前置条件**。相关变更只做受影响回归，优先当前 PLAN026 Fixed→Game→Auto/Health/生命周期。

## 当前施工导航（不是产品完成声明）
PLAN026 Windows Go冷TLS/OS/WAL＋Rust独占Wintun/Npcap稳态；**Fixed/Game/Auto/Health/服务器超时与休眠** 的新增细化施工、测试顺序见 [M0低成本整批契约](docs/decisions/M0-PLAN026-FEC-GAME-AUTO-HEALTH-LOW-COST-EXECUTION-20261029.md)。此前 [NativeOwner主决策](docs/decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md) 和 [阶段B技术盘点](docs/decisions/M0-PLAN026-FEC-GAME-RUST-STEADY-WIRING-RESEARCH-20261029.md) 按需读，不从本页猜已接线/通过。

先写全产品代码、双方调用/配置readback、用例、V2夹具、Actions与manifest，冻结同一SOURCE再集中测试：便宜编译/core→**Fixed→Game2/4→Auto最后（连同Keepalive/超时/休眠）**→必要同VM A/B。真实首次交付、低CPU/无HOL优先；每性能Action一个场景/测量job，旧新同VM，分清宿主容量和产品缺陷。

按需索引：[功能卡](docs/features/README.md)、[V2夹具](docs/testing/WL_PERF_HARNESS_V2.md)、[历史资料](docs/history/2026-10-28-M0-MAIN-HANDOFF.md)、[故障定位](docs/testing/NETWORK_TRIAGE.md)。历史证据不删，热入口不重复旧每轮日志。