# PLAN-008：产品接线解堵与局部优化并行

2026-10-19用户要求检查并解决集成堵点、安排此前架构优化。核验main `57fa576192ec39062623107f74c9b9bf3e3a94c3`；本页是下一工作包决策，不是产品PASS。既有registry是权限唯一来源；M0合入后一次登记下列包，不由本文自动授予worker写共享源码的权限。证据见[本次核验](../evidence/M0/PLAN-008-integration-unblock.json)。

## 已查明的问题

- M0 H167仍partial，SOURCE `708ecd311770c469fca7a155435cd10cab47db47` 的Action `39176419445` 14/14 PASS，但测试专用Go/Rust接线不等于可运行产品。真实off切换、成熟观测、配置/UI、生产入口仍有缺口；保留FEC2默认OFF与旧D10/p99/物理未验项。
- main没有完整旧GUI/CLI目录是源码装配问题，不是缺少授权或源码不可获得。`r0/source-lock.json`已固定旧源 `a7a82db31fe736ffedee330795a3234d358f1984`，现有Actions已检出并应用overlay。MIGRATION本来就要求复用冷层、GUI、配置和建连；本轮明确授权在wbd-next内实现这项复用，不需再次请求“legacy-product integration”许可。旧仓库主线写入、物理部署不在此补丁范围。
- M1 HEAD `c80ff6a52ee58860f7c108307fe25d74438703e2`的旧Governance `39086314217`确实FAIL（继承检查器历史边界）；中央 `39095544653` 的M1 job `117581114004`已经对同一SOURCE给出ROLE_SCOPE_PASS，工件已重新下载验hash。该run总体FAIL来自独立M4 job，不能误判M1失败，也不能抹掉历史红灯。M1补一次恢复记录即可，不重跑130项native或继续复制检查器。
- M3旧cursor仍写待审计，但main已有`M0-M3-017-scoped-acceptance-unified-G2-2026-10-18.json`。先消费已接受的冻结组件；不要因旧cursor继续等待或刷400k ISA-L。
- M0固定提示词把实际配置/UI都写成M0亲自修改，M4停在纯策略组件，造成串行瓶颈。M0保留共享接口和最终集成权，产品适配可一次授权M4独占。

## 1. 一次登记，四个完整包

M0先核当前HEAD和未结束run，保留当前已测源，再在一个分配提交里固定接口、文件所有者及证据入口。registry的assigned_task设当前完整包，goal明确引用本文件及该工位章节，done_when给验收摘要；发布任务不改长期提示词，不代写worker cursor。工位保留原branch/epoch，不为普通接班重置；确需权限修订按现有规则记录。当前014/017等组件事实保留，新任务ID由M0唯一登记。

| 工位 | 本轮完整包 | 边界与完成条件 |
|---|---|---|
| M0 | 实际Rust运行时与产品组合 | Rust admission/owner、唯一ABI/types、真实反向kind1、off转换和applied ACK、最终构建/组合CI；消费M2/M4接口，先做一个真正可运行的Normal切片，不继续按单包增加probe |
| M4 | 旧冷层产品装配与配置/UI | 固定旧源+本仓库overlay构建真实`cmd/wbd-client`、`cmd/wbd-server`及原Windows GUI；接原参数目录/持久化/CLI/请求与真实applied状态、加载错误与Stop；不改Rust owner、协议和自动算法 |
| M2 | 成熟回执/质量统计契约 | 在wbd-recovery内用真实first-send完成与已认证反向receipt计算有界成熟观察；固定窗口/范围/分母/unknown/censored，供现有Go controller消费；不建第二控制器，不改两次重传和预算，不先优化RACK索引 |
| M1 | Game去重与查找局部优化 | 保持Game共享、接口、ID/epoch/late语义，用环形/分页代次位图代替逐包rotate_left；有界索引代替open线性查找；功能等价、资源上限及同机成本成立即可交付。不动Arc所有权/FEC期限 |
| M3 | FEC2恢复工作区与表缓存优化 | 保持wire、矩阵、档位、e维恢复和公开契约；避免缓存命中仍深拷贝逆矩阵，复用补齐输入/输出工作区，缓存适用的最终解码表并计内存；不重选算法、不改变恢复结果或靠少发修复省CPU |

M1/M3不等待产品完整集成才开发，M0也不等待其优化才把已冻结正确版本接通。优化每项独立SOURCE，组合时一次合一项，保留可回退基线；组件PASS不自动提升整链路资格。

### 单一写入者

