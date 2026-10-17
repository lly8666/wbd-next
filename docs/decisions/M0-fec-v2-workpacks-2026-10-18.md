# PLAN-006：FEC v2 开工、并行边界与固定提示词

用户2026-10-18明确允许新Rust数据面不与旧Go互通，要求科学重设FEC/档位，并兼顾延迟、CPU和跨平台。本次交付设计与任务提案，不修改活动worker cursor/assigned_task，不代替正在工作的M0抢写主线。**本页进入main后，M0按实时状态一次登记以下完整包；下面的提示词不绕过registry权限。**

权威方案：[FEC_V2_BALANCED](../architecture/FEC_V2_BALANCED.md)，测试：[FEC_V2_TEST_PLAN](../architecture/FEC_V2_TEST_PLAN.md)。旧07中矩阵/20源/56B/32ms/旧档位兼容要求被本设计覆盖；必要正确性和原未通过门不变。旧日志和冻结M3-016不是错误历史，不覆写成V2资格。

## 1. 安全切换和先后顺序

1. **先给M0本页提示词**。它恢复当前未记完的集成/Actions事实，收尾一个安全批次，合入规划，固定当前基线。不能为新方案杀掉未归还lease或重开024调优；也不要求先完成整套旧FEC生产集成才允许V2。
2. M0一次冻结最小公共接口/能力位/kind/FrameBudget/快照有效性及构建测试入口，确认谁独占正在改的文件，登记M3/M1/M4新工作包。允许独立部分并行编码，不能拿移动worker HEAD拼组合。已有原包完成收据保留。
3. **M0确认登记后，给M3、M1、M4提示词，三者可并行**。包内实现/测试/修复/留痕自主，普通提交和局部PASS不需等M0合入；真实共享阻塞才升级。
4. M0在协议组件和owner接口完成时首次集中接线，随后接控制/平台，不等所有功能都做完才第一次运行。必需产品/新协议hard gate通过后再开真实弱网性能，最终新SOURCE统一资格。
5. **M2默认不用开新任务**。原repair组件继续复用；若缺首次发送/成熟反馈/删失样本统计，M0明确最小只读快照补丁才激活M2，不为自动FEC重写RACK、扩大重传预算或新增可靠控制流。

## 2. 完整包与边界

| 工位 | 建议工作包名（登记时使用唯一实际task_id） | 独占交付与done_when |
|---|---|---|
| M0 | FEC2-CONTRACT-INTEGRATION | 用户授权落章程/方案；版本能力与kind、typed接口、参数目录归属、质量统计有效性、shared CI/依赖；真实Go/Rust组合与全源证据。保持原023、产品未验项，不重复旧016全矩阵 |
| M3 | FEC2-CODEC-NATIVE | crates/wbd-codec内新矩阵/source+repair wire/partial/缺源恢复、表缓存/encode_into、scalar/ISA-L正确性、功能反例/同机组件成本；不写Go自动策略、不自建线程/计时器 |
| M1 | FEC2-OWNER-SCHEDULING | runtime/memory内3class、期限、资源、公平parity、Game共享/慢lane隔离、统计histogram、late/compact/Stop与loan；不重定义wire、auto选档或M2预算 |
| M4 | FEC2-POLICY-PLATFORMS | 复用Go唯一控制点实现7档/normal-aggressive/per-direction auto、配置CLI/GUI/生效回执、Windows/ARM64构建加载与包配套；不再写第二套Rust controller或自造传输 |

M0登记时明确`native/isal-safe/build.rs`的单一写入者（建议M4负责目标构建，M0授予这一个精确路径）；shared FFI签名先冻结，根Cargo/lock/workflows仍M0。若M4要修改真实Go配置/UI适配来源，M0先定位现有构建实际使用的源码/overlay，授予精确路径，不在一个未使用的示例里实现后称产品支持。不放宽全仓权限，不覆盖另一人的文件。

最小公共契约：scheme enum/capability；`FecSource/Repair`类型；borrowed input+owned output的encode_into；source-first的ParityJob/期限/取消结果；实际k/r_sent与原因计数；质量snapshot的VALID/UNKNOWN/CENSORED/CAPACITY字段；按revision在新block生效的Tx policy。字段一处定义，文档不另造C ABI副本。数据面不得每包跨Go/Rust边界。

## 3. M0 开工提示词（先发送）

你继续wbd-next的M0。先刷新main registry与cursor、逐提交恢复遗漏的Actions/交接；当前R0-023集成按安全批次收尾，已完成024不重调。用户已明确Rust新数据协议不需兼容旧Go，请合入并执行docs/architecture/FEC_V2_BALANCED.md、FEC_V2_TEST_PLAN.md及本决策。保留M3-016/Normal-off精确基线和所有OPEN，不把旧组件PASS当新资格。

