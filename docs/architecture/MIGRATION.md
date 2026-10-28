# 迁移顺序与旧功能继承

> **新Windows优先包（2026-10-28）：** [PLAN026 Go冷控制 + Rust NativeOwner](../decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md)覆盖下方旧 Windows Go direct-TCP/Auto/keepalive热路径过渡策略。保留既有 Go TLS/OS管理和安全回滚，不保留每包Go业务泵；先 Normal/off，再 Fixed/Auto/Game/Health/换lane。旧表仍作历史复用来源和功能清单，不代表今天已实施。

产品装配和并行归属按[PLAN-008](../decisions/M0-integration-unblock-2026-10-19.md)收口：复用固定旧SOURCE的Go冷层/配置/GUI已在用户授权范围；可在本仓库保存有hash的overlay/替换清单，Actions组装真实程序。缺少完整旧目录不构成再次申请许可的理由；不修改旧仓库主线、不移植旧数据wire、不移除未实现能力门来冒充接通。

Windows运行时去PowerShell按[PLAN-010](../decisions/M0-windows-native-migration-2026-10-19.md)：保留a7a82冷层主基线，定向导入后续12文件原生恢复增量，再由M4接实际CLI/GUI网络事务；不是整体更新旧源或改写Rust OS管理。老版最新仍调用脚本、生产WFP/完整崩溃恢复尚未通过，移植与产品资格分开。M0一次登记临时包和精确新增路径，原015在安全交接点接续。

用户最新限定：按一机单网络代理实例收口，M4完成整个产品运行时去脚本工作；不要求多代理共存或极端PnP自愈。M0须实际发布M4可用的最新Windows Actions调用入口，而非只授予文件路径；正常取消/清理/恢复、参数与真实无shell仍验，已有极端失败仅保留历史，不挡本包完成。

2026-10-18用户明确**不需要新Rust与旧Go数据面互通**。[FEC v2](FEC_V2_BALANCED.md)覆盖下表旧GF矩阵、20源/六档/32ms/56B及auto旧策略必须照搬的约束；它们作为V1历史参考保留。旧控制/建连复用、用户功能可见迁移、产品硬门和未关闭问题不变。R3执行新专项而非重新刷全套Go字节相等；具体开工由[M0工作包](../decisions/M0-fec-v2-workpacks-2026-10-18.md)登记。

## 原版依据与继承规则

研究锚点：`lly8666/wobuzhidao` 的 `next/adaptive-fec-aes-tun-20261010`，SOURCE **a7a82db31fe736ffedee330795a3234d358f1984**。这是 2026-10-14 读取时的源码，不是已通过全部产品/物理门的发布版。构建基线前再次固定具体提交，不能拿移动分支名填 evidence。旧 MODULE_MAP 部分“未实现”字样已落后于源码；优先实际实现和有范围的 STATUS 证据。

