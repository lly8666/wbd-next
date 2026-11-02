# 老功能产品化接续｜PLAN028–030总入口

2026-11-02用户授权准备后续方案，**本页028–030仅PLANNED，不切换当前registry任务（目前PLAN027A），不dispatch产品测试**。PLAN027已限定范围收口，历史NOT_RUN不重开旧矩阵。实际开工由用户调用对应M0提示词或按完整序列授权推进；届时M0在现有registry/cursor记录当前包，不另建任务系统。真实业务首到、无跨流HOL、低CPU优先；原认证/完整性/隔离/generation/固定密文/MTU/owned Stop硬门不变。

## 1. 三包与依赖

前置新增：[PLAN027A MTU统一](M0-PLAN027A-MTU-UNIFICATION-20261102.md) / [开工提示词](../prompts/M0-PLAN027A.md)。次序为027→027A→028；本页三包复用[唯一MTU契约](../architecture/MTU_CONTRACT.md)，不重新推导。已实现与SOURCE资格仍动态核，不为了先后顺序重复测试同一未变边界。

跨包配置约定：用户填的MTU始终是外层完整IP上限（默认1460、不含L2，显式最大1500仍可用）；内层TUN自动派生且只读展示。028传递/安装、029 UI/填充、030 server菜单均沿同一意图与effective快照，不增加手填内层参数。

| 包 | 只做这些增量 | 提示词 |
|---|---|---|
| [PLAN028](M0-PLAN028-SESSION-CONFIG-20261102.md) | 简化认证、自动IP、多客户端单端口/独立配置；各模式换lane；公共切网恢复与Windows/Linux通知接线 | [M0-PLAN028](../prompts/M0-PLAN028.md) |
| [PLAN029](M0-PLAN029-CLIENT-DNS-PADDING-20261102.md) | 服务端域名解析不被自身DNS劫持、Windows配置/UI接入、有限新流填充 | [M0-PLAN029](../prompts/M0-PLAN029.md) |
| [PLAN030](M0-PLAN030-SERVER-CLI-DELIVERY-20261102.md) | 最小服务端配置、中文wbd-next管理CLI、持久服务化/完整卸载、组合交付 | [M0-PLAN030](../prompts/M0-PLAN030.md) |

**先冻结028配置/会话接口，再并行029与030独立部分；集成与正式客户端测试依赖028实际接通。**生命周期、FEC、重传、加密数学不分别重新实现。总入口只管范围，进度只写既有cursor/devlog/evidence；每次接手读总入口+当前一包，不先读三包全部历史。

网络切换范围由028§4.1–4.2统一：现在落公共会话续接/路径事件和Windows/Linux客户端接线，保留内网IP、重认证/重算MTU、休眠不唤醒；Android只在后续客户端阶段接平台网络回调、socket绑定/VPN旁路及Wi-Fi/蜂窝真机验证。不新增第二个控制器，不要求现在提前完成Android。

## 2. 不重复PLAN027，未通过也不当作已完成

初审 `59f00500` / H867，推送前增量核到 `0d6ba006` / H870；开工必须刷新。证据仅其SOURCE/范围有效：

| 既有领域 | 已有证据/边界 | 本轮处理 |
|---|---|---|
| 稳态Rust、FEC2/SIMD、Game共享链、path MTU | 已有实现和多场景资格 | 直接用当前主线，不迁回Go热泵/RS20/旧包头/固定1280帽 |
| 去线上M2、低频质量/Health、Normal重传 | PLAN027已有成果，重传成本及Windows OFF等仍按当前任务收口 | 不另立算法/调优包，不复活旧A5 Go稳态比较 |
| Normal300s混合业务 | SOURCE3776 H866有Linux限定PASS，**未观测key rotation** | 不能拿它替代本轮各模式真实换lane |
| Game4最高FEC ON20M/250ms/30% | SOURCE3776 H866有Linux限定PASS；F/R/C全线速比例、Windows不在范围 | 不重刷整张弱网矩阵，新增会话适配才做受影响回归 |
| idle/Health/单双向黑洞 | H870已收SOURCE b747单双向105s恢复限定PASS；旧SOURCE377单向约64s停顿、b747另一条无产物的负面观察仍保留。Windows新退休接收接线尚未合格 | 复用已验实现；未决项归027，不在028–030复制第二个恢复器，也不把限定通过扩大 |
| 各模式换lane、Windows一些真实入口 | H870仍OPEN | 本轮做配置/多客户端集成资格；027若后来已有等价证据则扣除，不双重开工 |
| DNS/GUI/portable等 | 老Go实现与部分新路径证据并存，功能卡可能滞后 | 只核旧参数到新effective路径的缺口，不按过时卡片重做整套 |

引用：[Normal300s](../evidence/M0/PLAN027-H866-3776-NORMAL-ON300-MIXED-HOL-20261102.json)、[Game4](../evidence/M0/PLAN027-H866-3776-GAME4FEC6-ON20M30-20261102.json)、[旧单向失败](../evidence/M0/PLAN027-H863-3776-UNILATERAL105-2M-FAIL-20261102.json)、[最新单双向恢复及保留负面](../devlog/M0/20261102-PLAN027-H870-COLLECT-NATIVE-LIFECYCLE.md)。迁移清单以实际代码及精确证据为准，不把“老版测过”升级为新实现PASS。