- M0继续独占`crates/wbd-engine/src/v4_*`、组合入口、types/ABI、`r0/go_overlay/internal/realityfront/`的可信认证/控制后端、shared workflows/root依赖，以及`r0/go_overlay/internal/runtimeentry/r0_admission_mode.go`的能力门。
- M4获批的具体overlay路径可包含`r0/go_overlay/internal/configfile/`、`r0/go_overlay/cmd/wbd-client/`、`r0/go_overlay/cmd/wbd-server/`、`r0/go_overlay/windows/gui/`、`r0/go_overlay/docs/PARAMETERS.json`与`.md`、所需构建脚本；真实runtimeentry适配先选新的独立文件，M0登记精确路径后归M4。不要授予整个realityfront/runtimeentry与M0同时写。M4交付构建装配脚本，M0只接薄CI调用。
- M2保留wbd-recovery路径；若公共snapshot结构须变，M0一次定义，M2不能另造同名事实。M1/M3沿原模块权限，shared native依赖不再重复改。
- M0登记一次权限后，worker包内实现/Actions/修复/留痕自主；普通S/H和局部PASS不要求M0逐次合并。必要共享接口缺口一次汇总，独立工作继续。

## 2. 产品源码可复现装配，停止把缺目录当授权阻塞

沿用固定旧SOURCE的Actions检出，而非复制整个旧仓库或重写GUI。已确认旧源有`cmd/wbd-client/main_{linux,windows}.go`、`cmd/wbd-server/main_linux.go`、`internal/configfile/config.go`、`windows/gui/{MainForm,Portable,GuiTests}.cs`、`windows/gui/fields.json`、`docs/PARAMETERS.json`和`scripts/build_windows_gui.ps1`。

本仓库保存最小适配文件/patch及一份装配清单：旧SOURCE、本仓库SOURCE、每个replace目标的原blob/hash、create目标必须不存在、结果hash、工具链/target/features。只在Actions临时checkout应用；拒绝浮动旧分支、模糊patch或静默覆盖。创建文件继续可用现有overlay机制，修改原文件须显式replace记录。清单是构建来源，不是第二份功能/进度目录。

旧模块路径可以保持以便复用冷层；这不要求兼容旧Go数据wire或运行旧dataplane。参数唯一目录是装配后的原PARAMETERS，新旧名称迁移可见；不另外造一个只供测试的CLI/GUI。产品清单同时记录旧源与Rust源，不能只有一个容易误导的SOURCE。

产品桥接应从现有已验证实现收口为明确的实验引擎入口，避免永远只有`m0_*probe`符号可工作。默认发布入口继续保守；实验包显式选新引擎，并以真实受保护会话/owner能力启用。不能靠用户传`ready=true`或删除`ErrR0V4DataPlaneUnavailable`放行空实现，也不能静默退回旧数据面。

**分能力接通**：Normal/off可运行后做fixed，再接auto，再Game。尚未接通的mode明确拒绝；不必等所有Game/GUI/物理资格齐全才允许在Actions运行真实Normal实验程序。实际构建/加载、配置读写、启动业务路径和Stop都要验证，不把`go test`专用入口冒充产品入口。物理测试另列NOT_RUN。

## 3. M0与M2/M4一次冻结的接口

1. 区分`requested/pending/applied/rejected`；只有Rust真正应用新block政策才ACK，GUI显示请求不等于生效。off是mode转换，不是非法profile或静默r=0：停止新FEC编码，旧组有界drain，保留已承诺MTU预算、代次、密文和迟到处理；真实完成后反馈。M0拥有Rust实现，M4只消费回执。
2. 质量统计来自实际first-send完成、观察覆盖及成熟缺口；Uncertain/未发/控制PN不得算成功或线路丢包。不能用RX收到几包倒推发送分母，不能把同PN重传/FEC恢复重复计数。M2交付纯事件契约和跨许多block的回放；M0在真正原始sender+已认证receiver上接线。无法判定仍UNKNOWN；既有Go控制器只有一个，不由M2自建周期探针。
3. client/方向/epoch/revision绑定，Stop后拒绝旧事件，controller先停并join再拆owner。保持2s冷决策、idle不被control续命；不逐包调用Go，不增加固定逐包协议字段。

## 4. 测试与退出：不再把单包接线拆成无限阶梯

**工位测试入口补充**：[PLAN-009](M0-worker-selftest-entry-2026-10-19.md)解决M1/M3能push功能测试却仍等待M0代跑成本的缺口。M0一次补可消费精确源码/产物的公共入口，工位自行触发、核验与修复；保留当前任务/权限，不改长期提示词。入口实现/可用证据必须另行登记，方案合并不等于已可使用。