一次冻结FEC2能力/kind、MTU、codec/owner/policy接口、质量统计有效性及现有Actions入口；按实时单一写入者登记M3 codec、M1 owner、M4 Go自动策略/配置/跨平台三个完整包，必要时给M4精确native构建文件权限。M2只在确有最小统计缺口时派补丁。随后继续真实组合接线，不为普通S/H或局部绿灯中断。新协议不再要求旧Go字节相等；也不为比较新建旧生产兼容栈。全部验证在Actions，功能合批、性能一Action一场景、旧新同job顺序AB/BA、编译产物复用，容量不足停止加压。每包达到done_when即收口；最终记录配置/UI/有效后端、实际k/r、CPU/内存/wire、missing/p99与NOT_RUN，继续原产品门。

## 4. M3 开工提示词（M0登记后，与M1/M4并行）

你继续wbd-next的M3。刷新main registry和自己的cursor，先恢复遗漏；保留已完成016原证据，不再补无意义旧兼容测试。确认M0已登记FEC2包后，按FEC_V2_BALANCED第2–6/9节及专项测试实现单一rs16内核：k1..16、规范Cauchy/首行XOR与k1重复码、source10B/repair12B+受保护长度、partial/e维恢复、表缓存/缓冲复用/直接输出。原包不等组，大小端/dirty尾/迟到/epoch/所有权与MTU硬门保留。复用现有ISA-L，不开展RLC/喷泉码选型，不修改其他工位或自行创建线程。

在自己的权限内连续实现、Actions功能/精确SOURCE跨后端及同机组件成本、修复和留痕。Linux x64、ARM64、Windows分别证明实际后端；缺native资格明确标记。旧Go向量仅属于V1，V2以新独立数学oracle/golden验。完整包完成才冻结交付M0，遇共享接口阻塞记录最小缺口并继续独立部分；勿把26–45倍组件加速说成整机收益。

## 5. M1 开工提示词（M0登记后，与M3/M4并行）

你继续wbd-next的M1。先核main分配与worker cursor，保留已完成Game共享包。FEC2分配生效后，按FEC_V2_BALANCED第2/4/5/8节实现3class、最多16源、Normal 2–8ms/Game 1–4ms的绝对关闭期限、source即时服务、有界且不饥饿的parity/compact、实际k/r和容量快照。T按冻结RTT快照只影响新block；Game只编码一次、各lane独立加密，慢lane不拖首到。首发parity不占10%外层repair额度，但纳入真实容量账本；过期辅助作业释放、不扩队列。

只改已登记runtime/memory/tests，沿用现有owner/arena，别造第二套算法、auto controller或全局锁。先合批功能反例，成本测量一Action一场景，原包注入/首次交付/p99和missing一起报告；内存有界含未归还loan。包内自主完成测试修复S/H，整包才交M0，保留未接线和物理NOT_RUN。

## 6. M4 开工提示词（M0登记后，与M3/M1并行）

你继续wbd-next的M4。先刷新main分配与cursor，恢复事实。FEC2分配生效后按FEC_V2_BALANCED第3/7/9/10节，在现有Go唯一控制点实现固定7档、Normal双向独立auto/激进上一档、实际partial加权模型、有限升降/未知反馈/host容量处理；Game拒绝auto，fixed/off不启自动探针，控制消息不刷新业务idle。报告不能把最终receipt当真实首发loss；观测不可判就UNKNOWN，不把缺样本/整组消失当零。

接到实际配置/CLI/GUI/唯一参数目录和applied revision，server多client隔离；复用原质量合并/抑制，不新造固定周期大包。按M0授予的精确文件完成ISA-L ARM64 NEON/Windows构建与配套程序加载，跨编译不能冒充native。纯控制回放合批，真实auto波形/新旧成本按专项一Action一场景同job顺序比较。整包交精确SOURCE、配置真实生效证据和未验边界，不重写TLS/GUI框架/安装器。

## 7. 不钻牛角尖的退出规则

允许校正工程初值，但先给理论/实际观测，明确改前改后与影响；不能永远调参数。两次同因失败先定位最小原因，容量不够停止更重样本。不得为“全部0loss”放大T或资源；不得为省带宽延迟原包；不得把fallback或少发修复计为CPU优化。旧基线对照不需要永久产品兼容，过渡代码删除条件随组合交付一起写明。

全部结果用原devlog/evidence/cursor留痕，任务意外中断下轮先补记录。本文是长期可复用提示词，实际阶段/授权始终读main，不能半年后照本文重新开已完成的FEC2。