| 原模块/能力 | 决定 | 新实现/交接要求 |
|---|---|---|
| bootstrap、uTLS、借站握手/证书、admission | 沿用 Go 算法 | Rust I/O 适配和一次 capability 协商；抓包核真实 TLS 建连，不重造假握手 |
| auth、账号/租约/多客户端、地址隔离 | 沿用 | 非持久客户端 IP、7天租约等配置语义照旧；不得把身份隔离删成裸 IP 信任 |
| lifecycle、rotation、idle/keepalive、黑洞恢复策略 | 沿用策略 | Go 发命令，Rust 执行/计数/到期；A→A+B→B、真实 payload activity 不能被控制流量伪造 |
| `runtimeowner/recovery.go`、外层 steady | 重构 | 旧20%预算/128KiB burst/100ms defer 不直接继承；按 RECOVERY 新10%+稀疏例外设计 |
| `datapath/game_owner.go`、`gamelane` | 重构 | 去掉准备完全部 lanes 才发的串行屏障；共享 LINK/FEC、独立密码/seq；新 envelope 有版本门 |
| `fec/fastcodec.go`、`fused_encoder.go` | 复用SIMD/缺源恢复经验，新算法/wire | FEC v2短块Cauchy、独立数学golden与跨后端等价；旧Go向量只验V1，不约束新格式 |
| `fec/size_class_encoder.go` | 有界分类/首包期限经验保留 | v2采用256/512/MTU三class、k≤16及Normal/Game短期限；partial上取整代价明确，不锁死32ms |
| `fec/block.go`、`linkdata/fec_path.go` | 生命周期重做/语义保留 | immediate systematic、3s恢复 horizon、有界 compact；auto 切档旧状态有界 drain（原最多6个） |
| `tlsrecord/record.go` | Rust/成熟库 | 31B 基础成本、独立 record、HP/AEAD 向量、修复密文不变 |
| `linkdata/datagram_fragment.go` | Rust 移植并简化到期索引 | 原20B头、无分片快路、超 MTU 兼容、坏片/超时/dup门不丢；原扫描本就有界，不虚报巨额节省 |
| `pathmtu/budget.go` | 公式/配置继承 | outerMTU/options/MSS/FEC/Game一处预算；压力资格重新测，不宣布旧MTU已全面通过 |
| TUN/raw/Npcap 的逐包 I/O | Rust | 复用设备/过滤思路，准备好即批处理；所有权/close完成回执优先 |
| `platformflow`、direct-TCP/gVisor | 首轮沿用 Go | 批量接口，单独成本账；避免本轮重写TCP栈 |
| 自动FEC controller、接收质量报告 | Go唯一控制点，按FEC v2重设决策 | Rust提供实际k/收发/恢复和有效性；两方向独立、fixed/off不误启自动；未知/容量不盲升档，保留历史未合格场景 |
| Windows GUI、配置/CLI/参数目录 | 沿用/补新引擎项 | 每个功能有适用配置、帮助、真实生效回执；中文portable、不临时释放系统文件 |
| `--tls-startup-padding`、质量显示/报告、keepalive配置 | 沿用用户可见语义 | 有限启动填充仍仅适用原条件，不变成稳态大padding；2s显示快照不强迫固定周期wire包，控制包不刷新payload idle |
| WFP/Wintun/Npcap安装、DNS/分流/IPv6、崩溃恢复 | 沿用正在收尾方案 | 不在 Rust 重写注册表/驱动管理；由原仓库完成后精确移植 |
| Linux安装、服务化、配置加载 | 沿用简易方案 | 用户已明确不要复杂在线升级；引擎库与程序一起打包 |

## 原项目尚未关闭，不能靠重构抹掉

| 项目 | 读取时状态 | 本轮处理 |
|---|---|---|
| N4 Windows原生网络/恢复及运行时去脚本 | a7a82主基线+6ec6b583固定donor的12文件增量；现成Go API/WAL复用，正式CLI/GUI接线仍待做 | PLAN-010由M4限域导入及接线，M0提供Stop/CI/集成；不再无限等待旧仓库。ghost MTU恢复UNSUPPORTED、WFP生产门/真实全网络NOT_RUN保留 |
| N2 auto FEC C04/C05效率、C10 GE p99 | OPEN | 策略先复用，R5 回归；必要修复单独来源与资格 |
| N3 AES 更广弱网/CPU/native | scoped PASS，不全面 | R3/R5 补矩阵 |
| N5 GUI 实际驱动质量、N6整包 | 未全部完成/NOT_STARTED | R6 接入，不重写UI |
| MTU实际大包压力、持续UDP/TCP | 功能已改，压力仍待确认 | R5 特殊包矩阵，控制合法拒绝而非强求高损必达 |
| 旧80s下行中断 | OPEN_DEFERRED | 按用户意图优化后 R6 专项；序号回绕/单向黑洞均只是待查假设 |

旧补丁导入流程：列原仓库完整 SHA、目标路径、依赖和旧 scoped 证据→审核与Rust接口冲突→移入/适配→组合测试。不能拉一份最新旧项目全覆盖新引擎，也不能把旧CPU结果当Rust资格。

R0从原 `docs/PARAMETERS.json` 导入当时有效配置为单一迁移账本，逐项标 reuse/adapter/new/deferred 和CLI/配置/UI适用面；包括服务端按客户端接受cipher/FEC意图、Normal上下行auto独立、Game固定档、lane随机rotation区间、idle宽松余量、DNS/分流/IPv6默认值。不能仅移植本表列的源码而漏掉用户已有开关。旧参数重命名需要读取兼容/明确迁移说明；不悄悄改变默认值。