- **这一轮不重跑原14-job绿灯来证明文档或分配正确。** 功能可批量并行；性能必须移到独立Action：一场景/配置/seed、一个测量job、新旧同VM顺序AB/BA。已有混合扫描保存原范围，不倒写成合规性能A/B。
- 编译一次固定产物，供所有消费任务校验manifest/hash后复用。范围变化只重编相应目标，不每个断言重编Rust。Win/ARM原生codec通过不等于产品loader/驱动通过。
- M4：原配置/CLI/GUI同一参数往返、两client/两方向、保存重启、无效模式/缺库/错target、真实pending/applied/rejected、Stop。Windows loader+GUI native与Linux产品真实入口分别标范围；没有驱动时不冒充物理通过。
- M2：有覆盖/无覆盖、整块消失、乱序/重复/回执丢失、实际未发/uncertain、修复后到达、跨epoch/Stop和分母守恒，一批纯事件断言；M0再用真实双端回程验证。不得由夹具把注入真值直接喂给自动控制器。
- M1：窗口填满后持续前进、回绕/巨大跳跃、旧ID/重复、多lane首到、pressure/Stop；以操作计数证明确实不逐包搬整窗。一次Game共享接收代表性同机AB测成本，接口不变。
- M3：现有向量/dirty尾/长度/缺源集合/缓存淘汰等价；同机native旧新k16/r16/1200B/e4代表成本，**不是再比较scalar/ISA-L证明已有加速**；同时报分配/复制/缓存与内存上限，mixed partial功能补充即可。
- M0第一组合批次用真实构建的client/server、独立进程和netns：Normal/off→fixed→auto、持续大小包/并发TCP UDP与合法超MTU、真实反向回执、Stop/rotation/新包不等缺口。按完整能力一次成批，不重新证明source1/repair1再source2。使用既有10Mbps/方向与Game3Mbps锚点；网络损伤/大包理论不足、容量不足按原允许带解释。
- 组合功能成立后，正常容量同源lossless与5205分开Action，p99/首次交付/missing/CPU与真实wire账齐全。宿主CPU型号/核数/配额/PSI/注入器/drop记录，容量不足停止加压。旧D10/240s/p99/80s风险保留原范围；没跑不关门。

## 5. 后置项目与停止条件

本轮先交付可运行纵向切片和两个无协议变化的局部优化。M2全窗口重索引优化待真实回执语义冻结后独立做；Arc管理对象池化涉及Stop/loan，放到接口稳定以后；小包优先随后单独调度包，不借本轮引入新队列/新线协议。保留原始包长/业务分类可传递性即可，不预做复杂QoS。

接线可交付且必要功能通过后冻结基线，worker包达到done_when即收口；少量CPU差异落入噪声则INCONCLUSIVE，不无限刷seed，不因新优化延期基本产品接通。M0最终负责组合验收，不必亲写每个冷层适配文件。

## 6. 本轮任务摘要（供registry引用，不是长期启动提示词）

用户长期使用`docs/prompts/M0.md`至`M4.md`。以下只属于PLAN-008当前工作包，M0登记后工位通过registry.goal自行定位；不要求用户每轮复制这些任务细节，也不将其写入固定提示词。

**先M0**：刷新main/cursor，执行本决策。已有用户授权覆盖固定旧Go冷层/GUI/配置装配，不再请求单独legacy-product许可；保留实际能力门。核M1同SOURCE中央PASS，消费M3现有接受证据；一次登记M4产品适配、M2成熟观测、M1 Game去重、M3恢复工作区四包和精确文件所有者。你继续Rust真实入口/off ACK/回程与组合，不重跑无变化14-job，不改worker独占文件。每包独立Actions留痕，最终明确产品仍缺哪些门。

**登记后给M4**：按本决策第2/3/4节做真实旧冷层产品装配、配置/CLI/GUI/加载和有效回执；只改登记overlay/适配文件，不写Rust owner或重建控制器。先可构建/可加载，再真实配置生效，完整包自行Actions测试修复。

**登记后给M2**：按第3/4节交付真实first-send与成熟覆盖/缺失的有界统计契约和回放，未知/删失明确。M0接原认证回程；你不重写RACK、不发额外探针、不把RX计数假造分母。

**登记后给M1**：先用本次证据补旧blocked状态，保留旧FAIL；然后仅优化Game去重窗口/块查找，不动FEC时间或Arc回收。功能合批、操作量有界、一次同机旧新代表成本，完成即交付。

**登记后给M3**：已有017资格不重刷，保持wire/矩阵/结果/接口，优化恢复工作区与最终表缓存，明确额外内存。一次native旧新AB验证分配/CPU，未改善如实记录，不重跑算法竞赛。
