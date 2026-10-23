# 长期运行路径重构方案 v1

这是长期设计入口，不是当前进度快照。实现和资格分别读取 main 的 project、registry 及角色分支 cursor/evidence；不得从早期方案推断“尚未开始”或“已完成产品”。2026-10-14 用户明确的同机顺序 A/B 要求覆盖旧版“每 run 禁止 multi-leg”约定。

## 结论

采用 **原 Go 控制层 + 同进程 Rust 数据引擎**。建连、借站 TLS、认证、地址分配、配置/GUI、系统安装和网络管理沿用原方案；长期逐包执行的编解码、FEC、独立 AEAD、外层恢复、队列/定时器、TUN/raw 收发迁入 Rust。先减少重复工作和调度成本，再谈换语言的收益。不会重新实现完整 TLS、完整 TCP 栈或另一套管理平台。

Normal 是一条 lane 的同一引擎。Game 在一个逻辑方向只做一次 LINK/FEC，多个 lane 各自加密和发包；收到任意 lane 的有效 shard 都进入共同恢复状态。各 lane 的序号、密钥、nonce、TCP 外观保持独立。固定 off 走短路径，不创建 FEC 编码状态。自动档继续由Go唯一冷控制点决定，2026-10-18用户授权按[FEC v2](FEC_V2_BALANCED.md)重设选档规则，不并存两套控制器；历史未关闭项保留。

2026-10-23用户改为外层恢复最多一次、只重发原密文；真实送达、停止重传、外观 ACK 是三个概念。新包不受修复缓存大小或缺口门控。大流量修复约束在新发外层数据的10%以内；稀疏免比例但仍只有一次机会。容量按目标极限PPS×保留时间加余量设固定上限，payload按需使用、及时回收，共享内存预算；不持续动态扩缩ring。新规则和验收以[一次修复决策](../decisions/NETWORK-ONE-REPAIR-20261023.md)为准，产品实施进度仍读最新证据。

## 只按当前任务读取

实施入口是 **[模块施工说明 v2](modules/README.md)**：逐模块的结构、接口、执行顺序和反例门已经细化。该目录对receipt、桥接、KDF/admission、内存与解码的明确修订优先于v1总览；不必一次读完所有模块。

M0当前调优入口：[热路径成本修复与同Actions对比](../decisions/M0-hotpath-cost-first-2026-10-16.md)。按registry执行，同时依GOVERNANCE第3节一次分配其他模块完整工作包、阶段集中集成；不再要求024结束后才能启动独立模块。该决策的MTU预算、方向所有权、批量与验收边界保留，不重置阶段/硬门。

| 文档 | 解决的问题 |
|---|---|
| [FEC_V2_BALANCED.md](FEC_V2_BALANCED.md) / [专项测试](FEC_V2_TEST_PLAN.md) | 2026-10-18新授权：无旧Go数据互通要求，短块/新头/固定与自动档/跨平台；覆盖旧FEC格式和参数约束。工位开工见[工作包与提示词](../decisions/M0-fec-v2-workpacks-2026-10-18.md) |
| [HOT_PATH.md](HOT_PATH.md) | 模块、所有权、线程、跨语言边界、Normal/Game、FEC/加密选择 |
| [RECOVERY.md](RECOVERY.md) | 快速恢复、反馈、放弃、稀疏例外、时间/缓存计算 |
| [COST_MODEL.md](COST_MODEL.md) | 数学模型、具体数值、CPU/延迟指标、哪些不是承诺 |
| [MIGRATION.md](MIGRATION.md) | 旧模块复用、分阶段任务、并行界面、遗留问题 |
| [TEST_PLAN.md](TEST_PLAN.md) | 编译复用、同 job A/B、覆盖矩阵、容量停止规则 |
| [SOURCES_AND_DECISIONS.md](SOURCES_AND_DECISIONS.md) | 原始聊天与源码依据、开源选型、否决理由 |

入口文档不是每天追加的日志。当前进度只在角色 cursor；事实日志与证据仍使用既有 devlog/evidence。模型输出进入 Actions artifact；不把理论输出称为产品测试通过。

## 开工边界

任务分配与角色是否 active 以 main registry 为准，进度以登记分支 cursor 为准；已有共享类型、构建入口和组件证据不重复初始化。固定提示词不自行授予写入权限。接口冻结表示明确一次当前版本，不表示永远不能用证据改进。原版未收尾的 Windows 工作继续原仓库，按迁移表后来移入。

本方案的数值分为：用户硬要求、可核验公式、初始工程参数、测量后再定的目标。Agent 发现不合理指标，应提交计算/证据和替代允许带；不得偷偷改硬门，也不要为了守住错误数字反复做负向优化。