## 3. 成熟逻辑与参数：继承，不另搞方案比赛

固定老参考 `wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`，通过现有overlay/装配读取，**不替换新数据面**。先读相关实现/反例，再最小接线；当前主线修复优先于旧实现。

| 逻辑 | 参考位置/已核默认 | 规则 |
|---|---|---|
| Health/dead/退避 | `internal/runtimeentry/lifecycle_health.go`：15s/90s、失败退避1–30s；`runtimeowner/health.go`缺Health为UNKNOWN | 保留当前约±10%抖动及质量合并，不新增固定探针；dead≥3个keepalive周期 |
| idle/rotation | `runtimeentry/lifecycle.go`、`lifecycle_business_rotation_test.go`；旧ReplacementGrace默认3s；旧CLI idle/rotate默认0禁用 | 不误把用户试用的idle120s、rotation5–10min当所有人的新默认；作为试用预设/验收配置。新lane ready后退旧，业务到达优先 |
| 会话/IP | `logicaltunnel/lease_registry.go`、`runtimeentry/automatic_lease_test.go`、`realityfront/automatic_lease_test.go` | 非持久自动IP、7天租约、活动续租，复用地址隔离 |
| 网络/UI | `windowsclient/router.go`、`direct_udp_windows.go`、原configfile/GUI、`docs/PARAMETERS.json` | 原生owned网络管理；TUN分流，不写大量前缀路由；参数一处定义 |
| padding | `datapath/startup_padding.go`：256流、2s启动窗口、12record、2048B/流，旧默认off | 保留有限/无等待；029扩触发且去掉无必要TLS前缀重组 |
| 服务部署 | `deploy/linux/wbdctl`、`wbd-server.service`、`server.example.json` | 只搬配置/服务/owned恢复语义，不搬升级回滚中心 |

老参数入口：[PARAMETERS](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/docs/PARAMETERS.json)。不因“省CPU”删身份/generation、接收去重或篡改原密文；不为菜单重构稳态。

## 4. 可以怎样并行

- 028先一次明确配置schema/effective读回、session配置及EndpointResolver输入输出、只读ClientSnapshot；这是接口说明与必要最小代码，不是造通用框架。
- 028的认证/多客户端接线、029的DNS直出解析、030的服务CLI可以在各自模块开发；029填充仅在028流/record归属接口明确后实现。030先菜单/包配置功能测试，再接真实多客户端，不拿假session当产品验收。
- 共享auth/ABI/配置schema、生命周期、Windows WAL同一时间只有一个作者；改动由M0串行合入main。独立agent仅按另授路径工作，不因本表自动复活M1–M4。单M0也能等待Actions时推进独立模块。
- 一Action一场景测量进程/job，双端和多客户端是场景所需进程；各场景独立Actions并行，构建按SOURCE/目标平台/hash一次复用。同VM新旧或ON/OFF对照顺序运行，不争机器。
- 整个紧密关联工作包代码/调用方/配置/帮助/UI/夹具写齐再测；不每helper起Action，不把三包全部未验代码堆到最后。

过渡只在必要接入口保留短期旧/新选择，一次会话只有一个owner/控制器，不双发、不双改路由、不恢复Go热泵。已有成熟模块直接复用，不为了“新老并存”复制一整套系统。相关新入口真实通过后，同包删掉被替代adapter与临时测试开关；旧证据/回退提交留Git，不能把长期双轨维护算迁移完成。

## 5. 合理验收和停止

低负载功能为主：Normal每方向约5–10Mbps，Game逻辑约3Mbps；真实Windows↔Linux与Linux arm64资格按受影响后端补。弱网只选0/5/30%代表，不重跑027的10–200M全矩阵。各模式换lane按028单独列全，不用长测时间或PID活着代替。

先算实际MTU/分片、k:r/相关损伤和生成器能力，再看first delivery/p99/timeout/CPU/owned Stop；高损不用零丢、一次换代成功等不合理门。容量不足停更重同族，单核锁问题仍属产品。修有实证的问题，最多一次必要反序对照；微小噪声/无收益即停，不防御式扩框架或重复验证成熟策略。

每个包达到其退出条件即登记完成并给下一包入口；仅启动了某包不自动宣称其他包完成。若用户启动整个028–030序列，则阶段结束自动推进已授权下一包，不再等逐步派单。所有scope保留精确SOURCE、FAIL/NOT_RUN，最终只有配置到真正IO的完整链路通过才交付。旧独立CLI提案已撤出活动目录，内容由030吸收，历史见[b1aaf8d0版](https://github.com/lly8666/wbd-next/blob/b1aaf8d00d2aaa76d743eaedbd6579a8ea4c7204/docs/decisions/M0-SERVER-CLI-SIMPLIFICATION-20261102.md)。
