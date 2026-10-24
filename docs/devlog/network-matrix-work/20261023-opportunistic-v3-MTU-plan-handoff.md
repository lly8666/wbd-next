# 2026-10-23 机会式重传 v3 / MTU / 真实性能计划交付

用户直接授权：把补充设计推给现有测试岗位继续开发测试；此次是方案、交接和矛盾清理，不代替该岗位改产品或dispatch。起点远端 `experiment/network-matrix-tuning@a470dd08`，在独立干净worktree编写，保留其b179fd0e M1源TUN-drop修复和完整旧证据。

## 已核事实

- 最新status的run39967951884：新版10Mbps/单程200ms/0损内层TCP及源TUN drop=0，但有387次outer repair；这里沿用该工位已留证据，不声称本次重新下载原artifact。
- 全局quota的首发逐记录advance存在重复维护；实际发送全局锁已按批次拿，不谎称每包加锁。receipt timer已有有界处理，不能借优化再造整个计时系统。
- pinned旧Go的DefaultMSS1360解释1500外层少用100B；Go自动预算初始仍受默认MSS钳制，publicRecordWireLimit有1180/1280遗留helper。Rust path_budget仍有旧FEC56接口，需要真实调用链与FEC2 source10/repair14统一，不仅修改TUN。

## 此次交付

新增 `docs/decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md`，明确新策略、比例分母、缺口成熟处理、删除持续DATA RACK/PTO、共享候选/内存/工作量、动态MTU/MSS、CPU基准、UDP无丢包下限、TCP500净业务/窗口和线路预算、混跑无跨业务HOL、有限Actions工作包。计算摘要为 `docs/evidence/network-matrix-work/V3-opportunistic-plan-model-20261023.json`，MODEL_ONLY，非运行测试。

同步当前计划、永久说明/提示词、根章程、恢复/成本/测试/MTU文档、网络矩阵/夹具/容量/跨平台入口和既有status。旧一次快速修复决策标历史，旧结果不改PASS/FAIL，废止的低损恢复目标不得被旧判定器重新引入。保留与本任务无关的FEC/Windows/80s OPEN和章程要求。

新测试默认约1/2候选、9%首发信用目标/10%硬帽；标准F/C=0.8/1.1时repair/C约6.545%。0损近零修复；UDP剩余损失可比线路更低。TCP500应用、RTT400ms需要25MB flight，不能拿500M线路或小窗口检验净500M。MTU无其他限制时1500/off TUN应1429，Fixed/Auto1415，真实peer限制必须继续遵守。

## 核验和未做

本轮仅检查文档差异、链接目标/JSON结构并复算公式；未运行产品测试、未dispatch、未改产品/夹具代码或历史运行request。v3产品/readback/模型工具/判定器均IMPLEMENTATION_PENDING，Actions NOT_RUN。执行agent在现有分支按V3-A/B/C/D开发、构建一次复用产物，性能单Action单场景、同VM顺序A/B。FEC独立岗位不接管，main不修改。

推送采用正常fast-forward；若远端前进，先吸收增量、保留对方结果和现有status，再合并本次新计划授权，禁止force push。