2026-10-23 MTU定向增量：Linux公开V4两端 `--outer-mtu` 默认1500，内层TUN按封装/MSS/已认证双端record限制自动推导，见 [容量/MTU规则§3](../testing/NETWORK_CAPACITY_ENVELOPE.md#3-内层mtu随外层配置自动计算)。适用CLI/help与启动 `V4_PUBLIC_MTU` readback；Windows CLI/GUI另一路由M0迁入同语义，当前未声明接线或PASS。Auto不逐档改变TUN，LINK分片不向所有正常包重复收取头开销。

## 阶段与退出条件

| 阶段 | 有界交付 | 必要验证；达到即进入下一步 |
|---|---|---|
| **R0 接口与基线** | 固定 legacy source/toolchain/deps；最小 C ABI/handle/clock/wire golden；编译一次的产物约定；参数迁移清单 | 三目标能构建旧控制+空数据接口；Go↔C ABI布局/错误/停止回执；旧夹具短lossless能校准。没有空壳性能宣称 |
| **R1 Normal/off 纵向切片** | 一条 lane 从真实 TUN/raw 到交付；独立 AEAD；slab/ready批处理；无重传也能全路径工作 | lossless 混合大小/单向双向/稀疏、MTU边界、payload校验；旧新同 job配对CPU/p99，无HOL定向。不先加FEC掩盖I/O问题 |
| **R2 有界恢复** | ACK/receipt分离、2次修复、预算/稀疏例外、cache/timewheel | 1/5% IID、reorder、反馈损失、稀疏尾包；10/30%预算失效可控；seq/PN wrap及迟到/evict正确 |
| **R3 FEC** | FEC v2 ISA-L/标量/新规范互验证、partial/短期限/有界生命周期；fixed/auto接口 | 新专项功能/三目标/同机组件及真实交付成本，off短路径保护；旧冻结源码只作精确范围对照，不为V2制造旧生产互通栈 |
| **R4 Game共享链** | 2/4lane共享编码/恢复、独立AEAD、无慢lane前置屏障 | 独立/相关loss、慢lane/失效lane、rotation重叠、首到去重；3Mbps/方向锚点；CPU改善与f模型对应 |
| **R5 全配置与容量** | Auto普通/激进、AES三套、路径MTU、DNS/分流等组合；高效覆盖矩阵 | TEST_PLAN覆盖账本、容量阶梯及停止记录；所有配置实际生效；仅对证据有争议的性能增补反向配对 |
| **R6 组合交付前** | 导入旧N4/N5/N6收尾、打包、长测、80s专项、固定SOURCE | Actions真实可用能力全部完成；native-only明确列NOT_RUN，产物hash。用户另行安排物理；不能仅靠Rust重构宣称历史中断已解决 |

阶段按依赖推进，编码工作可并行但集成验收不得跳级。某优化达不到收益先测占比；两次同因失败后缩小复现，禁止换seed刷绿或无限改微优化。第一版不做WS、AF_XDP必选、跨进程RPC、自造TLS/密码库、备用lane延迟解密、全能插件系统。

## 并行界面（由M0激活后才有效）

- **M0**：共享 `types`/C ABI/wire版本、root deps、Go接入契约、构建/测量夹具、最终合并。R0先写真实最小契约，避免M1–M4各造接口。
- **M1**：engine ownership、slab/队列/时钟、Normal/Game pipeline/发送调度；不私改recover/codec算法。
- **M2**：receipt解析/丢失推断/shadow/预算/到期；输入纯事件，输出修复候选/释放事件；不得在模块里直接发socket或阻塞fresh。
- **M3**：codec/LINK/FEC/AEAD与golden；输入借用slice/ownedhandle、输出受界结果；不内建线程池/系统计时器，计时由owner提供。
- **M4**：platform driver批量接口、Go冷层adapter、portable装配和旧功能迁移；不改变业务调度策略。

最小事件：`BufferHandle`、`LaneKey(session,generation,lane)`、`SendCompletion(actual_bytes,time)`、`ReceiptDelta`、`RecoveryCandidate(frozen_handle,deadline)`、`FecShard`、`Delivery(first_id,handle)`、`EffectiveConfigSnapshot`。完整字段在R0的类型文件/契约中单一维护，文档不复制另一套ABI。

角色固定提示词在 `docs/prompts/`。执行测试必须标角色/request、唯一SOURCE/config/harness；新 agent 先恢复漏记再开发。阶段总结只保留当前契约、证据索引、未解决项、下一动作，长原始记录归档不塞入口。已完成任务无须每天再复读。
